import api from './axios'

import type {
    WatchlistCreateRequest,
    WatchlistItem,
} from '../types/watchlist'

export async function getWatchlist(): Promise<
    WatchlistItem[]
> {
    const response =
        await api.get<WatchlistItem[]>(
            '/watchlist',
        )

    return response.data
}

export async function addToWatchlist(
    payload: WatchlistCreateRequest,
): Promise<WatchlistItem> {
    const response =
        await api.post<WatchlistItem>(
            '/watchlist',
            payload,
        )

    return response.data
}

export async function removeFromWatchlist(
    symbol: string,
): Promise<void> {
    await api.delete(
        `/watchlist/${encodeURIComponent(
            symbol,
        )}`,
    )
}