import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'

import Header from '../components/layout/Header'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import Sidebar from '../components/layout/Sidebar'
import { useThemeStore } from '../store/theme.store'
import { useUIStore } from '../store/ui.store'

function UserLayout() {
    const theme = useThemeStore(
        (state) => state.theme,
    )

    const isMobileMenuOpen = useUIStore(
        (state) => state.isMobileMenuOpen,
    )

    /*
     * Đồng bộ theme với <html>.
     */
    useEffect(() => {
        document.documentElement.classList.toggle(
            'dark',
            theme === 'dark',
        )
    }, [theme])

    /*
     * Khi mobile drawer mở:
     * - khóa scroll của page phía sau
     * - chỉ áp dụng dưới breakpoint desktop
     *
     * Nếu người dùng resize sang desktop,
     * body sẽ được mở scroll trở lại.
     */
    useEffect(() => {
        const mobileMediaQuery =
            window.matchMedia(
                '(max-width: 1023px)',
            )

        const updateBodyScroll = () => {
            const shouldLockScroll =
                isMobileMenuOpen &&
                mobileMediaQuery.matches

            document.body.style.overflow =
                shouldLockScroll
                    ? 'hidden'
                    : ''
        }

        updateBodyScroll()

        mobileMediaQuery.addEventListener(
            'change',
            updateBodyScroll,
        )

        return () => {
            mobileMediaQuery.removeEventListener(
                'change',
                updateBodyScroll,
            )

            document.body.style.overflow = ''
        }
    }, [isMobileMenuOpen])

    return (
        <div className="min-h-screen min-h-dvh overflow-x-hidden bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
            {/* Desktop sidebar + mobile drawer */}
            <Sidebar />

            {/* Main application shell */}
            <div className="min-h-screen min-h-dvh min-w-0 lg:pl-64">
                <Header />

                <main
                    id="app-main-content"
                    className="
                        min-w-0
                        overflow-x-clip
                        pb-[calc(6rem+env(safe-area-inset-bottom))]
                        lg:pb-8
                    "
                >
                    <Outlet />
                </main>
            </div>

            {/* Mobile-only bottom navigation */}
            <MobileBottomNav />
        </div>
    )
}

export default UserLayout