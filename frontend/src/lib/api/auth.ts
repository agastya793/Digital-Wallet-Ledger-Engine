import { useMutation } from '@tanstack/react-query';
import { apiClient } from './client';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function useLoginMutation() {
  return useMutation({
    mutationFn: async (data: { email: string; password_hash: string }) => {
      // The backend uses OAuth2PasswordRequestForm which expects x-www-form-urlencoded
      const formData = new URLSearchParams();
      formData.append('username', data.email);
      formData.append('password', data.password_hash);

      const response = await apiClient.post<TokenResponse>(
        '/auth/login',
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );
      return response.data;
    },
  });
}

export function useRegisterMutation() {
  return useMutation({
    mutationFn: async (data: { email: string; password_hash: string; currency: string }) => {
      const response = await apiClient.post<{ id: string; email: string }>(
        '/auth/register',
        { email: data.email, password: data.password_hash }
      );
      return response.data;
    },
  });
}

export function useLogoutMutation() {
  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/auth/logout');
    },
  });
}
