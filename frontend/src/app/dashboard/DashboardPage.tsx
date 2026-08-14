import { useState, useEffect } from 'react';
import { Wallet, Loader2, ArrowUpRight, ArrowDownLeft, Plus, RefreshCw, Activity, ArrowDownToLine } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWallets, useWalletHistory, useCreateWallet, useDepositMutation } from '../../lib/api/wallets';
import { useAuthStore } from '../../stores/authStore';
import { toast } from 'sonner';

export function DashboardPage() {
  const navigate = useNavigate();
  const userEmail = useAuthStore((state) => state.userEmail);
  const { data: wallets, isLoading: isLoadingWallets, refetch: refetchWallets, isRefetching } = useWallets();
  const { mutate: createWallet, isPending: isCreatingWallet } = useCreateWallet();
  
  const [isCreateWalletOpen, setIsCreateWalletOpen] = useState(false);
  const [currencyInput, setCurrencyInput] = useState('');

  const closeCreateWalletDialog = () => {
    setIsCreateWalletOpen(false);
    setCurrencyInput('');
  };

  const handleCreateWallet = () => {
    const currency = currencyInput.trim().toUpperCase();
    if (!currency) {
      toast.error('Please enter a currency code.');
      return;
    }
    if (currency.length !== 3) {
      toast.error('Currency must be exactly 3 letters.');
      return;
    }
    if (!/^[A-Z]+$/.test(currency)) {
      toast.error('Currency must contain only letters.');
      return;
    }
    createWallet(currency, {
      onSuccess: () => {
        closeCreateWalletDialog();
      },
      onError: (err: any) => {
        toast.error(err.response?.data?.detail || 'Failed to create wallet.');
      },
    });
  };

  useEffect(() => {
    if (!isCreateWalletOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isCreatingWallet) {
        closeCreateWalletDialog();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isCreateWalletOpen, isCreatingWallet]);
  
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
            onClick={() => setIsCreateWalletOpen(true)}
            className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20 p-6 hover:bg-zinc-900/50 hover:border-zinc-700 transition-all group"
          >
            <div className="p-3 rounded-full bg-zinc-800 group-hover:bg-indigo-500/20 group-hover:text-indigo-400 text-zinc-400 transition-colors mb-3">
              <Plus className="h-6 w-6" />
            </div>
            <p className="text-sm font-medium text-zinc-300 group-hover:text-white transition-colors">
              Open New Wallet
            </p>
          </button>
        </div>
      </div>

      {isCreateWalletOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => !isCreatingWallet && closeCreateWalletDialog()}
          />
          <div className="relative w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-2xl">
            <h2 className="text-lg font-semibold text-white">Create New Wallet</h2>
            <p className="mt-2 text-sm text-zinc-400">
              Enter a 3-letter ISO currency code to open a new wallet (e.g. EUR, GBP).
            </p>
            <div className="mt-6">
              <label htmlFor="currency-code" className="block text-sm font-medium text-zinc-300">
                Currency code
              </label>
              <input
                id="currency-code"
                type="text"
                value={currencyInput}
                onChange={(e) => setCurrencyInput(e.target.value.toUpperCase())}
                placeholder="EUR"
                maxLength={3}
                autoFocus
                className="mt-2 block w-full rounded-lg border-0 bg-zinc-950 py-2.5 px-3 text-white shadow-sm ring-1 ring-inset ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm uppercase"
              />
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={closeCreateWalletDialog}
                disabled={isCreatingWallet}
                className="px-4 py-2 text-sm font-medium text-zinc-300 hover:text-white border border-zinc-700 rounded-lg hover:border-zinc-500 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateWallet}
                disabled={isCreatingWallet}
                className="flex items-center px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors disabled:opacity-50"
              >
                {isCreatingWallet ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Creating...
                  </>
                ) : (
                  'Create Wallet'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

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
                <li 
                  key={entry.id} 
                  onClick={() => navigate(`/wallets/${activeWallet?.id}/transactions/${entry.transaction_id}`)}
                  className="py-4 flex items-center justify-between group cursor-pointer hover:bg-zinc-800/30 px-4 sm:px-6 transition-all"
                >
                  <div className="flex items-center space-x-4">
                    <div className={`p-2 rounded-full ${
                      entry.entry_type === 'credit' 
                        ? 'bg-emerald-500/10 text-emerald-400' 
                        : 'bg-red-500/10 text-red-400'
                    }`}>
                      {entry.entry_type === 'credit' ? <ArrowDownLeft className="h-5 w-5" /> : <ArrowUpRight className="h-5 w-5" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white group-hover:text-indigo-400 transition-colors">
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
