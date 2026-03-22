'use client';

import { useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface WebSocketProviderProps {
  children: React.ReactNode;
}

/**
 * WebSocket Provider Component
 * Initializes WebSocket connections and manages connection lifecycle
 * Must be a client component to use hooks
 */
export default function WebSocketProvider({ children }: WebSocketProviderProps) {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    // In production, get token from auth provider (NextAuth, Clerk, etc.)
    // For development, use a mock token
    const mockToken = process.env.NEXT_PUBLIC_DEV_TOKEN || 'dev-token-12345';
    setToken(mockToken);
  }, []);

  // Initialize WebSocket connections
  const { isConnected } = useWebSocket(token);

  // Log connection status changes
  useEffect(() => {
    if (token) {
      console.log('[WebSocket] Connection status:', isConnected);
    }
  }, [isConnected, token]);

  return <>{children}</>;
}

// Made with Bob
