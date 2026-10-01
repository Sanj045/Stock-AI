import {
    ArrowRight,
    BadgeCheck,
    CircleAlert,
    Clock3,
    ExternalLink,
    LoaderCircle,
    Newspaper,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getStockNews } from '../../api/news'
import type { StockNewsItem } from '../../types/news'


type NewsPreviewProps = {
    symbols: string[]
}


function formatNewsTime(
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


function getEvidenceUrl(
    item: StockNewsItem,
) {
    if (
        item.evidence_verified === true &&
        item.evidence_url
    ) {
        return item.evidence_url
    }

    if (
        item.url_verified === true &&
        item.url
    ) {
        return item.url
    }

    if (
        item.url_available &&
        item.url
    ) {
        return item.url
    }

    return null
}


function getEvidenceSource(
    item: StockNewsItem,
) {
    if (
        item.evidence_verified === true &&
        item.evidence_source
    ) {
        return item.evidence_source
    }

    return (
        item.source ||
        item.original_source ||
        'Không rõ nguồn'
    )
}


function hasVerifiedEvidence(
    item: StockNewsItem,
) {
    return Boolean(
        item.evidence_verified === true ||
        item.url_verified === true,
    )
}


function NewsPreview({
    symbols,
}: NewsPreviewProps) {
    const navigate = useNavigate()

    const [
        selectedSymbol,
        setSelectedSymbol,
    ] = useState('')

    const effectiveSymbol =
        selectedSymbol ||
        symbols[0] ||
        ''

    const newsQuery = useQuery({
        queryKey: [
            'dashboard-news',
            effectiveSymbol,
        ],

        enabled:
            effectiveSymbol.length > 0,

        queryFn: () =>
            getStockNews(
                effectiveSymbol,
                3,
            ),

        staleTime: 5 * 60_000,
    })


    const handleOpenArticle = (
        url?: string | null,
    ) => {
        if (!url) {
            return
        }

        window.open(
            url,
            '_blank',
            'noopener,noreferrer',
        )
    }


    return (
        <article className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 dark:border-slate-800 dark:bg-slate-900">
            <div className="flex min-w-0 items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    <Newspaper
                        size={20}
                        aria-hidden="true"
                    />
                </div>

                <div className="min-w-0">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                        Tin tức theo dõi
                    </h2>

                    <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                        Xem các tin gần đây liên
                        quan đến cổ phiếu trong
                        Watchlist cùng nguồn dẫn
                        chứng đã được hệ thống
                        kiểm tra
                    </p>
                </div>
            </div>


            {symbols.length > 0 && (
                <div className="mt-5">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                        Chọn mã cổ phiếu
                    </p>

                    <div className="mt-3 flex flex-wrap gap-2">
                        {symbols.map(
                            (symbol) => {
                                const active =
                                    symbol ===
                                    effectiveSymbol

                                return (
                                    <button
                                        key={
                                            symbol
                                        }
                                        type="button"
                                        onClick={() =>
                                            setSelectedSymbol(
                                                symbol,
                                            )
                                        }
                                        className={[
                                            'min-h-10 rounded-xl border px-3 text-sm font-semibold transition',
                                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                                            active
                                                ? 'border-blue-600 bg-blue-600 text-white'
                                                : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-blue-500/30 dark:hover:bg-blue-500/10 dark:hover:text-blue-400',
                                        ].join(
                                            ' ',
                                        )}
                                    >
                                        {
                                            symbol
                                        }
                                    </button>
                                )
                            },
                        )}
                    </div>
                </div>
            )}


            {!effectiveSymbol && (
                <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center dark:border-slate-700 dark:bg-slate-800/40">
                    <Newspaper
                        size={30}
                        aria-hidden="true"
                        className="mx-auto text-slate-300 dark:text-slate-600"
                    />

                    <p className="mt-3 font-medium text-slate-700 dark:text-slate-200">
                        Chưa có mã để tải tin tức
                    </p>

                    <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                        Thêm cổ phiếu vào Watchlist
                        để xem các tin liên quan
                    </p>
                </div>
            )}


            {newsQuery.isLoading && (
                <div className="mt-5 flex min-h-40 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/40">
                    <div className="text-center">
                        <LoaderCircle
                            size={27}
                            aria-hidden="true"
                            className="mx-auto animate-spin text-blue-600 dark:text-blue-400"
                        />

                        <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
                            Đang tải tin tức{' '}
                            {effectiveSymbol}...
                        </p>
                    </div>
                </div>
            )}


            {newsQuery.isError && (
                <div
                    role="alert"
                    className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-500/20 dark:bg-amber-500/10"
                >
                    <div className="flex items-start gap-2">
                        <CircleAlert
                            size={18}
                            aria-hidden="true"
                            className="mt-0.5 shrink-0 text-amber-700 dark:text-amber-400"
                        />

                        <div>
                            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                                Không thể tải tin tức
                            </p>

                            <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                                Nguồn dữ liệu hiện
                                chưa phản hồi. Bạn
                                có thể thử lại.
                            </p>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={() =>
                            newsQuery.refetch()
                        }
                        className="mt-3 min-h-10 rounded-xl px-3 text-sm font-semibold text-blue-600 transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400 dark:hover:bg-blue-500/10"
                    >
                        Thử lại
                    </button>
                </div>
            )}


            {!newsQuery.isLoading &&
                !newsQuery.isError &&
                effectiveSymbol &&
                newsQuery.data?.length ===
                0 && (
                    <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center dark:border-slate-700 dark:bg-slate-800/40">
                        <Newspaper
                            size={28}
                            aria-hidden="true"
                            className="mx-auto text-slate-300 dark:text-slate-600"
                        />

                        <p className="mt-3 font-medium text-slate-700 dark:text-slate-200">
                            Chưa có tin gần đây
                        </p>

                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                            Hiện chưa có dữ liệu
                            tin tức cho{' '}
                            {effectiveSymbol}.
                        </p>
                    </div>
                )}


            {!newsQuery.isLoading &&
                !newsQuery.isError &&
                newsQuery.data &&
                newsQuery.data.length >
                0 && (
                    <div className="mt-5 divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
                        {newsQuery.data.map(
                            (item) => {
                                const evidenceUrl =
                                    getEvidenceUrl(
                                        item,
                                    )

                                const evidenceSource =
                                    getEvidenceSource(
                                        item,
                                    )

                                const verified =
                                    hasVerifiedEvidence(
                                        item,
                                    )

                                const canOpen =
                                    Boolean(
                                        evidenceUrl,
                                    )

                                return (
                                    <div
                                        key={
                                            item.article_id
                                        }
                                        className="min-w-0 bg-white p-4 sm:p-5 dark:bg-slate-900"
                                    >
                                        <div className="min-w-0">
                                            <p className="break-words text-sm font-semibold leading-6 text-slate-900 dark:text-white">
                                                {
                                                    item.title
                                                }
                                            </p>


                                            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                                                <span className="inline-flex min-w-0 items-center gap-1.5">
                                                    <span>
                                                        Nguồn dẫn chứng:
                                                    </span>

                                                    <span className="font-semibold text-slate-700 dark:text-slate-200">
                                                        {
                                                            evidenceSource
                                                        }
                                                    </span>
                                                </span>


                                                {verified && (
                                                    <span className="inline-flex items-center gap-1 font-medium text-blue-600 dark:text-blue-400">
                                                        <BadgeCheck
                                                            size={
                                                                14
                                                            }
                                                            aria-hidden="true"
                                                        />

                                                        Đã kiểm tra
                                                    </span>
                                                )}


                                                <span className="inline-flex items-center gap-1">
                                                    <Clock3
                                                        size={
                                                            13
                                                        }
                                                        aria-hidden="true"
                                                    />

                                                    {formatNewsTime(
                                                        item.publish_time,
                                                    )}
                                                </span>
                                            </div>


                                            {item.summary && (
                                                <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                                                    {
                                                        item.summary
                                                    }
                                                </p>
                                            )}


                                            {canOpen && (
                                                <button
                                                    type="button"
                                                    onClick={() =>
                                                        handleOpenArticle(
                                                            evidenceUrl,
                                                        )
                                                    }
                                                    aria-label={`Mở nguồn dẫn chứng cho ${item.title}`}
                                                    className="mt-3 inline-flex min-h-10 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-semibold text-blue-600 transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400 dark:hover:bg-blue-500/10"
                                                >
                                                    Xem nguồn dẫn chứng

                                                    <ExternalLink
                                                        size={
                                                            15
                                                        }
                                                        aria-hidden="true"
                                                    />
                                                </button>
                                            )}


                                            {!canOpen && (
                                                <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
                                                    Chưa có liên kết
                                                    dẫn chứng khả dụng.
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                )
                            },
                        )}
                    </div>
                )}


            <button
                type="button"
                onClick={() =>
                    navigate('/app/news')
                }
                className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-blue-600 transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-blue-400 dark:hover:bg-blue-500/10"
            >
                Xem tất cả tin tức

                <ArrowRight
                    size={17}
                    aria-hidden="true"
                />
            </button>
        </article>
    )
}


export default NewsPreview