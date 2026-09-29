import re
from functools import lru_cache

from stock.service import get_company_info
from logger import logger


# Những từ viết hoa thường xuất hiện trong câu hỏi
# nhưng không phải mã cổ phiếu.
IGNORED_SYMBOLS = {
    "API",
    "CEO",
    "CFO",
    "CTO",
    "EPS",
    "ROE",
    "ROA",
    "EBIT",
    "NAV",
    "GDP",
    "ETF",
    "IPO",
    "HOSE",
    "HNX",
    "UPCOM",
    "VCI",
    "KBS"
}


@lru_cache(maxsize=500)
def is_valid_stock_symbol(
    symbol: str
) -> bool:
    symbol = symbol.strip().upper()

    if not symbol:
        return False

    if symbol in IGNORED_SYMBOLS:
        return False

    try:
        data = get_company_info(symbol)

        if data is None:
            return False

        if data.empty:
            return False

        return True

    except Exception as exc:
        logger.debug(
            "Symbol validation failed for %s: %s",
            symbol,
            exc
        )

        return False


def extract_stock_candidates(
    message: str
) -> list[str]:
    if not message:
        return []

    candidates = []

    # =====================================================
    # Kiểu 1:
    # "mã FPT"
    # "cổ phiếu FPT"
    # "cp FPT"
    #
    # Hỗ trợ cả fpt viết thường.
    # =====================================================

    keyword_pattern = re.compile(
        r"\b(?:mã|cổ\s+phiếu|cp|stock|ticker)"
        r"\s*[:\-]?\s*([a-zA-Z]{3})\b",
        re.IGNORECASE
    )

    for match in keyword_pattern.findall(message):
        symbol = match.upper()

        if symbol not in candidates:
            candidates.append(symbol)

    # =====================================================
    # Kiểu 2:
    # chữ viết hoa 3 ký tự như FPT, HPG, VNM
    # =====================================================

    uppercase_pattern = re.compile(
        r"(?<![A-Z0-9])([A-Z]{3})(?![A-Z0-9])"
    )

    for match in uppercase_pattern.findall(message):
        symbol = match.upper()

        if symbol not in candidates:
            candidates.append(symbol)

    return candidates


def detect_stock_symbol(
    message: str
) -> str | None:
    candidates = extract_stock_candidates(
        message
    )

    for symbol in candidates:
        if is_valid_stock_symbol(symbol):
            logger.info(
                "Detected stock symbol %s from chat message",
                symbol
            )

            return symbol

    return None


def detect_symbol_from_history(
    history: list[dict] | None
) -> str | None:
    if not history:
        return None

    # Tìm từ message gần nhất trở về trước.
    for item in reversed(history):
        question = item.get(
            "question",
            ""
        )

        symbol = detect_stock_symbol(
            question
        )

        if symbol:
            return symbol

    return None