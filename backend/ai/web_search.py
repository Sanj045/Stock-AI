from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import urlparse

import re
import unicodedata

# pyrefly: ignore [missing-import]
import httpx

from config import TAVILY_API_KEY
from logger import logger


# =========================================================
# PHASE 4.6H.5 - GENERIC-TITLE SEARCH OPTIMIZATION
# =========================================================
#
# Mục tiêu:
#
# 1. Với title cụ thể:
#    - giữ cách search như trước.
#
# 2. Với title quá chung, ví dụ:
#    "ABB: Nghị quyết Hội đồng quản trị"
#    thì đưa ngày publish vào query Tavily:
#
#       ABB Nghị quyết Hội đồng quản trị 2026-09-28
#
#    để candidates gần đúng event hơn.
#
# 3. Không để Gemini phải phân biệt hàng loạt event cùng title
#    chỉ dựa trên một candidate set quá chung.
#
# 4. Sửa normalize tiếng Việt cho ký tự đ / Đ.
#
# =========================================================


# =========================================================
# CONFIG
# =========================================================

TAVILY_SEARCH_URL = (
    "https://api.tavily.com/search"
)

TAVILY_TIMEOUT_SECONDS = 15.0

DEFAULT_MAX_RESULTS = 5

TAVILY_RESULTS_PER_QUERY = 8

MAX_ALLOWED_RESULTS = 10

MAX_SEARCH_QUERIES = 3

MIN_LOCAL_RELEVANCE_SCORE = 0.12


# =========================================================
# SOURCE PRIORITY
# =========================================================

TRUSTED_FINANCE_DOMAINS = {
    "fpt.com",
    "hsx.vn",
    "hnx.vn",
    "ssc.gov.vn",
    "bsc.com.vn",
    "new.bsc.com.vn",
    "bc.bsc.com.vn",
    "vietstock.vn",
    "cafef.vn",
    "fireant.vn",
    "stockbiz.vn",
    "ssi.com.vn",
    "vndirect.com.vn",
    "masvn.com",
    "miraeasset.com.vn",
    "phs.vn",
    "24hmoney.vn",
}


LOW_VALUE_DOMAINS = {
    "studocu.vn",
    "jsdelivr.com",
    "github.com",
    "facebook.com",
    "youtube.com",
    "tiktok.com",
}


GENERIC_EVENT_TITLES = {
    "nghi quyet hoi dong quan tri",
    "nghi quyet hdqt",
    "quyet dinh hoi dong quan tri",
    "quyet dinh hdqt",
}


# =========================================================
# RESULT MODEL
# =========================================================

@dataclass(frozen=True)
class WebSearchCandidate:
    title: str
    url: str
    content: str | None
    score: float | None
    source_domain: str
    relevance_score: float
    trusted_source: bool


# =========================================================
# CONFIG VALIDATION
# =========================================================

if not TAVILY_API_KEY:
    raise RuntimeError(
        "TAVILY_API_KEY is not configured"
    )


# =========================================================
# BASIC HELPERS
# =========================================================

