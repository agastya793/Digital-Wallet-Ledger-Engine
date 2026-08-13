import { useState } from 'react';
import { Wallet, Loader2, ArrowUpRight, ArrowDownLeft, Plus, RefreshCw, Activity, ArrowDownToLine } from 'lucide-react';
import { useWallets, useWalletHistory, useCreateWallet, useDepositMutation } from '../../lib/api/wallets';
import { useAuthStore } from '../../stores/authStore';

export function DashboardPage() {
  const userEmail = useAuthStore((state) => state.userEmail);
  const { data: wallets, isLoading: isLoadingWallets, refetch: refetchWallets, isRefetching } = useWallets();
  const { mutate: createWallet, isPending: isCreatingWallet } = useCreateWallet();
  
  // Default to the first wallet (usually USD) if available
  const [selectedWalletId, setSelectedWalletId] = useState<string | null>(null);
  const activeWallet = wallets?.find(w => w.id === (selectedWalletId || wallets?.[0]?.id));

  const { data: history, isLoading: isLoadingHistory } = useWalletHistory(activeWallet?.id);
  const { mutate: deposit, isPending: isDepositing } = useDepositMutation(activeWallet?.id || '');

  if (isLoadingWallets) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Welcome back, {userEmail?.split('@')[0]}
          </h1>
          <p className="text-sm text-zinc-400 mt-1">Here is your financial overview.</p>
        </div>
        <button 
          onClick={() => refetchWallets()}
          className="flex items-center text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isRefetching ? 'animate-spin text-indigo-400' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Wallets Grid */}
      <div>
        <h2 className="text-lg font-medium text-white mb-4">Your Wallets</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {wallets?.map((wallet) => (
            <div 
              key={wallet.id}
              onClick={() => setSelectedWalletId(wallet.id)}
              className={`relative overflow-hidden rounded-2xl p-6 transition-all cursor-pointer border ${
                activeWallet?.id === wallet.id 
                  ? 'bg-indigo-600/10 border-indigo-500/50 shadow-[0_0_30px_-5px_rgba(99,102,241,0.3)]' 
                  : 'bg-zinc-900/50 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${activeWallet?.id === wallet.id ? 'bg-indigo-500/20 text-indigo-400' : 'bg-zinc-800 text-zinc-400'}`}>
                    <Wallet className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-zinc-300">{wallet.currency} Wallet</p>
                    <p className="text-xs text-zinc-500">{wallet.status}</p>
                  </div>
                </div>
              </div>
              <div className="mt-4 flex items-end justify-between">
                <p className={`text-3xl font-bold tracking-tight ${activeWallet?.id === wallet.id ? 'text-indigo-400' : 'text-white'}`}>
                  ${wallet.balance_display}
                </p>
                {activeWallet?.id === wallet.id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      const amount = window.prompt('Sandbox: Enter amount to deposit (e.g. 1000):', '1000');
                      if (amount && !isNaN(Number(amount)) && Number(amount) > 0) {
                        deposit(Number(amount));
                      }
                    }}
                    disabled={isDepositing}
                    className="flex items-center text-xs bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 px-3 py-1.5 rounded-lg transition-colors z-10 relative"
                  >
                    {isDepositing ? <Loader2 className="w-3 h-3 animate-spin mr-1.5" /> : <ArrowDownToLine className="w-3 h-3 mr-1.5" />}
                    Add Funds
                  </button>
                )}
              </div>
              
              {/* Decorative background glow for active wallet */}
              {activeWallet?.id === wallet.id && (
                <div className="absolute -bottom-4 -right-4 w-24 h-24 bg-indigo-500/20 blur-2xl rounded-full" />
              )}
            </div>
          ))}

          {/* New Wallet Button placeholder */}
          <button 
            onClick={() => {
              const currency = window.prompt('Enter 3-letter currency code (e.g. USD, EUR, GBP):', 'USD');
              if (currency && currency.length === 3) {
                createWallet(currency.toUpperCase());
              } else if (currency) {
                alert('Currency must be exactly 3 letters.');
              }
            }}
            disabled={isCreatingWallet}
            className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20 p-6 hover:bg-zinc-900/50 hover:border-zinc-700 transition-all group disabled:opacity-50"
          >
            <div className="p-3 rounded-full bg-zinc-800 group-hover:bg-indigo-500/20 group-hover:text-indigo-400 text-zinc-400 transition-colors mb-3">
              {isCreatingWallet ? <Loader2 className="h-6 w-6 animate-spin" /> : <Plus className="h-6 w-6" />}
            </div>
            <p className="text-sm font-medium text-zinc-300 group-hover:text-white transition-colors">
              {isCreatingWallet ? 'Creating...' : 'Open New Wallet'}
            </p>
          </button>
        </div>
      </div>

      {/* Transaction History Section */}
      <div className="mt-8">
        <div className="flex items-center space-x-2 mb-6">
          <Activity className="w-5 h-5 text-indigo-400" />
          <h2 className="text-lg font-medium text-white">Recent Activity ({activeWallet?.currency})</h2>
        </div>

        <div className="bg-zinc-900/50 rounded-2xl border border-zinc-800 overflow-hidden backdrop-blur-sm">
          {isLoadingHistory ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-zinc-500" />
            </div>
          ) : history && history.length > 0 ? (
            <ul className="divide-y divide-zinc-800">
              {history.map((entry) => (
                <li key={entry.id} className="p-4 sm:px-6 hover:bg-zinc-800/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className={`p-2 rounded-full ${
                        entry.entry_type === 'credit' 
                          ? 'bg-emerald-500/10 text-emerald-400' 
                          : 'bg-red-500/10 text-red-400'
                      }`}>
                        {entry.entry_type === 'credit' ? <ArrowDownLeft className="h-5 w-5" /> : <ArrowUpRight className="h-5 w-5" />}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">
                          {entry.entry_type === 'credit' ? 'Money Received' : 'Money Sent'}
                        </p>
                        <p className="text-xs text-zinc-500 mt-0.5">
                          {new Date(entry.created_at).toLocaleDateString('en-US', { 
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
                          })}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-bold ${
                        entry.entry_type === 'credit' ? 'text-emerald-400' : 'text-white'
                      }`}>
                        {entry.entry_type === 'credit' ? '+' : '-'}${entry.amount_display}
                      </p>
                      <p className="text-xs text-zinc-500 mt-0.5">
                        Balance: ${entry.balance_after_display}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-center py-12">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-zinc-800/50 mb-4">
                <Wallet className="h-6 w-6 text-zinc-500" />
              </div>
              <h3 className="text-sm font-medium text-white">No transactions yet</h3>
              <p className="text-xs text-zinc-500 mt-1">This wallet hasn't sent or received any money.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
