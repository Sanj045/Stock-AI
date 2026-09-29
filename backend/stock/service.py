from datetime import datetime, timedelta
from functools import lru_cache
from threading import RLock
import time

import pandas as pd
from bs4 import BeautifulSoup

from vnstock import Market, Reference, Fundamental

from logger import logger


market = Market()
reference = Reference()
fundamental = Fundamental()


# =========================================================
# CACHE CONFIG
# =========================================================

# Giá gần nhất thay đổi thường xuyên hơn.
LATEST_CACHE_TTL_SECONDS = 60

# Fundamentals thay đổi chậm.
FUNDAMENTALS_CACHE_TTL_SECONDS = 30 * 60

# News thay đổi thường xuyên nhưng không cần gọi mỗi request.
NEWS_CACHE_TTL_SECONDS = 5 * 60


_cache_lock = RLock()

_latest_cache = {}
_fundamentals_cache = {}
_news_cache = {}

_CACHE_MISS = object()


def _copy_cached_value(value):
    """
    Trả về bản copy của DataFrame / Series để code bên ngoài
    không thể sửa trực tiếp object đang nằm trong cache.
    """

    if isinstance(
        value,
        (pd.DataFrame, pd.Series)
    ):
        return value.copy(
            deep=True
        )

    return value


def _get_ttl_cache(
    cache: dict,
    key,
    ttl_seconds: int
):
    """
    Lấy dữ liệu từ TTL cache.

    Nếu chưa có hoặc đã hết hạn thì trả về _CACHE_MISS.
    """

    now = time.monotonic()

    with _cache_lock:
        cached_item = cache.get(
            key
        )

        if cached_item is None:
            return _CACHE_MISS

        cached_at, value = cached_item

        if (
            now - cached_at
            >= ttl_seconds
        ):
            cache.pop(
                key,
                None
            )

            return _CACHE_MISS

        return _copy_cached_value(
            value
        )


def _set_ttl_cache(
    cache: dict,
    key,
    value
):
    """
    Lưu dữ liệu vào TTL cache.
    """

    with _cache_lock:
        cache[key] = (
            time.monotonic(),
            _copy_cached_value(
                value
            )
        )


def clear_stock_caches():
    """
    Xóa toàn bộ cache stock trong RAM.

    Có thể dùng khi cần debug hoặc muốn ép backend
    lấy dữ liệu mới ngay lập tức.
    """

    with _cache_lock:
        _latest_cache.clear()
        _fundamentals_cache.clear()
        _news_cache.clear()

    _get_company_info_cached.cache_clear()

    logger.info(
        "Stock caches cleared"
    )


# =========================================================
# STOCK PRICE HISTORY
# =========================================================

def get_stock_history(
    symbol: str,
    start: str,
    end: str,
    interval: str = "1D"
):
    symbol = symbol.strip().upper()

    # History chưa cache vì start/end/interval
    # có rất nhiều tổ hợp khác nhau.
    return market.equity(
        symbol
    ).ohlcv(
        start=start,
        end=end,
        interval=interval
    )


# =========================================================
# LATEST STOCK PRICE
# =========================================================

def get_latest_stock(
    symbol: str
):
    symbol = symbol.strip().upper()

    cache_key = symbol

    cached = _get_ttl_cache(
        _latest_cache,
        cache_key,
        LATEST_CACHE_TTL_SECONDS
    )

    if cached is not _CACHE_MISS:
        logger.debug(
            "Latest stock cache hit for %s",
            symbol
        )

        return cached

    logger.info(
        "Fetching latest stock data from Vnstock for %s",
        symbol
    )

    today = datetime.now().date()

    start_date = (
        today
        - timedelta(days=14)
    )

    data = market.equity(
        symbol
    ).ohlcv(
        start=start_date.strftime(
            "%Y-%m-%d"
        ),
        end=today.strftime(
            "%Y-%m-%d"
        ),
        interval="1D"
    )

    if data is None or data.empty:
        result = None

    else:
        result = (
            data
            .iloc[-1]
            .copy()
        )

    _set_ttl_cache(
        _latest_cache,
        cache_key,
        result
    )

    return _copy_cached_value(
        result
    )


