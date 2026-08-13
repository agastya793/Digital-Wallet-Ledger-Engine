import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface Wallet {
  id: string;
  user_id: string;
  currency: string;
  balance: number;
  balance_display: string;
  status: 'active' | 'frozen' | 'closed';
  created_at: string;
  updated_at: string;
}

// Fetch all wallets for the current user
export function useWallets() {
  return useQuery({
    queryKey: ['wallets'],
    queryFn: async () => {
      const response = await apiClient.get<Wallet[]>('/wallets/');
      return response.data;
    },
  });
}

// Create a new wallet in a specific currency
export function useCreateWallet() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (currency: string) => {
      const response = await apiClient.post<Wallet>('/wallets/', { currency });
      return response.data;
    },
    onSuccess: () => {
      // Invalidate the cache to trigger a refetch
      queryClient.invalidateQueries({ queryKey: ['wallets'] });
    },
  });
}

// Deposit money into a wallet
export function useDepositMutation(walletId: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (amount: number) => {
      const response = await apiClient.post<Wallet>(`/wallets/${walletId}/deposit`, { amount });
      return response.data;
    },
    onSuccess: () => {
      // Invalidate the caches to trigger a refetch of balances and history
      queryClient.invalidateQueries({ queryKey: ['wallets'] });
      queryClient.invalidateQueries({ queryKey: ['wallet-history', walletId] });
    },
  });
}

export interface LedgerEntry {
  id: string;
  transaction_id: string;
  wallet_id: string;
  entry_type: 'debit' | 'credit';
  amount: number;
  amount_display: string;
  balance_after: number;
  balance_after_display: string;
  created_at: string;
}

// Fetch transaction history for a specific wallet
export function useWalletHistory(walletId: string | undefined) {
  return useQuery({
    queryKey: ['wallet-history', walletId],
    queryFn: async () => {
      const response = await apiClient.get<LedgerEntry[]>(`/wallets/${walletId}/history`);
      return response.data;
    },
    enabled: !!walletId, // Only run the query if we have a wallet ID
  });
}

export interface TransactionRead {
  id: string;
  transaction_type: string;
  description: string | null;
  reference_id: string | null;
  status: string;
  entries: LedgerEntry[];
  created_at: string;
}

// Fetch transaction detail for a specific wallet
export function useTransactionDetail(walletId: string | undefined, transactionId: string | undefined) {
  return useQuery({
    queryKey: ['transaction-detail', walletId, transactionId],
    queryFn: async () => {
      const response = await apiClient.get<TransactionRead>(`/wallets/${walletId}/transactions/${transactionId}`);
      return response.data;
    },
    enabled: !!walletId && !!transactionId,
  });
}
