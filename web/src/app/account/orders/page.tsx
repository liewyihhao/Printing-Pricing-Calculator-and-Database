"use client";

import Link from "next/link";
import { Package, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatMYR } from "@/lib/utils";

const MOCK_ORDERS = [
  { id: "ORD-1001", date: "2026-06-20", status: "Completed", items: "Business Card × 500, Flyer A5 × 1000", total: 285.50 },
  { id: "ORD-1002", date: "2026-06-25", status: "In production", items: "Sticker Round 50mm × 200", total: 68.00 },
];

export default function OrdersPage() {
  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-ink mb-8">My orders</h1>

        <div className="flex flex-col gap-4">
          {MOCK_ORDERS.map((order) => (
            <div key={order.id} className="bg-white rounded-xl border border-border p-5 flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <Package className="w-8 h-8 text-ink-muted shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-ink">{order.id}</div>
                  <div className="text-xs text-ink-muted mt-0.5">{order.items}</div>
                  <div className="text-xs text-ink-subtle mt-0.5">{order.date}</div>
                </div>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <div className="text-right hidden sm:block">
                  <div className="text-sm font-semibold text-ink price-display">{formatMYR(order.total)}</div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${order.status === "Completed" ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-700"}`}>
                    {order.status}
                  </span>
                </div>
                <Button variant="outline" size="sm" className="gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5" />
                  Reorder
                </Button>
              </div>
            </div>
          ))}
        </div>

        <p className="mt-6 text-sm text-ink-muted text-center">
          Sign in to see your full order history.{" "}
          <Link href="/auth/login" className="text-brand-600 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
