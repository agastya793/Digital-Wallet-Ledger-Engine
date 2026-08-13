import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './app/dashboard/DashboardPage';
import { TransfersPage } from './app/transfers/TransfersPage';
import { MerchantDashboardPage } from './app/merchants/MerchantDashboardPage';
import { LoginPage } from './app/auth/LoginPage';
import { RegisterPage } from './app/auth/RegisterPage';
import { useAuthStore } from './stores/authStore';

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
  return (
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
          <Route path="/wallet" element={<Navigate to="/dashboard" replace />} />
          <Route path="/transfers" element={<TransfersPage />} />
          <Route path="/merchants" element={<MerchantDashboardPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default App;
