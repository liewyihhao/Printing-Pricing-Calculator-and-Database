"use client";

import { useState, useCallback, useMemo, use, useEffect } from "react";
import { useProduct, useQuote, useProductContent } from "@/lib/pricing-api";
import { Configurator } from "@/components/products/Configurator";
import { PricePanel } from "@/components/products/PricePanel";
import { ProductContent } from "@/components/products/ProductContent";
import { Skeleton } from "@/components/ui/skeleton";
import { CATEGORY_ICONS, formatMYR } from "@/lib/utils";
import { ProductPhoto } from "@/components/products/ProductPhoto";
import { ProductBanner } from "@/components/products/ProductBanner";
import {
  resolveDefaults,
  isComplete as engineIsComplete,
  validQuantities,
  defaultQuantity,
} from "@/lib/engine";
import { ChevronRight } from "lucide-react";
import Link from "next/link";

export default function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const productId = Number(id);

  const { data: product, isLoading: productLoading } = useProduct(productId);
  const { data: content } = useProductContent(productId);
  const [values, setValues] = useState<Record<string, string | number>>({});
  const [quantity, setQuantity] = useState(100);

  // On product load, auto-fill defaults + a valid default quantity (mirrors the standalone
  // calculator, which shows a price immediately) so the configurator resolves the full cascade.
  useEffect(() => {
    if (!product) return;
    setValues((prev) => (Object.keys(prev).length ? prev : resolveDefaults(product, {})));
    setQuantity((q) => (validQuantities(product).includes(q) ? q : defaultQuantity(product)));
  }, [product]);

  const handleChange = useCallback((key: string, value: string | number) => {
    setValues((prev) => {
      if (!product) return { ...prev, [key]: value };
      // Set the value, then re-resolve the whole cascade: hidden fields drop out, downstream fields
      // whose allowed set changed snap to a valid default (identical to the standalone calculator).
      return resolveDefaults(product, { ...prev, [key]: value });
    });
  }, [product]);

  // Quotable when every applicable (visible, non-optional, non-number) field has a valid value.
  const isComplete = useMemo(
    () => (product ? engineIsComplete(product, values) : false),
    [product, values]
  );

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

        {/* Wide product hero banner (printoka media) */}
        <ProductBanner id={product.id} alt={product.name} />

        <div className="grid lg:grid-cols-2 gap-10 items-start">
          {/* LEFT: Product preview */}
          <div className="lg:sticky lg:top-24">
            {previewImage ? (
              <div className="aspect-square rounded-xl border border-border bg-surface-muted overflow-hidden flex items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={previewImage} alt={product.name} className="w-full h-full object-cover" />
              </div>
            ) : (
              <ProductPhoto
                id={product.id}
                icon={icon}
                alt={product.name}
                className="aspect-[4/3] rounded-xl border border-border"
              />
            )}
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

            {/* Configurator — fields grouped under Excard's questionnaire sections, Quantity inlined
                into General exactly like the supplier's order form. */}
            <Configurator
              product={product}
              values={values}
              onChange={handleChange}
              quantity={quantity}
              onQuantityChange={setQuantity}
            />

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

        {/* Rich education tabs — Product Spec · Artwork Spec · Templates (from our own catalogue) */}
        {content && <ProductContent content={content} />}
      </div>
    </div>
  );
}
