import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { QuoteResponse } from "@/lib/pricing-api";

export interface CartItem {
  id: string; // uuid
  productId: number;
  productName: string;
  category: string;
  options: Record<string, string | number>;
  quantity: number;
  quote: QuoteResponse | null;
  artworkRef?: string;
  designRef?: string;
  addedAt: number;
}

interface CartStore {
  items: CartItem[];
  addItem: (item: Omit<CartItem, "id" | "addedAt">) => void;
  updateItem: (id: string, updates: Partial<CartItem>) => void;
  removeItem: (id: string) => void;
  clearCart: () => void;
  itemCount: () => number;
  subtotal: () => number;
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (item) => {
        const id = crypto.randomUUID();
        set((s) => ({
          items: [...s.items, { ...item, id, addedAt: Date.now() }],
        }));
      },

      updateItem: (id, updates) => {
        set((s) => ({
          items: s.items.map((i) => (i.id === id ? { ...i, ...updates } : i)),
        }));
      },

      removeItem: (id) => {
        set((s) => ({ items: s.items.filter((i) => i.id !== id) }));
      },

      clearCart: () => set({ items: [] }),

      itemCount: () => get().items.reduce((sum, i) => sum + i.quantity, 0),

      subtotal: () =>
        get().items.reduce((sum, i) => sum + (i.quote?.cash ?? 0), 0),
    }),
    { name: "printoka-cart" }
  )
);
