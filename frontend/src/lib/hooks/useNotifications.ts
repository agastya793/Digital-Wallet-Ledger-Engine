import { useEffect, useRef } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { toast } from 'sonner';

interface TransactionEvent {
  transaction_id: string;
  type: 'sent' | 'received';
  amount: string;
  currency: string;
  partner: string;
  status: string;
}

export function useNotifications() {
  const token = useAuthStore((state) => state.token);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
      return;
    }

    // Connect to WebSocket
    const wsUrl = `ws://localhost:8000/api/v1/notifications/ws?token=${token}`;
    const socket = new WebSocket(wsUrl);
    ws.current = socket;

    socket.onopen = () => {
      console.log('WebSocket connected for notifications');
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'transaction_completed') {
          const data = message.data as TransactionEvent;
          
          if (data.type === 'received') {
            toast.success(`You received ${data.amount} ${data.currency} from ${data.partner}!`);
          } else if (data.type === 'sent') {
            toast.success(`Successfully sent ${data.amount} ${data.currency} to ${data.partner}.`);
          }
        }
      } catch (err) {
        console.error('Failed to parse websocket message', err);
      }
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [token, isAuthenticated]);
}
