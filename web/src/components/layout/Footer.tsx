import Link from "next/link";
import { Mail, Phone, MapPin, MessageCircle, Send, AtSign } from "lucide-react";

const COLUMNS: { heading: string; items: { label: string; href: string }[] }[] = [
  {
    heading: "Products",
    items: [
      { label: "Business Cards", href: "/products/1" },
      { label: "Flyers & Brochures", href: "/products/101" },
      { label: "Stickers & Labels", href: "/products/60" },
      { label: "Booklets", href: "/products/19" },
      { label: "Banners & Buntings", href: "/products/123" },
      { label: "Packaging & Boxes", href: "/products" },
      { label: "All products", href: "/products" },
    ],
  },
  {
    heading: "Support",
    items: [
      { label: "Instant price", href: "/products/1" },
      { label: "Template download", href: "/templates" },
      { label: "Artwork guidelines", href: "/support" },
      { label: "Track your order", href: "/track" },
      { label: "FAQ", href: "/support" },
      { label: "Contact us", href: "/support" },
    ],
  },
  {
    heading: "Company",
    items: [
      { label: "About us", href: "/about" },
      { label: "Membership plans", href: "/membership" },
      { label: "Partners", href: "/partners" },
      { label: "Terms & conditions", href: "/terms" },
    ],
  },
];

const REGIONS = ["Malaysia", "Singapore", "Brunei"];

const CITIES = [
  { slug: "kuala-lumpur", name: "Kuala Lumpur" },
  { slug: "petaling-jaya", name: "Petaling Jaya" },
  { slug: "penang", name: "Penang" },
  { slug: "johor-bahru", name: "Johor Bahru" },
  { slug: "ipoh", name: "Ipoh" },
  { slug: "melaka", name: "Melaka" },
  { slug: "seremban", name: "Seremban" },
  { slug: "kuching", name: "Kuching" },
  { slug: "kota-kinabalu", name: "Kota Kinabalu" },
  { slug: "alor-setar", name: "Alor Setar" },
  { slug: "kuala-terengganu", name: "Kuala Terengganu" },
  { slug: "miri", name: "Miri" },
];

export function Footer() {
  return (
    <footer className="border-t border-border bg-surface-muted mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-10">
          {/* Brand */}
          <div className="col-span-2">
            <Link href="/" className="inline-flex items-center mb-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.png" alt="Printoka" className="h-8 w-auto" />
            </Link>
            <p className="text-sm text-ink-muted leading-relaxed max-w-xs">
              Malaysia&apos;s trusted online printing company. Configure your print,
              see the exact price instantly, and we deliver across Malaysia,
              Singapore &amp; Brunei.
            </p>
            <div className="mt-5 flex flex-col gap-2 text-sm text-ink-muted">
              <a href="mailto:hello@printoka.com" className="flex items-center gap-2 hover:text-ink">
                <Mail className="w-4 h-4 shrink-0" /> hello@printoka.com
              </a>
              <a href="tel:+60123456789" className="flex items-center gap-2 hover:text-ink">
                <Phone className="w-4 h-4 shrink-0" /> +60 12-345 6789
              </a>
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 shrink-0" /> Kuala Lumpur, Malaysia
              </div>
            </div>
            <div className="mt-5 flex items-center gap-2">
              {[MessageCircle, AtSign, Send].map((Icon, n) => (
                <a
                  key={n}
                  href="#"
                  aria-label="Printoka social"
                  className="w-8 h-8 rounded-sm border border-border flex items-center justify-center text-ink-muted hover:text-white hover:bg-brand-500 hover:border-brand-500 transition-colors"
                >
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          {/* Link columns */}
          {COLUMNS.map((col) => (
            <div key={col.heading}>
              <h4 className="text-sm font-semibold text-ink mb-4">{col.heading}</h4>
              <ul className="flex flex-col gap-2.5">
                {col.items.map((item) => (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      className="text-sm text-ink-muted hover:text-brand-500 transition-colors"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {/* Country */}
          <div>
            <h4 className="text-sm font-semibold text-ink mb-4">Country</h4>
            <ul className="flex flex-col gap-2.5">
              {REGIONS.map((r) => (
                <li key={r} className="text-sm text-ink-muted">{r}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Local-SEO city links */}
        <div className="mt-12 pt-8 border-t border-border">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-subtle mb-3">
            Online printing across Malaysia
          </h4>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5">
            {CITIES.map((c) => (
              <Link
                key={c.slug}
                href={`/online-printing/${c.slug}`}
                className="text-xs text-ink-muted hover:text-brand-500 transition-colors"
              >
                Printing {c.name}
              </Link>
            ))}
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-ink-subtle">
          <p>© {new Date().getFullYear()} Printoka. All rights reserved.</p>
          <p>Print. Create. Elevate. — Made in Malaysia 🇲🇾</p>
        </div>
      </div>
    </footer>
  );
}
