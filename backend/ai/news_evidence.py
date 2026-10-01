from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from urllib.parse import urlparse

import re
import unicodedata

import httpx

from google import genai
from google.genai import types
from google.genai.errors import (
    ClientError,
    ServerError,
)

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
)

from ai.web_search import (
    WebSearchCandidate,
    is_generic_news_title,
    normalize_publish_date,
    search_news_candidates,
)

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODEL,
)

from logger import logger


# =========================================================
# PHASE 4.6H.5 - GENERIC-TITLE SEARCH OPTIMIZATION
# =========================================================
#
# Mục tiêu:
#
# 1. Giữ toàn bộ cache / cost-control của Phase 4.6H.
# 2. Không cho hai event khác nhau có cùng một tiêu đề quá chung
#    dùng chung một fallback evidence URL nếu chưa có bằng chứng
#    đủ để phân biệt.
# 3. Nếu candidate đầu tiên bị collision:
#    - loại candidate đó;
#    - cho Gemini chọn lại trong các candidate còn lại;
#    - KHÔNG gọi Tavily lại.
# 4. Chỉ áp dụng collision guard cho các title chung, ví dụ:
#    "ABB: Nghị quyết Hội đồng quản trị".
# 5. Direct original URL đã verify vẫn được ưu tiên vì đây là link
#    do nguồn gốc cung cấp, không phải fallback search.
#
# =========================================================


# =========================================================
# CONFIG
# =========================================================

EVIDENCE_CACHE_TTL_SECONDS = (
    6 * 60 * 60
)

NEGATIVE_EVIDENCE_CACHE_TTL_SECONDS = (
    20 * 60
)

SEARCH_CANDIDATE_CACHE_TTL_SECONDS = (
    30 * 60
)

EMPTY_SEARCH_CACHE_TTL_SECONDS = (
    10 * 60
)

URL_VERIFY_CACHE_TTL_SECONDS = (
    30 * 60
)

HTTP_TIMEOUT_SECONDS = 8.0

SEARCH_CANDIDATE_LIMIT = 5

MIN_ACCEPTED_LOCAL_RELEVANCE = 0.35


# Những tiêu đề này quá chung để chỉ dựa vào title mà kết luận
# hai record khác thời điểm là cùng một event.
GENERIC_EVENT_TITLES = {
    "nghi quyet hoi dong quan tri",
    "nghi quyet hdqt",
    "quyet dinh hoi dong quan tri",
    "quyet dinh hdqt",
}


# =========================================================
# GEMINI CLIENT
# =========================================================

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured"
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================================================
# RESULT MODELS
# =========================================================

@dataclass(frozen=True)
class NewsEvidence:
    url: str
    source: str
    method: str
    verified: bool


class EvidenceMatchResult(
    BaseModel
):
    matched_candidate_id: (
        int | None
    ) = Field(
        default=None
    )

    confidence: str = Field(
        default="low"
    )

    reason: str = Field(
        default=""
    )


# =========================================================
# CACHE STATE
# =========================================================

_cache_lock = RLock()


# Evidence cuối cùng:
#
# key:
# (
#     SYMBOL,
#     normalized title,
#     full publish_time
# )
_evidence_cache: dict[
    tuple[str, str, str],
    tuple[
        float,
        NewsEvidence | None,
    ],
] = {}


# Tavily candidates:
#
# Search query phụ thuộc chủ yếu vào symbol + title.
_search_candidate_cache: dict[
    tuple[str, str, str],
    tuple[
        float,
        list[WebSearchCandidate],
    ],
] = {}


# Cache kiểm tra URL.
_url_verify_cache: dict[
    str,
    tuple[
        float,
        str | None,
    ],
] = {}


# Evidence collision registry:
#
# key = verified evidence URL
#
# value = tập event keys đã được gắn với URL đó.
#
# Event key bao gồm:
# symbol + normalized title + full publish_time
#
# Registry chỉ tồn tại trong RAM giống các cache còn lại.
_evidence_url_event_registry: dict[
    str,
    set[
        tuple[str, str, str]
    ],
] = {}


# =========================================================
# TIME HELPERS
# =========================================================

