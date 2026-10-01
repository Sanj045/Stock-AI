import {
    ArrowRight,
    Bot,
    CircleAlert,
    Database,
    LoaderCircle,
    ShieldAlert,
    Sparkles,
} from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { analyzeStockStructured } from '../../api/analysis'

type AIAnalysisPreviewProps = {
    symbols: string[]
}

function humanizeDataLimitText(
    value: string,
) {
    return value
        .replaceAll(
            'status=error',
            'gặp lỗi',
        )
        .replaceAll(
            'status=empty',
            'không có dữ liệu',
        )
        .replaceAll(
            'status=available',
            'có dữ liệu',
        )
        .replaceAll(
            'price_history',
            'lịch sử giá',
        )
        .replaceAll(
            'company',
            'thông tin doanh nghiệp',
        )
        .replaceAll(
            'fundamentals',
            'dữ liệu cơ bản',
        )
        .replaceAll(
            'news',
            'tin tức',
        )
}

function AIAnalysisPreview({
    symbols,
}: AIAnalysisPreviewProps) {
    const navigate = useNavigate()

    const [selectedSymbol, setSelectedSymbol] =
        useState('')

    const effectiveSymbol =
        selectedSymbol || symbols[0] || ''

    const analysisMutation = useMutation({
        mutationFn: analyzeStockStructured,
    })

    const handleSelectSymbol = (
        symbol: string,
    ) => {
        setSelectedSymbol(symbol)

        if (
            analysisMutation.data?.symbol !==
            symbol
        ) {
            analysisMutation.reset()
        }
    }

    const handleAnalyze = () => {
        if (!effectiveSymbol) {
            return
        }

        analysisMutation.mutate(
            effectiveSymbol,
        )
    }

    const analysis =
        analysisMutation.data

    const firstDataLimit =
        analysis?.data_limits.limitations[0]

    const readableDataLimit =
        firstDataLimit
            ? humanizeDataLimitText(
                firstDataLimit,
            )
            : null

    return (
        <article className="min-w-0 overflow-hidden rounded-2xl border border-blue-200 bg-blue-50 p-5 shadow-sm sm:p-6 dark:border-blue-500/20 dark:bg-blue-500/10">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
                <Bot
                    size={21}
                    aria-hidden="true"
                />
            </div>

            <h2 className="mt-4 text-lg font-semibold text-slate-900 dark:text-white">
                Phân tích với Stock-AI
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                Chọn một mã cổ phiếu và tạo bản
                tóm tắt AI dựa trên dữ liệu hiện
                có.
            </p>

            {symbols.length > 0 ? (
                <>
                    <div className="mt-5">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            Chọn mã cổ phiếu
                        </p>

                        <div className="mt-3 flex flex-wrap gap-2">
                            {symbols.map(
                                (symbol) => {
                                    const isSelected =
                                        symbol ===
                                        effectiveSymbol

                                    return (
                                        <button
                                            key={
                                                symbol
                                            }
                                            type="button"
                                            onClick={() =>
                                                handleSelectSymbol(
                                                    symbol,
                                                )
                                            }
                                            disabled={
                                                analysisMutation.isPending
                                            }
                                            className={[
                                                'min-h-10 rounded-xl border px-3 text-sm font-semibold transition',
                                                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                                                'disabled:cursor-not-allowed disabled:opacity-50',
                                                isSelected
                                                    ? 'border-blue-600 bg-blue-600 text-white'
                                                    : 'border-blue-200 bg-white/70 text-blue-700 hover:bg-white dark:border-blue-500/30 dark:bg-slate-900/40 dark:text-blue-300 dark:hover:bg-slate-900/70',
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

                    <button
                        type="button"
                        onClick={handleAnalyze}
                        disabled={
                            analysisMutation.isPending
                        }
                        className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:focus-visible:ring-offset-slate-900"
                    >
                        {analysisMutation.isPending ? (
                            <>
                                <LoaderCircle
                                    size={18}
                                    aria-hidden="true"
                                    className="animate-spin"
                                />

                                Đang phân tích{' '}
                                {
                                    effectiveSymbol
                                }...
                            </>
                        ) : (
                            <>
                                <Sparkles
                                    size={18}
                                    aria-hidden="true"
                                />

                                Tạo tóm tắt AI
                            </>
                        )}
                    </button>
                </>
            ) : (
                <div className="mt-5 rounded-xl border border-blue-200 bg-white/60 p-4 dark:border-blue-500/20 dark:bg-slate-900/30">
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                        Chưa có mã để phân tích
                    </p>

                    <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                        Hãy thêm cổ phiếu vào
                        Watchlist hoặc mở trang
                        Phân tích AI.
                    </p>
                </div>
            )}

            {analysisMutation.isError && (
                <div
                    role="alert"
                    className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300"
                >
                    <CircleAlert
                        size={18}
                        aria-hidden="true"
                        className="mt-0.5 shrink-0"
                    />

                    <span>
                        Không thể tạo phân tích cho{' '}
                        {effectiveSymbol}. Vui lòng
                        thử lại.
                    </span>
                </div>
            )}

            {analysis && (
                <div className="mt-5 space-y-3">
                    <div className="rounded-xl border border-blue-200 bg-white/80 p-4 dark:border-blue-500/20 dark:bg-slate-900/50">
                        <div className="flex items-center gap-2">
                            <Sparkles
                                size={17}
                                aria-hidden="true"
                                className="shrink-0 text-blue-600 dark:text-blue-400"
                            />

                            <p className="text-sm font-semibold text-slate-900 dark:text-white">
                                Xu hướng giá —{' '}
                                {
                                    analysis.symbol
                                }
                            </p>
                        </div>

                        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                            {
                                analysis
                                    .price_trend
                                    .summary
                            }
                        </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-900/50">
                        <p className="text-sm font-semibold text-slate-900 dark:text-white">
                            Động lượng
                        </p>

                        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                            {
                                analysis.momentum
                                    .summary
                            }
                        </p>
                    </div>

                    <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 dark:border-amber-500/20 dark:bg-amber-500/10">
                        <div className="flex items-center gap-2">
                            <ShieldAlert
                                size={17}
                                aria-hidden="true"
                                className="shrink-0 text-amber-700 dark:text-amber-400"
                            />

                            <p className="text-sm font-semibold text-slate-900 dark:text-white">
                                Điểm cần lưu ý
                            </p>
                        </div>

                        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                            {
                                analysis.risks
                                    .summary
                            }
                        </p>
                    </div>

                    {readableDataLimit && (
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/50">
                            <div className="flex items-center gap-2">
                                <Database
                                    size={17}
                                    aria-hidden="true"
                                    className="shrink-0 text-slate-500 dark:text-slate-400"
                                />

                                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                                    Giới hạn dữ liệu
                                </p>
                            </div>

                            <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                                {
                                    readableDataLimit
                                }
                            </p>
                        </div>
                    )}

                    <button
                        type="button"
                        onClick={() =>
                            navigate(
                                `/app/analysis/${encodeURIComponent(
                                    analysis.symbol,
                                )}`,
                            )
                        }
                        className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-blue-200 bg-white px-4 py-2.5 text-sm font-semibold text-blue-700 transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-blue-500/30 dark:bg-slate-900/40 dark:text-blue-300 dark:hover:bg-blue-500/10"
                    >
                        Xem phân tích đầy đủ

                        <ArrowRight
                            size={17}
                            aria-hidden="true"
                        />
                    </button>
                </div>
            )}

            {!analysis && (
                <button
                    type="button"
                    onClick={() =>
                        navigate(
                            '/app/analysis',
                        )
                    }
                    className="mt-4 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl text-sm font-semibold text-blue-700 transition hover:bg-blue-100/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300 dark:hover:bg-blue-500/10"
                >
                    Mở trang phân tích AI

                    <ArrowRight
                        size={17}
                        aria-hidden="true"
                    />
                </button>
            )}
        </article>
    )
}

export default AIAnalysisPreview