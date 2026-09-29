import json
import math
import time

from concurrent.futures import (
    Future,
    ThreadPoolExecutor
)

from datetime import (
    datetime,
    timedelta,
    timezone
)

from threading import RLock

import pandas as pd

from logger import logger

from stock.service import (
    get_stock_history,
    get_company_info,
    get_financial_ratios,
    get_stock_news
)


# =========================================================
# CONFIG
# =========================================================

STOCK_CONTEXT_MAX_WORKERS = 4

CONTEXT_SCHEMA_VERSION = "4.2"

MAX_BUSINESS_MODEL_LENGTH = 1200

RECENT_PRICE_SESSIONS = 30

HISTORY_LOOKBACK_CALENDAR_DAYS = 90


# =========================================================
# CACHE CONFIG
# =========================================================

PRICE_HISTORY_CACHE_TTL_SECONDS = 60

STOCK_CONTEXT_CACHE_TTL_SECONDS = 30


_price_history_cache = {}

_stock_context_cache = {}


_price_history_cache_lock = RLock()

_stock_context_cache_lock = RLock()


_CACHE_MISS = object()


IMPORTANT_FUNDAMENTAL_IDS = {
    "trailing_eps",
    "book_value_per_share_bvps",

    "pe_ratio",
    "pb_ratio",
    "ps_ratio",

    "dividend_yield",
    "beta",
    "ev_ebitda",

    "gross_margin",
    "ebit_margin",
    "ebitda_net_revenue",
    "net_margin",

    "roe_trailling",
    "roa_trailling",

    "net_revenue",
    "gross_profit",
}


# =========================================================
# CACHE HELPERS
# =========================================================

def _get_ttl_cache(
    cache: dict,
    lock: RLock,
    key,
    ttl_seconds: int
):
    now = time.monotonic()

    with lock:

        cached = cache.get(
            key,
            _CACHE_MISS
        )

        if cached is _CACHE_MISS:
            return _CACHE_MISS


        cached_at, value = cached


        if (
            now - cached_at
            >= ttl_seconds
        ):
            cache.pop(
                key,
                None
            )

            return _CACHE_MISS


        return value


def _set_ttl_cache(
    cache: dict,
    lock: RLock,
    key,
    value
):
    with lock:

        cache[
            key
        ] = (
            time.monotonic(),
            value
        )


def clear_stock_context_caches():
    """
    Clear tất cả cache thuộc stock/context.py.

    Cache này chỉ nằm trong RAM.
    Khi restart backend, cache cũng tự mất.
    """

    with _price_history_cache_lock:
        _price_history_cache.clear()

    with _stock_context_cache_lock:
        _stock_context_cache.clear()

    logger.info(
        "Stock context caches cleared"
    )


# =========================================================
# GENERAL HELPERS
# =========================================================

