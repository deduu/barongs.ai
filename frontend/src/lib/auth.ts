export interface AuthUser {
  id: string;
  email: string;
  tenant_id: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const resp = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || `Login failed: ${resp.status}`);
  }
  return resp.json();
}

export async function register(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const resp = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || `Registration failed: ${resp.status}`);
  }
  return resp.json();
}

export async function fetchMe(token: string): Promise<AuthUser> {
  const resp = await fetch("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Unauthorized: ${resp.status}`);
  return resp.json();
}
