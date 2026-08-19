import type { Metadata } from "next";
import Link from "next/link";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Percent, Palette, Building2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Partner with Printoka — Reseller & Corporate Printing",
  description:
    "Partner with Printoka for reseller pricing, white-label printing and corporate credit terms. Designers, agencies and businesses print more and earn more.",
  alternates: { canonical: "https://www.printoka.com/partners" },
};

const REASONS = [
  { icon: Percent, title: "Reseller pricing", body: "Member tiers up to −14%, so you keep a healthy margin on every job you pass through." },
  { icon: Palette, title: "For designers & agencies", body: "Reliable print quality and artwork checks so the work you deliver looks exactly as designed." },
  { icon: Building2, title: "Corporate credit terms", body: "Consolidated billing and credit terms for high-volume corporate accounts (subject to application)." },
];

export default function PartnersPage() {
  return (
    <>
      <PageHero
        title="Partner with Printoka"
        subtitle="Designers, agencies and businesses trust Printoka as their print partner — dependable quality, honest pricing and service that makes you look good."
      />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid sm:grid-cols-3 gap-6">
          {REASONS.map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-lg border border-border bg-white p-6">
              <div className="w-10 h-10 rounded-sm bg-brand-50 flex items-center justify-center mb-4">
                <Icon className="w-5 h-5 text-brand-500" />
              </div>
              <h3 className="font-semibold text-ink mb-1.5">{title}</h3>
              <p className="text-sm text-ink-muted leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
        <div className="mt-14 rounded-xl border border-border bg-surface-muted px-8 py-10 text-center">
          <h2 className="text-2xl font-bold text-ink mb-2">Let&apos;s grow together</h2>
          <p className="text-ink-muted mb-6 max-w-xl mx-auto">
            Tell us about your business and we&apos;ll set you up with the right partner plan.
          </p>
          <Link href="/support"><Button size="lg">Get in touch</Button></Link>
        </div>
      </div>
    </>
  );
}
