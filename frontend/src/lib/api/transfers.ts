import { useMutation } from '@tanstack/react-query';
import { apiClient } from './client';

export interface TransferRequest {
  recipient_email: string;
  amount: number;
  currency: string;
}

export interface LedgerEntry {
  id: string;
  transaction_id: string;
  wallet_id: string;
  amount: number;
  direction: 'debit' | 'credit';
  created_at: string;
}

export interface TransferResponse {
  id: string;
  status: string;
  amount: number;
  currency: string;
  sender_wallet_id: string;
  recipient_wallet_id: string;
  ledger_entries: LedgerEntry[];
  created_at: string;
}

export function useCreateTransfer() {
  return useMutation({
    mutationFn: async (data: TransferRequest & { idempotencyKey: string }) => {
      const response = await apiClient.post<TransferResponse>(
        '/transfers/p2p',
        {
          recipient_email: data.recipient_email,
          amount: data.amount,
          currency: data.currency,
        },
        {
          headers: {
            'Idempotency-Key': data.idempotencyKey,
          },
        }
      );
      return response.data;
    },
  });
}
