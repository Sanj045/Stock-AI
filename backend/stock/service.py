from concurrent.futures import ThreadPoolExecutor, as_completed



from datetime import datetime, timedelta



from functools import lru_cache



import ipaddress



import socket



from threading import RLock



import time



from urllib.parse import urljoin, urlparse







import httpx



import pandas as pd



from bs4 import BeautifulSoup







from vnstock import Market, Reference, Fundamental







from logger import logger

from ai.news_evidence import (
    clear_news_evidence_cache,
    resolve_news_evidence,
)











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





# Kết quả kiểm tra link nguồn có thể cache lâu hơn news list.

NEWS_URL_VERIFY_CACHE_TTL_SECONDS = 30 * 60



# Timeout ngắn để một website lỗi không giữ request quá lâu.

NEWS_URL_VERIFY_TIMEOUT_SECONDS = 4.0



NEWS_URL_VERIFY_MAX_REDIRECTS = 5



NEWS_URL_VERIFY_WORKERS = 6











_cache_lock = RLock()







_latest_cache = {}



_fundamentals_cache = {}



_news_cache = {}

_news_url_verification_cache = {}







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



        _news_url_verification_cache.clear()







    _get_company_info_cached.cache_clear()








    clear_news_evidence_cache()
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







    # Chỉ parse khi text thực sự giống HTML.
    # URL thuần không được đưa vào BeautifulSoup để tránh
    # MarkupResemblesLocatorWarning.

    if "<" in text and ">" in text:

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



# NEWS URL VERIFICATION



# =========================================================





def _get_cached_news_url_verification(

    url: str

):

    now = time.monotonic()



    with _cache_lock:

        cached_item = (

            _news_url_verification_cache

            .get(url)

        )



        if cached_item is None:

            return _CACHE_MISS



        cached_at, verified_url = (

            cached_item

        )



        if (

            now - cached_at

            >= NEWS_URL_VERIFY_CACHE_TTL_SECONDS

        ):

            _news_url_verification_cache.pop(

                url,

                None

            )



            return _CACHE_MISS



        return verified_url





def _set_cached_news_url_verification(

    url: str,

    verified_url: str | None

):

    with _cache_lock:

        _news_url_verification_cache[url] = (

            time.monotonic(),

            verified_url

        )





def _is_public_http_url(

    url: str

):

    try:

        parsed = urlparse(url)

    except ValueError:

        return False



    if parsed.scheme.lower() not in {

        "http",

        "https"

    }:

        return False



    hostname = parsed.hostname



    if not hostname:

        return False



    hostname = hostname.strip().lower()



    if hostname in {

        "localhost",

        "localhost.localdomain"

    }:

        return False



    try:

        addresses = socket.getaddrinfo(

            hostname,

            parsed.port,

            type=socket.SOCK_STREAM

        )

    except (

        socket.gaierror,

        OSError

    ):

        return False



    for address_info in addresses:

        raw_ip = address_info[4][0]



        try:

            ip = ipaddress.ip_address(

                raw_ip

            )

        except ValueError:

            return False



        if (

            ip.is_private

            or ip.is_loopback

            or ip.is_link_local

            or ip.is_multicast

            or ip.is_reserved

            or ip.is_unspecified

        ):

            return False



    return True





def _probe_news_url(

    client: httpx.Client,

    url: str,

    method: str

):

    try:

        with client.stream(

            method,

            url,

            follow_redirects=False

        ) as response:

            return (

                response.status_code,

                response.headers.get(

                    "location"

                )

            )



    except (

        httpx.HTTPError,

        OSError

    ):

        return None, None





def _verify_news_url_uncached(

    url: str

):

    current_url = url



    headers = {

        "User-Agent": (

            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

            "AppleWebKit/537.36 (KHTML, like Gecko) "

            "Chrome/124.0 Safari/537.36"

        ),

        "Accept": (

            "text/html,application/xhtml+xml,"

            "application/xml;q=0.9,*/*;q=0.8"

        )

    }



    timeout = httpx.Timeout(

        NEWS_URL_VERIFY_TIMEOUT_SECONDS

    )



    try:

        with httpx.Client(

            timeout=timeout,

            headers=headers

        ) as client:

            for _ in range(

                NEWS_URL_VERIFY_MAX_REDIRECTS

                + 1

            ):

                if not _is_public_http_url(

                    current_url

                ):

                    return None



                status_code, location = (

                    _probe_news_url(

                        client,

                        current_url,

                        "HEAD"

                    )

                )



                # Nhiều website không hỗ trợ HEAD.

                # Khi HEAD lỗi, thử GET nhưng chỉ đọc headers.

                if (

                    status_code is None

                    or status_code >= 400

                ):

                    status_code, location = (

                        _probe_news_url(

                            client,

                            current_url,

                            "GET"

                        )

                    )



                if status_code is None:

                    return None



                if 200 <= status_code < 300:

                    return current_url



                if (

                    300 <= status_code < 400

                    and location

                ):

                    current_url = urljoin(

                        current_url,

                        location

                    )

                    continue



                return None



    except (

        httpx.HTTPError,

        OSError,

        ValueError

    ):

        return None



    return None





