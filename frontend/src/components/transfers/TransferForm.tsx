import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowRight, Loader2 } from 'lucide-react';
import { useCreateTransfer, type TransferResponse } from '../../lib/api/transfers';

const transferSchema = z.object({
  recipient_email: z.string().email('Please enter a valid email address'),
  amount: z.number().min(0.01, 'Amount must be at least $0.01'),
  currency: z.string().min(3).max(3),
});

type TransferFormValues = z.infer<typeof transferSchema>;

interface Props {
  onSuccess: (data: TransferResponse) => void;
}

export function TransferForm({ onSuccess }: Props) {
  const [error, setError] = useState<string | null>(null);
  
  const { register, handleSubmit, formState: { errors } } = useForm<TransferFormValues>({
    resolver: zodResolver(transferSchema),
    defaultValues: {
      currency: 'USD',
      amount: 50.00,
    }
  });

  const { mutate: createTransfer, isPending } = useCreateTransfer();

  const onSubmit = (data: TransferFormValues) => {
    setError(null);
    
    // Convert to minor units (cents) for the backend
    const amountInCents = Math.round(data.amount * 100);
    
    // Generate a fresh idempotency key for this attempt
    const idempotencyKey = crypto.randomUUID();

    createTransfer(
      {
        recipient_email: data.recipient_email,
        amount: amountInCents,
        currency: data.currency,
        idempotencyKey,
      },
      {
        onSuccess: (response) => {
          onSuccess(response);
        },
        onError: (err: any) => {
          setError(err.response?.data?.detail || 'An unexpected error occurred while transferring funds.');
        }
      }
    );
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl shadow-xl overflow-hidden">
      <div className="p-6 border-b border-zinc-800">
        <h2 className="text-xl font-bold text-white">Send Money</h2>
        <p className="text-sm text-zinc-400 mt-1">Transfer funds instantly to any email address.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-zinc-300 mb-2">Recipient Email</label>
          <input
            {...register('recipient_email')}
            type="email"
            placeholder="friend@example.com"
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
          />
          {errors.recipient_email && (
            <p className="text-xs text-red-400 mt-2">{errors.recipient_email.message}</p>
          )}
        </div>

        <div className="flex space-x-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-zinc-300 mb-2">Amount</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500">$</span>
              <input
                {...register('amount', { valueAsNumber: true })}
                type="number"
                step="0.01"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-8 pr-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
              />
            </div>
            {errors.amount && (
              <p className="text-xs text-red-400 mt-2">{errors.amount.message}</p>
            )}
          </div>

          <div className="w-1/3">
            <label className="block text-sm font-medium text-zinc-300 mb-2">Currency</label>
            <input
              {...register('currency')}
              type="text"
              readOnly
              className="w-full bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 py-3 text-zinc-500 cursor-not-allowed"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isPending}
          className="w-full flex items-center justify-center bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              Send Payment
              <ArrowRight className="w-5 h-5 ml-2" />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
