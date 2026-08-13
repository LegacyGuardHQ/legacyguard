const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const ACCESS_TOKEN_KEY = 'legacyguard.access_token';
const REFRESH_TOKEN_KEY = 'legacyguard.refresh_token';

export class ApiError extends Error {
  status: number;
  detail?: string;
  cause?: unknown;

  constructor(message: string, status: number, detail?: string, cause?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.cause = cause;
  }

  get isNetworkError(): boolean {
    return this.status === 0;
  }

  get isAuthenticationError(): boolean {
    return this.status === 401;
  }
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function saveTokens(accessToken: string, refreshToken: string): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: string | undefined;
  let parseFailure: unknown;

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') {
      detail = body.detail;
    } else if (Array.isArray(body.detail)) {
      detail = body.detail
        .map((item) => {
          if (typeof item === 'object' && item !== null && 'msg' in item) {
            return String((item as { msg: unknown }).msg);
          }
          return String(item);
        })
        .join(' ');
    }
  } catch (error) {
    parseFailure = error;
  }

  const message = detail || `Request failed with status ${response.status}`;
  return new ApiError(message, response.status, detail, parseFailure);
}

export async function request<T>(path: string, options: RequestInit = {}, authenticated = false): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (authenticated) {
    const token = getAccessToken();
    if (!token) {
      clearTokens();
      window.dispatchEvent(new CustomEvent('legacyguard:unauthorized'));
      throw new ApiError('Your session has expired. Please sign in again.', 401);
    }
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch (error) {
    throw new ApiError('Unable to reach the LegacyGuard backend.', 0, undefined, error);
  }

  if (response.status === 401 && authenticated) {
    clearTokens();
    window.dispatchEvent(new CustomEvent('legacyguard:unauthorized'));
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch (error) {
    throw new ApiError('The LegacyGuard backend returned an unreadable response.', response.status, undefined, error);
  }
}
