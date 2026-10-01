export type AnalysisSection = {
    summary: string
    facts: string[]
    interpretation: string[]
}

export type AnalysisNewsItem = {
    title?: string
    summary?: string | null
    url?: string | null
    published_at?: string | null
}

export type AnalysisNewsSection = {
    summary: string
    items: AnalysisNewsItem[]
    limitations: string[]
}

export type AnalysisRiskItem = {
    title: string
    description: string
    evidence: string[]
}

export type AnalysisRiskSection = {
    summary: string
    items: AnalysisRiskItem[]
}

export type AnalysisDataLimits = {
    limitations: string[]
}

export type StructuredStockAnalysis = {
    symbol: string
    analysis_type: string

    price_trend: AnalysisSection
    momentum: AnalysisSection
    volume: AnalysisSection
    volatility: AnalysisSection
    fundamentals: AnalysisSection

    news: AnalysisNewsSection
    risks: AnalysisRiskSection
    data_limits: AnalysisDataLimits
}