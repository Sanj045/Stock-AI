import { useEffect } from 'react'
import {
    Navigate,
    Outlet,
    useLocation,
} from 'react-router-dom'

import { useAuthStore } from '../../store/auth.store'

function ProtectedRoute() {
    const location = useLocation()

    const isAuthenticated = useAuthStore(
        (state) => state.isAuthenticated,
    )

    const isCheckingAuth = useAuthStore(
        (state) => state.isCheckingAuth,
    )

    const hasInitializedAuth = useAuthStore(
        (state) => state.hasInitializedAuth,
    )

    const initializeAuth = useAuthStore(
        (state) => state.initializeAuth,
    )

    useEffect(() => {
        void initializeAuth()
    }, [initializeAuth])

    if (
        isCheckingAuth ||
        !hasInitializedAuth
    ) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
                <div
                    role="status"
                    aria-live="polite"
                    className="text-center"
                >
                    <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600 dark:border-slate-700 dark:border-t-blue-400" />

                    <p className="mt-4 text-sm font-medium text-slate-600 dark:text-slate-300">
                        Đang kiểm tra phiên đăng nhập...
                    </p>
                </div>
            </div>
        )
    }

    if (!isAuthenticated) {
        return (
            <Navigate
                to="/login"
                replace
                state={{
                    from: location.pathname,
                }}
            />
        )
    }

    return <Outlet />
}

export default ProtectedRoute