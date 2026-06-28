"use client";

import { useState, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import type { ProductDetail, ProductField } from "@/lib/pricing-api";

interface ConfiguratorProps {
  product: ProductDetail;
  values: Record<string, string | number>;
  onChange: (key: string, value: string | number) => void;
}

export function Configurator({ product, values, onChange }: ConfiguratorProps) {
  return (
    <div className="flex flex-col gap-6">
      {product.fields.map((field) => (
        <FieldRenderer
          key={field.key}
          field={field}
          product={product}
          values={values}
          onChange={onChange}
        />
      ))}
    </div>
  );
}

function FieldRenderer({
  field,
  product,
  values,
  onChange,
}: {
  field: ProductField;
  product: ProductDetail;
  values: Record<string, string | number>;
  onChange: (key: string, value: string | number) => void;
}) {
  // Compute allowed options via validity cascade
  const allowedOptions = useMemo(() => {
    if (!product.validity) return field.options;
    const { primary, rules } = product.validity;

    // Primary field: always show all its own options
    if (field.key === primary) return field.options;

    const primaryValue = values[primary] as string | undefined;

    // Downstream field: get options from validity rules keyed by primary value
    const ruleForPrimary = primaryValue ? rules[primaryValue] : null;
    const allowedFromRules = ruleForPrimary?.[field.key] ?? null;

    if (field.options) {
      // Static options exist — filter them by validity rules if applicable
      if (!primaryValue || !allowedFromRules) return field.options;
      return field.options.filter((opt) => allowedFromRules.includes(opt));
    }

    // No static options: use validity rules as the option source
    // (field is null-options, driven entirely by the cascade)
    return allowedFromRules ?? [];
  }, [field, product.validity, values]);

  const currentValue = values[field.key] ?? "";

  if (field.type === "number") {
    return (
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-ink-secondary">
          {field.label}
          {field.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <input
          type="number"
          value={currentValue as number}
          min={field.min}
          max={field.max}
          onChange={(e) => onChange(field.key, Number(e.target.value))}
          className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500 w-full max-w-xs"
        />
        {field.min != null && field.max != null && (
          <p className="text-xs text-ink-muted">
            {field.min} – {field.max} mm
          </p>
        )}
      </div>
    );
  }

  // Image picker
  if (field.images && Object.keys(field.images).length > 0) {
    return (
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-ink-secondary">
          {field.label}
          {field.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
          {(allowedOptions ?? []).map((opt) => {
            const imgSrc = field.images![opt];
            const selected = currentValue === opt;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => onChange(field.key, opt)}
                className={cn(
                  "flex flex-col items-center gap-1.5 rounded-lg border-2 p-1.5 transition-all duration-150 text-center",
                  selected
                    ? "border-brand-500 bg-brand-50"
                    : "border-border hover:border-brand-300"
                )}
              >
                {imgSrc ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={imgSrc}
                    alt={opt}
                    className="w-full aspect-square object-cover rounded-md"
                  />
                ) : (
                  <div className="w-full aspect-square bg-surface-subtle rounded-md" />
                )}
                <span className="text-[10px] font-medium text-ink-secondary leading-tight">
                  {opt}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // Plain select
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-ink-secondary">
        {field.label}
        {field.required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <div className="flex flex-wrap gap-2">
        {(allowedOptions ?? []).map((opt) => {
          const selected = currentValue === opt;
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onChange(field.key, opt)}
              className={cn(
                "px-3 py-1.5 rounded-lg border text-sm font-medium transition-all duration-150",
                selected
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-border text-ink-secondary hover:border-brand-300 hover:text-ink"
              )}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}