def _verify_news_url(

    value

):

    cleaned_url = _clean_text(

        value,

        max_length=2000

    )



    if not cleaned_url:

        return None



    cached = (

        _get_cached_news_url_verification(

            cleaned_url

        )

    )



    if cached is not _CACHE_MISS:

        return cached



    verified_url = (

        _verify_news_url_uncached(

            cleaned_url

        )

    )



    _set_cached_news_url_verification(

        cleaned_url,

        verified_url

    )



    return verified_url





def _filter_verified_news_urls(

    data: pd.DataFrame,

    max_candidates: int

):

    if data is None or data.empty:

        return pd.DataFrame()



    candidates = data.copy()



    candidates = candidates[

        candidates["url"]

        .notna()

    ]



    candidates = candidates[

        candidates["url"]

        .astype(str)

        .str.strip()

        .ne("")

    ]



    if candidates.empty:

        return candidates



    candidates = (

        candidates

        .head(max_candidates)

        .copy()

    )



    verified_urls = {}



    unique_urls = list(

        dict.fromkeys(

            candidates["url"]

            .astype(str)

            .tolist()

        )

    )



    worker_count = min(

        NEWS_URL_VERIFY_WORKERS,

        max(1, len(unique_urls))

    )



    with ThreadPoolExecutor(

        max_workers=worker_count

    ) as executor:

        future_to_url = {

            executor.submit(

                _verify_news_url,

                url

            ): url

            for url in unique_urls

        }



        for future in as_completed(

            future_to_url

        ):

            url = future_to_url[future]



            try:

                verified_urls[url] = (

                    future.result()

                )

            except Exception as exc:

                logger.debug(

                    "News URL verification failed for %s: %s",

                    url,

                    exc

                )

                verified_urls[url] = None



    candidates["url"] = (

        candidates["url"]

        .astype(str)

        .map(verified_urls)

    )



    candidates = candidates[

        candidates["url"]

        .notna()

    ]



    if candidates.empty:

        return candidates



    candidates["url_available"] = True

    candidates["url_verified"] = True



    return candidates







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







def _news_publish_time_to_iso(
    value
) -> str | None:
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

    if isinstance(
        value,
        pd.Timestamp
    ):
        if pd.isna(value):
            return None

        return value.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    if isinstance(
        value,
        datetime
    ):
        return value.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    text = str(
        value
    ).strip()

    return (
        text
        or None
    )


def _build_balanced_news_candidate_pool(
    normalized_sources: list[pd.DataFrame],
    max_candidates: int
) -> pd.DataFrame:
    if not normalized_sources:
        return pd.DataFrame()

    max_candidates = max(
        1,
        max_candidates
    )

    rows = []
    seen_keys = set()

    max_rows_in_source = max(
        len(frame)
        for frame in normalized_sources
    )

    # Round-robin giữa các nguồn để KBS / VCI đều có cơ hội
    # xuất hiện trong candidate pool trước khi resolve evidence.
    for row_index in range(
        max_rows_in_source
    ):
        for frame in normalized_sources:
            if row_index >= len(frame):
                continue

            row = frame.iloc[
                row_index
            ].copy()

            title = _clean_text(
                row.get(
                    "title"
                ),
                max_length=500
            )

            if not title:
                continue

            publish_time = (
                _news_publish_time_to_iso(
                    row.get(
                        "publish_time"
                    )
                )
            )

            key = (
                title.casefold(),
                publish_time
            )

            if key in seen_keys:
                continue

            seen_keys.add(
                key
            )

            rows.append(
                row
            )

            if len(rows) >= max_candidates:
                return pd.DataFrame(
                    rows
                ).reset_index(
                    drop=True
                )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        rows
    ).reset_index(
        drop=True
    )


