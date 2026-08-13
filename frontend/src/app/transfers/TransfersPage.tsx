import { useState } from 'react';
import { TransferForm } from '../../components/transfers/TransferForm';
import { LedgerLegVisualizer } from '../../components/transactions/LedgerLegVisualizer';
import type { TransferResponse } from '../../lib/api/transfers';

export function TransfersPage() {
  const [lastTransfer, setLastTransfer] = useState<TransferResponse | null>(null);

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Transfers</h1>
        <p className="text-zinc-400 mt-2">
          Send money instantly using our Double-Entry Ledger Engine.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Form */}
        <div>
          <TransferForm onSuccess={(data) => setLastTransfer(data)} />
        </div>

        {/* Right Column: Visualization */}
        <div>
          {lastTransfer ? (
            <div className="space-y-4">
              <h2 className="text-lg font-medium text-white mb-4">Ledger Execution</h2>
              <LedgerLegVisualizer transfer={lastTransfer} />
            </div>
          ) : (
            <div className="h-full min-h-[400px] border border-dashed border-zinc-800 rounded-2xl flex flex-col items-center justify-center text-zinc-500 bg-zinc-950/50">
              <p>Waiting for transaction...</p>
              <p className="text-xs mt-2 text-zinc-600 text-center px-8">
                When you send a transfer, the atomic debit and credit legs will be visualized here.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
