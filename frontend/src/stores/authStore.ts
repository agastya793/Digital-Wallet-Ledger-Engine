import { create } from 'zustand';

interface AuthState {
  token: string | null;
  userEmail: string | null;
  isAuthenticated: boolean;
  setAuth: (token: string, email: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  userEmail: null,
  isAuthenticated: false,
  setAuth: (token, email) => set({ token, userEmail: email, isAuthenticated: true }),
  logout: () => set({ token: null, userEmail: null, isAuthenticated: false }),
}));
