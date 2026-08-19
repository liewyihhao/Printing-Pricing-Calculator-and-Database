"use client";

import { useState } from "react";
import type { ProductDetail } from "@/lib/pricing-api";
import { validQuantities, moq } from "@/lib/engine";

/** Quantity field — label-left + native <select> of the supplier's standard order quantities,
 *  matching Excard's classic order form. Products that accept an arbitrary quantity also get a
 *  "Custom…" option that reveals a number input. */
export function QuantityControl({
  product,
  quantity,
  onChange,
  hideLabel = false,
}: {
  product: ProductDetail;
  quantity: number;
  onChange: (q: number) => void;
  hideLabel?: boolean;
}) {
  const qtyOptions = validQuantities(product);
  const minQ = moq(product);
  const allowCustom = product.quantity.custom !== false || qtyOptions.length === 0;
  const inList = qtyOptions.includes(quantity);
  const [custom, setCustom] = useState(!inList && qtyOptions.length > 0);

  const showInput = qtyOptions.length === 0 || custom || !inList;

  const control = (
    <div className="flex flex-col gap-1.5">
      {qtyOptions.length > 0 && (
        <select
          id="f-quantity"
          value={inList && !custom ? String(quantity) : "__custom"}
          onChange={(e) => {
            if (e.target.value === "__custom") {
              setCustom(true);
            } else {
              setCustom(false);
              onChange(Number(e.target.value));
            }
          }}
          className="h-10 rounded-md border border-border bg-white px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500 w-full cursor-pointer"
        >
          {qtyOptions.map((q) => (
            <option key={q} value={q}>
              {q.toLocaleString()} pcs
            </option>
          ))}
          {allowCustom && <option value="__custom">Custom quantity…</option>}
        </select>
      )}
      {showInput && (
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={quantity}
            min={minQ}
            onChange={(e) => onChange(Math.max(minQ, Number(e.target.value) || minQ))}
            className="h-10 w-32 rounded-md border border-border bg-white px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <span className="text-sm text-ink-muted">pcs</span>
        </div>
      )}
      {product.quantity.note && (
        <p className="text-xs text-ink-subtle">{product.quantity.note}</p>
      )}
    </div>
  );

  if (hideLabel) return control;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,190px)_1fr] sm:items-start gap-1.5 sm:gap-4">
      <label htmlFor="f-quantity" className="text-sm font-medium text-ink-secondary sm:pt-2">
        Quantity<span className="text-red-500 ml-0.5">*</span>
      </label>
      {control}
    </div>
  );
}
