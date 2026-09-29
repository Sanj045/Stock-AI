from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query
)

from dependencies import get_current_user

from logger import logger

from models import User

from schemas import (
    StockAnalyzeRequest
)

from ai.schemas import (
    StructuredStockAnalysis
)

from ai.service import (
    analyze_stock,
    analyze_stock_structured
)

from stock.context import (
    build_stock_context
)

from stock.service import (
    get_stock_history,
    get_latest_stock,
    get_company_info,
    get_financial_ratios,
    get_stock_news
)


router = APIRouter(
    prefix="/stocks",
    tags=["stocks"]
)


# =========================================================
# SYMBOL HELPERS
# =========================================================

def _normalize_symbol(
    symbol: str
) -> str:

    symbol = (
        symbol
        .strip()
        .upper()
    )


    if not symbol:

        raise HTTPException(
            status_code=400,
            detail="Stock symbol is required"
        )


    if len(symbol) > 10:

        raise HTTPException(
            status_code=400,
            detail="Invalid stock symbol format"
        )


    return symbol


def _ensure_valid_stock_symbol(
    symbol: str
) -> None:
    """
    Validate ticker before building context / calling Gemini.

    Rules:
    - Valid company data:
        symbol is accepted.

    - Vnstock's known invalid-symbol ValueError:
        404.

    - Empty company data:
        404.

    - Other upstream / parsing / network errors:
        503.

    Internal exception details stay in server logs.
    """

    try:

        company = get_company_info(
            symbol
        )


    except ValueError as exc:

        message = str(
            exc
        ).lower()


        if (
            "invalid symbol" in message
            and "not recognized" in message
        ):

            logger.info(
                "Invalid stock symbol | symbol=%s",
                symbol
            )


            raise HTTPException(
                status_code=404,
                detail=(
                    f"Stock symbol '{symbol}' "
                    "was not found"
                )
            ) from exc


        logger.exception(
            "Stock symbol validation ValueError | "
            "symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=503,
            detail=(
                "Stock symbol validation service "
                "is temporarily unavailable"
            )
        ) from exc


    except Exception as exc:

        logger.exception(
            "Stock symbol validation failed | "
            "symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=503,
            detail=(
                "Stock symbol validation service "
                "is temporarily unavailable"
            )
        ) from exc


    if (
        company is None
        or company.empty
    ):

        logger.info(
            "Stock symbol returned no company data | "
            "symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=404,
            detail=(
                f"Stock symbol '{symbol}' "
                "was not found"
            )
        )


# =========================================================
# STOCK HISTORY
# =========================================================

@router.get(
    "/{symbol}/history"
)
def stock_history(
    symbol: str,

    start: date = Query(
        ...,
        description="Start date YYYY-MM-DD"
    ),

    end: date = Query(
        ...,
        description="End date YYYY-MM-DD"
    ),

    interval: str = Query(
        default="1D"
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    symbol = _normalize_symbol(
        symbol
    )


    try:

        data = get_stock_history(
            symbol=symbol,
            start=start.strftime(
                "%Y-%m-%d"
            ),
            end=end.strftime(
                "%Y-%m-%d"
            ),
            interval=interval
        )


        if (
            data is None
            or data.empty
        ):

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No stock history found "
                    f"for {symbol}"
                )
            )


        return {

            "symbol": symbol,

            "count": len(
                data
            ),

            "data": data.to_dict(
                orient="records"
            )
        }


    except HTTPException:
        raise


    except Exception:

        logger.exception(
            "Failed to fetch stock history | "
            "symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to fetch stock history"
            )
        )


# =========================================================
# LATEST STOCK
# =========================================================

@router.get(
    "/{symbol}/latest"
)
def stock_latest(
    symbol: str,

    current_user: User = Depends(
        get_current_user
    )
):

    symbol = _normalize_symbol(
        symbol
    )


    try:

        data = get_latest_stock(
            symbol
        )


        if data is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No latest stock data found "
                    f"for {symbol}"
                )
            )


        return {

            "symbol": symbol,

            "data": data.to_dict()
        }


    except HTTPException:
        raise


    except Exception:

        logger.exception(
            "Failed to fetch latest stock data | "
            "symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to fetch latest stock data"
            )
        )


# =========================================================
# COMPANY INFO
# =========================================================

