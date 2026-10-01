import { create } from 'zustand'

type UIState = {
    isMobileMenuOpen: boolean
    isSidebarCollapsed: boolean

    openMobileMenu: () => void
    closeMobileMenu: () => void
    toggleMobileMenu: () => void

    toggleSidebar: () => void
}

export const useUIStore = create<UIState>((set) => ({
    isMobileMenuOpen: false,
    isSidebarCollapsed: false,

    openMobileMenu: () => {
        set({ isMobileMenuOpen: true })
    },

    closeMobileMenu: () => {
        set({ isMobileMenuOpen: false })
    },

    toggleMobileMenu: () => {
        set((state) => ({
            isMobileMenuOpen: !state.isMobileMenuOpen,
        }))
    },

    toggleSidebar: () => {
        set((state) => ({
            isSidebarCollapsed: !state.isSidebarCollapsed,
        }))
    },
}))