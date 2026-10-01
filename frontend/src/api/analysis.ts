import api from './axios'

import type { StructuredStockAnalysis } from '../types/analysis'

export async function analyzeStockStructured(
    symbol: string,
): Promise<StructuredStockAnalysis> {
    const normalizedSymbol = symbol
        .trim()
        .toUpperCase()

    const response =
        await api.post<StructuredStockAnalysis>(
            `/stocks/${encodeURIComponent(
                normalizedSymbol,
            )}/analyze/structured`,
        )

    return response.data
}