# =========================================================
# COMPANY
# =========================================================

@lru_cache(maxsize=500)
def _get_company_info_cached(
    symbol: str
):
    logger.info(
        "Fetching company info from Vnstock for %s",
        symbol
    )

    return reference.company(
        symbol
    ).info()


def get_company_info(
    symbol: str
):
    symbol = symbol.strip().upper()

    data = _get_company_info_cached(
        symbol
    )

    if data is None:
        return None

    return data.copy(
        deep=True
    )


# =========================================================
# FUNDAMENTALS
# =========================================================

def get_financial_ratios(
    symbol: str,
    period: str = "quarter"
):
    symbol = symbol.strip().upper()

    period = (
        period
        .strip()
        .lower()
    )

    cache_key = (
        symbol,
        period
    )

    cached = _get_ttl_cache(
        _fundamentals_cache,
        cache_key,
        FUNDAMENTALS_CACHE_TTL_SECONDS
    )

    if cached is not _CACHE_MISS:
        logger.debug(
            "Fundamentals cache hit for %s period=%s",
            symbol,
            period
        )

        return cached

    logger.info(
        "Fetching fundamentals from Vnstock for %s period=%s",
        symbol,
        period
    )

    data = fundamental.equity(
        symbol
    ).ratio(
        period=period
    )

    if data is None or data.empty:
        _set_ttl_cache(
            _fundamentals_cache,
            cache_key,
            data
        )

        return data

    data = data.copy()

    # Vnstock có thể trả về cột bị thêm suffix "_1".
    # Không xóa vì đã xác nhận một số giá trị khác nhau.
    # Chỉ đổi tên thành "_alt" để tránh hiểu nhầm.
    renamed_columns = {}

    for column in data.columns:
        if column.endswith(
            "_1"
        ):
            renamed_columns[
                column
            ] = (
                column.removesuffix(
                    "_1"
                )
                + "_alt"
            )

    if renamed_columns:
        data = data.rename(
            columns=renamed_columns
        )

    _set_ttl_cache(
        _fundamentals_cache,
        cache_key,
        data
    )

    return data.copy(
        deep=True
    )


# =========================================================
# NEWS HELPERS
# =========================================================

def _clean_text(
    value,
    max_length: int = 400
):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None

    except (
        TypeError,
        ValueError
    ):
        pass

    text = str(
        value
    ).strip()

    if not text:
        return None

    # Xóa HTML nếu source trả HTML.
    text = BeautifulSoup(
        text,
        "html.parser"
    ).get_text(
        " ",
        strip=True
    )

    # Gộp khoảng trắng thừa.
    text = " ".join(
        text.split()
    )

    if not text:
        return None

    if len(text) > max_length:
        text = (
            text[
                :max_length
            ].rstrip()
            + "..."
        )

    return text


def _first_valid_text(
    *values,
    max_length: int = 400
):
    for value in values:
        cleaned = _clean_text(
            value,
            max_length=max_length
        )

        if cleaned:
            return cleaned

    return None


# =========================================================
# NEWS NORMALIZATION
# =========================================================

