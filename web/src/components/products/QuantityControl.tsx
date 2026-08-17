"use client";

import { Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProductDetail } from "@/lib/pricing-api";
import { validQuantities, moq } from "@/lib/engine";

/** Quantity field — rendered INSIDE the configurator's General section, matching how Excard groups
 *  Quantity in the questionnaire. Snaps to the product's real order ladder (moq / options). */
export function QuantityControl({
  product,
  quantity,
  onChange,
}: {
  product: ProductDetail;
  quantity: number;
  onChange: (q: number) => void;
}) {
  const qtyOptions = validQuantities(product);
  const idx = qtyOptions.indexOf(quantity);
  const stepTo = (target: number) => {
    if (qtyOptions.length) {
      onChange(qtyOptions.reduce((a, b) => (Math.abs(b - target) < Math.abs(a - target) ? b : a)));
    } else {
      onChange(Math.max(moq(product), target));
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-ink-secondary">
        Quantity<span className="text-brand-500 ml-0.5">*</span>
      </label>
      <div className="flex flex-wrap gap-2">
        {(qtyOptions.length ? qtyOptions.slice(0, 12) : [moq(product)]).map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onChange(q)}
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
      <div className="flex items-center gap-3 mt-1">
        <button
          type="button"
          onClick={() => (qtyOptions.length ? onChange(qtyOptions[Math.max(0, idx - 1)] ?? quantity) : stepTo(quantity - 1))}
          className="w-9 h-9 rounded-lg border border-border flex items-center justify-center hover:bg-surface-subtle transition-colors"
        >
          <Minus className="w-4 h-4 text-ink-secondary" />
        </button>
        <input
          type="number"
          value={quantity}
          min={moq(product)}
          onChange={(e) => stepTo(Number(e.target.value))}
          className="w-24 h-9 rounded-lg border border-border text-center text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          type="button"
          onClick={() => (qtyOptions.length ? onChange(qtyOptions[Math.min(qtyOptions.length - 1, idx + 1)] ?? quantity) : stepTo(quantity + 1))}
          className="w-9 h-9 rounded-lg border border-border flex items-center justify-center hover:bg-surface-subtle transition-colors"
        >
          <Plus className="w-4 h-4 text-ink-secondary" />
        </button>
        <span className="text-sm text-ink-muted">pcs</span>
      </div>
      {product.quantity.note && (
        <p className="text-xs text-ink-subtle">{product.quantity.note}</p>
      )}
    </div>
  );
}
