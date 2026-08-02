import { request } from './client';
import type { TokenResponse, User } from '../types/auth';

export function register(email: string, password: string): Promise<User> {
  return request<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function fetchCurrentUser(): Promise<User> {
  return request<User>('/auth/me', {}, true);
}

export function logout(): Promise<{ message: string }> {
  return request<{ message: string }>('/auth/logout', { method: 'POST' }, true);
}
