import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { Wallet, Loader2, ArrowRight } from 'lucide-react';
import { useLoginMutation, useRegisterMutation } from '../../lib/api/auth';
import { useCreateWallet } from '../../lib/api/wallets';
import { useAuthStore } from '../../stores/authStore';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const { mutate: login, isPending: isLoggingIn } = useLoginMutation();
  const { mutate: registerUser, isPending: isRegistering } = useRegisterMutation();
  const { mutate: createWallet, isPending: isCreatingWallet } = useCreateWallet();

  const isPending = isLoggingIn || isRegistering || isCreatingWallet;

  const onSubmit = (data: LoginFormValues) => {
    setError(null);
    login(
      { email: data.email, password_hash: data.password },
      {
        onSuccess: (response) => {
          setAuth(response.access_token, data.email);
          navigate('/dashboard');
        },
        onError: (err: any) => {
          // If login fails, attempt to register automatically
          registerUser(
            { email: data.email, password_hash: data.password, currency: 'USD' },
            {
              onSuccess: () => {
                // If registration succeeds, login and create initial wallet
                login(
                  { email: data.email, password_hash: data.password },
                  {
                    onSuccess: (response) => {
                      setAuth(response.access_token, data.email);
                      createWallet('USD', {
                        onSuccess: () => navigate('/dashboard'),
                        onError: () => navigate('/dashboard'),
                      });
                    },
                    onError: () => setError('Registration succeeded but login failed.'),
                  }
                );
              },
              onError: (regErr: any) => {
                if (regErr.response?.status === 409) {
                  // If 409 Conflict, the email already exists, which means they just typed the wrong password.
                  setError('Invalid email or password.');
                } else {
                  setError('Failed to authenticate. ' + (err.response?.data?.detail || ''));
                }
              }
            }
          );
        },
      }
    );
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 selection:bg-indigo-500/30">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="h-12 w-12 rounded-xl bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Wallet className="h-7 w-7 text-white" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-white">
          Sign in to your wallet
        </h2>
        <p className="mt-2 text-center text-sm text-zinc-400">
          Or{' '}
          <Link to="/register" className="font-medium text-indigo-400 hover:text-indigo-300 transition-colors">
            create a new wallet account
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-zinc-900/50 py-8 px-4 shadow-2xl shadow-black/50 sm:rounded-2xl sm:px-10 border border-zinc-800 backdrop-blur-xl">
          <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3">
                <p className="text-sm text-red-400 text-center">{error}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-zinc-300">Email address</label>
              <div className="mt-2">
                <input
                  {...register('email')}
                  type="email"
                  className="block w-full rounded-lg border-0 bg-zinc-950 py-2.5 px-3 text-white shadow-sm ring-1 ring-inset ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6 transition-all"
                />
                {errors.email && <p className="mt-2 text-sm text-red-400">{errors.email.message}</p>}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300">Password</label>
              <div className="mt-2">
                <input
                  {...register('password')}
                  type="password"
                  className="block w-full rounded-lg border-0 bg-zinc-950 py-2.5 px-3 text-white shadow-sm ring-1 ring-inset ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6 transition-all"
                />
                {errors.password && <p className="mt-2 text-sm text-red-400">{errors.password.message}</p>}
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isPending}
                className="flex w-full justify-center items-center rounded-lg bg-indigo-600 px-3 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isPending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
