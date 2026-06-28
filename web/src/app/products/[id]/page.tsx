"use client";

import { useState, useCallback, useMemo, use } from "react";
import { useProduct, useQuote } from "@/lib/pricing-api";
import { Configurator } from "@/components/products/Configurator";
import { PricePanel } from "@/components/products/PricePanel";
import { Skeleton } from "@/components/ui/skeleton";
import { QUICK_QTY, CATEGORY_ICONS, formatMYR } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { ChevronRight, Minus, Plus } from "lucide-react";
import Link from "next/link";

export default function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const productId = Number(id);

  const { data: product, isLoading: productLoading } = useProduct(productId);
  const [values, setValues] = useState<Record<string, string | number>>({});
  const [quantity, setQuantity] = useState(100);

  const handleChange = useCallback((key: string, value: string | number) => {
    setValues((prev) => {
      const next = { ...prev, [key]: value };
      // When primary validity field changes, clear downstream fields
      if (product?.validity?.primary === key) {
        for (const f of product.validity.fields) {
          delete next[f];
        }
      }
      return next;
    });
  }, [product]);

  // Determine if all required fields are filled
  const isComplete = useMemo(() => {
    if (!product) return false;
    return product.fields
      .filter((f) => f.required)
      .every((f) => values[f.key] != null && values[f.key] !== "");
  }, [product, values]);

  const {
    data: quote,
    isLoading: quoteLoading,
    error: quoteError,
  } = useQuote(productId, values, quantity, isComplete);

  // Preview image: use selected model image or first available
  const previewImage = useMemo(() => {
    if (!product) return null;
    for (const field of product.fields) {
      if (field.images) {
        const selectedVal = values[field.key] as string | undefined;
        if (selectedVal && field.images[selectedVal]) return field.images[selectedVal];
        // fallback to first
        const firstKey = Object.keys(field.images)[0];
        if (firstKey) return field.images[firstKey];
      }
    }
    return null;
  }, [product, values]);

  if (productLoading) {
    return (
      <div className="pt-24 pb-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <Skeleton className="h-4 w-48 mb-8" />
        <div className="grid lg:grid-cols-2 gap-10">
          <Skeleton className="aspect-square rounded-2xl" />
          <div className="space-y-4">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-4 w-1/3" />
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="pt-24 pb-20 text-center text-ink-muted">
        Product not found.
      </div>
    );
  }

  const icon = CATEGORY_ICONS[product.category] ?? "🖨️";

  return (
    <div className="pt-20 pb-20 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm text-ink-muted py-4 mb-6">
          <Link href="/" className="hover:text-ink transition-colors">Home</Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <Link href="/products" className="hover:text-ink transition-colors">Products</Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <span className="text-ink font-medium">{product.name}</span>
        </nav>

        <div className="grid lg:grid-cols-2 gap-10 items-start">
          {/* LEFT: Product preview */}
          <div className="lg:sticky lg:top-24">
            <div className="aspect-square rounded-2xl border border-border bg-surface-muted overflow-hidden flex items-center justify-center">
              {previewImage ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={previewImage}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-8xl">{icon}</span>
              )}
            </div>
            <div className="mt-4 p-4 rounded-xl bg-surface-muted border border-border">
              <p className="text-xs text-ink-muted text-center">
                Preview updates as you select options · Actual print may vary slightly
              </p>
            </div>
          </div>

          {/* RIGHT: Configurator + price */}
          <div className="flex flex-col gap-8">
            {/* Header */}
            <div>
              <p className="text-sm text-ink-muted mb-1">{product.category}</p>
              <h1 className="text-3xl font-bold text-ink tracking-tight">
                {product.name}
              </h1>
              {product.pricing_type === "reference" && (
                <p className="text-xs text-amber-600 mt-1">
                  Prices shown are indicative (±5–10% of market rate)
                </p>
              )}
            </div>

            {/* Configurator fields */}
            <div className="bg-white rounded-xl border border-border p-6">
              <h2 className="text-sm font-semibold text-ink mb-6">
                Specifications
              </h2>
              <Configurator
                product={product}
                values={values}
                onChange={handleChange}
              />
            </div>

            {/* Quantity */}
            <div className="bg-white rounded-xl border border-border p-6">
              <h2 className="text-sm font-semibold text-ink mb-4">Quantity</h2>

              {/* Quick chips */}
              <div className="flex flex-wrap gap-2 mb-4">
                {QUICK_QTY.filter(
                  (q) => q >= (product.quantity.min ?? 1)
                ).map((q) => (
                  <button
                    key={q}
                    onClick={() => setQuantity(q)}
                    className={cn(
                      "px-3 py-1.5 rounded-lg border text-sm font-medium transition-all",
                      quantity === q
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-border text-ink-secondary hover:border-brand-300"
                    )}
                  >
                    {q.toLocaleString()}
                  </button>
                ))}
              </div>

              {/* Stepper */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() =>
                    setQuantity((q) =>
                      Math.max(product.quantity.min ?? 1, q - 1)
                    )
                  }
                  className="w-9 h-9 rounded-lg border border-border flex items-center justify-center hover:bg-surface-subtle transition-colors"
                >
                  <Minus className="w-4 h-4 text-ink-secondary" />
                </button>
                <input
                  type="number"
                  value={quantity}
                  min={product.quantity.min ?? 1}
                  onChange={(e) =>
                    setQuantity(Math.max(product.quantity.min ?? 1, Number(e.target.value)))
                  }
                  className="w-24 h-9 rounded-lg border border-border text-center text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
                <button
                  onClick={() => setQuantity((q) => q + 1)}
                  className="w-9 h-9 rounded-lg border border-border flex items-center justify-center hover:bg-surface-subtle transition-colors"
                >
                  <Plus className="w-4 h-4 text-ink-secondary" />
                </button>
                <span className="text-sm text-ink-muted">pcs</span>
              </div>

              {product.quantity.note && (
                <p className="text-xs text-ink-subtle mt-2">
                  {product.quantity.note}
                </p>
              )}
            </div>

            {/* Price panel */}
            <PricePanel
              product={product}
              options={values}
              quantity={quantity}
              quote={quote}
              isLoading={quoteLoading}
              error={quoteError}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
