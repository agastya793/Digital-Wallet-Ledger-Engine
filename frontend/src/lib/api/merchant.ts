import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface MerchantProfile {
  id: string;
  business_name: string;
  webhook_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CheckoutSession {
  id: string;
  merchant_id: string;
  amount: number;
  amount_display: string;
  currency: string;
  description: string | null;
  status: 'pending' | 'paid' | 'expired';
  paid_by_user_id: string | null;
  paid_at: string | null;
  transaction_id: string | null;
  created_at: string;
}

export function useMerchantProfile() {
  return useQuery({
    queryKey: ['merchant-profile'],
    queryFn: async () => {
      const response = await apiClient.get<MerchantProfile>('/merchant/me');
      return response.data;
    },
    retry: false, // Don't retry if it fails (e.g. 404 because they aren't a merchant)
  });
}

export function useRegisterMerchant() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: { business_name: string; webhook_url?: string }) => {
      const response = await apiClient.post<{ merchant_id: string; business_name: string; api_key: string }>('/merchant/register', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['merchant-profile'] });
    },
  });
}

// NOTE: Creating a checkout session usually requires API key authentication from a backend.
// This is for demonstration purposes in our sandbox.
export function useCreateCheckout() {
  return useMutation({
    mutationFn: async (data: { amount: number; currency: string; description: string; apiKey: string }) => {
      const response = await apiClient.post<CheckoutSession>(
        '/merchant/checkout', 
        { amount: data.amount, currency: data.currency, description: data.description },
        {
          headers: {
            'X-API-Key': data.apiKey,
          }
        }
      );
      return response.data;
    }
  });
}

export function usePayCheckout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sessionId: string) => {
      const response = await apiClient.post<CheckoutSession>(`/merchant/checkout/${sessionId}/pay`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallets'] });
      queryClient.invalidateQueries({ queryKey: ['wallet-history'] });
    },
  });
}
