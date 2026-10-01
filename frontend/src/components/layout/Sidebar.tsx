import {
    BarChart3,
    Bot,
    ChartNoAxesCombined,
    MessageSquareText,
    Newspaper,
    Star,
    User,
    X,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { useAuthStore } from '../../store/auth.store'
import { useUIStore } from '../../store/ui.store'

const navigationItems = [
    {
        label: 'Tổng quan',
        to: '/app',
        icon: BarChart3,
        end: true,
    },
    {
        label: 'Cổ phiếu',
        to: '/app/stocks',
        icon: ChartNoAxesCombined,
    },
    {
        label: 'Theo dõi',
        to: '/app/watchlist',
        icon: Star,
    },
    {
        label: 'Phân tích AI',
        to: '/app/analysis',
        icon: Bot,
    },
    {
        label: 'Trợ lý AI',
        to: '/app/chat',
        icon: MessageSquareText,
    },
    {
        label: 'Cuộc trò chuyện',
        to: '/app/conversations',
        icon: MessageSquareText,
    },
    {
        label: 'Tin tức',
        to: '/app/news',
        icon: Newspaper,
    },
    {
        label: 'Tài khoản',
        to: '/app/profile',
        icon: User,
    },
]

function getUserInitial(username?: string) {
    if (!username) {
        return 'U'
    }

    return username
        .trim()
        .charAt(0)
        .toUpperCase()
}

function SidebarContent({
    onNavigate,
}: {
    onNavigate?: () => void
}) {
    const user = useAuthStore(
        (state) => state.user,
    )

    const username =
        user?.username || 'Người dùng'

    const userInitial =
        getUserInitial(user?.username)

    return (
        <div className="flex h-full flex-col">
            {/* Brand */}
            <div className="flex h-16 shrink-0 items-center border-b border-slate-200 px-5 dark:border-slate-800">
                <NavLink
                    to="/app"
                    onClick={onNavigate}
                    className="group flex min-w-0 items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-sm font-bold text-white shadow-sm shadow-blue-600/20 transition group-hover:bg-blue-700">
                        S
                    </div>

                    <div className="min-w-0">
                        <p className="truncate text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                            STOCK-AI
                        </p>

                        <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                            Stock Intelligence
                        </p>
                    </div>
                </NavLink>
            </div>

            {/* Navigation */}
            <nav
                className="min-h-0 flex-1 overflow-y-auto px-3 py-5"
                aria-label="Điều hướng chính"
            >
                <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400 dark:text-slate-500">
                    Menu
                </p>

                <div className="space-y-1">
                    {navigationItems.map((item) => {
                        const Icon = item.icon

                        return (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                end={item.end}
                                onClick={onNavigate}
                                className={({ isActive }) =>
                                    [
                                        'group relative flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5',
                                        'text-sm font-medium transition-all duration-150',
                                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                                        isActive
                                            ? 'bg-blue-50 text-blue-700 shadow-sm shadow-blue-100/70 dark:bg-blue-500/10 dark:text-blue-400 dark:shadow-none'
                                            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white',
                                    ].join(' ')
                                }
                            >
                                {({ isActive }) => (
                                    <>
                                        <span
                                            aria-hidden="true"
                                            className={[
                                                'absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full transition',
                                                isActive
                                                    ? 'bg-blue-600 dark:bg-blue-400'
                                                    : 'bg-transparent',
                                            ].join(' ')}
                                        />

                                        <span
                                            className={[
                                                'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors',
                                                isActive
                                                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400'
                                                    : 'text-slate-500 group-hover:text-slate-900 dark:text-slate-400 dark:group-hover:text-white',
                                            ].join(' ')}
                                        >
                                            <Icon
                                                size={19}
                                                strokeWidth={1.9}
                                                aria-hidden="true"
                                            />
                                        </span>

                                        <span className="truncate">
                                            {item.label}
                                        </span>
                                    </>
                                )}
                            </NavLink>
                        )
                    })}
                </div>
            </nav>

            {/* Current user */}
            <div className="shrink-0 border-t border-slate-200 p-4 dark:border-slate-800">
                <NavLink
                    to="/app/profile"
                    onClick={onNavigate}
                    className={({ isActive }) =>
                        [
                            'flex min-h-16 items-center gap-3 rounded-2xl border p-3 transition-colors duration-150',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                            isActive
                                ? 'border-blue-200 bg-blue-50 dark:border-blue-500/30 dark:bg-blue-500/10'
                                : 'border-slate-200 bg-slate-50 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/70 dark:hover:bg-slate-800',
                        ].join(' ')
                    }
                >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700 dark:bg-blue-500/15 dark:text-blue-400">
                        {userInitial}
                    </div>

                    <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                            {username}
                        </p>

                        <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">
                            Tài khoản đang đăng nhập
                        </p>
                    </div>
                </NavLink>
            </div>
        </div>
    )
}

function Sidebar() {
    const isMobileMenuOpen = useUIStore(
        (state) => state.isMobileMenuOpen,
    )

    const closeMobileMenu = useUIStore(
        (state) => state.closeMobileMenu,
    )

    return (
        <>
            {/* Desktop sidebar */}
            <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-slate-200 bg-white lg:block dark:border-slate-800 dark:bg-slate-900">
                <SidebarContent />
            </aside>

            {/* Mobile drawer */}
            {isMobileMenuOpen && (
                <div
                    className="fixed inset-0 z-50 lg:hidden"
                    role="dialog"
                    aria-modal="true"
                    aria-label="Menu điều hướng"
                >
                    <button
                        type="button"
                        aria-label="Đóng menu"
                        onClick={closeMobileMenu}
                        className="absolute inset-0 bg-slate-950/45 backdrop-blur-[2px]"
                    />

                    <aside
                        className="
                            relative
                            h-full
                            w-[min(86vw,320px)]
                            border-r
                            border-slate-200
                            bg-white
                            shadow-2xl
                            dark:border-slate-800
                            dark:bg-slate-900
                        "
                    >
                        <button
                            type="button"
                            onClick={closeMobileMenu}
                            aria-label="Đóng menu"
                            className="
                                absolute
                                right-3
                                top-3
                                z-10
                                flex
                                h-10
                                w-10
                                items-center
                                justify-center
                                rounded-xl
                                text-slate-500
                                transition-colors
                                duration-150
                                hover:bg-slate-100
                                hover:text-slate-900
                                focus-visible:outline-none
                                focus-visible:ring-2
                                focus-visible:ring-blue-500
                                dark:text-slate-400
                                dark:hover:bg-slate-800
                                dark:hover:text-white
                            "
                        >
                            <X
                                size={21}
                                strokeWidth={1.9}
                                aria-hidden="true"
                            />
                        </button>

                        <SidebarContent
                            onNavigate={closeMobileMenu}
                        />
                    </aside>
                </div>
            )}
        </>
    )
}

export default Sidebar