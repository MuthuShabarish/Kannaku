import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [business, setBusiness] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('kanakku_token'));
  const [isLoading, setIsLoading] = useState(true);
  const [lastRecoveryKey, setLastRecoveryKey] = useState(null);

  useEffect(() => {
    async function loadUser() {
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const res = await api.getMe();
        if (res.success && res.data) {
          setUser(res.data.user);
          setBusiness(res.data.business);
        } else {
          logout();
        }
      } catch (err) {
        console.warn('Session expired or invalid:', err);
        logout();
      } finally {
        setIsLoading(false);
      }
    }
    loadUser();
  }, [token]);

  const login = async (phone, pin_or_password) => {
    const res = await api.login({ phone, pin_or_password });
    if (res.success && res.data) {
      const accessToken = res.data.tokens.access_token;
      localStorage.setItem('kanakku_token', accessToken);
      setToken(accessToken);
      setUser(res.data.user);
      setBusiness(res.data.business);
      return res.data;
    }
    throw new Error('Login failed');
  };

  const register = async (payload) => {
    const res = await api.register(payload);
    if (res.success && res.data) {
      const accessToken = res.data.tokens.access_token;
      localStorage.setItem('kanakku_token', accessToken);
      setToken(accessToken);
      setUser(res.data.user);
      setBusiness(res.data.business);
      if (res.data.emergency_recovery_key) {
        setLastRecoveryKey(res.data.emergency_recovery_key);
      }
      return res.data;
    }
    throw new Error('Registration failed');
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // Ignore network errors on logout
    }
    localStorage.removeItem('kanakku_token');
    setToken(null);
    setUser(null);
    setBusiness(null);
  };

  const updateBusiness = (newData) => {
    setBusiness(prev => ({ ...prev, ...newData }));
  };

  const refreshBusiness = async () => {
    try {
      const res = await api.getMe();
      if (res.success && res.data) {
        setUser(res.data.user);
        setBusiness(res.data.business);
      }
    } catch (e) {
      console.warn('Failed to refresh business profile:', e);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        business,
        token,
        isAuthenticated: !!user,
        isLoading,
        lastRecoveryKey,
        clearLastRecoveryKey: () => setLastRecoveryKey(null),
        login,
        register,
        logout,
        updateBusiness,
        refreshBusiness,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
