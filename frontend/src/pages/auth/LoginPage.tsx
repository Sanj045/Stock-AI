import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import {
    ArrowRight,
    BarChart3,
    Bot,
    Eye,
    EyeOff,
    LockKeyhole,
    ShieldCheck,
    UserRound,
} from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import {
    Link,
    useLocation,
    useNavigate,
} from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import {
    getCurrentUser,
    loginUser,
} from '../../api/auth'
import { useAuthStore } from '../../store/auth.store'

const loginSchema = z.object({
    username: z
        .string()
        .trim()
        .min(
            3,
            'Tên đăng nhập phải có ít nhất 3 ký tự.',
        )
        .max(
            30,
            'Tên đăng nhập tối đa 30 ký tự.',
        ),

    password: z
        .string()
        .min(
            6,
            'Mật khẩu phải có ít nhất 6 ký tự.',
        )
        .max(
            64,
            'Mật khẩu tối đa 64 ký tự.',
        ),
})

type LoginFormData = z.infer<
    typeof loginSchema
>

type LoginLocationState = {
    from?: string
}

function LoginPage() {
    const navigate = useNavigate()
    const location = useLocation()

    const [showPassword, setShowPassword] =
        useState(false)

    const setToken = useAuthStore(
        (state) => state.setToken,
    )

    const setUser = useAuthStore(
        (state) => state.setUser,
    )

    const logout = useAuthStore(
        (state) => state.logout,
    )

    const {
        register,
        handleSubmit,
        formState: {
            errors,
            isSubmitting,
        },
    } = useForm<LoginFormData>({
        resolver: zodResolver(loginSchema),

        defaultValues: {
            username: '',
            password: '',
        },
    })

    const onSubmit = async (
        data: LoginFormData,
    ) => {
        try {
            const tokenData = await loginUser({
                username: data.username,
                password: data.password,
            })

            setToken(tokenData.access_token)

            const currentUser = await getCurrentUser()

            setUser(currentUser)

            toast.success('Đăng nhập thành công.')

            const locationState =
                location.state as LoginLocationState | null

            const requestedPath =
                locationState?.from

            const destination =
                requestedPath?.startsWith('/app')
                    ? requestedPath
                    : '/app'

            navigate(destination, {
                replace: true,
            })
        } catch (error) {
            logout()

            if (axios.isAxiosError(error)) {
                if (error.response?.status === 401) {
                    toast.error(
                        'Tên đăng nhập hoặc mật khẩu không đúng.',
                    )

                    return
                }

                const detail =
                    error.response?.data?.detail

                if (typeof detail === 'string') {
                    toast.error(detail)

                    return
                }

                if (!error.response) {
                    toast.error(
                        'Không thể kết nối tới máy chủ. Hãy kiểm tra backend.',
                    )

                    return
                }
            }

            toast.error(
                'Không thể đăng nhập. Vui lòng thử lại.',
            )
        }
    }

    return (
        <div className="min-h-screen bg-slate-950 lg:bg-slate-50 dark:lg:bg-slate-950">
            <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.05fr)_minmax(520px,0.95fr)]">
                {/* Desktop branding panel */}
                <section className="relative hidden overflow-hidden bg-slate-950 p-10 text-white lg:flex lg:min-h-screen lg:flex-col lg:justify-between xl:p-14">
                    <div
                        aria-hidden="true"
                        className="pointer-events-none absolute -left-40 -top-40 h-96 w-96 rounded-full bg-blue-600/20 blur-3xl"
                    />

                    <div
                        aria-hidden="true"
                        className="pointer-events-none absolute -bottom-48 right-0 h-[420px] w-[420px] rounded-full bg-blue-500/10 blur-3xl"
                    />

                    <Link
                        to="/"
                        className="relative z-10 inline-flex w-fit items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                    >
                        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-lg font-bold text-white">
                            S
                        </div>

                        <div>
                            <p className="text-xl font-bold tracking-tight">
                                STOCK-AI
                            </p>

                            <p className="text-sm text-slate-400">
                                Stock Intelligence
                            </p>
                        </div>
                    </Link>

                    <div className="relative z-10 max-w-xl">
                        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-400">
                            Stock Intelligence Platform
                        </p>

                        <h1 className="mt-5 text-4xl font-bold leading-[1.15] tracking-tight xl:text-5xl">
                            Hiểu dữ liệu thị trường rõ ràng hơn
                            với sự hỗ trợ của AI.
                        </h1>

                        <p className="mt-6 max-w-lg text-lg leading-8 text-slate-300">
                            Theo dõi cổ phiếu, xem các chỉ số
                            quan trọng và sử dụng AI để tổng hợp
                            dữ liệu trong một giao diện dễ sử dụng.
                        </p>

                        <div className="mt-10 grid gap-3">
                            <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
                                <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300">
                                    <BarChart3 size={20} />
                                </div>

                                <div>
                                    <p className="font-semibold">
                                        Theo dõi dữ liệu cổ phiếu
                                    </p>

                                    <p className="mt-1 text-sm leading-6 text-slate-400">
                                        Giá, xu hướng, kỹ thuật và các
                                        chỉ số cơ bản.
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
                                <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300">
                                    <Bot size={20} />
                                </div>

                                <div>
                                    <p className="font-semibold">
                                        Phân tích hỗ trợ bởi AI
                                    </p>

                                    <p className="mt-1 text-sm leading-6 text-slate-400">
                                        Tổng hợp dữ liệu theo hướng dễ
                                        đọc, trung lập và có cấu trúc.
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
                                <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300">
                                    <ShieldCheck size={20} />
                                </div>

                                <div>
                                    <p className="font-semibold">
                                        Tài khoản cá nhân
                                    </p>

                                    <p className="mt-1 text-sm leading-6 text-slate-400">
                                        Watchlist và các cuộc trò chuyện
                                        được lưu theo tài khoản.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <p className="relative z-10 text-sm text-slate-500">
                        STOCK-AI
                    </p>
                </section>

                {/* Login side */}
                <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-4 py-8 sm:px-6 lg:bg-slate-50 lg:px-10 xl:px-16 dark:lg:bg-slate-950">
                    {/* Desktop-only background */}
                    <div
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-0 hidden lg:block"
                    >
                        <div className="absolute left-[-8%] top-1/2 h-48 w-[116%] -translate-y-1/2 rounded-full bg-gradient-to-r from-blue-50/20 via-blue-200/70 to-blue-50/20 blur-2xl dark:from-blue-950/10 dark:via-blue-800/25 dark:to-blue-950/10" />

                        <div className="absolute -left-20 top-1/2 h-80 w-80 -translate-y-1/2 rounded-full bg-blue-400/10 blur-3xl" />

                        <div className="absolute right-8 top-[28%] h-64 w-64 rounded-full bg-blue-300/10 blur-3xl" />
                    </div>

                    <div className="relative z-10 w-full max-w-md">
                        {/* Mobile logo */}
                        <div className="mb-10 lg:hidden">
                            <Link
                                to="/"
                                className="inline-flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                            >
                                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 font-bold text-white">
                                    S
                                </div>

                                <div>
                                    <p className="text-lg font-bold tracking-tight text-white">
                                        STOCK-AI
                                    </p>

                                    <p className="text-xs text-slate-400">
                                        Stock Intelligence
                                    </p>
                                </div>
                            </Link>
                        </div>

                        {/* Login card */}
                        <div
                            className="
                rounded-3xl
                border
                border-white/90
                bg-white/95
                p-6
                shadow-[0_30px_90px_-20px_rgba(2,6,23,0.55)]
                backdrop-blur-xl
                ring-1
                ring-white/60

                sm:p-8

                lg:border-white/90
                lg:bg-white/90
                lg:p-9
                lg:shadow-[0_28px_75px_-24px_rgba(15,23,42,0.32)]
                lg:ring-slate-200/60

                xl:p-10

                dark:lg:border-slate-700/70
                dark:lg:bg-slate-900/88
                dark:lg:ring-slate-800/80
              "
                        >
                            <div>
                                <p className="text-sm font-semibold text-blue-600 dark:lg:text-blue-400">
                                    Chào mừng trở lại
                                </p>

                                <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl dark:lg:text-white">
                                    Đăng nhập
                                </h1>

                                <p className="mt-3 text-base leading-7 text-slate-500 dark:lg:text-slate-400">
                                    Đăng nhập để tiếp tục sử dụng
                                    STOCK-AI.
                                </p>
                            </div>

                            <form
                                onSubmit={handleSubmit(onSubmit)}
                                noValidate
                                className="mt-8 space-y-5"
                            >
                                {/* Username */}
                                <div>
                                    <label
                                        htmlFor="username"
                                        className="mb-2 block text-sm font-semibold text-slate-700 dark:lg:text-slate-200"
                                    >
                                        Tên đăng nhập
                                    </label>

                                    <div className="relative">
                                        <UserRound
                                            size={19}
                                            aria-hidden="true"
                                            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                                        />

                                        <input
                                            id="username"
                                            type="text"
                                            autoComplete="username"
                                            placeholder="Nhập tên đăng nhập"
                                            aria-invalid={
                                                Boolean(errors.username)
                                            }
                                            aria-describedby={
                                                errors.username
                                                    ? 'username-error'
                                                    : undefined
                                            }
                                            {...register('username')}
                                            className={[
                                                'h-12 w-full rounded-xl border bg-white pl-11 pr-4',
                                                'text-base text-slate-900 outline-none transition',
                                                'placeholder:text-slate-400',
                                                'focus:ring-2',
                                                'dark:lg:bg-slate-900 dark:lg:text-white',
                                                errors.username
                                                    ? 'border-red-500 focus:border-red-500 focus:ring-red-100 dark:lg:border-red-500 dark:lg:focus:ring-red-500/20'
                                                    : 'border-slate-300 focus:border-blue-500 focus:ring-blue-100 dark:lg:border-slate-700 dark:lg:focus:border-blue-500 dark:lg:focus:ring-blue-500/20',
                                            ].join(' ')}
                                        />
                                    </div>

                                    {errors.username && (
                                        <p
                                            id="username-error"
                                            role="alert"
                                            className="mt-2 text-sm text-red-700 dark:lg:text-red-400"
                                        >
                                            {errors.username.message}
                                        </p>
                                    )}
                                </div>

                                {/* Password */}
                                <div>
                                    <label
                                        htmlFor="password"
                                        className="mb-2 block text-sm font-semibold text-slate-700 dark:lg:text-slate-200"
                                    >
                                        Mật khẩu
                                    </label>

                                    <div className="relative">
                                        <LockKeyhole
                                            size={19}
                                            aria-hidden="true"
                                            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                                        />

                                        <input
                                            id="password"
                                            type={
                                                showPassword
                                                    ? 'text'
                                                    : 'password'
                                            }
                                            autoComplete="current-password"
                                            placeholder="Nhập mật khẩu"
                                            aria-invalid={
                                                Boolean(errors.password)
                                            }
                                            aria-describedby={
                                                errors.password
                                                    ? 'password-error'
                                                    : undefined
                                            }
                                            {...register('password')}
                                            className={[
                                                'h-12 w-full rounded-xl border bg-white pl-11 pr-12',
                                                'text-base text-slate-900 outline-none transition',
                                                'placeholder:text-slate-400',
                                                'focus:ring-2',
                                                'dark:lg:bg-slate-900 dark:lg:text-white',
                                                errors.password
                                                    ? 'border-red-500 focus:border-red-500 focus:ring-red-100 dark:lg:border-red-500 dark:lg:focus:ring-red-500/20'
                                                    : 'border-slate-300 focus:border-blue-500 focus:ring-blue-100 dark:lg:border-slate-700 dark:lg:focus:border-blue-500 dark:lg:focus:ring-blue-500/20',
                                            ].join(' ')}
                                        />

                                        <button
                                            type="button"
                                            onClick={() =>
                                                setShowPassword(
                                                    (current) => !current,
                                                )
                                            }
                                            aria-label={
                                                showPassword
                                                    ? 'Ẩn mật khẩu'
                                                    : 'Hiện mật khẩu'
                                            }
                                            className="absolute right-2 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:lg:text-slate-400 dark:lg:hover:bg-slate-800 dark:lg:hover:text-white"
                                        >
                                            {showPassword ? (
                                                <EyeOff size={19} />
                                            ) : (
                                                <Eye size={19} />
                                            )}
                                        </button>
                                    </div>

                                    {errors.password && (
                                        <p
                                            id="password-error"
                                            role="alert"
                                            className="mt-2 text-sm text-red-700 dark:lg:text-red-400"
                                        >
                                            {errors.password.message}
                                        </p>
                                    )}
                                </div>

                                {/* Submit */}
                                <button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-base font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:lg:focus-visible:ring-offset-slate-950"
                                >
                                    {isSubmitting
                                        ? 'Đang đăng nhập...'
                                        : 'Đăng nhập'}

                                    {!isSubmitting && (
                                        <ArrowRight
                                            size={19}
                                            aria-hidden="true"
                                        />
                                    )}
                                </button>
                            </form>

                            {/* Register link */}
                            <div className="mt-7 border-t border-slate-200 pt-6 text-center dark:lg:border-slate-800">
                                <p className="text-sm text-slate-500 dark:lg:text-slate-400">
                                    Chưa có tài khoản?{' '}
                                    <Link
                                        to="/register"
                                        className="font-semibold text-blue-600 transition hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:lg:text-blue-400 dark:lg:hover:text-blue-300"
                                    >
                                        Tạo tài khoản
                                    </Link>
                                </p>
                            </div>

                            {/* Disclaimer */}
                            <p className="mt-8 text-center text-xs leading-5 text-slate-400 dark:lg:text-slate-500">
                                STOCK-AI cung cấp công cụ hỗ trợ phân
                                tích dữ liệu và không thay thế quyết
                                định đầu tư của người dùng.
                            </p>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    )
}

export default LoginPage