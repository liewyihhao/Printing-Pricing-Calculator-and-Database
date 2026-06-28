"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useProducts } from "@/lib/pricing-api";
import { ProductCard } from "@/components/products/ProductCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

const POPULAR_IDS_FALLBACK_NAMES = [
  "Business Card",
  "Loose Sheet",
  "Sticker",
  "Booklet",
  "Flyer",
  "Label",
];

export function PopularProducts() {
  const { data: products, isLoading } = useProducts();

  const popular = products
    ? products
        .filter(
          (p) =>
            POPULAR_IDS_FALLBACK_NAMES.some((n) =>
              p.name.toLowerCase().includes(n.toLowerCase())
            ) || products.indexOf(p) < 8
        )
        .slice(0, 8)
    : [];

  return (
    <section className="py-20 bg-surface-muted">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-end justify-between mb-10">
          <div>
            <p className="text-sm font-semibold text-brand-600 uppercase tracking-widest mb-2">
              Popular
            </p>
            <h2 className="text-3xl font-bold text-ink">Our best sellers</h2>
          </div>
          <Link href="/products">
            <Button variant="ghost" size="sm" className="gap-1.5 hidden sm:flex">
              View all products <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-border bg-white p-4 space-y-3">
                <Skeleton className="h-36 w-full rounded-lg" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {popular.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}

        <div className="mt-8 text-center sm:hidden">
          <Link href="/products">
            <Button variant="outline">
              View all products <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
