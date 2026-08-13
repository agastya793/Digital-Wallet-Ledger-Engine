import { useState } from 'react';
import { useReconciliationJobs, useRunReconciliation, useReconciliationDiscrepancies } from '../../lib/api/system';
import type { ReconciliationJob } from '../../lib/api/system';
import { Activity, Play, AlertTriangle, CheckCircle, Search, ChevronRight, XCircle } from 'lucide-react';

export function SystemOpsPage() {
  const { data: jobs, isLoading: isLoadingJobs } = useReconciliationJobs();
  const { mutate: runJob, isPending: isRunning } = useRunReconciliation();
  
  const [selectedJob, setSelectedJob] = useState<ReconciliationJob | null>(null);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-indigo-400" />
            System Operations
          </h1>
          <p className="text-sm text-zinc-400 mt-1">Monitor ledger integrity and run administrative tasks.</p>
        </div>
        <button
          onClick={() => runJob()}
          disabled={isRunning}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition-colors disabled:opacity-50"
        >
          {isRunning ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          Run Reconciliation
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Jobs List */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-medium text-white flex items-center gap-2">
            Reconciliation History
          </h2>
          
          <div className="rounded-xl border border-white/5 bg-zinc-900/50 backdrop-blur-xl overflow-hidden">
            {isLoadingJobs ? (
              <div className="p-8 flex justify-center">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
              </div>
            ) : jobs && jobs.length > 0 ? (
              <table className="w-full text-left text-sm text-zinc-400">
                <thead className="border-b border-white/5 bg-white/5 text-xs uppercase text-zinc-300">
                  <tr>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium">Started At</th>
                    <th className="px-6 py-4 font-medium">Wallets Checked</th>
                    <th className="px-6 py-4 font-medium">Discrepancies</th>
                    <th className="px-6 py-4 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {jobs.map((job) => (
                    <tr 
                      key={job.id} 
                      className={`hover:bg-white/5 transition-colors cursor-pointer ${selectedJob?.id === job.id ? 'bg-white/5' : ''}`}
                      onClick={() => setSelectedJob(job)}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          {job.status === 'completed' && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                          {job.status === 'running' && <div className="w-4 h-4 animate-spin rounded-full border-2 border-amber-400 border-t-transparent" />}
                          {job.status === 'failed' && <XCircle className="w-4 h-4 text-rose-400" />}
                          <span className="capitalize">{job.status}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs">
                        {new Date(job.started_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4">{job.total_wallets_checked}</td>
                      <td className="px-6 py-4">
                        {job.discrepancies_found > 0 ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-rose-400/10 px-2 py-1 text-xs font-medium text-rose-400">
                            <AlertTriangle className="w-3 h-3" />
                            {job.discrepancies_found}
                          </span>
                        ) : (
                          <span className="text-zinc-500">0</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <ChevronRight className="w-4 h-4 inline-block text-zinc-600" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-zinc-500">
                No reconciliation jobs have been run yet.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Job Details */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-white flex items-center gap-2">
            Discrepancies
          </h2>
          
          <div className="rounded-xl border border-white/5 bg-zinc-900/50 backdrop-blur-xl p-6">
            {selectedJob ? (
              <DiscrepancyViewer jobId={selectedJob.id} />
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center text-zinc-500">
                <Search className="w-8 h-8 mb-3 opacity-20" />
                <p className="text-sm">Select a job from the history<br/>to view details.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DiscrepancyViewer({ jobId }: { jobId: string }) {
  const { data: discrepancies, isLoading } = useReconciliationDiscrepancies(jobId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  if (!discrepancies || discrepancies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <CheckCircle className="w-10 h-10 text-emerald-500/20 mb-3" />
        <p className="text-sm text-emerald-400/80 font-medium">Ledger is perfectly balanced</p>
        <p className="text-xs text-zinc-500 mt-1">No discrepancies found in this run.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-rose-400 bg-rose-400/10 p-3 rounded-lg border border-rose-400/20">
        <AlertTriangle className="w-5 h-5 shrink-0" />
        <p className="text-sm font-medium">Found {discrepancies.length} discrepancy(s)</p>
      </div>
      
      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
        {discrepancies.map(d => (
          <div key={d.id} className="p-4 rounded-lg bg-black/40 border border-white/5">
            <div className="text-xs text-zinc-500 mb-2 font-mono">Wallet ID: {d.wallet_id.substring(0,8)}...</div>
            
            <div className="grid grid-cols-2 gap-4 mb-3">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Expected (Ledger)</div>
                <div className="text-sm text-white font-mono">{d.expected_balance}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Actual (Cached)</div>
                <div className="text-sm text-rose-400 font-mono">{d.actual_balance}</div>
              </div>
            </div>
            
            <div className="pt-3 border-t border-white/5 flex justify-between items-center">
              <span className="text-xs text-zinc-500">Difference</span>
              <span className="text-sm font-mono text-amber-400">{d.difference > 0 ? '+' : ''}{d.difference}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