@router.get(
    "/{symbol}/company"
)
def stock_company(
    symbol: str,

    current_user: User = Depends(
        get_current_user
    )
):

    symbol = _normalize_symbol(
        symbol
    )


    try:

        data = get_company_info(
            symbol
        )


        if (
            data is None
            or data.empty
        ):

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No company information found "
                    f"for {symbol}"
                )
            )


        return {

            "symbol": symbol,

            "data": data.to_dict(
                orient="records"
            )
        }


    except HTTPException:
        raise


    except Exception:

        logger.exception(
            "Failed to fetch company information | "
            "symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to fetch company information"
            )
        )


# =========================================================
# FUNDAMENTALS
# =========================================================

@router.get(
    "/{symbol}/fundamentals"
)
def stock_fundamentals(
    symbol: str,

    period: str = Query(
        default="quarter"
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    symbol = _normalize_symbol(
        symbol
    )


    try:

        data = get_financial_ratios(
            symbol=symbol,
            period=period
        )


        if (
            data is None
            or data.empty
        ):

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No financial ratios found "
                    f"for {symbol}"
                )
            )


        return {

            "symbol": symbol,

            "period": period,

            "count": len(
                data
            ),

            "data": data.to_dict(
                orient="records"
            )
        }


    except HTTPException:
        raise


    except Exception:

        logger.exception(
            "Failed to fetch fundamentals | "
            "symbol=%s | period=%s",
            symbol,
            period
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to fetch fundamentals"
            )
        )


# =========================================================
# NEWS
# =========================================================

@router.get(
    "/{symbol}/news"
)
def stock_news(
    symbol: str,

    limit: int = Query(
        default=8,
        ge=1,
        le=50
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    symbol = _normalize_symbol(
        symbol
    )


    try:

        data = get_stock_news(
            symbol=symbol,
            limit=limit
        )


        if (
            data is None
            or data.empty
        ):

            return {

                "symbol": symbol,

                "count": 0,

                "data": []
            }


        return {

            "symbol": symbol,

            "count": len(
                data
            ),

            "data": data.to_dict(
                orient="records"
            )
        }


    except HTTPException:
        raise


    except Exception:

        logger.exception(
            "Failed to fetch stock news | "
            "symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to fetch stock news"
            )
        )


# =========================================================
# NORMAL TEXT STOCK ANALYSIS
# =========================================================

@router.post(
    "/{symbol}/analyze"
)
def stock_analyze(
    symbol: str,

    data: StockAnalyzeRequest,

    current_user: User = Depends(
        get_current_user
    )
):

    symbol = _normalize_symbol(
        symbol
    )


    # -----------------------------------------------------
    # Validate ticker BEFORE context + Gemini
    # -----------------------------------------------------

    _ensure_valid_stock_symbol(
        symbol
    )


    try:

        stock_context = (
            build_stock_context(
                symbol
            )
        )


        answer = analyze_stock(
            symbol=symbol,
            stock_context=stock_context,
            question=data.question
        )


        return {

            "symbol": symbol,

            "answer": answer
        }


    except HTTPException:
        raise


    except Exception:

        logger.exception(
            "Failed to analyze stock | "
            "symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to analyze stock"
            )
        )


# =========================================================
# STRUCTURED STOCK ANALYSIS
# =========================================================

@router.post(
    "/{symbol}/analyze/structured",
    response_model=StructuredStockAnalysis
)
def stock_analyze_structured(
    symbol: str,

    current_user: User = Depends(
        get_current_user
    )
):

    symbol = _normalize_symbol(
        symbol
    )


    # -----------------------------------------------------
    # Validate ticker BEFORE context + Gemini
    # -----------------------------------------------------

    _ensure_valid_stock_symbol(
        symbol
    )


    try:

        # -------------------------------------------------
        # Build resilient + cached stock context
        # -------------------------------------------------

        stock_context = (
            build_stock_context(
                symbol
            )
        )


        # -------------------------------------------------
        # Gemini structured analysis
        # -------------------------------------------------

        analysis = (
            analyze_stock_structured(
                symbol=symbol,
                stock_context=stock_context
            )
        )


        # -------------------------------------------------
        # Sanity check
        # -------------------------------------------------

        if (
            analysis.get(
                "symbol"
            )
            != symbol
        ):

            raise RuntimeError(
                "Structured analysis returned "
                "an unexpected stock symbol"
            )


        return analysis


    except HTTPException:
        raise


    except Exception:

        logger.exception(
            "Failed to generate structured "
            "stock analysis | symbol=%s",
            symbol
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate structured "
                "stock analysis"
            )
        )