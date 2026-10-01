import {
    Menu,
    Moon,
    Search,
    Sun,
} from 'lucide-react'
import type { FormEvent } from 'react'
import { useState } from 'react'
import {
    useLocation,
    useNavigate,
} from 'react-router-dom'

import { useAuthStore } from '../../store/auth.store'
import { useThemeStore } from '../../store/theme.store'
import { useUIStore } from '../../store/ui.store'

function getUserInitial(username?: string) {
    if (!username) {
        return 'U'
    }

    return username
        .trim()
        .charAt(0)
        .toUpperCase()
}

function Header() {
    const navigate = useNavigate()
    const location = useLocation()

    const [searchValue, setSearchValue] =
        useState('')

    const user = useAuthStore(
        (state) => state.user,
    )

    const theme = useThemeStore(
        (state) => state.theme,
    )

    const toggleTheme = useThemeStore(
        (state) => state.toggleTheme,
    )

    const openMobileMenu = useUIStore(
        (state) => state.openMobileMenu,
    )

    const isProfilePage =
        location.pathname === '/app/profile'

    const username =
        user?.username || 'Tài khoản'

    const userInitial =
        getUserInitial(user?.username)

    const handleSearch = (
        event: FormEvent<HTMLFormElement>,
    ) => {
        event.preventDefault()

        const symbol = searchValue
            .trim()
            .toUpperCase()

        if (!symbol) {
            return
        }

        navigate(
            `/app/stocks/${encodeURIComponent(symbol)}`,
        )

        setSearchValue('')
    }

    const searchForm = (
        <form
            onSubmit={handleSearch}
            role="search"
            className="relative w-full"
        >
            <Search
                size={18}
                strokeWidth={1.9}
                aria-hidden="true"
                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <label
                htmlFor="global-stock-search"
                className="sr-only"
            >
                Tìm mã cổ phiếu
            </label>

            <input
                id="global-stock-search"
                type="search"
                value={searchValue}
                onChange={(event) =>
                    setSearchValue(
                        event.target.value,
                    )
                }
                placeholder="Tìm mã cổ phiếu, ví dụ FPT..."
                autoComplete="off"
                spellCheck={false}
                enterKeyHint="search"
                className="
                    h-11
                    w-full
                    min-w-0
                    rounded-xl
                    border
                    border-slate-200
                    bg-slate-50
                    pl-11
                    pr-4
                    text-base
                    text-slate-900
                    outline-none
                    transition-all
                    duration-150
                    placeholder:text-slate-400
                    hover:border-slate-300
                    focus:border-blue-500
                    focus:bg-white
                    focus:ring-2
                    focus:ring-blue-100
                    dark:border-slate-700
                    dark:bg-slate-800
                    dark:text-white
                    dark:placeholder:text-slate-500
                    dark:hover:border-slate-600
                    dark:focus:border-blue-500
                    dark:focus:bg-slate-800
                    dark:focus:ring-blue-500/20
                "
            />
        </form>
    )

    return (
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-900/95">
            {/* Mobile top bar */}
            <div className="flex h-16 items-center gap-2 px-4 lg:hidden">
                <button
                    type="button"
                    onClick={openMobileMenu}
                    aria-label="Mở menu điều hướng"
                    className="
                        flex
                        h-11
                        w-11
                        shrink-0
                        items-center
                        justify-center
                        rounded-xl
                        text-slate-600
                        transition-colors
                        duration-150
                        hover:bg-slate-100
                        hover:text-slate-900
                        focus-visible:outline-none
                        focus-visible:ring-2
                        focus-visible:ring-blue-500
                        dark:text-slate-300
                        dark:hover:bg-slate-800
                        dark:hover:text-white
                    "
                >
                    <Menu
                        size={22}
                        strokeWidth={1.9}
                        aria-hidden="true"
                    />
                </button>

                <button
                    type="button"
                    onClick={() =>
                        navigate('/app')
                    }
                    aria-label="Về trang tổng quan"
                    className="
                        min-w-0
                        flex-1
                        rounded-lg
                        text-left
                        focus-visible:outline-none
                        focus-visible:ring-2
                        focus-visible:ring-blue-500
                    "
                >
                    <div className="flex min-w-0 items-center gap-2.5">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white">
                            S
                        </div>

                        <p className="truncate text-base font-bold tracking-tight text-slate-900 dark:text-white">
                            STOCK-AI
                        </p>
                    </div>
                </button>

                <button
                    type="button"
                    onClick={toggleTheme}
                    aria-label={
                        theme === 'light'
                            ? 'Chuyển sang giao diện tối'
                            : 'Chuyển sang giao diện sáng'
                    }
                    title={
                        theme === 'light'
                            ? 'Giao diện tối'
                            : 'Giao diện sáng'
                    }
                    className="
                        flex
                        h-11
                        w-11
                        shrink-0
                        items-center
                        justify-center
                        rounded-xl
                        text-slate-600
                        transition-colors
                        duration-150
                        hover:bg-slate-100
                        hover:text-slate-900
                        focus-visible:outline-none
                        focus-visible:ring-2
                        focus-visible:ring-blue-500
                        dark:text-slate-300
                        dark:hover:bg-slate-800
                        dark:hover:text-white
                    "
                >
                    {theme === 'light' ? (
                        <Moon
                            size={20}
                            strokeWidth={1.9}
                            aria-hidden="true"
                        />
                    ) : (
                        <Sun
                            size={20}
                            strokeWidth={1.9}
                            aria-hidden="true"
                        />
                    )}
                </button>

                <button
                    type="button"
                    onClick={() =>
                        navigate('/app/profile')
                    }
                    aria-label={`Mở tài khoản ${username}`}
                    title={username}
                    className={[
                        'flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-colors duration-150',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                        isProfilePage
                            ? 'bg-blue-50 dark:bg-blue-500/10'
                            : 'hover:bg-slate-100 dark:hover:bg-slate-800',
                    ].join(' ')}
                >
                    <span
                        className={[
                            'flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold',
                            isProfilePage
                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400'
                                : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
                        ].join(' ')}
                    >
                        {userInitial}
                    </span>
                </button>
            </div>

            {/* Mobile search */}
            <div className="px-4 pb-3 lg:hidden">
                {searchForm}
            </div>

            {/* Desktop header */}
            <div className="hidden h-16 items-center gap-4 px-6 lg:flex lg:px-8">
                <div className="w-full min-w-0 max-w-xl">
                    {searchForm}
                </div>

                <div className="ml-auto flex shrink-0 items-center gap-2">
                    <button
                        type="button"
                        onClick={toggleTheme}
                        aria-label={
                            theme === 'light'
                                ? 'Chuyển sang giao diện tối'
                                : 'Chuyển sang giao diện sáng'
                        }
                        title={
                            theme === 'light'
                                ? 'Giao diện tối'
                                : 'Giao diện sáng'
                        }
                        className="
                            flex
                            h-11
                            w-11
                            items-center
                            justify-center
                            rounded-xl
                            text-slate-600
                            transition-colors
                            duration-150
                            hover:bg-slate-100
                            hover:text-slate-900
                            focus-visible:outline-none
                            focus-visible:ring-2
                            focus-visible:ring-blue-500
                            dark:text-slate-300
                            dark:hover:bg-slate-800
                            dark:hover:text-white
                        "
                    >
                        {theme === 'light' ? (
                            <Moon
                                size={20}
                                strokeWidth={1.9}
                                aria-hidden="true"
                            />
                        ) : (
                            <Sun
                                size={20}
                                strokeWidth={1.9}
                                aria-hidden="true"
                            />
                        )}
                    </button>

                    <button
                        type="button"
                        onClick={() =>
                            navigate(
                                '/app/profile',
                            )
                        }
                        aria-label={`Mở tài khoản ${username}`}
                        className={[
                            'flex h-11 max-w-[220px] items-center gap-2.5 rounded-xl px-3 transition-colors duration-150',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                            isProfilePage
                                ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400'
                                : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800',
                        ].join(' ')}
                    >
                        <span
                            className={[
                                'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold',
                                isProfilePage
                                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400'
                                    : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
                            ].join(' ')}
                        >
                            {userInitial}
                        </span>

                        <span className="min-w-0 truncate text-sm font-medium">
                            {username}
                        </span>
                    </button>
                </div>
            </div>
        </header>
    )
}

export default Header