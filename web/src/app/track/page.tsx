"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Search, Package, CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useOrder, QuoteError } from "@/lib/pricing-api";
import { formatMYR } from "@/lib/utils";

const STAGES = [
  "Order received",
  "Artwork checking",
  "In production",
  "Finishing",
  "Packing",
  "Shipping",
  "Completed",
];

// The order API records a single "received" status (Printoka fulfils manually — no
// live production pipeline yet), so only the first stage is ever marked complete.
const STATUS_LABELS: Record<string, string> = {
  received: "Order received",
};

function TrackContent() {
  const params = useSearchParams();
  const initial = params.get("order") ?? "";
  const [orderNo, setOrderNo] = useState(initial);
  const [query, setQuery] = useState(initial || null);

  // Auto-look up when arriving with ?order= in the URL.
  useEffect(() => {
    if (initial) setQuery(initial);
  }, [initial]);

  const { data: order, isLoading, error, isError } = useOrder(query);
  const notFound = isError && error instanceof QuoteError && error.status === 404;

  const received =
    order?.received_at &&
    new Date(order.received_at).toLocaleString("en-MY", {
      dateStyle: "medium",
      timeStyle: "short",
    });

  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-2xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-10">
          <Package className="w-12 h-12 text-brand-600 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-ink mb-2">Track your order</h1>
          <p className="text-ink-muted">
            Enter your order number to see the current status.
          </p>
        </div>

        <form
          className="flex gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(orderNo.trim() || null);
          }}
        >
          <Input
            placeholder="e.g. ORD-260817-A1B2C3"
            value={orderNo}
            onChange={(e) => setOrderNo(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" className="gap-2 shrink-0" disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Track
          </Button>
        </form>

        {notFound && (
          <div className="mt-8 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-amber-800">Order not found</p>
              <p className="text-amber-700 mt-0.5">
                We couldn&apos;t find an order with that reference. Double-check the
                number from your confirmation email.
              </p>
            </div>
          </div>
        )}

        {order && (
          <div className="mt-10 bg-white rounded-2xl border border-border p-6 animate-slide-up">
            <div className="flex items-center justify-between mb-1">
              <div>
                <p className="text-xs text-ink-muted">Order</p>
                <p className="text-sm font-semibold text-ink">{order.order_ref}</p>
              </div>
              <span className="bg-green-50 text-green-700 text-xs font-medium px-3 py-1 rounded-full capitalize">
                {STATUS_LABELS[order.status] ?? order.status}
              </span>
            </div>
            {received && (
              <p className="text-xs text-ink-muted mb-6">Received {received}</p>
            )}

            {/* Item lines */}
            {order.items?.length > 0 && (
              <div className="mb-6 flex flex-col gap-2 text-sm divide-y divide-border border-y border-border py-3">
                {order.items.map((it, idx) => (
                  <div key={idx} className="flex justify-between gap-3 pt-2 first:pt-0">
                    <span className="text-ink-secondary">
                      {it.product_name || `Product ${it.product_id}`}
                      <span className="text-ink-subtle"> ×{it.quantity}</span>
                    </span>
                    <span className="price-display text-ink shrink-0">
                      {formatMYR(it.cash ?? 0)}
                    </span>
                  </div>
                ))}
                {order.totals?.grand_total != null && (
                  <div className="flex justify-between pt-2 font-semibold text-ink">
                    <span>Total</span>
                    <span className="price-display">
                      {formatMYR(order.totals.grand_total)}
                    </span>
                  </div>
                )}
              </div>
            )}

            <div className="flex flex-col gap-4">
              {STAGES.map((stage, i) => {
                const done = i === 0; // only "Order received" is real so far
                const active = i === 1;
                return (
                  <div key={stage} className="flex items-center gap-3">
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                        done
                          ? "bg-green-500"
                          : active
                          ? "bg-brand-500 animate-pulse"
                          : "bg-surface-subtle border border-border"
                      }`}
                    >
                      {done && <CheckCircle className="w-3 h-3 text-white" />}
                      {active && <div className="w-2 h-2 bg-white rounded-full" />}
                    </div>
                    <span
                      className={`text-sm ${
                        done
                          ? "text-green-700 font-medium"
                          : active
                          ? "text-brand-700 font-medium"
                          : "text-ink-muted"
                      }`}
                    >
                      {stage}
                    </span>
                    {active && (
                      <span className="text-xs text-brand-600 flex items-center gap-1 ml-auto">
                        <Clock className="w-3.5 h-3.5" /> Awaiting artwork
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            <p className="text-xs text-ink-subtle mt-6">
              You&apos;ll receive email updates as your order moves through production.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function TrackPage() {
  return (
    <Suspense>
      <TrackContent />
    </Suspense>
  );
}
