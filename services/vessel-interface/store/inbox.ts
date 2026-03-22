import { create } from 'zustand';

export type TriggerType =
  | 'BUDGET_EXCEEDED'
  | 'EXECUTION_FAILURE'
  | 'PII_DETECTED'
  | 'EXTERNAL_WRITE'
  | 'ANOMALY_DETECTED';

export type Severity = 'WARN' | 'BLOCK' | 'CRITICAL';

export type CardStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'DEFERRED' | 'EXPIRED';

export interface InboxCard {
  card_id: string;
  goal_id: string;
  task_id: string;
  agent_id: string;
  trigger_type: TriggerType;
  severity: Severity;
  title: string;
  description: string;
  proposed_action: string;
  estimated_cost_usd: number;
  status: CardStatus;
  created_at: string;
  expires_at: string;
  resolved_by_user_id?: string;
  resolved_at?: string;
}

export interface InboxStats {
  total_cards: number;
  pending_cards: number;
  approved_cards: number;
  rejected_cards: number;
  deferred_cards: number;
  expired_cards: number;
  critical_cards: number;
}

interface InboxStore {
  // Cards
  cards: InboxCard[];
  
  // Stats
  stats: InboxStats;
  
  // Connection status
  isConnected: boolean;
  lastEventTime: string | null;
  
  // Actions
  setCards: (cards: InboxCard[]) => void;
  addCard: (card: InboxCard) => void;
  updateCardStatus: (card_id: string, status: CardStatus) => void;
  removeCard: (card_id: string) => void;
  updateStats: (stats: Partial<InboxStats>) => void;
  setConnectionStatus: (isConnected: boolean) => void;
  reset: () => void;
  
  // Computed getters
  getPendingCards: () => InboxCard[];
  getCriticalCards: () => InboxCard[];
  getCardsByTriggerType: (trigger_type: TriggerType) => InboxCard[];
}

const initialStats: InboxStats = {
  total_cards: 0,
  pending_cards: 0,
  approved_cards: 0,
  rejected_cards: 0,
  deferred_cards: 0,
  expired_cards: 0,
  critical_cards: 0,
};

const calculateStats = (cards: InboxCard[]): InboxStats => {
  return {
    total_cards: cards.length,
    pending_cards: cards.filter((c) => c.status === 'PENDING').length,
    approved_cards: cards.filter((c) => c.status === 'APPROVED').length,
    rejected_cards: cards.filter((c) => c.status === 'REJECTED').length,
    deferred_cards: cards.filter((c) => c.status === 'DEFERRED').length,
    expired_cards: cards.filter((c) => c.status === 'EXPIRED').length,
    critical_cards: cards.filter((c) => c.severity === 'CRITICAL' && c.status === 'PENDING').length,
  };
};

export const useInboxStore = create<InboxStore>((set, get) => ({
  cards: [],
  stats: initialStats,
  isConnected: false,
  lastEventTime: null,

  setCards: (cards) =>
    set({
      cards,
      stats: calculateStats(cards),
    }),

  addCard: (card) =>
    set((state) => {
      const cards = [...state.cards, card];
      return {
        cards,
        stats: calculateStats(cards),
        lastEventTime: new Date().toISOString(),
      };
    }),

  updateCardStatus: (card_id, status) =>
    set((state) => {
      const cards = state.cards.map((c) =>
        c.card_id === card_id
          ? {
              ...c,
              status,
              resolved_at: new Date().toISOString(),
            }
          : c
      );
      return {
        cards,
        stats: calculateStats(cards),
        lastEventTime: new Date().toISOString(),
      };
    }),

  removeCard: (card_id) =>
    set((state) => {
      const cards = state.cards.filter((c) => c.card_id !== card_id);
      return {
        cards,
        stats: calculateStats(cards),
        lastEventTime: new Date().toISOString(),
      };
    }),

  updateStats: (stats) =>
    set((state) => ({
      stats: {
        ...state.stats,
        ...stats,
      },
    })),

  setConnectionStatus: (isConnected) =>
    set({ isConnected }),

  reset: () =>
    set({
      cards: [],
      stats: initialStats,
      isConnected: false,
      lastEventTime: null,
    }),

  // Computed getters
  getPendingCards: () => {
    return get().cards.filter((c) => c.status === 'PENDING');
  },

  getCriticalCards: () => {
    return get().cards.filter((c) => c.severity === 'CRITICAL' && c.status === 'PENDING');
  },

  getCardsByTriggerType: (trigger_type) => {
    return get().cards.filter((c) => c.trigger_type === trigger_type);
  },
}));

// Made with Bob
