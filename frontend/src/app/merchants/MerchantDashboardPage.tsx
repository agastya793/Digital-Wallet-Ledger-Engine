import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Store, Key, Loader2, Link2, CheckCircle2, Copy, Zap, ArrowRight } from 'lucide-react';
import { 
  useMerchantProfile, 
  useRegisterMerchant, 
  useCreateCheckout, 
  usePayCheckout,
  type CheckoutSession 
} from '../../lib/api/merchant';

const registerSchema = z.object({
  business_name: z.string().min(2, 'Business name is required'),
  webhook_url: z.string().url('Must be a valid URL').or(z.literal('')),
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export function MerchantDashboardPage() {
  const { data: profile, isLoading: isLoadingProfile, error: profileError } = useMerchantProfile();
  const [generatedApiKey, setGeneratedApiKey] = useState<string | null>(null);

  const isRegistered = !!profile;
  const showRegistrationForm = !isRegistered && profileError?.message?.includes('404');

  if (isLoadingProfile) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Merchant Gateway</h1>
        <p className="text-sm text-zinc-400 mt-1">Accept payments directly into your digital wallet.</p>
      </div>

      {showRegistrationForm && (
        <RegistrationForm onRegisterSuccess={setGeneratedApiKey} />
      )}

      {generatedApiKey && (
        <ApiKeyReveal apiKey={generatedApiKey} onAcknowledge={() => setGeneratedApiKey(null)} />
      )}

      {isRegistered && !generatedApiKey && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <MerchantProfileCard profile={profile} />
          <TestSandbox />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Registration Form
// ============================================================================
function RegistrationForm({ onRegisterSuccess }: { onRegisterSuccess: (key: string) => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });
  
  const { mutate: registerMerchant, isPending, error } = useRegisterMerchant();

  const onSubmit = (data: RegisterFormValues) => {
    registerMerchant(
      { business_name: data.business_name, webhook_url: data.webhook_url || undefined },
      {
        onSuccess: (res) => onRegisterSuccess(res.api_key),
      }
    );
  };

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 md:p-8 max-w-2xl backdrop-blur-sm">
      <div className="flex items-center space-x-3 mb-6">
        <div className="p-2.5 rounded-xl bg-indigo-500/20 text-indigo-400">
          <Store className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-white">Become a Merchant</h2>
          <p className="text-sm text-zinc-400">Start accepting wallet payments from users via API.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3">
            <p className="text-sm text-red-400">{error.message}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-zinc-300">Business Name</label>
          <input
            {...register('business_name')}
            className="mt-2 block w-full rounded-lg border-0 bg-zinc-950 py-2.5 px-3 text-white shadow-sm ring-1 ring-inset ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm"
            placeholder="Acme Corp"
          />
          {errors.business_name && <p className="mt-1 text-sm text-red-400">{errors.business_name.message}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-zinc-300">Webhook URL (Optional)</label>
          <input
            {...register('webhook_url')}
            className="mt-2 block w-full rounded-lg border-0 bg-zinc-950 py-2.5 px-3 text-white shadow-sm ring-1 ring-inset ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm"
            placeholder="https://api.acme.com/webhooks/payments"
          />
          <p className="mt-1.5 text-xs text-zinc-500">We will send a POST request here when a payment completes.</p>
          {errors.webhook_url && <p className="mt-1 text-sm text-red-400">{errors.webhook_url.message}</p>}
        </div>

        <button
          type="submit"
          disabled={isPending}
          className="flex w-full sm:w-auto justify-center items-center rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus:outline-none transition-all disabled:opacity-50"
        >
          {isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Key className="w-4 h-4 mr-2" />}
          Generate Live API Key
        </button>
      </form>
    </div>
  );
}

// ============================================================================
// API Key Reveal
// ============================================================================
function ApiKeyReveal({ apiKey, onAcknowledge }: { apiKey: string, onAcknowledge: () => void }) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-emerald-950/30 border border-emerald-900/50 rounded-2xl p-6 md:p-8 max-w-2xl relative overflow-hidden">
      <div className="absolute top-0 right-0 p-8 opacity-10">
        <Key className="w-32 h-32 text-emerald-400" />
      </div>
      
      <h2 className="text-xl font-bold text-emerald-400 mb-2">Registration Successful!</h2>
      <p className="text-zinc-300 text-sm mb-6 max-w-md">
        Your merchant account is active. Please save your live API key now. 
        <strong className="text-white block mt-2">For your security, it will never be shown again.</strong>
      </p>

      <div className="flex items-center space-x-2 bg-zinc-950 p-3 rounded-xl border border-zinc-800 mb-6 relative z-10">
        <code className="flex-1 text-emerald-400 font-mono text-sm break-all">{apiKey}</code>
        <button
          onClick={copyToClipboard}
          className="p-2 hover:bg-zinc-800 rounded-lg transition-colors text-zinc-400 hover:text-white shrink-0"
          title="Copy API Key"
        >
          {copied ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <Copy className="w-5 h-5" />}
        </button>
      </div>

      <button
        onClick={onAcknowledge}
        className="rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 transition-all relative z-10"
      >
        I have saved my API Key securely
      </button>
    </div>
  );
}

// ============================================================================
// Merchant Profile Card
// ============================================================================
function MerchantProfileCard({ profile }: { profile: any }) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 backdrop-blur-sm">
      <div className="flex items-center space-x-3 mb-6">
        <div className="p-2.5 rounded-xl bg-indigo-500/20 text-indigo-400">
          <Store className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">Business Details</h2>
        </div>
        <div className="ml-auto">
          <span className="inline-flex items-center rounded-full bg-emerald-400/10 px-2 py-1 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-400/20">
            Active
          </span>
        </div>
      </div>

      <dl className="space-y-4">
        <div>
          <dt className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Business Name</dt>
          <dd className="mt-1 text-sm text-white font-medium">{profile.business_name}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Webhook Endpoint</dt>
          <dd className="mt-1 text-sm text-zinc-300 flex items-center">
            {profile.webhook_url ? (
              <>
                <Link2 className="w-4 h-4 mr-1.5 text-zinc-500" />
                {profile.webhook_url}
              </>
            ) : (
              <span className="italic text-zinc-500">Not configured</span>
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Merchant ID</dt>
          <dd className="mt-1 text-xs font-mono text-zinc-400 break-all">{profile.id}</dd>
        </div>
      </dl>
    </div>
  );
}

// ============================================================================
// Test Sandbox
// ============================================================================
function TestSandbox() {
  const [apiKey, setApiKey] = useState('');
  const [amount, setAmount] = useState('1500'); // $15.00
  const [createdSession, setCreatedSession] = useState<CheckoutSession | null>(null);

  const { mutate: createCheckout, isPending: isCreating } = useCreateCheckout();
  const { mutate: payCheckout, isPending: isPaying } = usePayCheckout();

  const handleCreateSession = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey) {
      alert("Please enter your API Key");
      return;
    }
    
    createCheckout(
      { amount: parseInt(amount, 10), currency: 'USD', description: 'Test Order #123', apiKey },
      {
        onSuccess: (data) => setCreatedSession(data),
        onError: (err: any) => alert(err.response?.data?.detail || "Invalid API Key or server error"),
      }
    );
  };

  const handlePaySession = () => {
    if (!createdSession) return;
    
    payCheckout(createdSession.id, {
      onSuccess: (data) => setCreatedSession(data), // Status will be 'paid'
      onError: (err: any) => alert(err.response?.data?.detail || "Payment failed"),
    });
  };

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 backdrop-blur-sm relative overflow-hidden">
      <div className="flex items-center space-x-3 mb-6 relative z-10">
        <div className="p-2.5 rounded-xl bg-orange-500/20 text-orange-400">
          <Zap className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">Payment Sandbox</h2>
          <p className="text-xs text-zinc-400 mt-0.5">Test your API key and checkout flow.</p>
        </div>
      </div>

      {!createdSession ? (
        <form onSubmit={handleCreateSession} className="space-y-4 relative z-10">
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">Your API Key (sk_live_...)</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="block w-full rounded-lg border-0 bg-zinc-950 py-2 px-3 text-white shadow-sm ring-1 ring-inset ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-orange-500 sm:text-sm font-mono"
              placeholder="Paste your API key here"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">Amount (in cents)</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="block w-full rounded-lg border-0 bg-zinc-950 py-2 px-3 text-white shadow-sm ring-1 ring-inset ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-orange-500 sm:text-sm"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isCreating}
            className="w-full flex justify-center items-center rounded-lg bg-zinc-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-zinc-700 transition-all disabled:opacity-50"
          >
            {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate Checkout Session'}
          </button>
        </form>
      ) : (
        <div className="space-y-4 relative z-10">
          <div className="bg-zinc-950 rounded-xl p-4 border border-zinc-800">
            <div className="flex justify-between items-center mb-4">
              <span className="text-xs font-medium text-zinc-500">Checkout Session</span>
              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                createdSession.status === 'paid' 
                  ? 'bg-emerald-400/10 text-emerald-400 ring-1 ring-inset ring-emerald-400/20'
                  : 'bg-orange-400/10 text-orange-400 ring-1 ring-inset ring-orange-400/20'
              }`}>
                {createdSession.status.toUpperCase()}
              </span>
            </div>
            <div className="flex items-end justify-between mb-1">
              <span className="text-2xl font-bold text-white">${createdSession.amount_display}</span>
              <span className="text-sm font-medium text-zinc-400 mb-1">{createdSession.currency}</span>
            </div>
            <p className="text-sm text-zinc-400 truncate">{createdSession.description}</p>
          </div>

          {createdSession.status === 'pending' ? (
            <button
              onClick={handlePaySession}
              disabled={isPaying}
              className="w-full flex justify-center items-center rounded-lg bg-orange-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-orange-500 transition-all disabled:opacity-50"
            >
              {isPaying ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                <>Pay ${createdSession.amount_display} from my Wallet <ArrowRight className="w-4 h-4 ml-2" /></>
              )}
            </button>
          ) : (
            <button
              onClick={() => setCreatedSession(null)}
              className="w-full flex justify-center items-center rounded-lg bg-zinc-800 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 transition-all"
            >
              Start New Test
            </button>
          )}
        </div>
      )}
    </div>
  );
}