def _clean_string(
    value,
    max_length: int | None = None
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

    text = " ".join(
        text.split()
    )

    if (
        max_length is not None
        and len(text) > max_length
    ):
        text = (
            text[:max_length]
            .rstrip()
            + "..."
        )

    return text


def _json_safe_value(
    value
):
    if value is None:
        return None

    if isinstance(
        value,
        pd.Timestamp
    ):
        return value.isoformat()

    try:
        if pd.isna(value):
            return None

    except (
        TypeError,
        ValueError
    ):
        pass

    if hasattr(
        value,
        "item"
    ):
        try:
            return value.item()

        except (
            ValueError,
            AttributeError
        ):
            pass

    return value


def _safe_bool(
    value,
    default: bool = False
):
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default

    except (
        TypeError,
        ValueError
    ):
        pass

    return bool(
        value
    )


def _safe_float(
    value
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

    try:
        return float(
            value
        )

    except (
        TypeError,
        ValueError
    ):
        return None


def _round_number(
    value,
    digits: int = 2
):
    value = _safe_float(
        value
    )

    if value is None:
        return None

    return round(
        value,
        digits
    )


def _calculate_change_pct(
    current,
    previous
):
    current = _safe_float(
        current
    )

    previous = _safe_float(
        previous
    )

    if (
        current is None
        or previous is None
        or previous == 0
    ):
        return None

    return round(
        (
            current
            / previous
            - 1
        )
        * 100,
        2
    )


# =========================================================
# FETCH HELPERS
# =========================================================

def _fetch_price_history(
    symbol: str
):
    symbol = (
        symbol
        .strip()
        .upper()
    )


    today = (
        datetime.now()
        .date()
    )


    start_date = (
        today
        - timedelta(
            days=HISTORY_LOOKBACK_CALENDAR_DAYS
        )
    )


    cache_key = (
        symbol,
        start_date.isoformat(),
        today.isoformat(),
        "1D"
    )


    # -----------------------------------------------------
    # HISTORY CACHE LOOKUP
    # -----------------------------------------------------

    cached = _get_ttl_cache(
        cache=_price_history_cache,
        lock=_price_history_cache_lock,
        key=cache_key,
        ttl_seconds=(
            PRICE_HISTORY_CACHE_TTL_SECONDS
        )
    )


    if cached is not _CACHE_MISS:

        logger.info(
            "Price history cache HIT | "
            "symbol=%s",
            symbol
        )


        if isinstance(
            cached,
            pd.DataFrame
        ):
            return cached.copy(
                deep=True
            )


        return cached


    logger.info(
        "Price history cache MISS | "
        "symbol=%s",
        symbol
    )


    # -----------------------------------------------------
    # FETCH FROM VNSTOCK
    # -----------------------------------------------------

    start_time = (
        time.perf_counter()
    )


    data = get_stock_history(
        symbol=symbol,
        start=start_date.strftime(
            "%Y-%m-%d"
        ),
        end=today.strftime(
            "%Y-%m-%d"
        ),
        interval="1D"
    )


    duration = (
        time.perf_counter()
        - start_time
    )


    logger.info(
        "Stock context price history completed | "
        "symbol=%s | duration=%.3fs",
        symbol,
        duration
    )


    # -----------------------------------------------------
    # STORE HISTORY CACHE
    # -----------------------------------------------------

    if isinstance(
        data,
        pd.DataFrame
    ):
        cached_value = data.copy(
            deep=True
        )

    else:
        cached_value = data


    _set_ttl_cache(
        cache=_price_history_cache,
        lock=_price_history_cache_lock,
        key=cache_key,
        value=cached_value
    )


    return data


def _fetch_company(
    symbol: str
):
    start_time = (
        time.perf_counter()
    )

    data = get_company_info(
        symbol
    )

    duration = (
        time.perf_counter()
        - start_time
    )

    logger.info(
        "Stock context company completed | "
        "symbol=%s | duration=%.3fs",
        symbol,
        duration
    )

    return data


def _fetch_fundamentals(
    symbol: str
):
    start_time = (
        time.perf_counter()
    )

    data = get_financial_ratios(
        symbol=symbol,
        period="quarter"
    )

    duration = (
        time.perf_counter()
        - start_time
    )

    logger.info(
        "Stock context fundamentals completed | "
        "symbol=%s | duration=%.3fs",
        symbol,
        duration
    )

    return data


def _fetch_news(
    symbol: str,
    news_limit: int
):
    start_time = (
        time.perf_counter()
    )

    data = get_stock_news(
        symbol=symbol,
        limit=news_limit
    )

    duration = (
        time.perf_counter()
        - start_time
    )

    logger.info(
        "Stock context news completed | "
        "symbol=%s | "
        "limit=%s | "
        "duration=%.3fs",
        symbol,
        news_limit,
        duration
    )

    return data


# =========================================================
# RESILIENT SOURCE HANDLING
# =========================================================

def _is_empty_source(
    data
) -> bool:

    if data is None:
        return True

    if isinstance(
        data,
        pd.DataFrame
    ):
        return data.empty

    if isinstance(
        data,
        pd.Series
    ):
        return data.empty

    if isinstance(
        data,
        (
            list,
            dict,
            tuple,
            set
        )
    ):
        return len(
            data
        ) == 0

    return False


def _resolve_source_future(
    source_name: str,
    future: Future
):
    """
    Resolve một future nhưng không cho lỗi của một nguồn
    làm sập toàn bộ stock context.

    status:
    - ok
    - empty
    - error
    """

    try:

        data = future.result()


        if _is_empty_source(
            data
        ):
            logger.warning(
                "Stock context source returned no data | "
                "source=%s",
                source_name
            )

            return (
                pd.DataFrame(),
                {
                    "status": "empty",
                    "available": False
                }
            )


        return (
            data,
            {
                "status": "ok",
                "available": True
            }
        )


    except Exception:

        logger.exception(
            "Stock context source failed | "
            "source=%s",
            source_name
        )


        return (
            pd.DataFrame(),
            {
                "status": "error",
                "available": False
            }
        )


def _build_source_data_limits(
    sources: dict
):
    limitations = []


    labels = {

        "price_history": (
            "dữ liệu lịch sử giá"
        ),

        "company": (
            "thông tin doanh nghiệp"
        ),

        "fundamentals": (
            "dữ liệu chỉ số cơ bản"
        ),

        "news": (
            "dữ liệu tin tức"
        )
    }


    for (
        source_name,
        status
    ) in sources.items():

        source_label = labels.get(
            source_name,
            source_name
        )


        if (
            status.get(
                "status"
            )
            == "error"
        ):
            limitations.append(
                f"Không thể lấy {source_label} "
                "do nguồn dữ liệu gặp lỗi."
            )


        elif (
            status.get(
                "status"
            )
            == "empty"
        ):
            limitations.append(
                f"Nguồn {source_label} "
                "không trả về dữ liệu."
            )


    return limitations


# =========================================================
# CONTEXT METADATA
# =========================================================

def _build_metadata():
    return {

        "schema_version": (
            CONTEXT_SCHEMA_VERSION
        ),

        "generated_at_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "data_rules": {

            "market_data": (
                "Use only values present in this context "
                "as current market data."
            ),

            "missing_data": (
                "A missing or null field means the data "
                "is unavailable. Do not invent it."
            ),

            "source_availability": (
                "The top-level sources object reports whether "
                "each upstream data source is available. "
                "status=error means the source failed. "
                "status=empty means the source returned no data. "
                "Do not invent data for unavailable sources."
            ),

            "partial_failure": (
                "Some sections may be unavailable while other "
                "sections remain valid. Analyze only the sections "
                "whose data is present."
            ),

            "exact_field_names": (
                "Never create, rename, combine, or mention a "
                "technical field that does not exist in this context."
            ),

            "facts_vs_analysis": (
                "Clearly distinguish source data and calculated "
                "statistics from analytical interpretation."
            ),

            "price_units": (
                "OHLC and moving-average values use the "
                "source-native price unit. Do not convert or attach "
                "a currency unit unless explicitly provided."
            ),

            "price_history": (
                "price_history contains recent trading sessions "
                "ordered from oldest to newest."
            ),

            "latest": (
                "latest is derived from the most recent available "
                "trading session in price_history."
            ),

            "trend_changes": (
                "change_1d_pct, change_5d_pct and change_20d_pct "
                "are calculated from closing prices over trading "
                "sessions, not calendar days."
            ),

            "moving_averages": (
                "ma5 and ma20 are simple moving averages of closing "
                "prices over the latest 5 and 20 available trading "
                "sessions."
            ),

            "moving_average_distance": (
                "vs_ma5_pct and vs_ma20_pct measure the percentage "
                "distance of the latest closing price from the "
                "corresponding simple moving average."
            ),

            "ma_flags": (
                "above_ma5 and above_ma20 are neutral booleans "
                "showing whether the latest close is above the "
                "corresponding moving average."
            ),

            "ma_interpretation_limit": (
                "Being above or below a moving average may be "
                "described factually. Do not treat it as proof of "
                "future direction or as a standalone trading signal."
            ),

            "rsi14": (
                "rsi14 is calculated from the latest 14 "
                "close-to-close price changes using average gains "
                "and average losses."
            ),

            "rsi_thresholds": (
                "If RSI reference levels such as 30, 50 or 70 are "
                "mentioned, describe them only as common "
                "technical-analysis reference levels."
            ),

            "rsi_inference_limit": (
                "RSI alone does not establish that selling pressure "
                "is increasing, decreasing, slowing, exhausted, "
                "or that a reversal is beginning."
            ),

            "volatility_20d": (
                "volatility_20d_pct is the sample standard deviation "
                "of daily close-to-close percentage returns over the "
                "latest 20 available return observations."
            ),

            "volatility_interpretation_limit": (
                "Do not label volatility as low, moderate, high, "
                "normal or abnormal unless an explicit comparison "
                "benchmark is provided."
            ),

            "volume_ratio": (
                "volume_ratio_20d equals latest session volume "
                "divided by average volume over the latest "
                "20 sessions."
            ),

            "volume_inference_limit": (
                "volume_ratio_20d only describes relative volume. "
                "Do not infer investor behavior or the cause "
                "of the volume change."
            ),

            "price_position": (
                "price_position_20d_pct measures where the latest "
                "close sits between the 20-session low and high."
            ),

            "range_interpretation_limit": (
                "Being near high_20d or low_20d only describes "
                "position within the recent range. Do not call these "
                "levels support, resistance, bottom or top."
            ),

            "technical_causality": (
                "Do not infer investor motives or behavior from "
                "price, RSI, moving averages, volatility or volume."
            ),

            "technical_prediction": (
                "Technical indicators describe historical behavior "
                "only. They do not guarantee future price direction."
            ),

            "technical_language": (
                "Prefer neutral descriptions directly supported "
                "by the supplied statistics."
            ),

            "company_leadership": (
                "company.key_person is a neutral mapping of the "
                "source-provided person name and position."
            ),

            "charter_capital": (
                "company.charter_capital_reported_value is the "
                "numeric value returned by the source. Its unit "
                "is not declared in this context."
            ),

            "fundamental_periods": (
                "Fundamental period labels are provided directly "
                "by the data source."
            ),

            "alt_period": (
                "A fundamental period ending with _alt is a "
                "source-provided alternative variant."
            ),

            "fundamental_units": (
                "Do not add a unit to a fundamental value unless "
                "its label or context clearly supports that unit."
            ),

            "news_headlines": (
                "When summary_available is false, only headline "
                "metadata is available."
            ),

            "news_urls": (
                "When url_available is false, no article URL is "
                "available. Do not construct or guess one."
            )
        }
    }


# =========================================================
# PRICE HISTORY NORMALIZATION
# =========================================================

def _prepare_price_history(
    history
):
    if (
        history is None
        or history.empty
    ):
        return pd.DataFrame()


    data = history.copy()


    if "time" in data.columns:

        data[
            "time"
        ] = pd.to_datetime(
            data["time"],
            errors="coerce"
        )


        data = (
            data
            .sort_values(
                by="time",
                ascending=True
            )
        )


    if "close" in data.columns:

        data[
            "close"
        ] = pd.to_numeric(
            data["close"],
            errors="coerce"
        )


        data = data.dropna(
            subset=[
                "close"
            ]
        )


    for column in (
        "open",
        "high",
        "low",
        "volume"
    ):

        if column in data.columns:

            data[
                column
            ] = pd.to_numeric(
                data[column],
                errors="coerce"
            )


    return (
        data
        .tail(
            RECENT_PRICE_SESSIONS
        )
        .reset_index(
            drop=True
        )
    )


# =========================================================
# LATEST FROM HISTORY
# =========================================================

def _compact_latest_from_history(
    history
):
    if history.empty:
        return None


    row = history.iloc[-1]


    result = {}


    for field in (
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ):

        if field not in history.columns:
            continue


        value = _json_safe_value(
            row.get(
                field
            )
        )


        if value is not None:

            result[
                field
            ] = value


    return result


# =========================================================
# TECHNICAL INDICATORS
# =========================================================

def _calculate_rsi14(
    closes: pd.Series
):
    closes = (
        closes
        .dropna()
        .astype(float)
    )


    if len(closes) < 15:
        return None


    recent = (
        closes
        .tail(15)
    )


    delta = (
        recent
        .diff()
        .dropna()
    )


    gains = (
        delta
        .clip(
            lower=0
        )
    )


    losses = (
        -delta
        .clip(
            upper=0
        )
    )


    average_gain = float(
        gains.mean()
    )


    average_loss = float(
        losses.mean()
    )


    if (
        average_gain == 0
        and average_loss == 0
    ):
        return 50.0


    if average_loss == 0:
        return 100.0


    if average_gain == 0:
        return 0.0


    rs = (
        average_gain
        / average_loss
    )


    rsi = (
        100
        - (
            100
            / (
                1
                + rs
            )
        )
    )


    return round(
        rsi,
        2
    )


def _calculate_volatility_20d(
    closes: pd.Series
):
    closes = (
        closes
        .dropna()
        .astype(float)
    )


    if len(closes) < 21:
        return None


    recent = (
        closes
        .tail(21)
    )


    returns = (
        recent
        .pct_change()
        .dropna()
    )


    if len(returns) < 2:
        return None


    volatility = float(
        returns.std(
            ddof=1
        )
        * 100
    )


    if not math.isfinite(
        volatility
    ):
        return None


    return round(
        volatility,
        2
    )


# =========================================================
# TREND CALCULATION
# =========================================================

def _build_trend_summary(
    history
):
    if (
        history.empty
        or "close" not in history.columns
    ):
        return None


    closes = (
        history[
            "close"
        ]
        .dropna()
        .astype(float)
    )


    if closes.empty:
        return None


    latest_close = float(
        closes.iloc[-1]
    )


    result = {

        "available_sessions": int(
            len(history)
        ),

        "latest_close": round(
            latest_close,
            4
        )
    }


    # -----------------------------------------------------
    # PRICE CHANGES
    # -----------------------------------------------------

    result[
        "change_1d_pct"
    ] = (
        _calculate_change_pct(
            closes.iloc[-1],
            closes.iloc[-2]
        )
        if len(closes) >= 2
        else None
    )


    result[
        "change_5d_pct"
    ] = (
        _calculate_change_pct(
            closes.iloc[-1],
            closes.iloc[-6]
        )
        if len(closes) >= 6
        else None
    )


    result[
        "change_20d_pct"
    ] = (
        _calculate_change_pct(
            closes.iloc[-1],
            closes.iloc[-21]
        )
        if len(closes) >= 21
        else None
    )


    # -----------------------------------------------------
    # LAST 20 SESSIONS
    # -----------------------------------------------------

    last_20 = (
        history
        .tail(20)
    )


    high_20d = None

    low_20d = None

    average_volume_20d = None


    if (
        "high" in last_20.columns
        and last_20[
            "high"
        ].notna().any()
    ):

        high_20d = _round_number(
            last_20[
                "high"
            ].max(),
            4
        )


    if (
        "low" in last_20.columns
        and last_20[
            "low"
        ].notna().any()
    ):

        low_20d = _round_number(
            last_20[
                "low"
            ].min(),
            4
        )


    if (
        "volume" in last_20.columns
        and last_20[
            "volume"
        ].notna().any()
    ):

        average_volume_20d = round(
            float(
                last_20[
                    "volume"
                ]
                .dropna()
                .mean()
            ),
            2
        )


    result[
        "high_20d"
    ] = high_20d


    result[
        "low_20d"
    ] = low_20d


    result[
        "average_volume_20d"
    ] = average_volume_20d


    # -----------------------------------------------------
    # MA5
    # -----------------------------------------------------

    if len(closes) >= 5:

        ma5 = float(
            closes
            .tail(5)
            .mean()
        )


        result[
            "ma5"
        ] = round(
            ma5,
            4
        )


        result[
            "vs_ma5_pct"
        ] = _calculate_change_pct(
            latest_close,
            ma5
        )


        result[
            "above_ma5"
        ] = (
            latest_close
            > ma5
        )


    else:

        result[
            "ma5"
        ] = None

        result[
            "vs_ma5_pct"
        ] = None

        result[
            "above_ma5"
        ] = None


    # -----------------------------------------------------
    # MA20
    # -----------------------------------------------------

    if len(closes) >= 20:

        ma20 = float(
            closes
            .tail(20)
            .mean()
        )


        result[
            "ma20"
        ] = round(
            ma20,
            4
        )


        result[
            "vs_ma20_pct"
        ] = _calculate_change_pct(
            latest_close,
            ma20
        )


        result[
            "above_ma20"
        ] = (
            latest_close
            > ma20
        )


    else:

        result[
            "ma20"
        ] = None

        result[
            "vs_ma20_pct"
        ] = None

        result[
            "above_ma20"
        ] = None


    # -----------------------------------------------------
    # RSI14
    # -----------------------------------------------------

    result[
        "rsi14"
    ] = _calculate_rsi14(
        closes
    )


    # -----------------------------------------------------
    # VOLATILITY
    # -----------------------------------------------------

    result[
        "volatility_20d_pct"
    ] = _calculate_volatility_20d(
        closes
    )


    # -----------------------------------------------------
    # VOLUME RATIO
    # -----------------------------------------------------

    latest_volume = None


    if (
        "volume" in history.columns
        and history[
            "volume"
        ].notna().any()
    ):

        latest_volume = _safe_float(
            history.iloc[-1].get(
                "volume"
            )
        )


    if (
        latest_volume is not None
        and average_volume_20d is not None
        and average_volume_20d != 0
    ):

        result[
            "volume_ratio_20d"
        ] = round(
            latest_volume
            / average_volume_20d,
            2
        )


    else:

        result[
            "volume_ratio_20d"
        ] = None


    # -----------------------------------------------------
    # PRICE POSITION
    # -----------------------------------------------------

    if (
        high_20d is not None
        and low_20d is not None
        and high_20d != low_20d
    ):

        position = (
            (
                latest_close
                - low_20d
            )
            / (
                high_20d
                - low_20d
            )
            * 100
        )


        result[
            "price_position_20d_pct"
        ] = round(
            position,
            2
        )


    else:

        result[
            "price_position_20d_pct"
        ] = None


    return result


# =========================================================
# COMPACT PRICE HISTORY
# =========================================================

def _compact_price_history(
    history
):
    if history.empty:
        return []


    result = []


    for _, row in history.iterrows():

        item = {}


        if "time" in history.columns:

            time_value = _json_safe_value(
                row.get(
                    "time"
                )
            )


            if time_value is not None:

                item[
                    "t"
                ] = time_value


        field_mapping = {

            "open": "o",

            "high": "h",

            "low": "l",

            "close": "c",

            "volume": "v"
        }


        for (
            source_field,
            output_field
        ) in field_mapping.items():

            if source_field not in history.columns:
                continue


            value = _json_safe_value(
                row.get(
                    source_field
                )
            )


            if value is not None:

                item[
                    output_field
                ] = value


        result.append(
            item
        )


    return result


# =========================================================
# COMPACT COMPANY
# =========================================================

def _compact_company(
    company
):
    if (
        company is None
        or company.empty
    ):
        return None


    raw = (
        company
        .iloc[0]
        .to_dict()
    )


    result = {}


    symbol = _clean_string(
        raw.get(
            "symbol"
        )
    )


    if symbol:

        result[
            "symbol"
        ] = symbol


    exchange = _clean_string(
        raw.get(
            "exchange"
        )
    )


    if exchange:

        result[
            "exchange"
        ] = exchange


    company_type = _clean_string(
        raw.get(
            "company_type"
        )
    )


    if company_type:

        result[
            "company_type"
        ] = company_type


    listing_date = _json_safe_value(
        raw.get(
            "listing_date"
        )
    )


    if listing_date is not None:

        result[
            "listing_date"
        ] = listing_date


    charter_capital = _json_safe_value(
        raw.get(
            "charter_capital"
        )
    )


    if charter_capital is not None:

        result[
            "charter_capital_reported_value"
        ] = charter_capital


    outstanding_shares = _json_safe_value(
        raw.get(
            "outstanding_shares"
        )
    )


    if outstanding_shares is not None:

        result[
            "outstanding_shares"
        ] = outstanding_shares


    employee_count = _json_safe_value(
        raw.get(
            "number_of_employees"
        )
    )


    if employee_count is not None:

        result[
            "employee_count"
        ] = employee_count


    key_person_name = _clean_string(
        raw.get(
            "ceo_name"
        )
    )


    key_person_position = _clean_string(
        raw.get(
            "ceo_position"
        )
    )


    if (
        key_person_name
        or key_person_position
    ):

        key_person = {}


        if key_person_name:

            key_person[
                "name"
            ] = key_person_name


        if key_person_position:

            key_person[
                "position"
            ] = key_person_position


        result[
            "key_person"
        ] = key_person


    auditor = _clean_string(
        raw.get(
            "auditor"
        )
    )


    if auditor:

        result[
            "auditor"
        ] = auditor


    website = _clean_string(
        raw.get(
            "website"
        )
    )


    if website:

        result[
            "website"
        ] = website


    business_model = _clean_string(
        raw.get(
            "business_model"
        ),
        max_length=(
            MAX_BUSINESS_MODEL_LENGTH
        )
    )


    if business_model:

        result[
            "business_model"
        ] = business_model


    profile_as_of = _json_safe_value(
        raw.get(
            "as_of_date"
        )
    )


    if profile_as_of is not None:

        result[
            "profile_as_of"
        ] = profile_as_of


    return result


# =========================================================
# COMPACT FUNDAMENTALS
# =========================================================

def _compact_fundamentals(
    fundamentals
):
    if (
        fundamentals is None
        or fundamentals.empty
    ):
        return []


    result = []


    for _, row in fundamentals.iterrows():

        item_id = _clean_string(
            row.get(
                "item_id"
            )
        )


        if item_id not in IMPORTANT_FUNDAMENTAL_IDS:
            continue


        item = {
            "item_id": item_id
        }


        item_name = _clean_string(
            row.get(
                "item"
            ),
            max_length=180
        )


        if item_name:

            item[
                "label"
            ] = item_name


        values = {}


        for column in fundamentals.columns:

            if column in {
                "item",
                "item_id",
                "item_en",
                "unit"
            }:
                continue


            value = _json_safe_value(
                row.get(
                    column
                )
            )


            if value is None:
                continue


            values[
                str(
                    column
                )
            ] = value


        item[
            "values"
        ] = values


        result.append(
            item
        )


    return result


# =========================================================
# COMPACT NEWS
# =========================================================

def _compact_news(
    news
):
    if (
        news is None
        or news.empty
    ):
        return []


    result = []


    for _, row in news.iterrows():

        summary_available = _safe_bool(
            row.get(
                "summary_available"
            )
        )


        url_available = _safe_bool(
            row.get(
                "url_available"
            )
        )


        article = {}


        title = _clean_string(
            row.get(
                "title"
            ),
            max_length=300
        )


        if title:

            article[
                "title"
            ] = title


        publish_time = _json_safe_value(
            row.get(
                "publish_time"
            )
        )


        if publish_time is not None:

            article[
                "publish_time"
            ] = publish_time


        source = _clean_string(
            row.get(
                "source"
            )
        )


        if source:

            article[
                "source"
            ] = source


        article[
            "summary_available"
        ] = summary_available


        article[
            "url_available"
        ] = url_available


        if summary_available:

            summary = _clean_string(
                row.get(
                    "summary"
                ),
                max_length=400
            )


            if summary:

                article[
                    "summary"
                ] = summary


        if url_available:

            url = _clean_string(
                row.get(
                    "url"
                ),
                max_length=1000
            )


            if url:

                article[
                    "url"
                ] = url


        result.append(
            article
        )


    return result


# =========================================================
# BUILD STOCK CONTEXT - UNCACHED
# =========================================================

def _build_stock_context_uncached(
    symbol: str,
    news_limit: int = 8
) -> str:

    symbol = (
        symbol
        .strip()
        .upper()
    )


    news_limit = max(
        1,
        min(
            news_limit,
            50
        )
    )


    total_start_time = (
        time.perf_counter()
    )


    logger.info(
        "Building stock context | "
        "symbol=%s | "
        "news_limit=%s",
        symbol,
        news_limit
    )


    # =====================================================
    # PARALLEL FETCH
    # =====================================================

    with ThreadPoolExecutor(
        max_workers=(
            STOCK_CONTEXT_MAX_WORKERS
        ),
        thread_name_prefix=(
            "stock-context"
        )
    ) as executor:


        history_future = executor.submit(
            _fetch_price_history,
            symbol
        )


        company_future = executor.submit(
            _fetch_company,
            symbol
        )


        fundamentals_future = executor.submit(
            _fetch_fundamentals,
            symbol
        )


        news_future = executor.submit(
            _fetch_news,
            symbol,
            news_limit
        )


        (
            history,
            history_status
        ) = _resolve_source_future(
            "price_history",
            history_future
        )


        (
            company,
            company_status
        ) = _resolve_source_future(
            "company",
            company_future
        )


        (
            fundamentals,
            fundamentals_status
        ) = _resolve_source_future(
            "fundamentals",
            fundamentals_future
        )


        (
            news,
            news_status
        ) = _resolve_source_future(
            "news",
            news_future
        )


    # =====================================================
    # SOURCE STATUS
    # =====================================================

    sources = {

        "price_history": (
            history_status
        ),

        "company": (
            company_status
        ),

        "fundamentals": (
            fundamentals_status
        ),

        "news": (
            news_status
        )
    }


    # =====================================================
    # PRICE
    # =====================================================

    prepared_history = _prepare_price_history(
        history
    )


    latest_data = _compact_latest_from_history(
        prepared_history
    )


    trend_data = _build_trend_summary(
        prepared_history
    )


    price_history_data = _compact_price_history(
        prepared_history
    )


    # =====================================================
    # OTHER DATA
    # =====================================================

    company_data = _compact_company(
        company
    )


    fundamentals_data = _compact_fundamentals(
        fundamentals
    )


    news_data = _compact_news(
        news
    )


    # =====================================================
    # DATA LIMITS
    # =====================================================

    data_limits = (
        _build_source_data_limits(
            sources
        )
    )


    # =====================================================
    # FINAL CONTEXT
    # =====================================================

    context = {

        "metadata": (
            _build_metadata()
        ),

        "symbol": symbol,

        "sources": (
            sources
        ),

        "data_limits": (
            data_limits
        ),

        "latest": (
            latest_data
        ),

        "trend": (
            trend_data
        ),

        "price_history": (
            price_history_data
        ),

        "company": (
            company_data
        ),

        "fundamentals": (
            fundamentals_data
        ),

        "news": (
            news_data
        )
    }


    context_json = json.dumps(
        context,
        ensure_ascii=False,
        separators=(
            ",",
            ":"
        ),
        default=str
    )


    total_duration = (
        time.perf_counter()
        - total_start_time
    )


    failed_sources = [

        source_name

        for (
            source_name,
            status
        ) in sources.items()

        if status.get(
            "status"
        ) == "error"
    ]


    empty_sources = [

        source_name

        for (
            source_name,
            status
        ) in sources.items()

        if status.get(
            "status"
        ) == "empty"
    ]


    logger.info(
        "Stock context built | "
        "symbol=%s | "
        "schema=%s | "
        "duration=%.3fs | "
        "price_sessions=%s | "
        "fundamentals=%s | "
        "news=%s | "
        "failed_sources=%s | "
        "empty_sources=%s | "
        "context_chars=%s",
        symbol,
        CONTEXT_SCHEMA_VERSION,
        total_duration,
        len(
            price_history_data
        ),
        len(
            fundamentals_data
        ),
        len(
            news_data
        ),
        failed_sources,
        empty_sources,
        len(
            context_json
        )
    )


    return context_json


# =========================================================
# BUILD STOCK CONTEXT - CACHED
# =========================================================

def build_stock_context(
    symbol: str,
    news_limit: int = 8
) -> str:

    symbol = (
        symbol
        .strip()
        .upper()
    )


    news_limit = max(
        1,
        min(
            news_limit,
            50
        )
    )


    cache_key = (
        symbol,
        news_limit,
        CONTEXT_SCHEMA_VERSION
    )


    # -----------------------------------------------------
    # CONTEXT CACHE LOOKUP
    # -----------------------------------------------------

    cached = _get_ttl_cache(
        cache=_stock_context_cache,
        lock=_stock_context_cache_lock,
        key=cache_key,
        ttl_seconds=(
            STOCK_CONTEXT_CACHE_TTL_SECONDS
        )
    )


    if cached is not _CACHE_MISS:

        logger.info(
            "Stock context cache HIT | "
            "symbol=%s | "
            "news_limit=%s | "
            "schema=%s",
            symbol,
            news_limit,
            CONTEXT_SCHEMA_VERSION
        )

        return cached


    logger.info(
        "Stock context cache MISS | "
        "symbol=%s | "
        "news_limit=%s | "
        "schema=%s",
        symbol,
        news_limit,
        CONTEXT_SCHEMA_VERSION
    )


    # -----------------------------------------------------
    # BUILD FRESH CONTEXT
    # -----------------------------------------------------

    context_json = (
        _build_stock_context_uncached(
            symbol=symbol,
            news_limit=news_limit
        )
    )


    # -----------------------------------------------------
    # STORE CONTEXT CACHE
    # -----------------------------------------------------

    _set_ttl_cache(
        cache=_stock_context_cache,
        lock=_stock_context_cache_lock,
        key=cache_key,
        value=context_json
    )


    return context_json