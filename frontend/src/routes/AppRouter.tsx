import {
    Navigate,
    Route,
    Routes,
} from 'react-router-dom'

import ProtectedRoute from '../components/common/ProtectedRoute'
import PublicOnlyRoute from '../components/common/PublicOnlyRoute'
import UserLayout from '../layouts/UserLayout'
import DashboardPage from '../pages/DashboardPage'
import LoginPage from '../pages/auth/LoginPage'
import RegisterPage from '../pages/auth/RegisterPage'

function PlaceholderPage({
    title,
}: {
    title: string
}) {
    return (
        <div className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 dark:border-slate-800 dark:bg-slate-900">
                <p className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                    Stock-AI
                </p>

                <h1 className="mt-2 text-2xl font-bold text-slate-900 sm:text-3xl dark:text-white">
                    {title}
                </h1>

                <p className="mt-3 text-base text-slate-500 dark:text-slate-400">
                    Màn hình này sẽ được triển khai ở phase
                    tương ứng.
                </p>
            </div>
        </div>
    )
}

function AppRouter() {
    return (
        <Routes>
            <Route
                path="/"
                element={
                    <Navigate
                        to="/app"
                        replace
                    />
                }
            />

            <Route element={<PublicOnlyRoute />}>
                <Route
                    path="/login"
                    element={<LoginPage />}
                />

                <Route
                    path="/register"
                    element={<RegisterPage />}
                />
            </Route>

            <Route element={<ProtectedRoute />}>
                <Route
                    path="/app"
                    element={<UserLayout />}
                >
                    <Route
                        index
                        element={<DashboardPage />}
                    />

                    <Route
                        path="stocks"
                        element={
                            <PlaceholderPage title="Cổ phiếu" />
                        }
                    />

                    <Route
                        path="stocks/:symbol"
                        element={
                            <PlaceholderPage title="Chi tiết cổ phiếu" />
                        }
                    />

                    <Route
                        path="watchlist"
                        element={
                            <PlaceholderPage title="Theo dõi" />
                        }
                    />

                    <Route
                        path="analysis"
                        element={
                            <PlaceholderPage title="Phân tích AI" />
                        }
                    />

                    <Route
                        path="analysis/:symbol"
                        element={
                            <PlaceholderPage title="Phân tích AI" />
                        }
                    />

                    <Route
                        path="chat"
                        element={
                            <PlaceholderPage title="Trợ lý AI" />
                        }
                    />

                    <Route
                        path="chat/:conversationId"
                        element={
                            <PlaceholderPage title="Trợ lý AI" />
                        }
                    />

                    <Route
                        path="conversations"
                        element={
                            <PlaceholderPage title="Cuộc trò chuyện" />
                        }
                    />

                    <Route
                        path="news"
                        element={
                            <PlaceholderPage title="Tin tức" />
                        }
                    />

                    <Route
                        path="profile"
                        element={
                            <PlaceholderPage title="Tài khoản" />
                        }
                    />
                </Route>
            </Route>

            <Route
                path="*"
                element={
                    <Navigate
                        to="/app"
                        replace
                    />
                }
            />
        </Routes>
    )
}

export default AppRouter