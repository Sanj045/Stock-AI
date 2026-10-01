export type StockLatest = {
    time?: string | null
    open: number
    high: number
    low: number
    close: number
    volume: number
}

export type StockLatestResponse = {
    symbol: string
    data: StockLatest
}