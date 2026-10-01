import axios from 'axios'
import {
    ArrowRight,
    ChartNoAxesCombined,
    CircleAlert,
    Clock3,
    LoaderCircle,
    MessageSquareText,
    RefreshCw,
    Search,
    ShieldCheck,
    Star,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import type { FormEvent } from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getLatestStock } from '../api/stocks'
import { getWatchlist } from '../api/watchlist'
import AIAnalysisPreview from '../components/dashboard/AIAnalysisPreview'
import NewsPreview from '../components/dashboard/NewsPreview'
import { useAuthStore } from '../store/auth.store'

function formatNumber(value: number) {
    return new Intl.NumberFormat('vi-VN', {
        maximumFractionDigits: 2,
    }).format(value)
}

function formatVolume(value: number) {
    if (value >= 1_000_000) {
        return `${formatNumber(
            value / 1_000_000,
        )}M`
    }

    if (value >= 1_000) {
        return `${formatNumber(
            value / 1_000,
        )}K`
    }

    return formatNumber(value)
}

function formatDataTime(
    value?: string | null,
) {
    if (
        !value ||
        typeof value !== 'string'
    ) {
        return 'Chưa rõ thời gian'
    }

    const [datePart, timePart] =
        value.split('T')

    if (!datePart) {
        return value
    }

    const [year, month, day] =
        datePart.split('-')

    if (!year || !month || !day) {
        return value
    }

    const time =
        timePart?.slice(0, 5) || ''

    return `${day}/${month}/${year}${time ? ` ${time}` : ''
        }`
}

