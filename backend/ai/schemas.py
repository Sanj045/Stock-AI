from pydantic import BaseModel, Field


# =========================================================
# GENERIC ANALYSIS SECTION
# =========================================================

class AnalysisSection(BaseModel):
    summary: str = Field(
        description=(
            "Tóm tắt ngắn gọn bằng tiếng Việt, "
            "chỉ dựa trên dữ liệu được cung cấp."
        )
    )

    facts: list[str] = Field(
        default_factory=list,
        description=(
            "Các dữ liệu hoặc thống kê thực tế "
            "được sử dụng trong phần phân tích."
        )
    )

    interpretation: list[str] = Field(
        default_factory=list,
        description=(
            "Các nhận định trung tính được phép suy ra "
            "từ dữ liệu, không dự báo chắc chắn."
        )
    )


# =========================================================
# NEWS SECTION
# =========================================================

class NewsItem(BaseModel):
    title: str

    source: str | None = None

    publish_time: str | None = None

    summary_available: bool = False

    url_available: bool = False

    url: str | None = None


class NewsAnalysisSection(BaseModel):
    summary: str

    items: list[NewsItem] = Field(
        default_factory=list
    )

    limitations: list[str] = Field(
        default_factory=list
    )


# =========================================================
# RISK SECTION
# =========================================================

class RiskItem(BaseModel):
    title: str

    description: str

    evidence: list[str] = Field(
        default_factory=list
    )


class RisksSection(BaseModel):
    summary: str

    items: list[RiskItem] = Field(
        default_factory=list
    )


# =========================================================
# DATA LIMIT
# =========================================================

class DataLimitsSection(BaseModel):
    limitations: list[str] = Field(
        default_factory=list
    )


# =========================================================
# STRUCTURED STOCK ANALYSIS
# =========================================================

class StructuredStockAnalysis(BaseModel):
    symbol: str

    analysis_type: str = "structured_stock_analysis"

    price_trend: AnalysisSection

    momentum: AnalysisSection

    volume: AnalysisSection

    volatility: AnalysisSection

    fundamentals: AnalysisSection

    news: NewsAnalysisSection

    risks: RisksSection

    data_limits: DataLimitsSection