def _monotonic_now() -> float:
    import time

    return time.monotonic()


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def _strip_accents(
    value: str,
) -> str:
    # Unicode NFD không tự chuyển "đ" thành "d".
    #
    # Nếu không xử lý riêng, chuỗi:
    #
    # "Nghị quyết Hội đồng quản trị"
    #
    # có thể bị normalize thành:
    #
    # "nghi quyet hoi ong quan tri"
    #
    # và collision guard sẽ không nhận diện đây là generic title.
    value = (
        value
        .replace("đ", "d")
        .replace("Đ", "D")
    )

    normalized = unicodedata.normalize(
        "NFD",
        value,
    )

    return "".join(
        char
        for char in normalized
        if unicodedata.category(
            char
        ) != "Mn"
    )


def _normalize_title_key(
    value: str,
) -> str:
    value = (
        value
        .strip()
        .lower()
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


def _normalize_symbol(
    symbol: str,
) -> str:
    return (
        symbol
        .strip()
        .upper()
    )


def _title_without_symbol(
    symbol: str,
    title: str,
) -> str:
    normalized_symbol = (
        _normalize_title_key(
            symbol
        )
    )

    normalized_title = (
        _normalize_title_key(
            title
        )
    )

    if not normalized_symbol:
        return normalized_title

    prefix = (
        normalized_symbol
        + " "
    )

    if normalized_title.startswith(
        prefix
    ):
        return normalized_title[
            len(prefix):
        ].strip()

    return normalized_title


def _is_generic_event_title(
    symbol: str,
    title: str,
) -> bool:
    cleaned = (
        _title_without_symbol(
            symbol,
            title,
        )
    )

    return (
        cleaned
        in GENERIC_EVENT_TITLES
    )


# =========================================================
# PUBLISH TIME NORMALIZATION
# =========================================================

def _publish_time_key(
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

        return parsed.replace(
            microsecond=0
        ).isoformat()

    except ValueError:
        pass

    return value


# =========================================================
# CACHE KEYS
# =========================================================

def _evidence_cache_key(
    symbol: str,
    title: str,
    publish_time: str | None,
):
    return (
        _normalize_symbol(
            symbol
        ),
        _normalize_title_key(
            title
        ),
        _publish_time_key(
            publish_time
        ),
    )


def _search_cache_key(
    symbol: str,
    title: str,
    publish_time: str | None = None,
):
    normalized_symbol = (
        _normalize_symbol(
            symbol
        )
    )

    normalized_title = (
        _normalize_title_key(
            title
        )
    )

    # Với generic title, candidate set phải tách theo ngày.
    #
    # Nếu giữ cache chỉ theo symbol + title thì:
    #
    # ABB: Nghị quyết Hội đồng quản trị - 28/09
    #
    # và:
    #
    # ABB: Nghị quyết Hội đồng quản trị - 25/09
    #
    # sẽ dùng chung candidate list, làm mất tác dụng của
    # date-specific Tavily query trong web_search.py.
    if is_generic_news_title(
        normalized_symbol,
        title,
    ):
        date_key = (
            normalize_publish_date(
                publish_time
            )
        )

    else:
        date_key = ""

    return (
        normalized_symbol,
        normalized_title,
        date_key,
    )


# =========================================================
# EVIDENCE CACHE
# =========================================================

def _get_cached_evidence(
    symbol: str,
    title: str,
    publish_time: str | None,
):
    key = _evidence_cache_key(
        symbol,
        title,
        publish_time,
    )

    now = _monotonic_now()

    with _cache_lock:
        cached = (
            _evidence_cache.get(
                key
            )
        )

        if cached is None:
            return False, None

        cached_at, result = cached

        ttl = (
            EVIDENCE_CACHE_TTL_SECONDS
            if result is not None
            else NEGATIVE_EVIDENCE_CACHE_TTL_SECONDS
        )

        if (
            now - cached_at
            >= ttl
        ):
            _evidence_cache.pop(
                key,
                None,
            )

            return False, None

        return True, result


def _set_cached_evidence(
    symbol: str,
    title: str,
    publish_time: str | None,
    result: NewsEvidence | None,
):
    key = _evidence_cache_key(
        symbol,
        title,
        publish_time,
    )

    with _cache_lock:
        _evidence_cache[key] = (
            _monotonic_now(),
            result,
        )


# =========================================================
# SEARCH CANDIDATE CACHE
# =========================================================

def _get_cached_search_candidates(
    symbol: str,
    title: str,
    publish_time: str | None = None,
):
    key = _search_cache_key(
        symbol,
        title,
        publish_time,
    )

    now = _monotonic_now()

    with _cache_lock:
        cached = (
            _search_candidate_cache.get(
                key
            )
        )

        if cached is None:
            return False, []

        cached_at, candidates = cached

        ttl = (
            SEARCH_CANDIDATE_CACHE_TTL_SECONDS
            if candidates
            else EMPTY_SEARCH_CACHE_TTL_SECONDS
        )

        if (
            now - cached_at
            >= ttl
        ):
            _search_candidate_cache.pop(
                key,
                None,
            )

            return False, []

        return True, list(
            candidates
        )


def _set_cached_search_candidates(
    symbol: str,
    title: str,
    publish_time: str | None,
    candidates: list[
        WebSearchCandidate
    ],
):
    key = _search_cache_key(
        symbol,
        title,
        publish_time,
    )

    with _cache_lock:
        _search_candidate_cache[key] = (
            _monotonic_now(),
            list(candidates),
        )


# =========================================================
# URL VERIFY CACHE
# =========================================================

def _get_cached_verified_url(
    url: str,
):
    now = _monotonic_now()

    with _cache_lock:
        cached = (
            _url_verify_cache.get(
                url
            )
        )

        if cached is None:
            return False, None

        cached_at, result = cached

        if (
            now - cached_at
            >= URL_VERIFY_CACHE_TTL_SECONDS
        ):
            _url_verify_cache.pop(
                url,
                None,
            )

            return False, None

        return True, result


def _set_cached_verified_url(
    url: str,
    result: str | None,
):
    with _cache_lock:
        _url_verify_cache[url] = (
            _monotonic_now(),
            result,
        )


# =========================================================
# COLLISION REGISTRY
# =========================================================

def _register_evidence_url_event(
    url: str,
    symbol: str,
    title: str,
    publish_time: str | None,
):
    event_key = (
        _evidence_cache_key(
            symbol,
            title,
            publish_time,
        )
    )

    with _cache_lock:
        events = (
            _evidence_url_event_registry
            .setdefault(
                url,
                set(),
            )
        )

        events.add(
            event_key
        )


def _has_evidence_collision(
    url: str,
    symbol: str,
    title: str,
    publish_time: str | None,
) -> bool:
    # Chỉ guard title chung.
    if not _is_generic_event_title(
        symbol,
        title,
    ):
        return False

    logger.debug(
        "Generic title collision guard active | "
        "symbol=%s | title=%s | publish_time=%s",
        symbol,
        title[:100],
        _publish_time_key(
            publish_time
        ),
    )

    event_key = (
        _evidence_cache_key(
            symbol,
            title,
            publish_time,
        )
    )

    with _cache_lock:
        existing_events = (
            _evidence_url_event_registry
            .get(
                url,
                set(),
            )
        )

        if not existing_events:
            return False

        # Nếu URL đã được đăng ký cho đúng event hiện tại
        # thì không phải collision.
        if (
            event_key
            in existing_events
        ):
            return False

        # Generic title + URL đã thuộc event khác.
        return True


# =========================================================
# CACHE MANAGEMENT
# =========================================================

def clear_news_evidence_cache():
    with _cache_lock:
        _evidence_cache.clear()
        _search_candidate_cache.clear()
        _url_verify_cache.clear()
        _evidence_url_event_registry.clear()

    logger.info(
        "News evidence caches cleared"
    )


def get_news_evidence_cache_stats():
    with _cache_lock:
        return {
            "evidence_entries": len(
                _evidence_cache
            ),
            "search_candidate_entries": len(
                _search_candidate_cache
            ),
            "url_verify_entries": len(
                _url_verify_cache
            ),
            "collision_registry_urls": len(
                _evidence_url_event_registry
            ),
        }


# =========================================================
# URL HELPERS
# =========================================================

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


def _hostname_from_url(
    value: str,
) -> str:
    try:
        host = (
            urlparse(
                value
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


def _friendly_source_name(
    candidate: WebSearchCandidate,
) -> str:
    domain = (
        candidate.source_domain
        or _hostname_from_url(
            candidate.url
        )
    )

    source_map = {
        "cafef.vn": "CafeF",
        "stockbiz.vn": "StockBiz",
        "masvn.com": "Mirae Asset",
        "vietstock.vn": "Vietstock",
        "phs.vn": "PHS",
        "ssi.com.vn": "SSI",
        "vndirect.com.vn": "VNDIRECT",
        "bsc.com.vn": "BSC",
        "new.bsc.com.vn": "BSC",
        "bc.bsc.com.vn": "BSC",
        "fpt.com": "FPT",
        "hsx.vn": "HOSE",
        "hnx.vn": "HNX",
    }

    if domain in source_map:
        return source_map[
            domain
        ]

    return (
        domain
        or "Nguồn web"
    )


# =========================================================
# HTTP VERIFICATION
# =========================================================

def verify_evidence_url(
    url: str | None,
) -> str | None:
    if not _is_http_url(
        url
    ):
        return None

    cleaned_url = (
        url
        .strip()
    )

    cache_hit, cached = (
        _get_cached_verified_url(
            cleaned_url
        )
    )

    if cache_hit:
        logger.debug(
            "Evidence URL verify cache HIT | url=%s",
            cleaned_url,
        )

        return cached

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "*/*;q=0.8"
        ),
    }

    verified_url = None

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=HTTP_TIMEOUT_SECONDS,
            headers=headers,
        ) as http_client:

            try:
                response = (
                    http_client.head(
                        cleaned_url
                    )
                )

                if (
                    200
                    <= response.status_code
                    < 400
                ):
                    final_url = str(
                        response.url
                    )

                    if _is_http_url(
                        final_url
                    ):
                        verified_url = (
                            final_url
                        )

            except httpx.HTTPError:
                pass

            if verified_url is None:
                try:
                    response = (
                        http_client.get(
                            cleaned_url
                        )
                    )

                    if (
                        200
                        <= response.status_code
                        < 400
                    ):
                        final_url = str(
                            response.url
                        )

                        if _is_http_url(
                            final_url
                        ):
                            verified_url = (
                                final_url
                            )

                except httpx.HTTPError:
                    pass

    except Exception as exc:
        logger.debug(
            "Evidence URL verification failed | "
            "url=%s | error=%s",
            cleaned_url,
            exc,
        )

    _set_cached_verified_url(
        cleaned_url,
        verified_url,
    )

    return verified_url


# =========================================================
# GEMINI MATCH PROMPT
# =========================================================

def _build_match_prompt(
    symbol: str,
    title: str,
    publish_time: str | None,
    candidates: list[
        WebSearchCandidate
    ],
) -> str:
    candidate_blocks = []

    for candidate_id, item in enumerate(
        candidates
    ):
        snippet = (
            item.content
            or ""
        )

        if len(snippet) > 700:
            snippet = (
                snippet[:700]
                + "..."
            )

        candidate_blocks.append(
            f"""
CANDIDATE_ID: {candidate_id}
TITLE: {item.title}
DOMAIN: {item.source_domain}
SNIPPET: {snippet}
LOCAL_RELEVANCE: {item.relevance_score}
""".strip()
        )

    candidates_text = (
        "\n\n".join(
            candidate_blocks
        )
    )

    return f"""
Bạn đang xác minh nguồn dẫn chứng cho một tin tức
chứng khoán Việt Nam.

TIN GỐC:

Mã cổ phiếu:
{symbol}

Tiêu đề:
{title}

Thời gian:
{publish_time or "không rõ"}

DANH SÁCH CANDIDATE:

{candidates_text}

NHIỆM VỤ:

Chỉ chọn candidate nếu candidate đó nói về CÙNG
SỰ KIỆN hoặc CÙNG THÔNG BÁO với tin gốc.

QUY TẮC BẮT BUỘC:

1. Không chọn bài chỉ vì cùng nói về {symbol}.

2. Không chọn bài chỉ vì cùng nhắc đến phát hành cổ
   phiếu, tăng vốn, HĐQT hoặc nghị quyết.

3. Các chi tiết quan trọng phải tương ứng, ví dụ:
   - loại quyết định / nghị quyết;
   - cơ quan ban hành;
   - phương án phát hành;
   - mục đích tăng vốn;
   - nguồn vốn chủ sở hữu nếu tiêu đề gốc có nêu.

4. Phải chú ý thời gian của tin gốc.

5. Với tiêu đề quá chung như:
   "Nghị quyết Hội đồng quản trị"
   thì không được chỉ dựa vào việc title giống nhau.

6. Nếu candidate nói về một nghị quyết khác, đợt phát
   hành khác hoặc sự kiện khác thì không chọn.

7. Không được tạo URL.

8. Không được tạo candidate mới.

9. Chỉ được trả matched_candidate_id thuộc danh sách
   đã cung cấp.

10. Nếu không candidate nào đủ chắc chắn:
    matched_candidate_id phải là null.

11. confidence chỉ được là:
    - high
    - medium
    - low

12. Chỉ dùng confidence high hoặc medium khi thực sự
    có bằng chứng rằng hai tiêu đề/snippet nói về cùng
    sự kiện.

Trả kết quả đúng schema.
""".strip()


# =========================================================
# GEMINI MATCH GENERATION
# =========================================================

def _match_with_model(
    model: str,
    prompt: str,
) -> EvidenceMatchResult:
    logger.info(
        "Gemini evidence match request | "
        "model=%s",
        model,
    )

    response = (
        client.models.generate_content(
            model=model,
            contents=prompt,
            config=(
                types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=500,
                    response_mime_type=(
                        "application/json"
                    ),
                    response_schema=(
                        EvidenceMatchResult
                    ),
                )
            ),
        )
    )

    parsed = getattr(
        response,
        "parsed",
        None,
    )

    if isinstance(
        parsed,
        EvidenceMatchResult,
    ):
        return parsed

    if isinstance(
        parsed,
        dict,
    ):
        return (
            EvidenceMatchResult
            .model_validate(
                parsed
            )
        )

    if (
        parsed is not None
        and hasattr(
            parsed,
            "model_dump",
        )
    ):
        return (
            EvidenceMatchResult
            .model_validate(
                parsed.model_dump()
            )
        )

    text = getattr(
        response,
        "text",
        None,
    )

    if not text:
        raise RuntimeError(
            "Gemini returned empty evidence match"
        )

    return (
        EvidenceMatchResult
        .model_validate_json(
            text
        )
    )


