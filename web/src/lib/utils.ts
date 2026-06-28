import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMYR(amount: number): string {
  return new Intl.NumberFormat("en-MY", {
    style: "currency",
    currency: "MYR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatWeight(kg: number): string {
  if (kg < 1) return `${Math.round(kg * 1000)} g`;
  return `${kg.toFixed(2)} kg`;
}

/** Courier rate: flat RM 8 for first kg + RM 2/kg after, peninsular Malaysia */
export function computeDelivery(weightKg: number): number {
  const ceil = Math.ceil(weightKg);
  if (ceil <= 1) return 8;
  return 8 + (ceil - 1) * 2;
}

export const TAX_RATE = 0; // SST not applied at checkout for B2B; adjust as needed

export function applyTax(amount: number): number {
  return amount * (1 + TAX_RATE);
}

/** Production lead times by category */
export const LEAD_TIMES: Record<string, string> = {
  "Cards & Stationery": "3–5 working days",
  "Books & Pads": "5–7 working days",
  "Stickers & Labels": "3–5 working days",
  "Marketing & Signage": "5–7 working days",
  "Packaging & Bags": "7–10 working days",
  Calendars: "7–10 working days",
  "Promo & Gifts": "7–14 working days",
  Other: "5–7 working days",
};

export const QUICK_QTY = [50, 100, 250, 500, 1000, 2000, 5000];

export const TIER_LABELS: Record<string, string> = {
  Cash: "List",
  Silver: "Silver −4%",
  Gold: "Gold −8%",
  Platinum: "Platinum −14%",
};

export const TIER_COLORS: Record<string, string> = {
  Cash: "text-ink-secondary",
  Silver: "text-slate-500",
  Gold: "text-amber-600",
  Platinum: "text-purple-600",
};

export const CATEGORY_ICONS: Record<string, string> = {
  "Cards & Stationery": "📇",
  "Books & Pads": "📚",
  "Stickers & Labels": "🏷️",
  "Marketing & Signage": "📢",
  "Packaging & Bags": "📦",
  Calendars: "📅",
  "Promo & Gifts": "🎁",
  Other: "🖨️",
};