def _resolve_news_row_evidence(
    symbol: str,
    row: pd.Series
) -> pd.Series | None:
    title = _clean_text(
        row.get(
            "title"
        ),
        max_length=500
    )

    if not title:
        return None

    publish_time = (
        _news_publish_time_to_iso(
            row.get(
                "publish_time"
            )
        )
    )

    original_url = _clean_text(
        row.get(
            "url"
        ),
        max_length=2000
    )

    original_source = _clean_text(
        row.get(
            "source"
        ),
        max_length=100
    )

    try:
        evidence = (
            resolve_news_evidence(
                symbol=symbol,
                title=title,
                publish_time=(
                    publish_time
                ),
                original_url=(
                    original_url
                ),
                original_source=(
                    original_source
                ),
            )
        )

    except Exception as exc:
        logger.warning(
            "News evidence resolution failed | "
            "symbol=%s | title=%s | error=%s",
            symbol,
            title[:120],
            exc
        )

        return None

    if (
        evidence is None
        or not evidence.verified
        or not evidence.url
    ):
        logger.info(
            "No verified evidence for news | "
            "symbol=%s | title=%s",
            symbol,
            title[:120]
        )

        return None

    resolved = row.copy()

    # Giữ lại provenance của Vnstock / KBS / VCI.
    resolved[
        "original_url"
    ] = original_url

    resolved[
        "original_source"
    ] = original_source

    # Evidence đã được direct verify hoặc Tavily + Gemini match
    # rồi HTTP verify trong ai.news_evidence.
    resolved[
        "evidence_url"
    ] = evidence.url

    resolved[
        "evidence_source"
    ] = evidence.source

    resolved[
        "evidence_method"
    ] = evidence.method

    resolved[
        "evidence_verified"
    ] = bool(
        evidence.verified
    )

    # Giữ backward compatibility cho frontend hiện tại:
    # url/source luôn trỏ tới nguồn evidence thật đang dùng.
    resolved[
        "url"
    ] = evidence.url

    resolved[
        "source"
    ] = evidence.source

    resolved[
        "url_available"
    ] = True

    resolved[
        "url_verified"
    ] = True

    return resolved


def get_stock_news(
    symbol: str,
    sources: list[str] | None = None,
    limit: int = 10
):
    symbol = (
        symbol
        .strip()
        .upper()
    )

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

    # Overfetch raw candidates vì một số tin có thể:
    # - không có URL gốc,
    # - URL gốc 404,
    # - Tavily không tìm được candidate phù hợp,
    # - Gemini từ chối tất cả candidate,
    # - evidence URL không verify được.
    max_candidates_per_source = min(
        50,
        max(
            10,
            limit * 4
        )
    )

    # -----------------------------------------------------
    # Fetch + normalize Vnstock sources
    # Không loại tin chỉ vì original URL thiếu / chết.
    # Resolver phía sau sẽ fallback sang Tavily.
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
                .head(
                    max_candidates_per_source
                )
                .reset_index(
                    drop=True
                )
            )

            if normalized.empty:
                continue

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
    # Candidate pool cân bằng giữa các nguồn
    # -----------------------------------------------------

    max_pool_size = min(
        50,
        max(
            12,
            limit * 4
        )
    )

    candidate_pool = (
        _build_balanced_news_candidate_pool(
            normalized_sources=(
                normalized_sources
            ),
            max_candidates=(
                max_pool_size
            )
        )
    )

    if candidate_pool.empty:
        result = pd.DataFrame()

        _set_ttl_cache(
            _news_cache,
            cache_key,
            result
        )

        return result

    # -----------------------------------------------------
    # Phase 4.6E4:
    # Direct original URL -> Tavily -> Gemini match -> verify.
    #
    # Chỉ những tin có evidence_verified=True mới được trả về.
    # Mỗi tin hiển thị vì thế đều có nguồn dẫn chứng thực.
    # -----------------------------------------------------

    resolved_rows = []

    for _, row in (
        candidate_pool.iterrows()
    ):
        resolved = (
            _resolve_news_row_evidence(
                symbol=symbol,
                row=row
            )
        )

        if resolved is None:
            continue

        resolved_rows.append(
            resolved
        )

        if len(
            resolved_rows
        ) >= limit:
            break

    if not resolved_rows:
        result = pd.DataFrame()

        _set_ttl_cache(
            _news_cache,
            cache_key,
            result
        )

        logger.info(
            "Verified stock news completed | "
            "symbol=%s | requested=%s | returned=0",
            symbol,
            limit
        )

        return result

    selected = pd.DataFrame(
        resolved_rows
    )

    selected = (
        selected
        .drop_duplicates(
            subset=[
                "title",
                "publish_time"
            ],
            keep="first"
        )
        .sort_values(
            by="publish_time",
            ascending=False,
            na_position="last"
        )
        .head(
            limit
        )
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

    logger.info(
        "Verified stock news completed | "
        "symbol=%s | requested=%s | returned=%s",
        symbol,
        limit,
        len(selected)
    )

    return selected.copy(
        deep=True
    )