def _match_with_fallback(
    prompt: str,
) -> EvidenceMatchResult | None:
    models = []

    for model in (
        GEMINI_MODEL,
        GEMINI_FALLBACK_MODEL,
    ):
        if (
            model
            and model
            not in models
        ):
            models.append(
                model
            )

    for model in models:
        try:
            result = (
                _match_with_model(
                    model=model,
                    prompt=prompt,
                )
            )

            logger.info(
                "Gemini evidence match completed | "
                "model=%s | candidate_id=%s | "
                "confidence=%s",
                model,
                result.matched_candidate_id,
                result.confidence,
            )

            return result

        except ClientError as exc:
            logger.warning(
                "Gemini evidence match client error | "
                "model=%s | error=%s",
                model,
                exc,
            )

            continue

        except ServerError as exc:
            logger.warning(
                "Gemini evidence match server error | "
                "model=%s | error=%s",
                model,
                exc,
            )

            continue

        except (
            ValidationError,
            ValueError,
            TypeError,
            RuntimeError,
        ) as exc:
            logger.warning(
                "Gemini evidence match invalid output | "
                "model=%s | error=%s",
                model,
                exc,
            )

            continue

    return None


# =========================================================
# CANDIDATE SELECTION
# =========================================================

def match_news_candidate(
    symbol: str,
    title: str,
    publish_time: str | None,
    candidates: list[
        WebSearchCandidate
    ],
    excluded_urls: set[str] | None = None,
) -> WebSearchCandidate | None:
    if not candidates:
        return None

    excluded_urls = (
        excluded_urls
        or set()
    )

    filtered_candidates = [
        candidate
        for candidate in candidates
        if (
            candidate.relevance_score
            >= MIN_ACCEPTED_LOCAL_RELEVANCE
            and candidate.url
            not in excluded_urls
        )
    ]

    if not filtered_candidates:
        logger.info(
            "No candidates passed evidence filters | "
            "symbol=%s",
            symbol,
        )

        return None

    prompt = _build_match_prompt(
        symbol=symbol,
        title=title,
        publish_time=publish_time,
        candidates=filtered_candidates,
    )

    match = (
        _match_with_fallback(
            prompt
        )
    )

    if match is None:
        return None

    candidate_id = (
        match.matched_candidate_id
    )

    if candidate_id is None:
        logger.info(
            "Gemini rejected all evidence candidates | "
            "symbol=%s",
            symbol,
        )

        return None

    if (
        candidate_id < 0
        or candidate_id
        >= len(
            filtered_candidates
        )
    ):
        logger.warning(
            "Gemini returned invalid candidate id | "
            "symbol=%s | candidate_id=%s",
            symbol,
            candidate_id,
        )

        return None

    confidence = (
        match.confidence
        .strip()
        .lower()
    )

    if confidence not in {
        "high",
        "medium",
    }:
        logger.info(
            "Evidence candidate rejected due to "
            "low confidence | symbol=%s | "
            "candidate_id=%s",
            symbol,
            candidate_id,
        )

        return None

    selected = (
        filtered_candidates[
            candidate_id
        ]
    )

    logger.info(
        "Evidence candidate selected | "
        "symbol=%s | "
        "domain=%s | "
        "relevance=%.4f | "
        "confidence=%s",
        symbol,
        selected.source_domain,
        selected.relevance_score,
        confidence,
    )

    return selected


