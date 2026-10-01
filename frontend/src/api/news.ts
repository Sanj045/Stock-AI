import api from './axios'

import type {
    StockNewsItem,
    StockNewsResponse,
} from '../types/news'

export async function getStockNews(
    symbol: string,
    limit = 3,
): Promise<StockNewsItem[]> {
    const normalizedSymbol = symbol
        .trim()
        .toUpperCase()

    const response =
        await api.get<StockNewsResponse>(
            `/stocks/${encodeURIComponent(
                normalizedSymbol,
            )}/news`,
            {
                params: {
                    limit,
                },
            },
        )

    return response.data.data
}