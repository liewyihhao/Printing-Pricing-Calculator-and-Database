"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { ProductSummary, ProductDetail } from "@/lib/pricing-api";
import { fetchProduct, fetchQuote } from "@/lib/pricing-api";
import { formatMYR, CATEGORY_ICONS, LEAD_TIMES } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

function useStartingPrice(product: ProductSummary) {
  // Fetch detail to get first valid config, then quote it
  const detailQuery = useQuery({
    queryKey: ["product", product.id],
    queryFn: () => fetchProduct(product.id),
    staleTime: 1000 * 60 * 10,
  });

  const detail = detailQuery.data as ProductDetail | undefined;

  const priceQuery = useQuery({
    queryKey: ["starting-price", product.id],
    queryFn: async () => {
      if (!detail || product.pricing_type === "contact") return null;
      // Build minimal valid options from first option of each required field
      const options: Record<string, string | number> = {};
      for (const field of detail.fields) {
        if (field.required) {
          if (field.type === "select" && field.options?.[0]) {
            options[field.key] = field.options[0];
          } else if (field.type === "number" && field.min != null) {
            options[field.key] = field.min;
          }
        }
      }
      const qty = detail.quantity.min || 100;
      try {
        const q = await fetchQuote({ product_id: product.id, options, quantity: qty });
        return q.per_unit;
      } catch {
        return null;
      }
    },
    enabled: !!detail && product.pricing_type !== "contact",
    staleTime: 1000 * 60 * 5,
    retry: false,
  });

  return { perUnit: priceQuery.data, loading: detailQuery.isLoading || priceQuery.isLoading };
}

export function ProductCard({ product }: { product: ProductSummary }) {
  const icon = CATEGORY_ICONS[product.category] ?? "🖨️";
  const leadTime = LEAD_TIMES[product.category] ?? "5–7 working days";
  const { perUnit, loading } = useStartingPrice(product);

  return (
    <Link href={`/products/${product.id}`} className="group block">
      <div className="bg-white rounded-xl border border-border p-4 hover:shadow-card-hover hover:border-brand-200 transition-all duration-200 h-full flex flex-col">
        {/* Image / icon area */}
        <div className="aspect-[4/3] rounded-lg bg-surface-muted flex items-center justify-center text-5xl mb-4 group-hover:bg-brand-50 transition-colors">
          {icon}
        </div>

        <div className="flex-1 flex flex-col gap-1.5">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm font-semibold text-ink leading-snug">
              {product.name}
            </h3>
            {product.pricing_type === "contact" && (
              <Badge variant="secondary" className="shrink-0 text-[10px]">
                Quote
              </Badge>
            )}
          </div>

          <p className="text-xs text-ink-muted">{product.category}</p>

          <div className="mt-auto pt-3 flex items-end justify-between">
            <div>
              {product.pricing_type === "contact" ? (
                <span className="text-xs text-ink-muted">Request a quote</span>
              ) : loading ? (
                <Skeleton className="h-4 w-20" />
              ) : perUnit != null ? (
                <span className="text-sm font-semibold text-ink">
                  from {formatMYR(perUnit)}
                  <span className="text-xs text-ink-muted font-normal"> /pc</span>
                </span>
              ) : null}
              <p className="text-[10px] text-ink-subtle mt-0.5">{leadTime}</p>
            </div>
            <ArrowRight className="w-4 h-4 text-ink-subtle group-hover:text-brand-600 group-hover:translate-x-0.5 transition-all" />
          </div>
        </div>
      </div>
    </Link>
  );
}
