import api from './axios'

import type {
    AuthUser,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
} from '../types/auth'

export async function registerUser(
    payload: RegisterRequest,
): Promise<void> {
    await api.post('/register', payload)
}

export async function loginUser(
    payload: LoginRequest,
): Promise<TokenResponse> {
    const formData = new URLSearchParams()

    formData.append('username', payload.username)
    formData.append('password', payload.password)

    const response = await api.post<TokenResponse>(
        '/login',
        formData,
        {
            headers: {
                'Content-Type':
                    'application/x-www-form-urlencoded',
            },
        },
    )

    return response.data
}

export async function getCurrentUser(): Promise<AuthUser> {
    const response = await api.get<AuthUser>('/me')

    return response.data
}