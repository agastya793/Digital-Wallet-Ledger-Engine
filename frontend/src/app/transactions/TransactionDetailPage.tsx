import { useParams, useNavigate } from 'react-router-dom';
import { useTransactionDetail } from '../../lib/api/wallets';
import { 
  ArrowLeft, FileText, CheckCircle, Clock, XCircle, 
  ArrowRightLeft, Hash, Activity, RefreshCw 
} from 'lucide-react';

export function TransactionDetailPage() {
  const { walletId, transactionId } = useParams<{ walletId: string, transactionId: string }>();
  const navigate = useNavigate();
  
  const { data: transaction, isLoading, isError } = useTransactionDetail(walletId, transactionId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent"></div>
      </div>
    );
  }

  if (isError || !transaction) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-center text-red-400">
        <XCircle className="mx-auto mb-4 h-12 w-12 opacity-50" />
        <h3 className="mb-2 text-lg font-medium text-red-200">Transaction Not Found</h3>
        <p className="text-sm">We couldn't load this transaction or you don't have access to it.</p>
        <button
          onClick={() => navigate(`/wallet`)}
          className="mt-6 rounded-lg bg-zinc-800 px-4 py-2 text-sm font-medium hover:bg-zinc-700 transition-colors"
        >
          Return to Wallet
        </button>
      </div>
    );
  }

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'completed':
        return { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-400/10' };
      case 'pending':
      case 'processing':
        return { icon: RefreshCw, color: 'text-amber-400', bg: 'bg-amber-400/10' };
      case 'failed':
      case 'reversed':
        return { icon: XCircle, color: 'text-rose-400', bg: 'bg-rose-400/10' };
      default:
        return { icon: Clock, color: 'text-zinc-400', bg: 'bg-zinc-800' };
    }
  };

  const StatusIcon = getStatusConfig(transaction.status).icon;
  const statusColor = getStatusConfig(transaction.status).color;
  const statusBg = getStatusConfig(transaction.status).bg;

  // Calculate total absolute amount involved (assuming zero-sum, sum of debits = amount moved)
  const totalAmount = transaction.entries
    .filter(e => e.entry_type === 'debit')
    .reduce((sum, e) => sum + e.amount, 0);

  return (
    <div className="mx-auto max-w-4xl space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate(-1)}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800/50 hover:bg-zinc-800 text-zinc-400 hover:text-white transition-all"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Transaction Details</h1>
            <p className="text-sm text-zinc-400">
              {new Date(transaction.created_at).toLocaleString()}
            </p>
          </div>
        </div>
        <div className={`flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${statusColor} ${statusBg} border border-current/10`}>
          <StatusIcon className="h-4 w-4" />
          <span className="capitalize">{transaction.status}</span>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-white/5 bg-white/5 p-5 backdrop-blur-xl transition-all hover:bg-white/10">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-zinc-400">Total Value</h3>
            <Activity className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-white">
            ${(totalAmount / 100).toFixed(2)}
          </p>
        </div>
        
        <div className="rounded-2xl border border-white/5 bg-white/5 p-5 backdrop-blur-xl transition-all hover:bg-white/10">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-zinc-400">Type</h3>
            <ArrowRightLeft className="h-4 w-4 text-blue-400" />
          </div>
          <p className="mt-2 text-lg font-bold text-white capitalize">
            {transaction.transaction_type.replace('_', ' ')}
          </p>
        </div>

        <div className="col-span-2 rounded-2xl border border-white/5 bg-white/5 p-5 backdrop-blur-xl transition-all hover:bg-white/10">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-zinc-400">Context</h3>
            <FileText className="h-4 w-4 text-purple-400" />
          </div>
          <p className="mt-2 text-md font-medium text-zinc-200 line-clamp-2">
            {transaction.description || 'No description provided'}
          </p>
        </div>
      </div>

      {/* Technical Details */}
      <div className="rounded-2xl border border-white/5 bg-zinc-900/50 overflow-hidden backdrop-blur-xl">
        <div className="border-b border-white/5 bg-black/20 p-4">
          <h3 className="font-semibold text-white">Technical Metadata</h3>
        </div>
        <div className="grid gap-px bg-white/5 sm:grid-cols-2">
          <div className="bg-zinc-900/90 p-4">
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Transaction ID (Request ID)</p>
            <p className="mt-1 font-mono text-sm text-zinc-300 break-all">{transaction.id}</p>
          </div>
          <div className="bg-zinc-900/90 p-4">
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Idempotency Key (Reference)</p>
            <p className="mt-1 font-mono text-sm text-zinc-300 break-all">{transaction.reference_id || 'N/A'}</p>
          </div>
        </div>
      </div>

      {/* Ledger Entries */}
      <div className="rounded-2xl border border-white/5 bg-zinc-900/50 overflow-hidden backdrop-blur-xl">
        <div className="border-b border-white/5 bg-black/20 p-4 flex items-center gap-2">
          <Hash className="h-5 w-5 text-zinc-400" />
          <h3 className="font-semibold text-white">Double-Entry Ledger Movements</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="bg-white/[0.02] text-xs uppercase text-zinc-500">
              <tr>
                <th className="px-6 py-4 font-medium">Wallet ID (Account)</th>
                <th className="px-6 py-4 font-medium">Direction</th>
                <th className="px-6 py-4 font-medium text-right">Amount</th>
                <th className="px-6 py-4 font-medium text-right">Balance After</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {transaction.entries.map((entry) => {
                const isCredit = entry.entry_type === 'credit';
                return (
                  <tr key={entry.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-zinc-400">
                      {entry.wallet_id}
                      {entry.wallet_id === walletId && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                          My Wallet
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border
                        ${isCredit 
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                          : 'bg-rose-500/10 text-rose-400 border-rose-500/20'}`}>
                        {isCredit ? '+' : '-'} {entry.entry_type.toUpperCase()}
                      </span>
                    </td>
                    <td className={`px-6 py-4 text-right font-medium ${isCredit ? 'text-emerald-400' : 'text-rose-400'}`}>
                      ${entry.amount_display}
                    </td>
                    <td className="px-6 py-4 text-right text-zinc-400">
                      ${entry.balance_after_display}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      
    </div>
  );
}