# =========================================================
# SEARCH CANDIDATE RESOLUTION
# =========================================================

def _get_or_search_candidates(
    symbol: str,
    title: str,
    publish_time: str | None,
) -> list[
    WebSearchCandidate
]:
    cache_hit, cached_candidates = (
        _get_cached_search_candidates(
            symbol,
            title,
            publish_time,
        )
    )

    if cache_hit:
        logger.info(
            "News candidate search cache HIT | "
            "symbol=%s | title=%s | date=%s | count=%s",
            symbol,
            title[:100],
            (
                normalize_publish_date(
                    publish_time
                )
                if is_generic_news_title(
                    symbol,
                    title,
                )
                else "shared"
            ),
            len(cached_candidates),
        )

        return cached_candidates

    candidates = (
        search_news_candidates(
            symbol=symbol,
            title=title,
            publish_time=(
                publish_time
            ),
            max_results=(
                SEARCH_CANDIDATE_LIMIT
            ),
        )
    )

    _set_cached_search_candidates(
        symbol,
        title,
        publish_time,
        candidates,
    )

    return candidates


# =========================================================
# WEB FALLBACK
# =========================================================

def search_news_evidence(
    symbol: str,
    title: str,
    publish_time: str | None = None,
) -> NewsEvidence | None:
    symbol = (
        _normalize_symbol(
            symbol
        )
    )

    title = title.strip()

    if not symbol or not title:
        return None

    cache_hit, cached = (
        _get_cached_evidence(
            symbol,
            title,
            publish_time,
        )
    )

    if cache_hit:
        logger.info(
            "News evidence cache HIT | "
            "symbol=%s | title=%s | publish_time=%s",
            symbol,
            title[:100],
            _publish_time_key(
                publish_time
            ),
        )

        return cached

    logger.info(
        "Searching web evidence | "
        "symbol=%s | title=%s",
        symbol,
        title[:120],
    )

    candidates = (
        _get_or_search_candidates(
            symbol=symbol,
            title=title,
            publish_time=(
                publish_time
            ),
        )
    )

    logger.info(
        "Web evidence candidates ready | "
        "symbol=%s | count=%s",
        symbol,
        len(candidates),
    )

    excluded_urls: set[str] = set()

    # Tối đa thử bằng số candidate hiện có.
    #
    # Nếu candidate bị collision, không search Tavily lại.
    # Chỉ cho Gemini chọn tiếp trong danh sách còn lại.
    for attempt in range(
        len(candidates)
    ):
        selected = (
            match_news_candidate(
                symbol=symbol,
                title=title,
                publish_time=(
                    publish_time
                ),
                candidates=candidates,
                excluded_urls=(
                    excluded_urls
                ),
            )
        )

        if selected is None:
            break

        verified_url = (
            verify_evidence_url(
                selected.url
            )
        )

        if not verified_url:
            logger.warning(
                "Selected evidence URL failed "
                "HTTP verification | "
                "symbol=%s | url=%s",
                symbol,
                selected.url,
            )

            excluded_urls.add(
                selected.url
            )

            continue

        if _has_evidence_collision(
            verified_url,
            symbol,
            title,
            publish_time,
        ):
            logger.warning(
                "Evidence collision detected | "
                "symbol=%s | "
                "title=%s | "
                "publish_time=%s | "
                "url=%s | "
                "attempt=%s",
                symbol,
                title[:100],
                _publish_time_key(
                    publish_time
                ),
                verified_url,
                attempt + 1,
            )

            # Loại cả URL candidate ban đầu và final URL sau redirect.
            excluded_urls.add(
                selected.url
            )

            excluded_urls.add(
                verified_url
            )

            continue

        evidence = NewsEvidence(
            url=verified_url,
            source=(
                _friendly_source_name(
                    selected
                )
            ),
            method=(
                "tavily_gemini_match"
            ),
            verified=True,
        )

        _set_cached_evidence(
            symbol,
            title,
            publish_time,
            evidence,
        )

        _register_evidence_url_event(
            evidence.url,
            symbol,
            title,
            publish_time,
        )

        logger.info(
            "Fallback evidence verified | "
            "symbol=%s | "
            "source=%s | "
            "url=%s",
            symbol,
            evidence.source,
            evidence.url,
        )

        return evidence

    _set_cached_evidence(
        symbol,
        title,
        publish_time,
        None,
    )

    logger.info(
        "No safe verified evidence after collision guard | "
        "symbol=%s | title=%s",
        symbol,
        title[:120],
    )

    return None