def _normalize_kbs_news(
    data: pd.DataFrame
):
    urls = []

    for value in data["url"]:
        if value is None:
            urls.append(
                None
            )
            continue

        try:
            if pd.isna(value):
                urls.append(
                    None
                )
                continue

        except (
            TypeError,
            ValueError
        ):
            pass

        value = str(
            value
        ).strip()

        if not value:
            urls.append(
                None
            )

        elif value.startswith(
            (
                "http://",
                "https://"
            )
        ):
            urls.append(
                value
            )

        elif value.startswith(
            "/"
        ):
            urls.append(
                "https://www.kbsec.com.vn"
                + value
            )

        else:
            urls.append(
                value
            )

    normalized = pd.DataFrame({
        "article_id": data[
            "article_id"
        ],
        "title": data[
            "title"
        ],
        "summary": None,
        "publish_time": data[
            "publish_time"
        ],
        "url": urls,
        "image_url": None,
        "source": "KBS"
    })

    normalized[
        "summary_available"
    ] = False

    normalized[
        "url_available"
    ] = (
        normalized["url"]
        .notna()
        & normalized["url"]
        .astype(str)
        .str.strip()
        .ne("")
    )

    return normalized


def _normalize_vci_news(
    data: pd.DataFrame
):
    titles = []
    summaries = []

    for _, row in data.iterrows():
        title = _first_valid_text(
            row.get(
                "news_title"
            ),
            row.get(
                "friendly_title"
            ),
            max_length=300
        )

        summary = _first_valid_text(
            row.get(
                "news_short_content"
            ),
            row.get(
                "news_sub_title"
            ),
            row.get(
                "friendly_sub_title"
            ),
            row.get(
                "news_full_content"
            ),
            max_length=400
        )

        titles.append(
            title
        )

        summaries.append(
            summary
        )

    normalized = pd.DataFrame({
        "article_id": data[
            "news_id"
        ],
        "title": titles,
        "summary": summaries,
        "publish_time": data[
            "public_date"
        ],
        "url": data[
            "news_source_link"
        ],
        "image_url": data[
            "news_image_url"
        ],
        "source": "VCI"
    })

    normalized[
        "summary_available"
    ] = (
        normalized["summary"]
        .notna()
        & normalized["summary"]
        .astype(str)
        .str.strip()
        .ne("")
    )

    normalized[
        "url_available"
    ] = (
        normalized["url"]
        .notna()
        & normalized["url"]
        .astype(str)
        .str.strip()
        .ne("")
    )

    return normalized


# =========================================================
# NEWS
# =========================================================