function DashboardPage() {
    const navigate = useNavigate()

    const user = useAuthStore(
        (state) => state.user,
    )

    const [searchValue, setSearchValue] =
        useState('')

    const [searchError, setSearchError] =
        useState<string | null>(null)

    const [isSearching, setIsSearching] =
        useState(false)

    const username =
        user?.username || 'người dùng'

    const watchlistQuery = useQuery({
        queryKey: ['watchlist'],
        queryFn: getWatchlist,
        staleTime: 60_000,
    })

    const watchlistPreview =
        watchlistQuery.data?.slice(0, 5) ??
        []

    const watchlistSymbols =
        watchlistPreview.map(
            (item) => item.symbol,
        )

    const latestQuotesQuery = useQuery({
        queryKey: [
            'dashboard-watchlist-latest',
            ...watchlistSymbols,
        ],

        enabled:
            watchlistSymbols.length > 0,

        staleTime: 60_000,

        queryFn: async () => {
            const results =
                await Promise.all(
                    watchlistSymbols.map(
                        async (symbol) => {
                            try {
                                const latest =
                                    await getLatestStock(
                                        symbol,
                                    )

                                return {
                                    symbol,
                                    latest,
                                    available: true,
                                }
                            } catch {
                                return {
                                    symbol,
                                    latest: null,
                                    available: false,
                                }
                            }
                        },
                    ),
                )

            return results
        },
    })

    const latestQuotes =
        latestQuotesQuery.data ?? []

    const availableQuoteCount =
        latestQuotes.filter(
            (item) =>
                item.available &&
                item.latest !== null,
        ).length

    const latestDataTimes =
        latestQuotes
            .map(
                (item) =>
                    item.latest?.time,
            )
            .filter(
                (
                    value,
                ): value is string =>
                    typeof value ===
                    'string' &&
                    value.length > 0,
            )
            .sort()

    const latestDataTime =
        latestDataTimes.at(-1)

    const isRefreshing =
        watchlistQuery.isFetching ||
        latestQuotesQuery.isFetching

    const normalizeSymbol = (
        value: string,
    ) =>
        value.trim().toUpperCase()

    const validateSymbol = (
        symbol: string,
    ) => {
        if (!symbol) {
            return 'Vui lòng nhập mã cổ phiếu.'
        }

        if (symbol.length > 10) {
            return 'Mã cổ phiếu tối đa 10 ký tự.'
        }

        if (!/^[A-Z0-9]+$/.test(symbol)) {
            return 'Mã cổ phiếu chỉ nên gồm chữ cái và chữ số.'
        }

        return null
    }

    const openStock = async (
        rawSymbol: string,
    ) => {
        const symbol =
            normalizeSymbol(rawSymbol)

        const validationError =
            validateSymbol(symbol)

        if (validationError) {
            setSearchError(
                validationError,
            )
            return
        }

        setSearchError(null)
        setIsSearching(true)

        try {
            await getLatestStock(symbol)

            navigate(
                `/app/stocks/${encodeURIComponent(
                    symbol,
                )}`,
            )

            setSearchValue('')
        } catch (error) {
            if (axios.isAxiosError(error)) {
                const status =
                    error.response?.status

                if (
                    status === 404 ||
                    status === 400
                ) {
                    setSearchError(
                        `Không tìm thấy dữ liệu cho mã ${symbol}. Vui lòng kiểm tra lại mã cổ phiếu.`,
                    )
                    return
                }

                if (!error.response) {
                    setSearchError(
                        'Không thể kết nối tới máy chủ. Vui lòng kiểm tra backend.',
                    )
                    return
                }
            }

            setSearchError(
                `Không thể kiểm tra mã ${symbol} lúc này. Vui lòng thử lại.`,
            )
        } finally {
            setIsSearching(false)
        }
    }

    const handleSearch = async (
        event: FormEvent<HTMLFormElement>,
    ) => {
        event.preventDefault()

        await openStock(searchValue)
    }

    const handleSearchChange = (
        value: string,
    ) => {
        setSearchValue(value)

        if (searchError) {
            setSearchError(null)
        }
    }

    const handleRefreshWatchlist =
        async () => {
            const watchlistResult =
                await watchlistQuery.refetch()

            if (
                watchlistResult.data &&
                watchlistResult.data.length >
                0
            ) {
                await latestQuotesQuery.refetch()
            }
        }

    return (
        <div className="mx-auto w-full min-w-0 max-w-[1440px] overflow-x-clip px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            {/* Page introduction */}
            <section className="min-w-0">
                <p className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                    Tổng quan
                </p>

                <div className="mt-2 min-w-0">
                    <h1 className="break-words text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl dark:text-white">
                        Xin chào, {username}
                    </h1>

                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500 sm:text-base dark:text-slate-400">
                        Theo dõi cổ phiếu, xem dữ
                        liệu thị trường và sử dụng
                        các công cụ phân tích của
                        Stock-AI tại mọi nơi
                    </p>
                </div>
            </section>

            {/* Overview */}
            <section
                aria-label="Tổng quan danh sách theo dõi"
                className="mt-6 grid min-w-0 grid-cols-2 gap-3 lg:grid-cols-3 lg:gap-4"
            >
                <article className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 dark:border-slate-800 dark:bg-slate-900">
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                        Đang theo dõi
                    </p>

                    <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
                        {watchlistQuery.isLoading
                            ? '—'
                            : watchlistQuery
                                .data
                                ?.length ??
                            0}
                    </p>

                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                        Mã cổ phiếu
                    </p>
                </article>

                <article className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 dark:border-slate-800 dark:bg-slate-900">
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                        Có dữ liệu giá
                    </p>

                    <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
                        {latestQuotesQuery.isLoading
                            ? '—'
                            : availableQuoteCount}
                    </p>

                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                        Trong phần xem trước
                    </p>
                </article>

                <article className="col-span-2 min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 lg:col-span-1 dark:border-slate-800 dark:bg-slate-900">
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                        Dữ liệu gần nhất
                    </p>

                    <p className="mt-2 break-words text-lg font-bold text-slate-900 sm:text-xl dark:text-white">
                        {latestDataTime
                            ? formatDataTime(
                                latestDataTime,
                            )
                            : 'Chưa có thông tin thời gian'}
                    </p>

                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                        Thời điểm cập nhật gần nhất
                    </p>
                </article>
            </section>

            {/* Stock search */}
            <section
                aria-labelledby="dashboard-search-title"
                className="mt-6 min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 dark:border-slate-800 dark:bg-slate-900"
            >
                <div className="flex min-w-0 items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400">
                        <Search
                            size={20}
                            aria-hidden="true"
                        />
                    </div>

                    <div className="min-w-0">
                        <h2
                            id="dashboard-search-title"
                            className="text-lg font-semibold text-slate-900 dark:text-white"
                        >
                            Tra cứu cổ phiếu
                        </h2>

                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            Nhập mã cổ phiếu.
                            Stock-AI sẽ kiểm tra dữ
                            liệu trước khi mở trang
                            chi tiết
                        </p>
                    </div>
                </div>

                <form
                    onSubmit={handleSearch}
                    role="search"
                    className="mt-5"
                >
                    <div className="flex min-w-0 flex-col gap-3 sm:flex-row">
                        <div className="relative min-w-0 flex-1">
                            <Search
                                size={18}
                                aria-hidden="true"
                                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                            />

                            <label
                                htmlFor="dashboard-stock-search"
                                className="sr-only"
                            >
                                Mã cổ phiếu
                            </label>

                            <input
                                id="dashboard-stock-search"
                                type="search"
                                value={searchValue}
                                onChange={(
                                    event,
                                ) =>
                                    handleSearchChange(
                                        event
                                            .target
                                            .value,
                                    )
                                }
                                placeholder="Ví dụ: FPT, VCB, HPG..."
                                autoComplete="off"
                                spellCheck={false}
                                enterKeyHint="search"
                                aria-invalid={
                                    searchError
                                        ? true
                                        : undefined
                                }
                                aria-describedby={
                                    searchError
                                        ? 'dashboard-search-error'
                                        : undefined
                                }
                                className={[
                                    'h-12 w-full min-w-0 rounded-xl border bg-slate-50 pl-11 pr-4 text-base text-slate-900 outline-none transition placeholder:text-slate-400',
                                    'dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-500',
                                    searchError
                                        ? 'border-amber-400 focus:border-amber-500 focus:ring-2 focus:ring-amber-100 dark:border-amber-500/70 dark:focus:ring-amber-500/20'
                                        : 'border-slate-200 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:hover:border-slate-600 dark:focus:border-blue-500 dark:focus:bg-slate-800 dark:focus:ring-blue-500/20',
                                ].join(
                                    ' ',
                                )}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={
                                isSearching
                            }
                            className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:focus-visible:ring-offset-slate-900"
                        >
                            {isSearching ? (
                                <>
                                    <LoaderCircle
                                        size={18}
                                        aria-hidden="true"
                                        className="animate-spin"
                                    />

                                    Đang kiểm tra...
                                </>
                            ) : (
                                <>
                                    Xem cổ phiếu

                                    <ArrowRight
                                        size={18}
                                        aria-hidden="true"
                                    />
                                </>
                            )}
                        </button>
                    </div>

                    {searchError && (
                        <div
                            id="dashboard-search-error"
                            role="alert"
                            className="mt-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300"
                        >
                            <CircleAlert
                                size={17}
                                aria-hidden="true"
                                className="mt-0.5 shrink-0"
                            />

                            <span>
                                {searchError}
                            </span>
                        </div>
                    )}
                </form>

                {watchlistPreview.length >
                    0 && (
                        <div className="mt-5 border-t border-slate-100 pt-4 dark:border-slate-800">
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                                Truy cập nhanh từ
                                Watchlist
                            </p>

                            <div className="mt-3 flex min-w-0 flex-wrap gap-2">
                                {watchlistPreview.map(
                                    (item) => (
                                        <button
                                            key={
                                                item.id
                                            }
                                            type="button"
                                            disabled={
                                                isSearching
                                            }
                                            onClick={() =>
                                                openStock(
                                                    item.symbol,
                                                )
                                            }
                                            className="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-blue-500/30 dark:hover:bg-blue-500/10 dark:hover:text-blue-400"
                                        >
                                            {
                                                item.symbol
                                            }
                                        </button>
                                    ),
                                )}
                            </div>
                        </div>
                    )}
            </section>

            {/* Watchlist + AI */}
            <section className="mt-6 grid min-w-0 items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
                {/* Watchlist */}
                <article className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 dark:border-slate-800 dark:bg-slate-900">
                    <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        <div className="flex min-w-0 items-start gap-3">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400">
                                <Star
                                    size={20}
                                    aria-hidden="true"
                                />
                            </div>

                            <div className="min-w-0">
                                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                                    Danh sách theo dõi
                                </h2>

                                <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                                    Hiển thị tối đa
                                    5 mã đầu tiên
                                    trong watchlist
                                    của bạn
                                </p>
                            </div>
                        </div>

                        <div className="flex shrink-0 items-center gap-1">
                            <button
                                type="button"
                                onClick={
                                    handleRefreshWatchlist
                                }
                                disabled={
                                    isRefreshing
                                }
                                aria-label="Làm mới dữ liệu watchlist"
                                title="Làm mới dữ liệu"
                                className="flex h-11 w-11 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
                            >
                                <RefreshCw
                                    size={18}
                                    aria-hidden="true"
                                    className={
                                        isRefreshing
                                            ? 'animate-spin'
                                            : ''
                                    }
                                />
                            </button>

                            <button
                                type="button"
                                onClick={() =>
                                    navigate(
                                        '/app/watchlist',
                                    )
                                }
                                className="inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-semibold text-blue-600 transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400 dark:hover:bg-blue-500/10"
                            >
                                Xem tất cả

                                <ArrowRight
                                    size={17}
                                    aria-hidden="true"
                                />
                            </button>
                        </div>
                    </div>

                    {watchlistQuery.isLoading && (
                        <div className="mt-5 flex min-h-48 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/40">
                            <div className="text-center">
                                <LoaderCircle
                                    size={28}
                                    aria-hidden="true"
                                    className="mx-auto animate-spin text-blue-600 dark:text-blue-400"
                                />

                                <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
                                    Đang tải
                                    watchlist...
                                </p>
                            </div>
                        </div>
                    )}

                    {watchlistQuery.isError && (
                        <div className="mt-5 flex min-h-48 items-center justify-center rounded-xl border border-amber-200 bg-amber-50 p-5 text-center dark:border-amber-500/20 dark:bg-amber-500/10">
                            <div>
                                <CircleAlert
                                    size={30}
                                    aria-hidden="true"
                                    className="mx-auto text-amber-700 dark:text-amber-400"
                                />

                                <p className="mt-3 font-medium text-slate-800 dark:text-slate-100">
                                    Không thể tải
                                    watchlist
                                </p>

                                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                                    Hãy kiểm tra kết
                                    nối tới backend
                                    rồi thử lại
                                </p>

                                <button
                                    type="button"
                                    onClick={() =>
                                        watchlistQuery.refetch()
                                    }
                                    className="mt-3 min-h-11 rounded-xl px-4 text-sm font-semibold text-blue-600 transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400 dark:hover:bg-blue-500/10"
                                >
                                    Thử lại
                                </button>
                            </div>
                        </div>
                    )}

                    {!watchlistQuery.isLoading &&
                        !watchlistQuery.isError &&
                        watchlistPreview.length ===
                        0 && (
                            <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center dark:border-slate-700 dark:bg-slate-800/40">
                                <Star
                                    size={34}
                                    aria-hidden="true"
                                    className="mx-auto text-slate-300 dark:text-slate-600"
                                />

                                <p className="mt-3 font-medium text-slate-700 dark:text-slate-200">
                                    Watchlist đang
                                    trống
                                </p>

                                <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-slate-500 dark:text-slate-400">
                                    Khi bạn thêm cổ
                                    phiếu vào danh
                                    sách theo dõi,
                                    chúng sẽ xuất
                                    hiện tại đây
                                </p>

                                <button
                                    type="button"
                                    onClick={() =>
                                        navigate(
                                            '/app/stocks',
                                        )
                                    }
                                    className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                                >
                                    Tìm cổ phiếu

                                    <ArrowRight
                                        size={17}
                                        aria-hidden="true"
                                    />
                                </button>
                            </div>
                        )}

                    {!watchlistQuery.isLoading &&
                        !watchlistQuery.isError &&
                        watchlistPreview.length >
                        0 && (
                            <>
                                {latestQuotesQuery.isLoading ? (
                                    <div className="mt-5 flex min-h-48 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/40">
                                        <div className="text-center">
                                            <LoaderCircle
                                                size={
                                                    28
                                                }
                                                aria-hidden="true"
                                                className="mx-auto animate-spin text-blue-600 dark:text-blue-400"
                                            />

                                            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
                                                Đang
                                                tải dữ
                                                liệu
                                                giá...
                                            </p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="mt-5 grid min-w-0 gap-3">
                                        {watchlistPreview.map(
                                            (
                                                item,
                                            ) => {
                                                const quote =
                                                    latestQuotes.find(
                                                        (
                                                            quoteItem,
                                                        ) =>
                                                            quoteItem.symbol ===
                                                            item.symbol,
                                                    )

                                                if (
                                                    !quote?.latest
                                                ) {
                                                    return (
                                                        <div
                                                            key={
                                                                item.id
                                                            }
                                                            className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/40"
                                                        >
                                                            <div className="flex min-w-0 items-start justify-between gap-3">
                                                                <div className="min-w-0">
                                                                    <p className="truncate font-semibold text-slate-900 dark:text-white">
                                                                        {
                                                                            item.symbol
                                                                        }
                                                                    </p>

                                                                    <div className="mt-2 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                                                                        <CircleAlert
                                                                            size={
                                                                                16
                                                                            }
                                                                            aria-hidden="true"
                                                                            className="shrink-0 text-amber-600 dark:text-amber-400"
                                                                        />

                                                                        <span>
                                                                            Chưa
                                                                            lấy
                                                                            được
                                                                            dữ
                                                                            liệu
                                                                            giá.
                                                                        </span>
                                                                    </div>
                                                                </div>

                                                                <button
                                                                    type="button"
                                                                    onClick={() =>
                                                                        navigate(
                                                                            `/app/stocks/${encodeURIComponent(
                                                                                item.symbol,
                                                                            )}`,
                                                                        )
                                                                    }
                                                                    className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-xl px-3 text-sm font-semibold text-blue-600 transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400 dark:hover:bg-blue-500/10"
                                                                >
                                                                    Chi tiết
                                                                </button>
                                                            </div>
                                                        </div>
                                                    )
                                                }

                                                const latest =
                                                    quote.latest

                                                return (
                                                    <article
                                                        key={
                                                            item.id
                                                        }
                                                        className="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white transition hover:border-slate-300 hover:shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
                                                    >
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                navigate(
                                                                    `/app/stocks/${encodeURIComponent(
                                                                        item.symbol,
                                                                    )}`,
                                                                )
                                                            }
                                                            className="w-full min-w-0 p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500 sm:p-5"
                                                        >
                                                            <div className="flex min-w-0 items-start justify-between gap-4">
                                                                <div className="min-w-0">
                                                                    <p className="truncate text-lg font-bold text-slate-900 dark:text-white">
                                                                        {
                                                                            item.symbol
                                                                        }
                                                                    </p>

                                                                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                                                                        Mã đang
                                                                        theo dõi
                                                                    </p>
                                                                </div>

                                                                <div className="shrink-0 text-right">
                                                                    <p className="text-xl font-bold tabular-nums text-slate-950 dark:text-white">
                                                                        {formatNumber(
                                                                            latest.close,
                                                                        )}
                                                                    </p>

                                                                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                                                                        Giá đóng
                                                                        cửa
                                                                    </p>
                                                                </div>
                                                            </div>

                                                            <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-slate-100 pt-4 sm:grid-cols-4 dark:border-slate-800">
                                                                <div className="min-w-0">
                                                                    <p className="text-xs text-slate-500 dark:text-slate-400">
                                                                        Mở cửa
                                                                    </p>

                                                                    <p className="mt-1 truncate text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                                                                        {formatNumber(
                                                                            latest.open,
                                                                        )}
                                                                    </p>
                                                                </div>

                                                                <div className="min-w-0">
                                                                    <p className="text-xs text-slate-500 dark:text-slate-400">
                                                                        Cao nhất
                                                                    </p>

                                                                    <p className="mt-1 truncate text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                                                                        {formatNumber(
                                                                            latest.high,
                                                                        )}
                                                                    </p>
                                                                </div>

                                                                <div className="min-w-0">
                                                                    <p className="text-xs text-slate-500 dark:text-slate-400">
                                                                        Thấp nhất
                                                                    </p>

                                                                    <p className="mt-1 truncate text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                                                                        {formatNumber(
                                                                            latest.low,
                                                                        )}
                                                                    </p>
                                                                </div>

                                                                <div className="min-w-0">
                                                                    <p className="text-xs text-slate-500 dark:text-slate-400">
                                                                        Khối
                                                                        lượng
                                                                    </p>

                                                                    <p className="mt-1 truncate text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                                                                        {formatVolume(
                                                                            latest.volume,
                                                                        )}
                                                                    </p>
                                                                </div>
                                                            </div>

                                                            <div className="mt-4 border-t border-slate-100 pt-3 dark:border-slate-800">
                                                                <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                                                                    Giá tính
                                                                    theo nghìn
                                                                    đồng/cổ
                                                                    phiếu
                                                                </p>

                                                                <div className="mt-2 flex min-w-0 items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                                                                    <Clock3
                                                                        size={
                                                                            14
                                                                        }
                                                                        aria-hidden="true"
                                                                        className="shrink-0"
                                                                    />

                                                                    <span className="truncate">
                                                                        Dữ
                                                                        liệu:{' '}
                                                                        {formatDataTime(
                                                                            latest.time,
                                                                        )}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </button>
                                                    </article>
                                                )
                                            },
                                        )}
                                    </div>
                                )}
                            </>
                        )}
                </article>

                {/* AI Analysis Preview */}
                <AIAnalysisPreview
                    symbols={watchlistSymbols}
                />
            </section>

            {/* News Preview */}
            <section className="mt-6 min-w-0">
                <NewsPreview
                    symbols={watchlistSymbols}
                />
            </section>

            {/* Secondary tools */}
            <section className="mt-6 grid min-w-0 items-start gap-4 md:grid-cols-2">
                <article className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        <ChartNoAxesCombined
                            size={20}
                            aria-hidden="true"
                        />
                    </div>

                    <h2 className="mt-4 text-lg font-semibold text-slate-900 dark:text-white">
                        Cổ phiếu
                    </h2>

                    <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                        Tra cứu mã và mở trang chi
                        tiết để xem dữ liệu của từng
                        cổ phiếu
                    </p>

                    <button
                        type="button"
                        onClick={() =>
                            navigate(
                                '/app/stocks',
                            )
                        }
                        className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl text-sm font-semibold text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400"
                    >
                        Mở danh mục

                        <ArrowRight
                            size={17}
                            aria-hidden="true"
                        />
                    </button>
                </article>

                <article className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        <MessageSquareText
                            size={20}
                            aria-hidden="true"
                        />
                    </div>

                    <h2 className="mt-4 text-lg font-semibold text-slate-900 dark:text-white">
                        Trợ lý AI
                    </h2>

                    <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                        Trao đổi với trợ lý để hiểu
                        rõ hơn về dữ liệu và kết quả
                        phân tích
                    </p>

                    <button
                        type="button"
                        onClick={() =>
                            navigate('/app/chat')
                        }
                        className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl text-sm font-semibold text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400"
                    >
                        Mở trợ lý

                        <ArrowRight
                            size={17}
                            aria-hidden="true"
                        />
                    </button>
                </article>
            </section>

            {/* Information notice */}
            <section className="mt-6 min-w-0">
                <div className="flex min-w-0 items-start gap-3 rounded-2xl border border-slate-200 bg-slate-100/70 p-4 sm:p-5 dark:border-slate-800 dark:bg-slate-900/60">
                    <ShieldCheck
                        size={20}
                        aria-hidden="true"
                        className="mt-0.5 shrink-0 text-slate-500 dark:text-slate-400"
                    />

                    <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                            Thông tin dữ liệu
                        </p>

                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            Stock-AI hỗ trợ tổng hợp
                            và phân tích thông tin.
                            Nội dung hiển thị nhằm
                            mục đích tham khảo và
                            không phải là khuyến nghị
                            mua hoặc bán chứng khoán
                        </p>
                    </div>
                </div>
            </section>
        </div>
    )
}

export default DashboardPage