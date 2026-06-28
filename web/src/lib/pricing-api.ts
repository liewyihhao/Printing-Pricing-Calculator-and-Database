import axios, { AxiosError } from "axios";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

const BASE = process.env.NEXT_PUBLIC_PRICING_API ?? "http://localhost:8000";

export const pricingApi = axios.create({
  baseURL: BASE,
  timeout: 10000,
});

// ─── Types ───────────────────────────────────────────────────────────────────

export type PricingType = "exact" | "reference" | "contact";

export type ProductCategory =
  | "Cards & Stationery"
  | "Books & Pads"
  | "Stickers & Labels"
  | "Marketing & Signage"
  | "Packaging & Bags"
  | "Calendars"
  | "Promo & Gifts"
  | "Other";

export interface ProductSummary {
  id: number;
  name: string;
  category: ProductCategory;
  pricing_type: PricingType;
}

export type FieldType = "select" | "number";

export interface ProductField {
  key: string;
  label: string;
  type: FieldType;
  required: boolean;
  options?: string[];
  images?: Record<string, string>; // option → data-URI
  min?: number;
  max?: number;
}

export interface ValidityRules {
  primary: string; // field key that triggers cascading
  fields: string[]; // downstream field keys
  rules: Record<string, Record<string, string[]>>; // primary-value → {field → allowed[]}
}

export interface QuantityConfig {
  min: number;
  note?: string;
}

export interface ProductDetail extends ProductSummary {
  markup: number;
  tiers: string[];
  fields: ProductField[];
  validity?: ValidityRules;
  quantity: QuantityConfig;
}

export interface QuoteRequest {
  product_id: number;
  options: Record<string, string | number>;
  quantity: number;
}

export interface QuoteResponse {
  product_id: number;
  product: string;
  quantity: number;
  currency: string;
  pricing_type: PricingType;
  cash: number;
  per_unit: number;
  tiers: {
    Cash: number;
    Silver: number;
    Gold: number;
    Platinum: number;
  };
  weight_kg: number;
}

export class QuoteError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "QuoteError";
  }
}

// ─── API functions ────────────────────────────────────────────────────────────

export async function fetchProducts(params?: {
  category?: string;
  pricing_type?: string;
}): Promise<ProductSummary[]> {
  const { data } = await pricingApi.get<ProductSummary[]>("/api/v1/products", {
    params,
  });
  return data;
}

export async function fetchProduct(id: number): Promise<ProductDetail> {
  const { data } = await pricingApi.get<ProductDetail>(`/api/v1/products/${id}`);
  return data;
}

export async function fetchQuote(req: QuoteRequest): Promise<QuoteResponse> {
  try {
    const { data } = await pricingApi.post<QuoteResponse>("/api/v1/quote", req);
    return data;
  } catch (err) {
    const e = err as AxiosError;
    throw new QuoteError(e.response?.status ?? 0, e.message);
  }
}

// ─── React Query hooks ────────────────────────────────────────────────────────

export function useProducts(params?: {
  category?: string;
  pricing_type?: string;
}) {
  return useQuery({
    queryKey: ["products", params],
    queryFn: () => fetchProducts(params),
    staleTime: 1000 * 60 * 10, // 10 min
    gcTime: 1000 * 60 * 60,
  });
}

export function useProduct(id: number | null) {
  return useQuery({
    queryKey: ["product", id],
    queryFn: () => fetchProduct(id!),
    enabled: id != null,
    staleTime: 1000 * 60 * 10,
    gcTime: 1000 * 60 * 60,
  });
}

export function useQuote(
  productId: number | null,
  options: Record<string, string | number>,
  quantity: number,
  enabled = true
) {
  const [debouncedOptions, setDebouncedOptions] = useState(options);
  const [debouncedQty, setDebouncedQty] = useState(quantity);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setDebouncedOptions(options);
      setDebouncedQty(quantity);
    }, 250);
    return () => clearTimeout(timer.current);
  }, [options, quantity]);

  return useQuery({
    queryKey: ["quote", productId, debouncedOptions, debouncedQty],
    queryFn: () =>
      fetchQuote({
        product_id: productId!,
        options: debouncedOptions,
        quantity: debouncedQty,
      }),
    enabled: enabled && productId != null && quantity > 0,
    retry: false,
    staleTime: 0,
  });
}
