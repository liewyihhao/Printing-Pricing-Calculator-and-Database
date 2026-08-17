"use client";

import { useState } from "react";
import { useCartStore } from "@/stores/cart";
import { useCreateOrder } from "@/lib/pricing-api";
import { formatMYR, computeDelivery } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowRight, Check, CreditCard, Lock, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import Link from "next/link";

const STEPS = ["Cart", "Address", "Shipping", "Payment", "Confirm"];

export default function CheckoutPage() {
  const router = useRouter();
  const { items, subtotal, clearCart } = useCartStore();
  const createOrder = useCreateOrder();
  const [step, setStep] = useState(1);
  const [address, setAddress] = useState({
    name: "",
    email: "",
    phone: "",
    line1: "",
    line2: "",
    city: "",
    state: "",
    postcode: "",
  });

  const sub = subtotal();
  const totalWeight = items.reduce((s, i) => s + (i.quote?.weight_kg ?? 0), 0);
  const delivery = computeDelivery(totalWeight);
  const grand = sub + delivery;

  const addressComplete =
    address.name.trim() &&
    address.email.trim() &&
    address.phone.trim() &&
    address.line1.trim() &&
    address.city.trim() &&
    address.state.trim() &&
    address.postcode.trim();

  const handleContinueToShipping = () => {
    if (!addressComplete) {
      toast.error("Please fill in all required delivery details.");
      return;
    }
    setStep(2);
  };

  const handlePlaceOrder = async () => {
    if (items.length === 0) {
      router.push("/cart");
      return;
    }
    try {
      const res = await createOrder.mutateAsync({
        items: items.map((i) => ({
          product_id: i.productId,
          product_name: i.productName,
          options: i.options,
          quantity: i.quantity,
          unit_price: i.quote?.per_unit ?? null,
          cash: i.quote?.cash ?? null,
          weight_kg: i.quote?.weight_kg ?? null,
        })),
        contact: {
          name: address.name,
          email: address.email,
          phone: address.phone,
        },
        delivery: {
          line1: address.line1,
          line2: address.line2,
          city: address.city,
          state: address.state,
          postcode: address.postcode,
          method: "Standard courier (J&T / Pos Laju)",
        },
        totals: {
          subtotal: sub,
          delivery_fee: delivery,
          grand_total: grand,
        },
      });
      clearCart();
      toast.success("Order placed! Reference " + res.order_ref);
      router.push("/order-success?order=" + encodeURIComponent(res.order_ref));
    } catch {
      toast.error("Could not place your order. Please try again.");
    }
  };

  if (items.length === 0) {
    return (
      <div className="pt-24 pb-20 min-h-screen flex flex-col items-center justify-center gap-6 text-center">
        <div>
          <h1 className="text-2xl font-bold text-ink mb-2">Your cart is empty</h1>
          <p className="text-ink-muted">Add a product before checking out.</p>
        </div>
        <Link href="/products">
          <Button size="lg">Browse products</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <h1 className="text-3xl font-bold text-ink mb-8">Checkout</h1>

        {/* Progress */}
        <div className="flex items-center gap-0 mb-10">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center flex-1 last:flex-none">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${
                  i < step
                    ? "bg-brand-600 text-white"
                    : i === step
                    ? "bg-brand-100 text-brand-700 border-2 border-brand-600"
                    : "bg-surface-subtle text-ink-subtle"
                }`}
              >
                {i < step ? <Check className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span
                className={`ml-1.5 text-xs font-medium hidden sm:block ${
                  i <= step ? "text-ink" : "text-ink-subtle"
                }`}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-px mx-2 ${
                    i < step ? "bg-brand-400" : "bg-border"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="grid sm:grid-cols-5 gap-8">
          {/* Form */}
          <div className="sm:col-span-3 bg-white rounded-xl border border-border p-6">
            {step === 1 && (
              <div>
                <h2 className="font-semibold text-ink mb-4">Delivery address</h2>
                <div className="flex flex-col gap-4">
                  <Input label="Full name" required value={address.name} onChange={e => setAddress(p => ({ ...p, name: e.target.value }))} />
                  <Input label="Email address" type="email" required value={address.email} onChange={e => setAddress(p => ({ ...p, email: e.target.value }))} />
                  <Input label="Phone number" required value={address.phone} onChange={e => setAddress(p => ({ ...p, phone: e.target.value }))} />
                  <Input label="Address line 1" required value={address.line1} onChange={e => setAddress(p => ({ ...p, line1: e.target.value }))} />
                  <Input label="Address line 2" value={address.line2} onChange={e => setAddress(p => ({ ...p, line2: e.target.value }))} />
                  <div className="grid grid-cols-2 gap-4">
                    <Input label="City" required value={address.city} onChange={e => setAddress(p => ({ ...p, city: e.target.value }))} />
                    <Input label="Postcode" required value={address.postcode} onChange={e => setAddress(p => ({ ...p, postcode: e.target.value }))} />
                  </div>
                  <Input label="State" required value={address.state} onChange={e => setAddress(p => ({ ...p, state: e.target.value }))} />
                </div>
                <Button className="mt-6 w-full gap-2" onClick={handleContinueToShipping}>
                  Continue to shipping <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
            )}

            {step === 2 && (
              <div>
                <h2 className="font-semibold text-ink mb-4">Shipping method</h2>
                <div className="rounded-lg border-2 border-brand-500 bg-brand-50 p-4">
                  <div className="flex justify-between text-sm font-medium text-brand-700">
                    <span>Standard courier (J&T / Pos Laju)</span>
                    <span>{formatMYR(delivery)}</span>
                  </div>
                  <p className="text-xs text-brand-600 mt-1">2–4 working days after dispatch</p>
                </div>
                <Button className="mt-6 w-full gap-2" onClick={() => setStep(3)}>
                  Continue to payment <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
            )}

            {step === 3 && (
              <div>
                <h2 className="font-semibold text-ink mb-4">Payment</h2>
                <div className="flex flex-col gap-3">
                  {["Credit / Debit Card", "FPX Online Banking", "E-wallet (TNG / GrabPay)"].map((method) => (
                    <label key={method} className="flex items-center gap-3 p-4 rounded-lg border border-border cursor-pointer hover:border-brand-300 transition-colors">
                      <input type="radio" name="payment" className="accent-brand-600" defaultChecked={method.includes("Card")} />
                      <CreditCard className="w-4 h-4 text-ink-muted" />
                      <span className="text-sm font-medium text-ink">{method}</span>
                    </label>
                  ))}
                </div>
                <div className="mt-4 p-4 rounded-lg bg-surface-muted border border-border">
                  <p className="text-xs text-ink-muted flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5" /> Payments are processed securely. We never store card details.
                  </p>
                </div>
                <Button
                  className="mt-6 w-full gap-2"
                  onClick={handlePlaceOrder}
                  disabled={createOrder.isPending}
                >
                  {createOrder.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Placing order…
                    </>
                  ) : (
                    <>
                      Place order · {formatMYR(grand)}
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>

          {/* Order summary */}
          <div className="sm:col-span-2">
            <div className="bg-white rounded-xl border border-border p-5 sticky top-24">
              <h3 className="text-sm font-semibold text-ink mb-4">Order summary</h3>
              <div className="flex flex-col gap-2.5 text-sm divide-y divide-border">
                {items.map((item) => (
                  <div key={item.id} className="flex justify-between pt-2.5 first:pt-0">
                    <span className="text-ink-secondary truncate max-w-[150px]">
                      {item.productName} ×{item.quantity}
                    </span>
                    <span className="price-display text-ink shrink-0">
                      {formatMYR(item.quote?.cash ?? 0)}
                    </span>
                  </div>
                ))}
                <div className="flex justify-between pt-2.5 text-ink-muted">
                  <span>Delivery</span>
                  <span className="price-display">{formatMYR(delivery)}</span>
                </div>
                <div className="flex justify-between pt-2.5 font-semibold text-ink">
                  <span>Total</span>
                  <span className="price-display">{formatMYR(grand)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
