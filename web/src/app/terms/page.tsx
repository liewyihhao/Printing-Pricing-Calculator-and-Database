import type { Metadata } from "next";
import { PageHero } from "@/components/layout/PageHero";

export const metadata: Metadata = {
  title: "Terms & Conditions — Printoka",
  description: "Printoka's terms and conditions covering orders, pricing, artwork, production, delivery, and returns.",
  alternates: { canonical: "https://www.printoka.com/terms" },
};

const SECTIONS = [
  { h: "Orders & pricing", p: "Prices shown are calculated live from your selected specifications and quantity, in Malaysian Ringgit (RM), and are inclusive of the applicable membership tier discount where shown. An order is confirmed once payment (or approved credit terms) and print-ready artwork are received." },
  { h: "Artwork", p: "You are responsible for the content and correctness of files you supply. We check artwork for print-readiness (bleed, resolution, colour, dimensions) and will flag issues, but final approval rests with you. Supply files as PDF/AI/EPS or high-resolution JPEG/PNG at 300 DPI with 3mm bleed." },
  { h: "Production & turnaround", p: "Standard turnaround is typically 48 hours after artwork approval; finishing, custom and large-format products may take longer. Timelines begin only after artwork is approved and payment is confirmed." },
  { h: "Delivery", p: "We deliver across Malaysia, Singapore and Brunei. Delivery estimates are provided at checkout based on weight and destination; international orders may be subject to duties and taxes." },
  { h: "Colour & variation", p: "Printed colours may vary slightly from on-screen previews due to differences in monitors, materials and printing processes. Minor variation is inherent to printing and is not considered a defect." },
  { h: "Returns & reprints", p: "Because products are custom-produced to your specification, we reprint or refund only where an order does not match the approved specification or artwork due to a production error on our part. Contact us within 7 days of delivery." },
];

export default function TermsPage() {
  return (
    <>
      <PageHero title="Terms & conditions" crumb="Terms" subtitle="The terms that apply when you order from Printoka." />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="flex flex-col gap-8">
          {SECTIONS.map((s, i) => (
            <section key={s.h}>
              <h2 className="text-lg font-bold text-ink mb-2">{i + 1}. {s.h}</h2>
              <p className="text-ink-muted leading-relaxed">{s.p}</p>
            </section>
          ))}
        </div>
        <p className="text-xs text-ink-subtle mt-12">
          This summary is provided for convenience and may be updated from time to time. For the full
          terms applicable to your order, contact Printoka support.
        </p>
      </div>
    </>
  );
}
