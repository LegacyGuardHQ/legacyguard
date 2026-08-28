import { beforeEach, describe, expect, it } from 'vitest';
import { clearTokens, getAccessToken, saveAccessToken } from '../api/client';

describe('authentication token storage', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('stores only the short-lived access token and removes a legacy refresh token', () => {
    sessionStorage.setItem('legacyguard.refresh_token', 'legacy-refresh-token');

    saveAccessToken('synthetic-access-token');

    expect(getAccessToken()).toBe('synthetic-access-token');
    expect(sessionStorage.getItem('legacyguard.refresh_token')).toBeNull();
  });

  it('clears both current access tokens and legacy refresh tokens', () => {
    sessionStorage.setItem('legacyguard.access_token', 'synthetic-access-token');
    sessionStorage.setItem('legacyguard.refresh_token', 'legacy-refresh-token');

    clearTokens();

    expect(getAccessToken()).toBeNull();
    expect(sessionStorage.getItem('legacyguard.refresh_token')).toBeNull();
  });

  it('removes a legacy refresh token while restoring authentication state', () => {
    sessionStorage.setItem('legacyguard.refresh_token', 'legacy-refresh-token');

    expect(getAccessToken()).toBeNull();
    expect(sessionStorage.getItem('legacyguard.refresh_token')).toBeNull();
  });
});
