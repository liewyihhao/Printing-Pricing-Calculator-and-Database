"use client";

import { useState, useMemo } from "react";
import { Search } from "lucide-react";
import { useProducts } from "@/lib/pricing-api";
import { ProductCard } from "@/components/products/ProductCard";
import { Skeleton } from "@/components/ui/skeleton";
import { CATEGORY_ICONS } from "@/lib/utils";
import type { ProductCategory } from "@/lib/pricing-api";

const CATEGORIES: ProductCategory[] = [
  "Cards & Stationery",
  "Books & Pads",
  "Stickers & Labels",
  "Marketing & Signage",
  "Packaging & Bags",
  "Calendars",
  "Promo & Gifts",
  "Other",
];

export default function ProductsPage() {
  const { data: products, isLoading } = useProducts();
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const filtered = useMemo(() => {
    if (!products) return [];
    return products.filter((p) => {
      const matchCat =
        activeCategory === "All" || p.category === activeCategory;
      const matchSearch =
        !search || p.name.toLowerCase().includes(search.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [products, search, activeCategory]);

  const grouped = useMemo(() => {
    const map = new Map<string, typeof filtered>();
    for (const p of filtered) {
      if (!map.has(p.category)) map.set(p.category, []);
      map.get(p.category)!.push(p);
    }
    return map;
  }, [filtered]);

  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-4xl font-bold text-ink mb-2">All Products</h1>
          <p className="text-ink-muted">
            {products?.length ?? "—"} products · configure, price, and order instantly
          </p>
        </div>

        {/* Search + category filter */}
        <div className="flex flex-col sm:flex-row gap-4 mb-10">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-subtle" />
            <input
              type="search"
              placeholder="Search products…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-10 w-full rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 text-ink placeholder:text-ink-subtle"
            />
          </div>

          {/* Category pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setActiveCategory("All")}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                activeCategory === "All"
                  ? "bg-brand-600 text-white"
                  : "bg-surface-subtle text-ink-secondary hover:bg-surface-muted"
              }`}
            >
              All
            </button>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors flex items-center gap-1.5 ${
                  activeCategory === cat
                    ? "bg-brand-600 text-white"
                    : "bg-surface-subtle text-ink-secondary hover:bg-surface-muted"
                }`}
              >
                <span>{CATEGORY_ICONS[cat]}</span>
                <span className="hidden sm:inline">{cat}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Product grid */}
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-border bg-white p-4 space-y-3">
                <Skeleton className="h-32 w-full rounded-lg" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : grouped.size === 0 ? (
          <div className="text-center py-20 text-ink-muted">
            No products found matching &ldquo;{search}&rdquo;.
          </div>
        ) : activeCategory !== "All" ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {filtered.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-14">
            {Array.from(grouped.entries()).map(([cat, items]) => (
              <div key={cat}>
                <div className="flex items-center gap-2 mb-5">
                  <span className="text-2xl">{CATEGORY_ICONS[cat]}</span>
                  <h2 className="text-xl font-semibold text-ink">{cat}</h2>
                  <span className="text-sm text-ink-subtle ml-1">
                    ({items.length})
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                  {items.map((p) => (
                    <ProductCard key={p.id} product={p} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
