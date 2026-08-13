import { useState } from 'react';
import { useWallets, useDepositMutation } from '../../lib/api/wallets';
import { CreditCard, Plus, ArrowRight, ShieldCheck, CreditCard as CardIcon } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';

export function WalletPage() {
  const { data: wallets, isLoading } = useWallets();
  const primaryWallet = wallets?.[0];
  const userEmail = useAuthStore((state) => state.userEmail);
  
  const [amount, setAmount] = useState<string>('');
  const [isFlipped, setIsFlipped] = useState(false);
  
  const depositMutation = useDepositMutation(primaryWallet?.id || '');

  const handleDeposit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || isNaN(Number(amount)) || Number(amount) <= 0) return;
    
    depositMutation.mutate(Number(amount), {
      onSuccess: () => {
        setAmount('');
      }
    });
  };

  if (isLoading) {
    return <div className="text-zinc-400">Loading wallet...</div>;
  }

  if (!primaryWallet) {
    return <div className="text-zinc-400">No active wallet found.</div>;
  }

  // Generate a mock but consistent card number based on wallet ID
  const generateMockCard = (seed: string) => {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
      hash = seed.charCodeAt(i) + ((hash << 5) - hash);
    }
    const num = Math.abs(hash).toString().padStart(16, '0').slice(0, 16);
    return {
      number: `4232 ${num.slice(4, 8)} ${num.slice(8, 12)} ${num.slice(12, 16)}`,
      cvv: num.slice(0, 3),
      exp: '12/28'
    };
  };

  const cardDetails = generateMockCard(primaryWallet.id);

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Your Wallet</h1>
        <p className="text-sm text-zinc-400 mt-1">Manage your virtual card and funding sources.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Left Column: Virtual Card */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-white">Virtual Debit Card</h2>
            <button 
              onClick={() => setIsFlipped(!isFlipped)}
              className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 bg-blue-500/10 px-2 py-1 rounded border border-blue-500/20 transition-colors"
            >
              <CardIcon className="h-3 w-3" />
              Flip Card
            </button>
          </div>
          
          <div className="perspective-1000 relative w-full aspect-[1.586/1] max-w-[400px] group cursor-pointer" onClick={() => setIsFlipped(!isFlipped)}>
            <div className={`w-full h-full absolute transition-all duration-500 preserve-3d ${isFlipped ? 'rotate-y-180' : ''}`}>
              
              {/* Front of card */}
              <div className="absolute w-full h-full backface-hidden rounded-2xl p-6 flex flex-col justify-between bg-gradient-to-br from-zinc-800 to-zinc-900 border border-zinc-700/50 shadow-2xl overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full opacity-20 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]" />
                <div className="absolute -right-20 -top-20 w-40 h-40 bg-blue-500 rounded-full blur-[80px] opacity-40 mix-blend-screen" />
                <div className="absolute -left-20 -bottom-20 w-40 h-40 bg-purple-500 rounded-full blur-[80px] opacity-40 mix-blend-screen" />
                
                <div className="flex justify-between items-start relative z-10">
                  <p className="text-zinc-100 font-medium tracking-wide drop-shadow-sm truncate">{userEmail || 'User'}</p>
                  <div className="text-white/80 font-medium tracking-widest text-sm flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-blue-400" />
                    SECURE CARD
                  </div>
                  <div className="flex space-x-1">
                    <div className="w-8 h-8 rounded-full bg-red-500/80 mix-blend-screen" />
                    <div className="w-8 h-8 rounded-full bg-yellow-500/80 mix-blend-screen -ml-4" />
                  </div>
                </div>
                
                <div className="relative z-10 space-y-4">
                  <div className="text-zinc-400 text-xs tracking-widest uppercase">Available Balance</div>
                  <div className="text-4xl font-light text-white tracking-tight">{primaryWallet.balance_display}</div>
                  <div className="pt-2 flex justify-between items-end">
                    <div className="space-y-1">
                      <div className="text-zinc-500 text-[10px] tracking-widest uppercase">Card Number</div>
                      <div className="text-white tracking-widest font-mono text-sm opacity-90">•••• •••• •••• {cardDetails.number.slice(-4)}</div>
                    </div>
                    <div className="space-y-1 text-right">
                      <div className="text-zinc-500 text-[10px] tracking-widest uppercase">Valid Thru</div>
                      <div className="text-white tracking-widest font-mono text-sm opacity-90">{cardDetails.exp}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Back of card */}
              <div className="absolute w-full h-full backface-hidden rotate-y-180 rounded-2xl flex flex-col bg-gradient-to-br from-zinc-800 to-zinc-900 border border-zinc-700/50 shadow-2xl overflow-hidden">
                <div className="absolute -right-20 -top-20 w-40 h-40 bg-blue-500 rounded-full blur-[80px] opacity-20 mix-blend-screen" />
                <div className="w-full h-12 bg-black mt-6" />
                <div className="p-6 flex-1 flex flex-col justify-center">
                  <div className="flex items-center justify-end gap-2">
                    <span className="text-zinc-500 text-xs tracking-widest uppercase">CVV</span>
                    <div className="bg-white/90 text-black font-mono px-3 py-1 text-sm rounded">{cardDetails.cvv}</div>
                  </div>
                  <div className="mt-auto pt-4 text-[10px] text-zinc-500 text-center uppercase tracking-wider">
                    Authorized signature required. <br/>This card is property of {userEmail || 'User'}.
                  </div>
                </div>
              </div>

            </div>
          </div>
          
          <div className="bg-zinc-800/30 border border-zinc-700/50 rounded-xl p-4 flex justify-between items-center">
            <div>
              <div className="text-sm font-medium text-white">Card Status</div>
              <div className="text-xs text-emerald-400 flex items-center gap-1 mt-1">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Active & Ready
              </div>
            </div>
            <button className="text-sm text-zinc-400 hover:text-white transition-colors border border-zinc-700 hover:border-zinc-500 rounded-md px-3 py-1.5">
              Freeze Card
            </button>
          </div>
        </div>

        {/* Right Column: Funding */}
        <div className="space-y-6">
          <h2 className="text-lg font-medium text-white">Funding Sources</h2>
          
          <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-6">
            <h3 className="text-sm font-medium text-white flex items-center gap-2 mb-4">
              <Plus className="h-4 w-4 text-emerald-400" />
              Top Up Balance
            </h3>
            
            <form onSubmit={handleDeposit} className="space-y-4">
              <div>
                <label className="block text-xs text-zinc-400 mb-1.5 uppercase tracking-wider">Amount ({primaryWallet.currency})</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-zinc-500 sm:text-sm">$</span>
                  </div>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="block w-full pl-7 pr-12 bg-zinc-900 border border-zinc-700 rounded-lg text-white focus:ring-blue-500 focus:border-blue-500 sm:text-sm py-2.5 transition-colors"
                    placeholder="0.00"
                  />
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                    <span className="text-zinc-500 sm:text-sm">{primaryWallet.currency}</span>
                  </div>
                </div>
              </div>
              
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={depositMutation.isPending || !amount}
                  className="w-full flex items-center justify-center gap-2 bg-white hover:bg-zinc-200 text-black px-4 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {depositMutation.isPending ? 'Processing...' : 'Simulate Bank Transfer'}
                  {!depositMutation.isPending && <ArrowRight className="h-4 w-4" />}
                </button>
              </div>
              
              {depositMutation.isSuccess && (
                <div className="text-xs text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 p-2.5 rounded-md mt-4 text-center">
                  Successfully deposited funds into your wallet!
                </div>
              )}
            </form>
          </div>
          
          <div className="bg-zinc-800/30 border border-zinc-700/50 rounded-xl p-5">
            <h3 className="text-sm font-medium text-zinc-300 mb-3">Linked Accounts</h3>
            <div className="flex items-center justify-between p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
                  <CreditCard className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-medium text-white">Chase Bank</div>
                  <div className="text-xs text-zinc-500">Checking •••• 9928</div>
                </div>
              </div>
              <div className="text-xs bg-zinc-800 text-zinc-400 px-2 py-1 rounded">Default</div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}