def get_stock_news(
    symbol: str,
    sources: list[str] | None = None,
    limit: int = 10
):
    symbol = symbol.strip().upper()

    # -----------------------------------------------------
    # Normalize sources
    # -----------------------------------------------------

    if sources is None:
        normalized_source_names = [
            "KBS",
            "VCI"
        ]

    else:
        normalized_source_names = []

        for source in sources:
            source = (
                source
                .strip()
                .upper()
            )

            if (
                source
                and source
                not in normalized_source_names
            ):
                normalized_source_names.append(
                    source
                )

    limit = max(
        1,
        min(
            limit,
            50
        )
    )

    # sources phải chuyển thành tuple để dùng làm cache key.
    cache_key = (
        symbol,
        tuple(
            normalized_source_names
        ),
        limit
    )

    cached = _get_ttl_cache(
        _news_cache,
        cache_key,
        NEWS_CACHE_TTL_SECONDS
    )

    if cached is not _CACHE_MISS:
        logger.debug(
            "News cache hit for %s sources=%s limit=%s",
            symbol,
            normalized_source_names,
            limit
        )

        return cached

    logger.info(
        "Fetching stock news from Vnstock for %s sources=%s",
        symbol,
        normalized_source_names
    )

    normalized_sources = []

    # -----------------------------------------------------
    # Fetch và normalize từng source
    # -----------------------------------------------------

    for source in normalized_source_names:
        try:
            data = reference.company(
                symbol
            ).news(
                source=source
            )

            if (
                data is None
                or data.empty
            ):
                continue

            if source == "KBS":
                normalized = (
                    _normalize_kbs_news(
                        data
                    )
                )

            elif source == "VCI":
                normalized = (
                    _normalize_vci_news(
                        data
                    )
                )

            else:
                continue

            normalized[
                "publish_time"
            ] = pd.to_datetime(
                normalized[
                    "publish_time"
                ],
                errors="coerce"
            )

            # Bỏ row không có title.
            normalized = (
                normalized
                .dropna(
                    subset=[
                        "title"
                    ]
                )
            )

            normalized = normalized[
                normalized[
                    "title"
                ]
                .astype(str)
                .str.strip()
                .ne("")
            ]

            normalized = (
                normalized
                .sort_values(
                    by="publish_time",
                    ascending=False,
                    na_position="last"
                )
            )

            normalized_sources.append(
                normalized
            )

        except Exception as exc:
            logger.warning(
                "News source %s failed for %s: %s",
                source,
                symbol,
                exc
            )

    if not normalized_sources:
        result = pd.DataFrame()

        _set_ttl_cache(
            _news_cache,
            cache_key,
            result
        )

        return result

    # -----------------------------------------------------
    # Chia quota ban đầu cho từng nguồn
    # -----------------------------------------------------

    source_count = len(
        normalized_sources
    )

    quota_per_source = max(
        1,
        limit
        // source_count
    )

    selected_frames = []
    remaining_frames = []

    for frame in normalized_sources:
        selected_frames.append(
            frame.head(
                quota_per_source
            )
        )

        remaining_frames.append(
            frame.iloc[
                quota_per_source:
            ]
        )

    selected = pd.concat(
        selected_frames,
        ignore_index=True
    )

    # -----------------------------------------------------
    # Loại tin trùng ở phần đã chọn
    # -----------------------------------------------------

    selected = (
        selected
        .drop_duplicates(
            subset=[
                "title",
                "publish_time"
            ],
            keep="first"
        )
    )

    # -----------------------------------------------------
    # Nếu chưa đủ limit thì lấy thêm từ remaining
    # -----------------------------------------------------

    if (
        len(selected)
        < limit
    ):
        remaining = pd.concat(
            remaining_frames,
            ignore_index=True
        )

        if not remaining.empty:
            remaining = (
                remaining
                .drop_duplicates(
                    subset=[
                        "title",
                        "publish_time"
                    ],
                    keep="first"
                )
            )

            remaining = (
                remaining
                .sort_values(
                    by="publish_time",
                    ascending=False,
                    na_position="last"
                )
            )

            existing_keys = set(
                zip(
                    selected[
                        "title"
                    ],
                    selected[
                        "publish_time"
                    ]
                )
            )

            extra_rows = []

            for _, row in remaining.iterrows():
                key = (
                    row["title"],
                    row["publish_time"]
                )

                if (
                    key
                    in existing_keys
                ):
                    continue

                extra_rows.append(
                    row
                )

                existing_keys.add(
                    key
                )

                if (
                    len(selected)
                    + len(extra_rows)
                    >= limit
                ):
                    break

            if extra_rows:
                selected = pd.concat(
                    [
                        selected,
                        pd.DataFrame(
                            extra_rows
                        )
                    ],
                    ignore_index=True
                )

    # -----------------------------------------------------
    # Sort cuối cùng
    # -----------------------------------------------------

    selected = (
        selected
        .sort_values(
            by="publish_time",
            ascending=False,
            na_position="last"
        )
    )

    selected = selected.head(
        limit
    )

    selected = (
        selected
        .reset_index(
            drop=True
        )
    )

    # -----------------------------------------------------
    # Timestamp -> JSON string
    # -----------------------------------------------------

    selected[
        "publish_time"
    ] = (
        selected[
            "publish_time"
        ]
        .dt.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
    )

    # -----------------------------------------------------
    # NaN / NaT -> None
    # -----------------------------------------------------

    selected = (
        selected
        .astype(object)
        .where(
            pd.notna(
                selected
            ),
            None
        )
    )

    # -----------------------------------------------------
    # Save TTL cache
    # -----------------------------------------------------

    _set_ttl_cache(
        _news_cache,
        cache_key,
        selected
    )

    return selected.copy(
        deep=True
    )