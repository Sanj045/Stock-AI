export type StockNewsItem = {
    article_id: number | string
    title: string
    summary?: string | null
    publish_time?: string | null

    url?: string | null
    image_url?: string | null
    source?: string | null

    summary_available?: boolean
    url_available?: boolean

    original_url?: string | null
    original_source?: string | null

    evidence_url?: string | null
    evidence_source?: string | null
    evidence_method?: string | null
    evidence_verified?: boolean

    url_verified?: boolean
}

export type StockNewsResponse = {
    symbol: string
    count: number
    data: StockNewsItem[]
}