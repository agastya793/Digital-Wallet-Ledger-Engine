import { useEffect, useState } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './app/dashboard/DashboardPage';
import { WalletPage } from './app/wallet/WalletPage';
import { TransfersPage } from './app/transfers/TransfersPage';
import { MerchantDashboardPage } from './app/merchants/MerchantDashboardPage';
import { LoginPage } from './app/auth/LoginPage';
import { RegisterPage } from './app/auth/RegisterPage';
import { TransactionDetailPage } from './app/transactions/TransactionDetailPage';
import { SystemOpsPage } from './app/admin/SystemOpsPage';
import { useAuthStore } from './stores/authStore';
import axios from 'axios';
import { Toaster } from 'sonner';

// Protect routes that require login
function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

// Redirect logged-in users away from auth pages
function PublicRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}

function App() {
  const [isInitializing, setIsInitializing] = useState(true);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const setAuth = useAuthStore((state) => state.setAuth);

  useEffect(() => {
    const initAuth = async () => {
      if (isAuthenticated) {
        setIsInitializing(false);
        return;
      }
      
      try {
        // Attempt silent refresh using HttpOnly cookie
        const response = await axios.post(
          'http://localhost:8000/api/v1/auth/refresh',
          {},
          { withCredentials: true }
        );
        const { access_token } = response.data;
        
        // Fetch user profile to get the email
        const meResponse = await axios.get('http://localhost:8000/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${access_token}` },
        });
        
        setAuth(access_token, meResponse.data.email);
      } catch {
        // Refresh failed (no cookie, expired, etc), remain logged out
      } finally {
        setIsInitializing(false);
      }
    };
    initAuth();
  }, [isAuthenticated, setAuth]);

  if (isInitializing) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-gray-950">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <>
      <Toaster position="top-right" theme="dark" richColors />
      <Routes>
        {/* Public Routes */}
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* Protected Routes */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/wallet" element={<WalletPage />} />
            <Route path="/wallets/:walletId/transactions/:transactionId" element={<TransactionDetailPage />} />
            <Route path="/transfers" element={<TransfersPage />} />
            <Route path="/merchants" element={<MerchantDashboardPage />} />
            <Route path="/admin" element={<SystemOpsPage />} />
          </Route>
        </Route>
      </Routes>
    </>
  );
}

export default App;
