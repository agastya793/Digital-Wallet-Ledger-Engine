import { Link, Outlet, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Wallet, 
  ArrowLeftRight, 
  Store,
  Bell,
  LogOut,
  Activity
} from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { useNotifications } from '../../lib/hooks/useNotifications';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Wallet', href: '/wallet', icon: Wallet },
  { name: 'Transfers', href: '/transfers', icon: ArrowLeftRight },
  { name: 'Merchants', href: '/merchants', icon: Store },
  { name: 'System Ops', href: '/admin', icon: Activity },
];

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export function AppLayout() {
  const location = useLocation();
  useNotifications();

  return (
    <div className="flex h-screen w-full bg-zinc-950 text-zinc-50 overflow-hidden">
      
      {/* Sidebar */}
      <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 border-r border-zinc-800 bg-zinc-900/50 backdrop-blur-xl">
        <div className="flex flex-col flex-grow pt-6 pb-4 overflow-y-auto">
          <div className="flex items-center flex-shrink-0 px-6 mb-8">
            <div className="h-8 w-8 rounded-lg bg-indigo-500 flex items-center justify-center mr-3">
              <Wallet className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">LedgerEngine</span>
          </div>
          
          <div className="px-4 flex-grow">
            <nav className="flex-1 space-y-2">
              {navigation.map((item) => {
                const isActive = location.pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={classNames(
                      isActive 
                        ? 'bg-zinc-800 text-white shadow-sm ring-1 ring-zinc-700/50' 
                        : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100',
                      'group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200'
                    )}
                  >
                    <item.icon
                      className={classNames(
                        isActive ? 'text-indigo-400' : 'text-zinc-500 group-hover:text-zinc-300',
                        'mr-3 flex-shrink-0 h-5 w-5 transition-colors'
                      )}
                      aria-hidden="true"
                    />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
          </div>
          
          {/* User Profile Footer */}
          <div className="flex-shrink-0 flex border-t border-zinc-800 p-4 mt-auto">
            <button 
              onClick={() => {
                useAuthStore.getState().logout();
                window.location.href = '/login';
              }}
              className="flex-shrink-0 w-full group block"
            >
              <div className="flex items-center">
                <div>
                  <div className="inline-block h-9 w-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 shadow-inner flex items-center justify-center text-white font-bold text-sm">
                    {useAuthStore((state) => state.userEmail)?.charAt(0).toUpperCase() || 'U'}
                  </div>
                </div>
                <div className="ml-3 text-left max-w-[130px]">
                  <p className="text-sm font-medium text-white group-hover:text-indigo-400 transition-colors truncate">
                    Wallet User
                  </p>
                  <p className="text-xs font-medium text-zinc-500 group-hover:text-zinc-400 truncate">
                    {useAuthStore((state) => state.userEmail) || 'Unknown User'}
                  </p>
                </div>
                <LogOut className="ml-auto h-4 w-4 text-zinc-500 group-hover:text-red-400 transition-colors" />
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="md:pl-64 flex flex-col flex-1 w-full h-full">
        {/* Top Header */}
        <div className="sticky top-0 z-10 flex-shrink-0 flex h-16 bg-zinc-950/80 backdrop-blur-lg border-b border-zinc-800">
          <div className="flex-1 px-4 flex justify-between sm:px-6 lg:px-8">
            <div className="flex-1 flex items-center">
              {/* Optional Search Bar can go here */}
            </div>
            <div className="ml-4 flex items-center md:ml-6 space-x-4">
              <button
                type="button"
                className="bg-zinc-900 p-2 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-zinc-900 focus:ring-indigo-500 transition-all"
              >
                <span className="sr-only">View notifications</span>
                <Bell className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>

        {/* Dynamic Page Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