# =========================================================
# DIRECT + FALLBACK
# =========================================================

def resolve_news_evidence(
    symbol: str,
    title: str,
    publish_time: str | None = None,
    original_url: str | None = None,
    original_source: str | None = None,
) -> NewsEvidence | None:
    symbol = (
        _normalize_symbol(
            symbol
        )
    )

    title = title.strip()

    if not symbol or not title:
        return None

    cache_hit, cached = (
        _get_cached_evidence(
            symbol,
            title,
            publish_time,
        )
    )

    if cache_hit:
        logger.info(
            "News evidence cache HIT | "
            "symbol=%s | title=%s | publish_time=%s",
            symbol,
            title[:100],
            _publish_time_key(
                publish_time
            ),
        )

        return cached

    # -----------------------------------------------------
    # DIRECT ORIGINAL URL
    # -----------------------------------------------------

    if original_url:
        logger.info(
            "Checking original news URL | "
            "symbol=%s | source=%s",
            symbol,
            (
                original_source
                or "unknown"
            ),
        )

        verified_original = (
            verify_evidence_url(
                original_url
            )
        )

        if verified_original:
            logger.info(
                "Original news URL verified | "
                "symbol=%s | source=%s",
                symbol,
                (
                    original_source
                    or "unknown"
                ),
            )

            evidence = NewsEvidence(
                url=verified_original,
                source=(
                    original_source
                    or _hostname_from_url(
                        verified_original
                    )
                    or "Nguồn gốc"
                ),
                method="direct",
                verified=True,
            )

            _set_cached_evidence(
                symbol,
                title,
                publish_time,
                evidence,
            )

            # Direct source vẫn được đăng ký để fallback của một
            # generic event khác không vô tình dùng lại URL này.
            _register_evidence_url_event(
                evidence.url,
                symbol,
                title,
                publish_time,
            )

            return evidence

        logger.info(
            "Original news URL unavailable | "
            "symbol=%s | "
            "fallback_to_web_search=true",
            symbol,
        )

    else:
        logger.info(
            "Original news URL missing | "
            "symbol=%s | "
            "fallback_to_web_search=true",
            symbol,
        )

    return search_news_evidence(
        symbol=symbol,
        title=title,
        publish_time=publish_time,
    )
