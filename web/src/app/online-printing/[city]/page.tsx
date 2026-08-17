import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { JsonLd } from "@/components/seo/JsonLd";
import { Truck, Zap, MapPin } from "lucide-react";

// The cities Printoka targets for local SEO (matches the live sitemap).
const CITIES: Record<string, { name: string; state: string; blurb: string }> = {
  "kuala-lumpur": { name: "Kuala Lumpur", state: "Federal Territory", blurb: "the heart of Malaysia's business district" },
  "petaling-jaya": { name: "Petaling Jaya", state: "Selangor", blurb: "one of Selangor's busiest commercial hubs" },
  "ipoh": { name: "Ipoh", state: "Perak", blurb: "Perak's vibrant state capital" },
  "penang": { name: "Penang", state: "Penang", blurb: "the island's thriving business community" },
  "johor-bahru": { name: "Johor Bahru", state: "Johor", blurb: "the gateway city of southern Malaysia" },
  "melaka": { name: "Melaka", state: "Melaka", blurb: "the historic heart of the south" },
  "alor-setar": { name: "Alor Setar", state: "Kedah", blurb: "the capital of Kedah" },
  "kuala-terengganu": { name: "Kuala Terengganu", state: "Terengganu", blurb: "the east-coast state capital" },
  "seremban": { name: "Seremban", state: "Negeri Sembilan", blurb: "the growing capital of Negeri Sembilan" },
  "kuching": { name: "Kuching", state: "Sarawak", blurb: "the largest city in Sarawak" },
  "miri": { name: "Miri", state: "Sarawak", blurb: "Sarawak's northern resort city" },
  "kota-kinabalu": { name: "Kota Kinabalu", state: "Sabah", blurb: "the coastal capital of Sabah" },
  "malaysia": { name: "Malaysia", state: "", blurb: "businesses nationwide" },
};

const POPULAR = [
  { label: "Business Cards", href: "/products/1" },
  { label: "Flyers & Brochures", href: "/products/101" },
  { label: "Stickers & Labels", href: "/products/60" },
  { label: "Banners", href: "/products/123" },
  { label: "Booklets", href: "/products/19" },
  { label: "Packaging", href: "/products" },
];

export function generateStaticParams() {
  return Object.keys(CITIES).map((city) => ({ city }));
}

export async function generateMetadata({ params }: { params: Promise<{ city: string }> }): Promise<Metadata> {
  const { city } = await params;
  const c = CITIES[city];
  if (!c) return {};
  const where = c.name === "Malaysia" ? "Malaysia" : `${c.name}${c.state ? `, ${c.state}` : ""}`;
  return {
    title: `Online Printing ${where} — Business Cards, Flyers, Stickers | Printoka`,
    description: `Affordable online printing in ${c.name}. Business cards, flyers, brochures, stickers, banners & more with instant live pricing and fast delivery to ${c.name}.`,
    alternates: { canonical: `https://www.printoka.com/online-printing/${city}` },
  };
}

export default async function CityPage({ params }: { params: Promise<{ city: string }> }) {
  const { city } = await params;
  const c = CITIES[city];
  if (!c) notFound();
  const where = c.name === "Malaysia" ? "Malaysia" : `${c.name}${c.state ? `, ${c.state}` : ""}`;

  return (
    <>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "LocalBusiness",
          name: `Printoka Online Printing — ${c.name}`,
          areaServed: c.name,
          url: `https://www.printoka.com/online-printing/${city}`,
          priceRange: "RM",
        }}
      />
      <PageHero
        title={`Online Printing in ${c.name}`}
        crumb={c.name}
        subtitle={`Professional, affordable printing for ${c.blurb}. Configure your job, see the exact price instantly, and we deliver to ${c.name}.`}
      />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid sm:grid-cols-3 gap-6 mb-14">
          {[
            { icon: Zap, t: "Instant live pricing", b: `No quotes — see your exact price the moment you configure, wherever you are in ${c.name}.` },
            { icon: Truck, t: `Fast delivery to ${c.name}`, b: "Scheduled, trackable delivery — even for large, bulky orders." },
            { icon: MapPin, t: "Serving all of Malaysia", b: "From KL to East Malaysia, plus Singapore and Brunei." },
          ].map(({ icon: Icon, t, b }) => (
            <div key={t} className="rounded-lg border border-border bg-white p-6">
              <Icon className="w-6 h-6 text-brand-500 mb-3" />
              <h3 className="font-semibold text-ink text-sm mb-1.5">{t}</h3>
              <p className="text-sm text-ink-muted leading-relaxed">{b}</p>
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-bold text-ink mb-3">Popular prints in {c.name}</h2>
        <p className="text-ink-muted mb-6 max-w-2xl">
          More than 100 products online, all with instant pricing and delivery to {where}.
        </p>
        <div className="flex flex-wrap gap-2.5 mb-14">
          {POPULAR.map((p) => (
            <Link
              key={p.label}
              href={p.href}
              className="px-4 py-2 rounded-sm border border-border text-sm font-medium text-ink-secondary hover:border-brand-300 hover:text-brand-500 transition-colors"
            >
              {p.label}
            </Link>
          ))}
        </div>

        <div className="rounded-xl border border-border bg-surface-muted px-8 py-10 text-center">
          <h2 className="text-2xl font-bold text-ink mb-2">Printing in {c.name}, done right</h2>
          <p className="text-ink-muted mb-6">Get an instant price on any product — no quote needed.</p>
          <Link href="/products"><Button size="lg">Browse all products</Button></Link>
        </div>
      </div>
    </>
  );
}
