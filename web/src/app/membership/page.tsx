import type { Metadata } from "next";
import Link from "next/link";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";

export const metadata: Metadata = {
  title: "Membership Plans — Printoka Member Pricing",
  description:
    "Unlock exclusive member pricing with Printoka. Silver −4%, Gold −8% and Platinum −14% off every order, plus corporate credit terms. See transparent tier pricing on every product.",
  alternates: { canonical: "https://www.printoka.com/membership" },
};

const TIERS = [
  { name: "Cash", discount: "List price", note: "Standard pricing, no membership required.", featured: false,
    perks: ["Instant live pricing", "All 100+ products", "Nationwide delivery"] },
  { name: "Silver", discount: "−4%", note: "For regular buyers.", featured: false,
    perks: ["Everything in Cash", "4% off every order", "Priority artwork checks"] },
  { name: "Gold", discount: "−8%", note: "Our most popular tier.", featured: true,
    perks: ["Everything in Silver", "8% off every order", "Dedicated print expert"] },
  { name: "Platinum", discount: "−14%", note: "For high-volume & corporate.", featured: false,
    perks: ["Everything in Gold", "14% off every order", "Corporate credit terms"] },
];

export default function MembershipPage() {
  return (
    <>
      <PageHero
        title="Membership plans"
        subtitle="Exclusive member pricing on every order — the more you print, the more you save. Every tier's price is shown transparently on each product page."
      />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {TIERS.map((t) => (
            <div
              key={t.name}
              className={t.featured
                ? "rounded-xl border-2 border-brand-500 bg-white p-6 relative shadow-card"
                : "rounded-xl border border-border bg-white p-6"}
            >
              {t.featured && (
                <span className="absolute -top-3 left-6 bg-brand-500 text-white text-[11px] font-semibold px-2.5 py-1 rounded-sm">
                  Most popular
                </span>
              )}
              <h3 className="font-semibold text-ink">{t.name}</h3>
              <div className="mt-2 text-3xl font-extrabold text-ink tracking-tight">
                {t.discount}
              </div>
              <p className="text-sm text-ink-muted mt-1 mb-5">{t.note}</p>
              <ul className="flex flex-col gap-2.5">
                {t.perks.map((p) => (
                  <li key={p} className="flex items-start gap-2 text-sm text-ink-secondary">
                    <Check className="w-4 h-4 text-brand-500 shrink-0 mt-0.5" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <p className="text-center text-sm text-ink-muted mt-8">
          Tier eligibility and corporate credit terms are subject to application.
        </p>

        <div className="mt-14 text-center">
          <Link href="/products/1">
            <Button size="lg">See tier pricing on a product</Button>
          </Link>
        </div>
      </div>
    </>
  );
}
