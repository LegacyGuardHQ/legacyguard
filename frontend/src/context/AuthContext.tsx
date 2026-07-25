import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  ApiError,
  clearTokens,
  fetchCurrentUser,
  getAccessToken,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  saveTokens,
  type User,
} from '../services/api';

type AuthContextValue = {
  user: User | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  const resetSession = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const restoreSession = useCallback(async () => {
    if (!getAccessToken()) {
      setIsInitializing(false);
      return;
    }

    try {
      setUser(await fetchCurrentUser());
    } catch {
      resetSession();
    } finally {
      setIsInitializing(false);
    }
  }, [resetSession]);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    const handleUnauthorized = () => resetSession();
    window.addEventListener('legacyguard:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('legacyguard:unauthorized', handleUnauthorized);
  }, [resetSession]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await loginRequest(email, password);
    saveTokens(tokens);
    try {
      setUser(await fetchCurrentUser());
    } catch (error) {
      resetSession();
      throw error;
    }
  }, [resetSession]);

  const register = useCallback(async (email: string, password: string) => {
    await registerRequest(email, password);
    await login(email, password);
  }, [login]);

  const logout = useCallback(async () => {
    try {
      if (getAccessToken()) {
        await logoutRequest();
      }
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) {
        throw error;
      }
    } finally {
      resetSession();
    }
  }, [resetSession]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isAuthenticated: Boolean(user),
    isInitializing,
    login,
    register,
    logout,
  }), [user, isInitializing, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
