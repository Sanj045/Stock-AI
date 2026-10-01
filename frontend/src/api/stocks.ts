import api from './axios'

import type {
    StockLatest,
    StockLatestResponse,
} from '../types/stock'

export async function getLatestStock(
    symbol: string,
): Promise<StockLatest> {
    const normalizedSymbol = symbol
        .trim()
        .toUpperCase()

    const response =
        await api.get<StockLatestResponse>(
            `/stocks/${encodeURIComponent(
                normalizedSymbol,
            )}/latest`,
        )

    return response.data.data
}