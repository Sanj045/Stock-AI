import { create } from 'zustand'

import { getCurrentUser } from '../api/auth'
import type { AuthUser } from '../types/auth'

type AuthState = {
    token: string | null
    user: AuthUser | null

    isAuthenticated: boolean
    isCheckingAuth: boolean
    hasInitializedAuth: boolean

    setToken: (token: string) => void
    setUser: (user: AuthUser) => void

    initializeAuth: () => Promise<void>
    logout: () => void
}

const storedToken = localStorage.getItem('stock_ai_token')

export const useAuthStore = create<AuthState>((set, get) => ({
    token: storedToken,
    user: null,

    isAuthenticated: false,
    isCheckingAuth: Boolean(storedToken),
    hasInitializedAuth: false,

    setToken: (token) => {
        localStorage.setItem('stock_ai_token', token)

        set({
            token,
        })
    },

    setUser: (user) => {
        set({
            user,
            isAuthenticated: true,
        })
    },

    initializeAuth: async () => {
        if (get().hasInitializedAuth) {
            return
        }

        const token =
            get().token ??
            localStorage.getItem('stock_ai_token')

        if (!token) {
            set({
                token: null,
                user: null,
                isAuthenticated: false,
                isCheckingAuth: false,
                hasInitializedAuth: true,
            })

            return
        }

        set({
            token,
            isCheckingAuth: true,
        })

        try {
            const user = await getCurrentUser()

            set({
                token,
                user,
                isAuthenticated: true,
                isCheckingAuth: false,
                hasInitializedAuth: true,
            })
        } catch {
            localStorage.removeItem('stock_ai_token')

            set({
                token: null,
                user: null,
                isAuthenticated: false,
                isCheckingAuth: false,
                hasInitializedAuth: true,
            })
        }
    },

    logout: () => {
        localStorage.removeItem('stock_ai_token')

        set({
            token: null,
            user: null,
            isAuthenticated: false,
            isCheckingAuth: false,
            hasInitializedAuth: true,
        })
    },
}))