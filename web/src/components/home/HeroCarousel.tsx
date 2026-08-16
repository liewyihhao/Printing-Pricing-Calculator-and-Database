"use client";

import Link from "next/link";
import { useState, useEffect, useCallback } from "react";
import { ChevronLeft, ChevronRight, ArrowRight, Zap, Truck, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SLIDES = [1, 2, 3, 4, 5, 6];
const AUTO_MS = 5500;

const BADGES = [
  { icon: Zap, text: "Instant live pricing" },
  { icon: Truck, text: "Nationwide delivery" },
  { icon: Shield, text: "Secure checkout" },
];

export function HeroCarousel() {
  const [i, setI] = useState(0);
  const [paused, setPaused] = useState(false);

  const go = useCallback((n: number) => setI((n + SLIDES.length) % SLIDES.length), []);

  useEffect(() => {
    if (paused) return;
    const t = setInterval(() => setI((p) => (p + 1) % SLIDES.length), AUTO_MS);
    return () => clearInterval(t);
  }, [paused]);

  return (
    <section className="bg-white pt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div
          className="relative overflow-hidden rounded-xl border border-border bg-white group"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
        >
          <Link href="/products" aria-label="Browse Printoka products" className="block">
            {/* Track */}
            <div
              className="flex transition-transform duration-700 ease-out"
              style={{ transform: `translateX(-${i * 100}%)` }}
            >
              {SLIDES.map((n) => (
                <div key={n} className="min-w-full">
                  {/* desktop 2000×600, mobile 1080×720 */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`/hero/slide-${n}.jpg`}
                    alt={`Printoka online printing — slide ${n}`}
                    className="hidden sm:block w-full h-auto"
                    fetchPriority={n === 1 ? "high" : "low"}
                  />
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`/hero/slide-m-${n}.jpg`}
                    alt={`Printoka online printing — slide ${n}`}
                    className="block sm:hidden w-full h-auto"
                  />
                </div>
              ))}
            </div>
          </Link>

          {/* Prev / Next */}
          <button
            onClick={() => go(i - 1)}
            aria-label="Previous slide"
            className="absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white/80 backdrop-blur border border-border flex items-center justify-center text-ink shadow-sm opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={() => go(i + 1)}
            aria-label="Next slide"
            className="absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white/80 backdrop-blur border border-border flex items-center justify-center text-ink shadow-sm opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white"
          >
            <ChevronRight className="w-5 h-5" />
          </button>

          {/* Dots */}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-2">
            {SLIDES.map((_, n) => (
              <button
                key={n}
                onClick={() => go(n)}
                aria-label={`Go to slide ${n + 1}`}
                className={cn(
                  "h-2 rounded-full transition-all",
                  n === i ? "w-6 bg-brand-500" : "w-2 bg-ink-subtle/50 hover:bg-ink-subtle"
                )}
              />
            ))}
          </div>
        </div>

        {/* CTA row + trust badges under the carousel */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-6">
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            {BADGES.map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-1.5 text-sm font-medium text-ink-muted">
                <Icon className="w-4 h-4 text-brand-500" />
                {text}
              </div>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <Link href="/products">
              <Button size="lg" className="gap-2">
                Browse all products
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/products/1">
              <Button variant="outline" size="lg">Get an instant price</Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
