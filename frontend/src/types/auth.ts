export type LoginRequest = {
    username: string
    password: string
}

export type RegisterRequest = {
    username: string
    password: string
}

export type TokenResponse = {
    access_token: string
    token_type: string
}

export type AuthUser = {
    id?: number
    username: string
    is_admin?: boolean
}