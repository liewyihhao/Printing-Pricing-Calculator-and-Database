"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const ITEMS = [
  {
    q: "How does live pricing work?",
    a: "As you configure your product (size, paper, quantity, finishing), our system queries the pricing engine in real time. The price updates within milliseconds — no forms to submit, no quotes to wait for.",
  },
  {
    q: "What file formats do you accept?",
    a: "We accept PDF, AI, EPS, PSD, PNG, and JPG. For best results, upload a print-ready PDF with 3mm bleed, CMYK colour mode, and 300 DPI resolution. Our system validates your file automatically and flags any issues.",
  },
  {
    q: "How fast is the turnaround?",
    a: "Most products ship within 3–5 working days after artwork approval. Booklets and packaging take 5–10 working days. Exact lead times are shown on each product page before you order.",
  },
  {
    q: "What are the membership tiers?",
    a: "All customers start at Cash (list price). Silver members get −4%, Gold −8%, and Platinum −14% off every order. Tier upgrades are based on order history. All four prices are shown when you configure a product.",
  },
  {
    q: "Can I reorder a past job?",
    a: "Yes. Every completed order is saved in your account. One click adds the same specs back to your cart — just re-quote (prices may have changed) and checkout.",
  },
  {
    q: "What if my artwork has problems?",
    a: "We automatically check for common issues (insufficient bleed, low resolution, wrong colour mode). If a problem is found, you'll be notified before production starts so you can upload a corrected file.",
  },
  {
    q: "Do you deliver outside Malaysia?",
    a: "Currently we deliver within Peninsular Malaysia and East Malaysia (Sabah & Sarawak). Singapore and Brunei delivery is coming soon.",
  },
];

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-border last:border-0">
      <button
        className="w-full text-left flex items-center justify-between py-5 gap-4"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="text-sm font-semibold text-ink">{q}</span>
        <ChevronDown
          className={cn(
            "w-4 h-4 text-ink-muted shrink-0 transition-transform duration-200",
            open && "rotate-180"
          )}
        />
      </button>
      {open && (
        <p className="text-sm text-ink-muted leading-relaxed pb-5 animate-slide-down">
          {a}
        </p>
      )}
    </div>
  );
}

export function FAQ() {
  return (
    <section className="py-24 bg-surface-muted">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-12">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-widest mb-2">
            FAQ
          </p>
          <h2 className="text-3xl font-bold text-ink">Common questions</h2>
        </div>
        <div className="bg-white rounded-2xl border border-border px-6">
          {ITEMS.map((item) => (
            <FAQItem key={item.q} {...item} />
          ))}
        </div>
      </div>
    </section>
  );
}
