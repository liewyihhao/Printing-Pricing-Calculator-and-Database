"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle, Package, Clock, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useOrder } from "@/lib/pricing-api";
import { formatMYR } from "@/lib/utils";

const TIMELINE = [
  { label: "Order received", stageDone: true },
  { label: "Artwork review", stageDone: false },
  { label: "In production", stageDone: false },
  { label: "Finishing", stageDone: false },
  { label: "Packing", stageDone: false },
  { label: "Shipped", stageDone: false },
  { label: "Delivered", stageDone: false },
];

function OrderSuccessContent() {
  const params = useSearchParams();
  const orderId = params.get("order") ?? "";
  const { data: order, isLoading } = useOrder(orderId || null);

  const received =
    order?.received_at &&
    new Date(order.received_at).toLocaleString("en-MY", {
      dateStyle: "medium",
      timeStyle: "short",
    });

  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-ink mb-2">Order confirmed!</h1>
        <p className="text-ink-muted mb-1">
          Thank you for your order. We&apos;ll get started once your artwork is approved.
        </p>
        <p className="text-sm text-brand-600 font-semibold mb-2">
          Order {orderId || "—"}
        </p>
        {received && (
          <p className="text-xs text-ink-muted mb-10">Received {received}</p>
        )}
        {!received && <div className="mb-10" />}

        {/* Order line items + totals (from the real recorded order) */}
        {order && order.items?.length > 0 && (
          <div className="bg-white rounded-2xl border border-border p-6 mb-8 text-left">
            <h2 className="text-sm font-semibold text-ink mb-4 flex items-center gap-2">
              <Package className="w-4 h-4 text-brand-600" />
              Order summary
            </h2>
            <div className="flex flex-col gap-2.5 text-sm divide-y divide-border">
              {order.items.map((it, idx) => (
                <div key={idx} className="flex justify-between gap-3 pt-2.5 first:pt-0">
                  <span className="text-ink-secondary">
                    {it.product_name || `Product ${it.product_id}`}
                    <span className="text-ink-subtle"> ×{it.quantity}</span>
                  </span>
                  <span className="price-display text-ink shrink-0">
                    {formatMYR(it.cash ?? 0)}
                  </span>
                </div>
              ))}
              {order.totals?.delivery_fee != null && (
                <div className="flex justify-between pt-2.5 text-ink-muted">
                  <span>Delivery</span>
                  <span className="price-display">
                    {formatMYR(order.totals.delivery_fee)}
                  </span>
                </div>
              )}
              {order.totals?.grand_total != null && (
                <div className="flex justify-between pt-2.5 font-semibold text-ink">
                  <span>Total</span>
                  <span className="price-display">
                    {formatMYR(order.totals.grand_total)}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="bg-white rounded-2xl border border-border p-6 mb-8 text-left">
          <h2 className="text-sm font-semibold text-ink mb-5 flex items-center gap-2">
            <Clock className="w-4 h-4 text-brand-600" />
            Order progress
          </h2>
          <div className="flex flex-col gap-4">
            {TIMELINE.map((step, i) => (
              <div key={step.label} className="flex items-center gap-3">
                <div
                  className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                    step.stageDone
                      ? "bg-green-500"
                      : i === 1
                      ? "border-2 border-brand-400 bg-brand-50"
                      : "border border-border bg-surface-subtle"
                  }`}
                >
                  {step.stageDone && <CheckCircle className="w-3 h-3 text-white" />}
                </div>
                <span
                  className={`text-sm ${
                    step.stageDone
                      ? "text-green-700 font-medium"
                      : i === 1
                      ? "text-brand-700 font-medium"
                      : "text-ink-muted"
                  }`}
                >
                  {step.label}
                </span>
                {i === 1 && (
                  <span className="text-xs bg-amber-100 text-amber-700 rounded-full px-2 py-0.5 ml-auto">
                    Pending artwork
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href={orderId ? `/track?order=${encodeURIComponent(orderId)}` : "/track"}>
            <Button variant="outline" className="gap-2">
              <Package className="w-4 h-4" />
              Track this order
            </Button>
          </Link>
          <Link href="/products">
            <Button className="gap-2">
              Continue shopping <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>

        {isLoading && (
          <p className="text-xs text-ink-subtle mt-6">Loading order details…</p>
        )}
      </div>
    </div>
  );
}

export default function OrderSuccessPage() {
  return (
    <Suspense>
      <OrderSuccessContent />
    </Suspense>
  );
}
