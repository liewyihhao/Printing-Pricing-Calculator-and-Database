"use client";

import { useState } from "react";
import { Search, Package, CheckCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const STAGES = [
  "Payment received",
  "Artwork checking",
  "In production",
  "Finishing",
  "Packing",
  "Shipping",
  "Completed",
];

export default function TrackPage() {
  const [orderNo, setOrderNo] = useState("");
  const [searched, setSearched] = useState(false);

  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-2xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-10">
          <Package className="w-12 h-12 text-brand-600 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-ink mb-2">Track your order</h1>
          <p className="text-ink-muted">Enter your order number to see the current status.</p>
        </div>

        <div className="flex gap-3">
          <Input
            placeholder="e.g. ORD-1234567890"
            value={orderNo}
            onChange={(e) => setOrderNo(e.target.value)}
            className="flex-1"
          />
          <Button onClick={() => setSearched(true)} className="gap-2 shrink-0">
            <Search className="w-4 h-4" />
            Track
          </Button>
        </div>

        {searched && (
          <div className="mt-10 bg-white rounded-2xl border border-border p-6 animate-slide-up">
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-xs text-ink-muted">Order</p>
                <p className="text-sm font-semibold text-ink">{orderNo || "ORD-1234567890"}</p>
              </div>
              <span className="bg-amber-50 text-amber-700 text-xs font-medium px-3 py-1 rounded-full">
                In production
              </span>
            </div>

            <div className="flex flex-col gap-4">
              {STAGES.map((stage, i) => {
                const done = i < 3;
                const active = i === 3;
                return (
                  <div key={stage} className="flex items-center gap-3">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${done ? "bg-green-500" : active ? "bg-brand-500 animate-pulse" : "bg-surface-subtle border border-border"}`}>
                      {done && <CheckCircle className="w-3 h-3 text-white" />}
                      {active && <div className="w-2 h-2 bg-white rounded-full" />}
                    </div>
                    <span className={`text-sm ${done ? "text-green-700 font-medium" : active ? "text-brand-700 font-medium" : "text-ink-muted"}`}>
                      {stage}
                    </span>
                    {active && (
                      <span className="text-xs text-brand-600 flex items-center gap-1 ml-auto">
                        <Clock className="w-3.5 h-3.5" /> Est. 2 more days
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
