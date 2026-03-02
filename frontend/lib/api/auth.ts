const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  username: string
  email: string
  role: string
  created_at: string
  last_login_at: string
  is_active: boolean
}

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    if (Array.isArray(detail)) {
      throw new Error(detail.map((d: { msg: string }) => d.msg).join(", "))
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed")
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function loginUser(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export async function registerUser(
  username: string,
  email: string,
  password: string,
): Promise<UserResponse> {
  return request<UserResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  })
}

export async function refreshTokens(refresh_token: string): Promise<TokenResponse> {
  return request<TokenResponse>("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token }),
  })
}

export async function logoutUser(refresh_token: string): Promise<void> {
  return request<void>("/api/v1/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token }),
  })
}

export async function logoutAllSessions(access_token: string): Promise<void> {
  return request<void>("/api/v1/auth/logout_all", {
    method: "POST",
    headers: { Authorization: `Bearer ${access_token}` },
  })
}
