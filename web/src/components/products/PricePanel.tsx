"use client";

import { ShoppingCart, MessageSquare, RefreshCw } from "lucide-react";
import type { QuoteResponse } from "@/lib/pricing-api";
import { QuoteError } from "@/lib/pricing-api";
import {
  formatMYR,
  computeDelivery,
  TIER_LABELS,
  TIER_COLORS,
  LEAD_TIMES,
} from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useCartStore } from "@/stores/cart";
import type { ProductDetail } from "@/lib/pricing-api";
import { toast } from "sonner";

interface PricePanelProps {
  product: ProductDetail;
  options: Record<string, string | number>;
  quantity: number;
  quote: QuoteResponse | undefined;
  isLoading: boolean;
  error: Error | null;
  userTier?: keyof QuoteResponse["tiers"];
}

export function PricePanel({
  product,
  options,
  quantity,
  quote,
  isLoading,
  error,
  userTier = "Cash",
}: PricePanelProps) {
  const addItem = useCartStore((s) => s.addItem);

  const isContactProduct = product.pricing_type === "contact";
  const is422 = error instanceof QuoteError && error.status === 422;
  const showQuoteForm = isContactProduct || is422;

  const handleAddToCart = () => {
    if (!quote) return;
    addItem({
      productId: product.id,
      productName: product.name,
      category: product.category,
      options,
      quantity,
      quote,
    });
    toast.success(`${product.name} added to cart`);
  };

  const delivery = quote ? computeDelivery(quote.weight_kg) : null;
  const total = quote && delivery != null ? quote.cash + delivery : null;

  const leadTime = LEAD_TIMES[product.category] ?? "5–7 working days";

  if (showQuoteForm) {
    return (
      <div className="rounded-xl border border-border bg-surface-muted p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink">
          <MessageSquare className="w-4 h-4 text-brand-600" />
          Request a quote
        </div>
        <p className="text-sm text-ink-muted">
          This product requires a custom quote. Fill in your details and we&apos;ll
          get back to you within 1 business day.
        </p>
        <QuoteRequestForm product={product} options={options} quantity={quantity} />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-brand-200 bg-white shadow-price p-6 flex flex-col gap-5">
      {/* Per-unit + total */}
      <div>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-24" />
          </div>
        ) : quote ? (
          <div className="animate-price-tick">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-ink price-display">
                {formatMYR(quote.cash)}
              </span>
              <span className="text-sm text-ink-muted">total</span>
            </div>
            <div className="text-sm text-ink-muted mt-0.5">
              {formatMYR(quote.per_unit)} per unit · {quantity.toLocaleString()} pcs
            </div>
          </div>
        ) : (
          <div className="text-sm text-ink-muted">
            Complete your configuration to see pricing.
          </div>
        )}
      </div>

      {/* Membership tier table */}
      {quote && (
        <div className="rounded-lg border border-border overflow-hidden">
          <div className="px-3 py-2 bg-surface-muted border-b border-border">
            <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide">
              Membership tiers
            </p>
          </div>
          <div className="divide-y divide-border">
            {(Object.entries(quote.tiers) as [keyof typeof quote.tiers, number][]).map(
              ([tier, price]) => (
                <div
                  key={tier}
                  className={`flex items-center justify-between px-3 py-2 ${
                    tier === userTier ? "bg-brand-50" : ""
                  }`}
                >
                  <span
                    className={`text-xs font-medium ${
                      tier === userTier
                        ? "text-brand-700 font-semibold"
                        : TIER_COLORS[tier]
                    }`}
                  >
                    {TIER_LABELS[tier] ?? tier}
                    {tier === userTier && (
                      <span className="ml-1.5 bg-brand-100 text-brand-700 text-[9px] px-1.5 py-0.5 rounded-full">
                        yours
                      </span>
                    )}
                  </span>
                  <span
                    className={`text-xs font-semibold price-display ${
                      tier === userTier ? "text-brand-700" : "text-ink"
                    }`}
                  >
                    {formatMYR(price)}
                  </span>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Delivery + total breakdown */}
      {quote && delivery != null && (
        <div className="space-y-2 text-sm border-t border-border pt-4">
          <div className="flex justify-between text-ink-muted">
            <span>Subtotal</span>
            <span className="price-display">{formatMYR(quote.cash)}</span>
          </div>
          <div className="flex justify-between text-ink-muted">
            <span>
              Est. delivery ({quote.weight_kg.toFixed(2)} kg)
            </span>
            <span className="price-display">{formatMYR(delivery)}</span>
          </div>
          <div className="flex justify-between font-semibold text-ink pt-1 border-t border-border">
            <span>Estimated total</span>
            <span className="price-display">{formatMYR(total!)}</span>
          </div>
        </div>
      )}

      {/* Lead time */}
      <p className="text-xs text-ink-muted flex items-center gap-1.5">
        <RefreshCw className="w-3.5 h-3.5" />
        Estimated production: {leadTime} after artwork approval
      </p>

      {/* Add to cart */}
      <Button
        size="lg"
        onClick={handleAddToCart}
        disabled={!quote || isLoading}
        className="w-full rounded-xl"
      >
        <ShoppingCart className="w-4 h-4" />
        {isLoading ? "Calculating…" : "Add to cart"}
      </Button>

      {error && !(error instanceof QuoteError && error.status === 422) && (
        <p className="text-xs text-red-600 text-center">
          Failed to get pricing — please try again.
        </p>
      )}
    </div>
  );
}

function QuoteRequestForm({
  product,
  options,
  quantity,
}: {
  product: ProductDetail;
  options: Record<string, string | number>;
  quantity: number;
}) {
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        toast.success("Quote request sent! We'll be in touch within 1 business day.");
      }}
    >
      <input
        type="email"
        required
        placeholder="Your email address"
        className="h-10 rounded-lg border border-border px-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
      <textarea
        placeholder="Additional notes or requirements (optional)"
        rows={3}
        className="rounded-lg border border-border px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
      <Button type="submit" size="md">
        Send quote request
      </Button>
    </form>
  );
}
