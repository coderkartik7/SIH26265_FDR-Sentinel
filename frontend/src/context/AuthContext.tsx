import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';
import apiClient from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  login: (token: string, refreshToken: string, userData: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const normalizeUser = (u: any): User | null => {
  if (!u) return null;
  return {
    ...u,
    role: (u.role ? String(u.role).toUpperCase() : 'INSTITUTION') as UserRole,
  };
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('sentinel_user');
    try {
      return saved ? normalizeUser(JSON.parse(saved)) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('sentinel_access_token');
  });

  const login = (accessToken: string, refreshToken: string, userData: User) => {
    const normalized = normalizeUser(userData) || userData;
    localStorage.setItem('sentinel_access_token', accessToken);
    localStorage.setItem('sentinel_refresh_token', refreshToken);
    localStorage.setItem('sentinel_user', JSON.stringify(normalized));
    setToken(accessToken);
    setUser(normalized);
  };

  const logout = () => {
    localStorage.removeItem('sentinel_access_token');
    localStorage.removeItem('sentinel_refresh_token');
    localStorage.removeItem('sentinel_user');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const res = await apiClient.get<User>('/auth/me');
      const normalized = normalizeUser(res.data) || res.data;
      setUser(normalized);
      localStorage.setItem('sentinel_user', JSON.stringify(normalized));
    } catch (err) {
      console.error('Failed to refresh user profile', err);
    }
  };

  const currentRole = (user?.role ? String(user.role).toUpperCase() : null) as UserRole | null;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: currentRole,
        isAuthenticated: !!token && !!user,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
