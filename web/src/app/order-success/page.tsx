"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle, Package, Clock, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const TIMELINE = [
  { label: "Payment received", done: true },
  { label: "Artwork review", done: false },
  { label: "In production", done: false },
  { label: "Finishing", done: false },
  { label: "Packing", done: false },
  { label: "Shipped", done: false },
  { label: "Delivered", done: false },
];

function OrderSuccessContent() {
  const params = useSearchParams();
  const orderId = params.get("order") ?? "ORD-XXXXXXXX";

  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-ink mb-2">Order confirmed!</h1>
        <p className="text-ink-muted mb-1">
          Thank you for your order. We&apos;ll get started once your artwork is approved.
        </p>
        <p className="text-sm text-brand-600 font-semibold mb-10">Order {orderId}</p>

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
                    step.done
                      ? "bg-green-500"
                      : i === 1
                      ? "border-2 border-brand-400 bg-brand-50"
                      : "border border-border bg-surface-subtle"
                  }`}
                >
                  {step.done && <CheckCircle className="w-3 h-3 text-white" />}
                </div>
                <span
                  className={`text-sm ${
                    step.done ? "text-green-700 font-medium" : i === 1 ? "text-brand-700 font-medium" : "text-ink-muted"
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
          <Link href="/account/orders">
            <Button variant="outline" className="gap-2">
              <Package className="w-4 h-4" />
              View my orders
            </Button>
          </Link>
          <Link href="/products">
            <Button className="gap-2">
              Continue shopping <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
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
