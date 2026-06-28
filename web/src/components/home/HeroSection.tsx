"use client";

import Link from "next/link";
import { ArrowRight, Star, Zap, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";

const STATS = [
  { value: "10,000+", label: "Orders delivered" },
  { value: "48 hrs", label: "Average turnaround" },
  { value: "99.2%", label: "On-time delivery" },
  { value: "4.9★", label: "Customer rating" },
];

const BADGES = [
  { icon: Zap, text: "Live pricing" },
  { icon: Shield, text: "Secure checkout" },
  { icon: Star, text: "Premium quality" },
];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-white pt-32 pb-20 lg:pt-40 lg:pb-28">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(#6366f1 1px, transparent 1px), linear-gradient(90deg, #6366f1 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />
      {/* Gradient blobs */}
      <div className="absolute top-20 right-1/4 w-96 h-96 bg-brand-100 rounded-full blur-3xl opacity-40 -translate-y-1/2" />
      <div className="absolute bottom-0 left-1/4 w-64 h-64 bg-purple-100 rounded-full blur-3xl opacity-30" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          {/* Pill badge */}
          <div className="inline-flex items-center gap-2 rounded-full bg-brand-50 border border-brand-200 px-4 py-1.5 text-sm text-brand-700 font-medium mb-8">
            <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
            Instant live pricing — no quotes needed
          </div>

          <h1 className="text-5xl lg:text-6xl font-extrabold text-ink leading-[1.1] tracking-tight mb-6">
            Professional printing,{" "}
            <span className="text-brand-600">ordered online</span>
          </h1>

          <p className="text-xl text-ink-muted leading-relaxed mb-10 max-w-2xl mx-auto">
            Business cards, flyers, brochures, stickers and more. Configure
            your specs, see the price instantly, upload artwork, and we&apos;ll
            deliver to your door.
          </p>

          {/* Trust badges */}
          <div className="flex items-center justify-center gap-6 mb-10">
            {BADGES.map(({ icon: Icon, text }) => (
              <div
                key={text}
                className="flex items-center gap-1.5 text-sm text-ink-muted"
              >
                <Icon className="w-4 h-4 text-brand-500" />
                {text}
              </div>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-16">
            <Link href="/products">
              <Button size="lg" className="gap-2 rounded-xl shadow-sm">
                Browse products
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/products">
              <Button variant="outline" size="lg" className="rounded-xl">
                Get instant quote
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-2xl mx-auto">
            {STATS.map(({ value, label }) => (
              <div key={label} className="text-center">
                <div className="text-2xl font-bold text-ink tracking-tight">
                  {value}
                </div>
                <div className="text-xs text-ink-muted mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