def _normalize_text(
    value,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


def _is_http_url(
    value: str | None,
) -> bool:
    if not value:
        return False

    try:
        parsed = urlparse(
            value.strip()
        )

    except Exception:
        return False

    return (
        parsed.scheme
        in {
            "http",
            "https",
        }
        and bool(
            parsed.netloc
        )
    )


def _extract_domain(
    url: str,
) -> str:
    try:
        host = (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

    except Exception:
        return ""

    if host.startswith(
        "www."
    ):
        host = host[4:]

    return host


def _is_trusted_domain(
    domain: str,
) -> bool:
    if not domain:
        return False

    if domain in TRUSTED_FINANCE_DOMAINS:
        return True

    for trusted in TRUSTED_FINANCE_DOMAINS:
        if domain.endswith(
            "." + trusted
        ):
            return True

    return False


def _is_low_value_domain(
    domain: str,
) -> bool:
    if not domain:
        return False

    if domain in LOW_VALUE_DOMAINS:
        return True

    for blocked in LOW_VALUE_DOMAINS:
        if domain.endswith(
            "." + blocked
        ):
            return True

    return False


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def _strip_accents(
    value: str,
) -> str:
    # NFD không tự đổi đ -> d.
    value = (
        value
        .replace("đ", "d")
        .replace("Đ", "D")
    )

    normalized = (
        unicodedata.normalize(
            "NFD",
            value,
        )
    )

    return "".join(
        char
        for char in normalized
        if unicodedata.category(
            char
        )
        != "Mn"
    )


def _normalize_for_matching(
    value: str,
) -> str:
    value = (
        value
        .lower()
        .strip()
    )

    value = _strip_accents(
        value
    )

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def _token_set(
    value: str,
) -> set[str]:
    normalized = (
        _normalize_for_matching(
            value
        )
    )

    stop_words = {
        "va",
        "ve",
        "cua",
        "cho",
        "voi",
        "tai",
        "tu",
        "den",
        "mot",
        "cac",
        "nhung",
        "duoc",
        "viec",
        "theo",
        "trong",
        "tren",
        "khi",
        "la",
        "de",
        "do",
        "nay",
    }

    return {
        token
        for token
        in normalized.split()
        if (
            len(token) >= 2
            and token
            not in stop_words
        )
    }


# =========================================================
# QUERY BUILDING HELPERS
# =========================================================

def _remove_symbol_prefix(
    symbol: str,
    title: str,
) -> str:
    pattern = (
        rf"^\s*{re.escape(symbol)}"
        r"\s*[:\-–—]\s*"
    )

    cleaned = re.sub(
        pattern,
        "",
        title,
        flags=re.IGNORECASE,
    )

    return " ".join(
        cleaned.split()
    ).strip()


def _title_without_symbol_for_matching(
    symbol: str,
    title: str,
) -> str:
    cleaned = _remove_symbol_prefix(
        symbol,
        title,
    )

    return _normalize_for_matching(
        cleaned
    )


def is_generic_news_title(
    symbol: str,
    title: str,
) -> bool:
    return (
        _title_without_symbol_for_matching(
            symbol,
            title,
        )
        in GENERIC_EVENT_TITLES
    )


def normalize_publish_date(
    publish_time: str | None,
) -> str:
    if not publish_time:
        return ""

    value = publish_time.strip()

    if not value:
        return ""

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        return parsed.date().isoformat()

    except ValueError:
        pass

    if re.match(
        r"^\d{4}-\d{2}-\d{2}",
        value,
    ):
        return value[:10]

    return ""


def _publish_date_variants(
    publish_time: str | None,
) -> list[str]:
    date_key = normalize_publish_date(
        publish_time
    )

    if not date_key:
        return []

    try:
        parsed = datetime.strptime(
            date_key,
            "%Y-%m-%d",
        )

    except ValueError:
        return [
            date_key
        ]

    return [
        parsed.strftime(
            "%Y-%m-%d"
        ),
        parsed.strftime(
            "%d/%m/%Y"
        ),
    ]


def _important_terms(
    title: str,
    limit: int = 12,
) -> list[str]:
    tokens = list(
        _token_set(
            title
        )
    )

    priority_terms = [
        "quyet",
        "dinh",
        "nghi",
        "hdqt",
        "hoi",
        "dong",
        "quan",
        "tri",
        "phat",
        "hanh",
        "co",
        "phieu",
        "tang",
        "von",
        "nvcsh",
        "nguon",
        "chu",
        "so",
        "huu",
        "dang",
        "ky",
        "niem",
        "yet",
        "bao",
        "cao",
        "ket",
        "qua",
    ]

    ordered = []

    for term in priority_terms:
        if (
            term in tokens
            and term
            not in ordered
        ):
            ordered.append(
                term
            )

    for token in sorted(
        tokens
    ):
        if token not in ordered:
            ordered.append(
                token
            )

        if len(ordered) >= limit:
            break

    return ordered[
        :limit
    ]


def build_news_search_queries(
    symbol: str,
    title: str,
    publish_time: str | None = None,
) -> list[str]:
    symbol = (
        symbol
        .strip()
        .upper()
    )

    title = title.strip()

    if not symbol:
        raise ValueError(
            "symbol is required"
        )

    if not title:
        raise ValueError(
            "title is required"
        )

    cleaned_title = (
        _remove_symbol_prefix(
            symbol,
            title,
        )
    )

    generic_title = (
        is_generic_news_title(
            symbol,
            title,
        )
    )

    date_variants = (
        _publish_date_variants(
            publish_time
        )
    )

    queries = []

    # -----------------------------------------------------
    # Generic title:
    #
    # Ưu tiên date-specific query trước.
    # -----------------------------------------------------

    if (
        generic_title
        and date_variants
    ):
        queries.append(
            f"{symbol} "
            f"{cleaned_title} "
            f"{date_variants[0]}"
        )

        if len(
            date_variants
        ) > 1:
            queries.append(
                f"{symbol} "
                f"{cleaned_title} "
                f"{date_variants[1]}"
            )

        important = (
            _important_terms(
                cleaned_title
            )
        )

        if important:
            queries.append(
                f"{symbol} "
                f"{' '.join(important)} "
                f"{date_variants[0]}"
            )

    else:
        # -------------------------------------------------
        # Specific title:
        #
        # Giữ pipeline trước đây.
        # -------------------------------------------------

        queries.append(
            f"{symbol} {cleaned_title}"
        )

        important = (
            _important_terms(
                cleaned_title
            )
        )

        if important:
            queries.append(
                f"{symbol} "
                f"{' '.join(important)}"
            )

        event_query = (
            f"{symbol} phát hành cổ phiếu "
            "tăng vốn nguồn vốn chủ sở hữu"
        )

        queries.append(
            event_query
        )

    unique_queries = []

    seen = set()

    for query in queries:
        cleaned = " ".join(
            query.split()
        ).strip()

        key = (
            cleaned
            .lower()
        )

        if (
            cleaned
            and key not in seen
        ):
            seen.add(
                key
            )

            unique_queries.append(
                cleaned
            )

    return unique_queries[
        :MAX_SEARCH_QUERIES
    ]


# =========================================================
# RELEVANCE
# =========================================================

def _calculate_relevance(
    original_title: str,
    symbol: str,
    candidate_title: str,
    candidate_content: str | None,
    trusted_source: bool,
) -> float:
    original_normalized = (
        _normalize_for_matching(
            original_title
        )
    )

    candidate_title_normalized = (
        _normalize_for_matching(
            candidate_title
        )
    )

    candidate_full_text = (
        candidate_title
        + " "
        + (
            candidate_content
            or ""
        )
    )

    candidate_full_normalized = (
        _normalize_for_matching(
            candidate_full_text
        )
    )

    sequence_score = (
        SequenceMatcher(
            None,
            original_normalized,
            candidate_title_normalized,
        ).ratio()
    )

    original_tokens = (
        _token_set(
            original_title
        )
    )

    candidate_tokens = (
        _token_set(
            candidate_full_text
        )
    )

    if original_tokens:
        overlap_score = (
            len(
                original_tokens
                & candidate_tokens
            )
            / len(
                original_tokens
            )
        )

    else:
        overlap_score = 0.0

    normalized_symbol = (
        _normalize_for_matching(
            symbol
        )
    )

    symbol_score = (
        1.0
        if normalized_symbol
        in candidate_full_normalized.split()
        else 0.0
    )

    trusted_bonus = (
        0.10
        if trusted_source
        else 0.0
    )

    score = (
        sequence_score * 0.40
        + overlap_score * 0.45
        + symbol_score * 0.05
        + trusted_bonus
    )

    return round(
        min(
            score,
            1.0,
        ),
        4,
    )


# =========================================================
# SINGLE TAVILY SEARCH
# =========================================================

def _search_tavily_once(
    query: str,
) -> list[dict]:
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "topic": "general",
        "search_depth": "basic",
        "max_results": (
            TAVILY_RESULTS_PER_QUERY
        ),
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }

    logger.info(
        "Tavily search request | "
        "topic=general | "
        "query=%s",
        query[:200],
    )

    try:
        with httpx.Client(
            timeout=TAVILY_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            response = client.post(
                TAVILY_SEARCH_URL,
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Tavily HTTP error | "
            "status=%s | query=%s",
            exc.response.status_code,
            query[:180],
        )

        return []

    except httpx.HTTPError as exc:
        logger.warning(
            "Tavily request failed | "
            "query=%s | error=%s",
            query[:180],
            exc,
        )

        return []

    except ValueError as exc:
        logger.warning(
            "Tavily invalid JSON | "
            "query=%s | error=%s",
            query[:180],
            exc,
        )

        return []

    raw_results = (
        data.get(
            "results"
        )
        or []
    )

    return [
        item
        for item in raw_results
        if isinstance(
            item,
            dict,
        )
    ]


# =========================================================
# SEARCH PIPELINE
# =========================================================

def search_news_candidates(
    symbol: str,
    title: str,
    publish_time: str | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> list[WebSearchCandidate]:
    symbol = (
        symbol
        .strip()
        .upper()
    )

    title = title.strip()

    if not symbol:
        raise ValueError(
            "symbol is required"
        )

    if not title:
        raise ValueError(
            "title is required"
        )

    max_results = max(
        1,
        min(
            int(
                max_results
            ),
            MAX_ALLOWED_RESULTS,
        ),
    )

    generic_title = (
        is_generic_news_title(
            symbol,
            title,
        )
    )

    publish_date = (
        normalize_publish_date(
            publish_time
        )
    )

    queries = (
        build_news_search_queries(
            symbol=symbol,
            title=title,
            publish_time=(
                publish_time
            ),
        )
    )

    logger.info(
        "Stock news web search started | "
        "symbol=%s | queries=%s | "
        "generic_title=%s | publish_date=%s",
        symbol,
        len(
            queries
        ),
        generic_title,
        publish_date or "none",
    )

    raw_by_url: dict[
        str,
        dict,
    ] = {}

    # -----------------------------------------------------
    # Search lần lượt.
    #
    # Nếu query đầu tiên đã cho đủ candidate tốt thì dừng,
    # giúp tiết kiệm Tavily credits.
    # -----------------------------------------------------

    for index, query in enumerate(
        queries,
        start=1,
    ):
        raw_results = (
            _search_tavily_once(
                query
            )
        )

        for item in raw_results:
            url = _normalize_text(
                item.get(
                    "url"
                )
            )

            if not _is_http_url(
                url
            ):
                continue

            domain = (
                _extract_domain(
                    url
                )
            )

            if _is_low_value_domain(
                domain
            ):
                continue

            if url not in raw_by_url:
                raw_by_url[
                    url
                ] = item

        provisional_good = 0

        for url, item in raw_by_url.items():
            domain = (
                _extract_domain(
                    url
                )
            )

            candidate_title = (
                _normalize_text(
                    item.get(
                        "title"
                    )
                )
            )

            content = (
                _normalize_text(
                    item.get(
                        "content"
                    )
                )
            )

            if not candidate_title:
                continue

            trusted = (
                _is_trusted_domain(
                    domain
                )
            )

            relevance = (
                _calculate_relevance(
                    original_title=title,
                    symbol=symbol,
                    candidate_title=(
                        candidate_title
                    ),
                    candidate_content=(
                        content
                        or None
                    ),
                    trusted_source=trusted,
                )
            )

            if (
                relevance
                >= MIN_LOCAL_RELEVANCE_SCORE
            ):
                provisional_good += 1

        logger.info(
            "Tavily query completed | "
            "symbol=%s | "
            "query_index=%s | "
            "unique_results=%s | "
            "qualified_so_far=%s",
            symbol,
            index,
            len(
                raw_by_url
            ),
            provisional_good,
        )

        if (
            provisional_good
            >= max_results
        ):
            break

    candidates: list[
        WebSearchCandidate
    ] = []

    for url, item in (
        raw_by_url.items()
    ):
        candidate_title = (
            _normalize_text(
                item.get(
                    "title"
                )
            )
        )

        content = (
            _normalize_text(
                item.get(
                    "content"
                )
            )
        )

        if not candidate_title:
            continue

        domain = (
            _extract_domain(
                url
            )
        )

        trusted = (
            _is_trusted_domain(
                domain
            )
        )

        relevance_score = (
            _calculate_relevance(
                original_title=title,
                symbol=symbol,
                candidate_title=(
                    candidate_title
                ),
                candidate_content=(
                    content
                    or None
                ),
                trusted_source=trusted,
            )
        )

        if (
            relevance_score
            < MIN_LOCAL_RELEVANCE_SCORE
        ):
            continue

        raw_provider_score = (
            item.get(
                "score"
            )
        )

        provider_score = None

        if (
            raw_provider_score
            is not None
        ):
            try:
                provider_score = float(
                    raw_provider_score
                )

            except (
                TypeError,
                ValueError,
            ):
                provider_score = None

        candidates.append(
            WebSearchCandidate(
                title=(
                    candidate_title
                ),
                url=url,
                content=(
                    content
                    or None
                ),
                score=(
                    provider_score
                ),
                source_domain=domain,
                relevance_score=(
                    relevance_score
                ),
                trusted_source=(
                    trusted
                ),
            )
        )

    candidates.sort(
        key=lambda item: (
            item.trusted_source,
            item.relevance_score,
            (
                item.score
                if item.score
                is not None
                else 0.0
            ),
        ),
        reverse=True,
    )

    candidates = candidates[
        :max_results
    ]

    logger.info(
        "Stock news web search completed | "
        "symbol=%s | "
        "raw_unique=%s | "
        "qualified=%s | "
        "generic_title=%s | "
        "publish_date=%s",
        symbol,
        len(
            raw_by_url
        ),
        len(
            candidates
        ),
        generic_title,
        publish_date or "none",
    )

    return candidates
