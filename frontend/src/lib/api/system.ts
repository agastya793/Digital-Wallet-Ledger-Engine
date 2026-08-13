import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface ReconciliationJob {
  id: string;
  status: 'running' | 'completed' | 'failed';
  total_wallets_checked: number;
  discrepancies_found: number;
  started_at: string;
  completed_at: string | null;
}

export interface ReconciliationDiscrepancy {
  id: string;
  job_id: string;
  wallet_id: string;
  expected_balance: number;
  actual_balance: number;
  difference: number;
  resolved: boolean;
  created_at: string;
}

export function useReconciliationJobs() {
  return useQuery({
    queryKey: ['reconciliation-jobs'],
    queryFn: async () => {
      const response = await apiClient.get<ReconciliationJob[]>('/reconciliation/jobs');
      return response.data;
    },
  });
}

export function useReconciliationDiscrepancies(jobId: string) {
  return useQuery({
    queryKey: ['reconciliation-discrepancies', jobId],
    queryFn: async () => {
      const response = await apiClient.get<ReconciliationDiscrepancy[]>(`/reconciliation/jobs/${jobId}/discrepancies`);
      return response.data;
    },
    enabled: !!jobId,
  });
}

export function useRunReconciliation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<ReconciliationJob>('/reconciliation/run');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reconciliation-jobs'] });
    },
  });
}
