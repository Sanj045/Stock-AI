import {
    Bot,
    Home,
    MessageSquareText,
    Star,
    User,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navigationItems = [
    {
        label: 'Tổng quan',
        shortLabel: 'Home',
        to: '/app',
        icon: Home,
        end: true,
    },
    {
        label: 'Theo dõi',
        shortLabel: 'Theo dõi',
        to: '/app/watchlist',
        icon: Star,
    },
    {
        label: 'Phân tích AI',
        shortLabel: 'AI',
        to: '/app/analysis',
        icon: Bot,
    },
    {
        label: 'Trợ lý AI',
        shortLabel: 'Chat',
        to: '/app/chat',
        icon: MessageSquareText,
    },
    {
        label: 'Tài khoản',
        shortLabel: 'Tài khoản',
        to: '/app/profile',
        icon: User,
    },
]

function MobileBottomNav() {
    return (
        <nav
            aria-label="Điều hướng chính trên thiết bị di động"
            className="
                fixed
                inset-x-0
                bottom-0
                z-40
                border-t
                border-slate-200
                bg-white/95
                pb-[env(safe-area-inset-bottom)]
                backdrop-blur-xl
                lg:hidden
                dark:border-slate-800
                dark:bg-slate-900/95
            "
        >
            <div className="mx-auto grid h-16 max-w-xl grid-cols-5">
                {navigationItems.map((item) => {
                    const Icon = item.icon

                    return (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.end}
                            aria-label={item.label}
                            className={({ isActive }) =>
                                [
                                    'relative flex min-w-0 flex-col items-center justify-center gap-1',
                                    'px-1 text-[11px] font-medium transition-colors duration-150',
                                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500',
                                    isActive
                                        ? 'text-blue-600 dark:text-blue-400'
                                        : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white',
                                ].join(' ')
                            }
                        >
                            {({ isActive }) => (
                                <>
                                    <span
                                        aria-hidden="true"
                                        className={[
                                            'absolute top-0 h-0.5 w-8 rounded-b-full transition-colors',
                                            isActive
                                                ? 'bg-blue-600 dark:bg-blue-400'
                                                : 'bg-transparent',
                                        ].join(' ')}
                                    />

                                    <span
                                        className={[
                                            'flex h-7 w-9 items-center justify-center rounded-lg transition-colors',
                                            isActive
                                                ? 'bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400'
                                                : '',
                                        ].join(' ')}
                                    >
                                        <Icon
                                            size={20}
                                            strokeWidth={1.9}
                                            aria-hidden="true"
                                        />
                                    </span>

                                    <span className="max-w-full truncate">
                                        {item.shortLabel}
                                    </span>
                                </>
                            )}
                        </NavLink>
                    )
                })}
            </div>
        </nav>
    )
}

export default MobileBottomNav