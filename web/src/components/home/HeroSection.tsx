"use client";

import Link from "next/link";
import { ArrowRight, Zap, Shield, Truck } from "lucide-react";
import { Button } from "@/components/ui/button";

const STATS = [
  { value: "100+", label: "Products online" },
  { value: "48 hrs", label: "Fast turnaround" },
  { value: "10,000+", label: "Orders delivered" },
  { value: "4.9★", label: "Customer rating" },
];

const BADGES = [
  { icon: Zap, text: "Instant live pricing" },
  { icon: Truck, text: "Nationwide delivery" },
  { icon: Shield, text: "Secure checkout" },
];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-white pt-32 pb-16 lg:pt-40 lg:pb-24">
      {/* Subtle grid + a hint of the brand-gradient glow */}
      <div
        className="absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage:
            "linear-gradient(#212121 1px, transparent 1px), linear-gradient(90deg, #212121 1px, transparent 1px)",
          backgroundSize: "44px 44px",
        }}
      />
      <div className="absolute -top-24 right-1/4 w-[28rem] h-[28rem] rounded-full blur-3xl opacity-[0.12] printoka-gradient" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          {/* Pill badge */}
          <div className="inline-flex items-center gap-2 rounded-full bg-brand-50 border border-brand-200 px-4 py-1.5 text-sm text-brand-700 font-semibold mb-8">
            <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
            Instant live pricing — no quotes needed
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-ink leading-[1.08] tracking-tight mb-6">
            Online Printing in Malaysia,{" "}
            <span className="text-brand-500">Singapore &amp; Brunei</span>
          </h1>

          <p className="text-lg sm:text-xl text-ink-muted leading-relaxed mb-9 max-w-2xl mx-auto">
            More than 100 products online — business cards, stickers &amp; labels,
            flyers, brochures, banners &amp; more. Configure your print, see the exact
            price instantly, upload your artwork, and we deliver to your door.
          </p>

          {/* Trust badges */}
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mb-9">
            {BADGES.map(({ icon: Icon, text }) => (
              <div
                key={text}
                className="flex items-center gap-1.5 text-sm font-medium text-ink-muted"
              >
                <Icon className="w-4 h-4 text-brand-500" />
                {text}
              </div>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-16">
            <Link href="/products">
              <Button size="lg" className="gap-2">
                Browse all products
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/products/1">
              <Button variant="outline" size="lg">
                Get an instant price
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
