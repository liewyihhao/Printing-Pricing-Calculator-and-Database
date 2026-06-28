"use client";

import { useCartStore, type CartItem } from "@/stores/cart";
import { formatMYR, computeDelivery } from "@/lib/utils";
import { Trash2, ShoppingBag, ArrowRight, RefreshCw } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useQuote } from "@/lib/pricing-api";

function CartItemRow({ item }: { item: CartItem }) {
  const { updateItem, removeItem } = useCartStore();

  const { data: freshQuote, isLoading } = useQuote(
    item.productId,
    item.options,
    item.quantity,
    true
  );

  // Sync fresh quote into cart
  if (freshQuote && freshQuote.cash !== item.quote?.cash) {
    updateItem(item.id, { quote: freshQuote });
  }

  const price = freshQuote?.cash ?? item.quote?.cash ?? 0;

  return (
    <div className="flex items-start gap-4 py-5 border-b border-border last:border-0">
      <div className="w-16 h-16 rounded-lg bg-surface-muted flex items-center justify-center text-2xl shrink-0">
        🖨️
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <Link
              href={`/products/${item.productId}`}
              className="text-sm font-semibold text-ink hover:text-brand-600 transition-colors"
            >
              {item.productName}
            </Link>
            <p className="text-xs text-ink-muted mt-0.5">
              {Object.entries(item.options)
                .map(([k, v]) => `${v}`)
                .join(" · ")}
            </p>
            <p className="text-xs text-ink-subtle mt-0.5">
              Qty: {item.quantity.toLocaleString()} pcs
            </p>
          </div>
          <div className="text-right shrink-0">
            {isLoading ? (
              <div className="h-5 w-20 shimmer rounded" />
            ) : (
              <span className="text-sm font-semibold text-ink price-display">
                {formatMYR(price)}
              </span>
            )}
            {freshQuote && item.quote && freshQuote.cash !== item.quote.cash && (
              <p className="text-xs text-amber-600 flex items-center gap-1 mt-0.5">
                <RefreshCw className="w-3 h-3" /> Price updated
              </p>
            )}
          </div>
        </div>
      </div>
      <button
        onClick={() => removeItem(item.id)}
        className="p-2 text-ink-subtle hover:text-red-600 transition-colors rounded-lg hover:bg-red-50"
        aria-label="Remove item"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
}

export default function CartPage() {
  const { items, subtotal } = useCartStore();
  const sub = subtotal();
  const totalWeight = items.reduce(
    (sum, i) => sum + (i.quote?.weight_kg ?? 0),
    0
  );
  const delivery = computeDelivery(totalWeight);
  const grand = sub + delivery;

  if (items.length === 0) {
    return (
      <div className="pt-24 pb-20 min-h-screen flex flex-col items-center justify-center gap-6 text-center">
        <ShoppingBag className="w-16 h-16 text-ink-subtle" />
        <div>
          <h1 className="text-2xl font-bold text-ink mb-2">Your cart is empty</h1>
          <p className="text-ink-muted">Add some products to get started.</p>
        </div>
        <Link href="/products">
          <Button size="lg">Browse products</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-ink mb-8">Your cart</h1>

        <div className="grid lg:grid-cols-3 gap-8 items-start">
          {/* Items */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-border px-6">
            {items.map((item) => (
              <CartItemRow key={item.id} item={item} />
            ))}
          </div>

          {/* Summary */}
          <div className="bg-white rounded-xl border border-border p-6 flex flex-col gap-4">
            <h2 className="text-base font-semibold text-ink">Order summary</h2>

            <div className="space-y-2.5 text-sm">
              <div className="flex justify-between text-ink-muted">
                <span>Subtotal ({items.length} item{items.length !== 1 ? "s" : ""})</span>
                <span className="price-display">{formatMYR(sub)}</span>
              </div>
              <div className="flex justify-between text-ink-muted">
                <span>Estimated delivery ({totalWeight.toFixed(2)} kg)</span>
                <span className="price-display">{formatMYR(delivery)}</span>
              </div>
              <div className="flex justify-between font-semibold text-ink pt-2 border-t border-border">
                <span>Total</span>
                <span className="price-display">{formatMYR(grand)}</span>
              </div>
            </div>

            <Link href="/checkout">
              <Button size="lg" className="w-full rounded-xl gap-2">
                Proceed to checkout
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>

            <p className="text-xs text-ink-subtle text-center">
              Prices re-quoted live. Final amount confirmed at checkout.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
