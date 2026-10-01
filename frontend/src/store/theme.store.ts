import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark'

type ThemeState = {
    theme: Theme
    setTheme: (theme: Theme) => void
    toggleTheme: () => void
}

export const useThemeStore = create<ThemeState>()(
    persist(
        (set, get) => ({
            theme: 'light',

            setTheme: (theme) => {
                set({ theme })

                document.documentElement.classList.toggle(
                    'dark',
                    theme === 'dark',
                )
            },

            toggleTheme: () => {
                const nextTheme = get().theme === 'light' ? 'dark' : 'light'

                set({ theme: nextTheme })

                document.documentElement.classList.toggle(
                    'dark',
                    nextTheme === 'dark',
                )
            },
        }),
        {
            name: 'stock_ai_theme',
        },
    ),
)