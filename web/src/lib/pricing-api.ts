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

export interface ShowWhenCond {
  field: string;
  values?: string[];
  notValues?: string[];
}
export type ShowWhen = ShowWhenCond | { all: ShowWhenCond[] };

export interface ProductField {
  key: string;
  label: string;
  type: FieldType;
  required: boolean;
  options?: string[];
  images?: Record<string, string>; // option → data-URI
  min?: number;
  max?: number;
  section?: string; // Excard questionnaire section (General / Optional Finishing / …)
  swatch?: boolean;
  optional?: boolean;
  showWhen?: ShowWhen;
  note?: string;
  default?: string | number;
}

export interface ValidityRuleSet {
  primary: string; // field key that triggers cascading
  fields: string[]; // downstream field keys
  rules: Record<string, Record<string, string[]>>; // primary-value → {field → allowed[]}
}
// A product may carry one rule-set OR an array of them (array-validity, intersected).
export type ValidityRules = ValidityRuleSet | ValidityRuleSet[];

export interface QuantityConfig {
  moq?: number;
  maxq?: number;
  min?: number; // legacy alias
  options?: number[];
  mode?: string;
  custom?: boolean; // whether an arbitrary quantity (not just `options`) is accepted
  note?: string;
}

export interface ProductDetail extends ProductSummary {
  markup: number;
  tiers: string[];
  fields: ProductField[];
  validity?: ValidityRules;
  quantity: QuantityConfig;
  sectionOrder?: string[]; // Excard's section order
  quantitySection?: string | null; // Excard section holding Quantity (null ⇒ render it separately)
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

// ─── Orders ─────────────────────────────────────────────────────────────────
// Printoka's OWN order flow — POSTs a configured order *request* (no payment) to
// the calculator API, which records it and returns ORD-YYMMDD-XXXXXX. Never links
// out to the supplier. Mirrors app/public_api.py OrderRequest / OrderLine.

export interface OrderLine {
  product_id: number;
  product_name: string;
  options: Record<string, string | number>;
  quantity: number;
  unit_price?: number | null;
  cash?: number | null;
  weight_kg?: number | null;
}

export interface OrderRequestBody {
  items: OrderLine[];
  contact: Record<string, string>; // name, email, phone, company
  delivery: Record<string, string>; // address lines, method, destination
  artwork?: Record<string, string>; // filename, note, design_service
  totals: Record<string, number>; // subtotal, delivery_fee, grand_total
  remarks?: string;
}

export interface OrderCreateResponse {
  ok: boolean;
  order_ref: string;
  status: string;
  received_at: string;
}

// The stored record echoed back by GET /api/v1/orders/{ref}.
export interface OrderRecord extends OrderRequestBody {
  order_ref: string;
  status: string;
  received_at: string;
}

export async function createOrder(
  body: OrderRequestBody
): Promise<OrderCreateResponse> {
  const { data } = await pricingApi.post<OrderCreateResponse>(
    "/api/v1/orders",
    body
  );
  return data;
}

// ─── Product editorial content (Product Spec / Artwork Spec / Templates) ───────
// Generated from our own catalogue (app.build_spec_content) — copyright-safe education,
// rendered as tabs on the product page. Two block shapes: keyvalue rows or a bullet list.

export interface ContentKeyValueBlock {
  title?: string;
  type: "keyvalue";
  rows: { k: string; v: string }[];
  note?: string;
}
export interface ContentListBlock {
  title?: string;
  type: "list";
  items: string[];
  note?: string;
}
export type ContentBlock = ContentKeyValueBlock | ContentListBlock;

export interface ProductContent {
  sections: ContentBlock[]; // Product Spec
  artwork: ContentBlock[]; // Artwork Spec
  templates: ContentBlock[]; // Template sizes
}

export async function fetchProductContent(id: number): Promise<ProductContent> {
  const { data } = await pricingApi.get<ProductContent>(
    `/api/v1/products/${id}/content`
  );
  return data;
}

export async function fetchOrder(ref: string): Promise<OrderRecord> {
  try {
    const { data } = await pricingApi.get<OrderRecord>(
      `/api/v1/orders/${encodeURIComponent(ref)}`
    );
    return data;
  } catch (err) {
    const e = err as AxiosError;
    throw new QuoteError(e.response?.status ?? 0, e.message);
  }
}

// ─── API functions ────────────────────────────────────────────────────────────

export async function fetchProducts(params?: {
  category?: string;
  pricing_type?: string;
}): Promise<ProductSummary[]> {
  const { data } = await pricingApi.get<ProductSummary[] | { products: ProductSummary[] }>(
    "/api/v1/products",
    { params }
  );
  // API may return either a plain array or { count, products: [...] }
  return Array.isArray(data) ? data : (data as { products: ProductSummary[] }).products;
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
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

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

export function useCreateOrder() {
  return useMutation({
    mutationFn: (body: OrderRequestBody) => createOrder(body),
  });
}

export function useProductContent(id: number | null) {
  return useQuery({
    queryKey: ["product-content", id],
    queryFn: () => fetchProductContent(id!),
    enabled: id != null,
    staleTime: 1000 * 60 * 10,
    gcTime: 1000 * 60 * 60,
  });
}

export function useOrder(ref: string | null) {
  return useQuery({
    queryKey: ["order", ref],
    queryFn: () => fetchOrder(ref!),
    enabled: !!ref,
    retry: false,
    staleTime: 1000 * 30,
  });
}
