import Link from "next/link";
import { Package, Mail, Phone, MapPin } from "lucide-react";

const LINKS = {
  Products: [
    { label: "Business Cards", href: "/products?category=Cards+%26+Stationery" },
    { label: "Flyers & Brochures", href: "/products?category=Marketing+%26+Signage" },
    { label: "Stickers", href: "/products?category=Stickers+%26+Labels" },
    { label: "Booklets", href: "/products?category=Books+%26+Pads" },
    { label: "All Products", href: "/products" },
  ],
  Services: [
    { label: "Online Design Tool", href: "/design" },
    { label: "Template Download", href: "/templates" },
    { label: "Artwork Upload", href: "/upload" },
    { label: "Track Order", href: "/track" },
    { label: "Reorder", href: "/account/orders" },
  ],
  Company: [
    { label: "About Us", href: "/about" },
    { label: "Contact", href: "/contact" },
    { label: "Blog", href: "/blog" },
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
  ],
};

export function Footer() {
  return (
    <footer className="border-t border-border bg-surface-muted mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-10">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-4">
              <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
                <Package className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-lg text-ink">Printoka</span>
            </Link>
            <p className="text-sm text-ink-muted leading-relaxed max-w-xs">
              Professional online printing made easy. High quality, fast
              turnaround, delivered to your door across Malaysia.
            </p>
            <div className="mt-6 flex flex-col gap-2.5 text-sm text-ink-muted">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 shrink-0" />
                hello@printoka.com
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 shrink-0" />
                +60 11-1234 5678
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 shrink-0" />
                Kuala Lumpur, Malaysia
              </div>
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(LINKS).map(([heading, items]) => (
            <div key={heading}>
              <h4 className="text-sm font-semibold text-ink mb-4">{heading}</h4>
              <ul className="flex flex-col gap-2.5">
                {items.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="text-sm text-ink-muted hover:text-ink transition-colors"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-subtle">
          <p>© {new Date().getFullYear()} Printoka. All rights reserved.</p>
          <p>Made with care in Malaysia 🇲🇾</p>
        </div>
      </div>
    </footer>
  );
}
