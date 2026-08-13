import { ArrowDown, CheckCircle2 } from 'lucide-react';
import type { TransferResponse } from '../../lib/api/transfers';

interface Props {
  transfer: TransferResponse;
}

export function LedgerLegVisualizer({ transfer }: Props) {
  // Format amount to standard currency string
  const formatAmount = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(amount / 100);
  };

  const debit = transfer.ledger_entries?.find(e => e.direction === 'debit');
  const credit = transfer.ledger_entries?.find(e => e.direction === 'credit');

  return (
    <div className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-6 shadow-xl backdrop-blur-md animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 mr-2" />
            Transfer Successful
          </h3>
          <p className="text-xs text-zinc-500 mt-1 font-mono">
            TXN: {transfer.id.split('-')[0]}
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-emerald-400">
            {formatAmount(transfer.amount, transfer.currency)}
          </p>
        </div>
      </div>

      <div className="relative">
        {/* Connection Line */}
        <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-zinc-800/50" />

        {/* Debit Leg */}
        <div className="relative flex items-start mb-12">
          <div className="absolute -left-[5px] top-4 w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
          <div className="ml-12 w-full">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-zinc-300">Sender Wallet</span>
              <span className="text-sm font-bold text-red-400">
                - {formatAmount(transfer.amount, transfer.currency)}
              </span>
            </div>
            <div className="bg-zinc-950/50 border border-zinc-800/50 rounded-lg p-3 font-mono text-xs text-zinc-500">
              <div className="flex justify-between">
                <span>Entry: {debit?.id.split('-')[0] || '...'}</span>
                <span className="text-red-500/70">DEBIT</span>
              </div>
              <div className="mt-1">Wallet ID: {transfer.sender_wallet_id.split('-')[0]}</div>
            </div>
          </div>
        </div>

        {/* Middle Node */}
        <div className="absolute left-[18px] top-1/2 -translate-y-1/2 flex items-center bg-zinc-900 px-2">
          <ArrowDown className="w-4 h-4 text-zinc-600" />
        </div>

        {/* Credit Leg */}
        <div className="relative flex items-start">
          <div className="absolute -left-[5px] top-4 w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500/50" />
          <div className="ml-12 w-full">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-zinc-300">Recipient Wallet</span>
              <span className="text-sm font-bold text-emerald-400">
                + {formatAmount(transfer.amount, transfer.currency)}
              </span>
            </div>
            <div className="bg-zinc-950/50 border border-zinc-800/50 rounded-lg p-3 font-mono text-xs text-zinc-500">
              <div className="flex justify-between">
                <span>Entry: {credit?.id.split('-')[0] || '...'}</span>
                <span className="text-emerald-500/70">CREDIT</span>
              </div>
              <div className="mt-1">Wallet ID: {transfer.recipient_wallet_id.split('-')[0]}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
