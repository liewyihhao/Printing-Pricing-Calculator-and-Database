import type { Metadata } from "next";
import Link from "next/link";
import { PageHero } from "@/components/layout/PageHero";
import { Mail, MessageCircle, FileDown, FileCheck2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Support & Help — Printoka Online Printing",
  description:
    "Get help with your Printoka order: artwork guidelines, template downloads, delivery, file formats and more. Talk to our print experts.",
  alternates: { canonical: "https://www.printoka.com/support" },
};

const FAQS = [
  { q: "Can I see the price before ordering?", a: "Yes — Printoka shows live pricing instantly as you configure. No quotes; the price updates in real time as you change options and quantity." },
  { q: "What file formats do you accept?", a: "PDF, AI, EPS and high-resolution JPEG/PNG at 300 DPI with 3mm bleed. Free artwork templates are available for download." },
  { q: "How long does printing take?", a: "Most standard products are ready within 48 hours after artwork approval. Delivery adds 1–3 business days depending on your location." },
  { q: "Do you deliver to Singapore and Brunei?", a: "Yes. Printoka ships to Malaysia, Singapore and Brunei. International rates apply for Singapore and Brunei orders." },
  { q: "Do you offer membership discounts?", a: "Yes — Silver (−4%), Gold (−8%) and Platinum (−14%) off list price. All tier prices are shown on every product page." },
  { q: "Will you check my artwork?", a: "Our print experts review every file before printing to make sure it's press-ready — we'll flag any issues before you commit." },
];

const HELP = [
  { icon: FileCheck2, title: "Artwork guidelines", body: "Bleed, resolution, colour and file-format requirements for a perfect print." },
  { icon: FileDown, title: "Template download", body: "Free, correctly-sized templates for every product.", href: "/templates" },
  { icon: MessageCircle, title: "Chat with us", body: "Talk to a print expert about anything custom." },
  { icon: Mail, title: "Email support", body: "hello@printoka.com — we reply fast." },
];

export default function SupportPage() {
  return (
    <>
      <PageHero title="Support & help" subtitle="Everything you need for a smooth, press-ready order — and real people when you need them." />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-16">
          {HELP.map(({ icon: Icon, title, body, href }) => {
            const inner = (
              <div className="rounded-lg border border-border bg-white p-5 h-full hover:border-brand-200 hover:shadow-card-hover transition-all">
                <Icon className="w-6 h-6 text-brand-500 mb-3" />
                <h3 className="font-semibold text-ink text-sm mb-1">{title}</h3>
                <p className="text-xs text-ink-muted leading-relaxed">{body}</p>
              </div>
            );
            return href ? <Link key={title} href={href}>{inner}</Link> : <div key={title}>{inner}</div>;
          })}
        </div>

        <h2 className="text-2xl font-bold text-ink mb-6">Frequently asked questions</h2>
        <div className="divide-y divide-border rounded-lg border border-border bg-white">
          {FAQS.map((f) => (
            <details key={f.q} className="group px-5 py-4">
              <summary className="flex items-center justify-between cursor-pointer list-none font-medium text-ink">
                {f.q}
                <span className="text-brand-500 group-open:rotate-45 transition-transform text-xl leading-none">+</span>
              </summary>
              <p className="mt-2.5 text-sm text-ink-muted leading-relaxed">{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </>
  );
}
