import Link from "next/link";
import { Download, FileImage } from "lucide-react";
import { Button } from "@/components/ui/button";

const TEMPLATES = [
  { name: "Business Card (Standard)", size: "90 × 54 mm", formats: ["AI", "PDF", "PSD"] },
  { name: "A5 Flyer", size: "148 × 210 mm", formats: ["AI", "PDF", "PSD"] },
  { name: "A4 Flyer", size: "210 × 297 mm", formats: ["AI", "PDF"] },
  { name: "DL Flyer", size: "99 × 210 mm", formats: ["AI", "PDF"] },
  { name: "A5 Booklet Cover", size: "148 × 210 mm + 3mm bleed", formats: ["AI", "PDF"] },
  { name: "Round Sticker 50mm", size: "50 mm diameter", formats: ["AI", "PDF"] },
];

export default function TemplatesPage() {
  return (
    <div className="pt-24 pb-20 min-h-screen">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-10">
          <h1 className="text-4xl font-bold text-ink mb-2">Artwork templates</h1>
          <p className="text-ink-muted">
            Download print-ready templates with correct dimensions, bleed marks, and safe zones.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          {TEMPLATES.map((tpl) => (
            <div key={tpl.name} className="bg-white rounded-xl border border-border p-5 flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-surface-subtle flex items-center justify-center shrink-0">
                <FileImage className="w-5 h-5 text-ink-muted" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-ink">{tpl.name}</h3>
                <p className="text-xs text-ink-muted mt-0.5">{tpl.size} · 3mm bleed · 300 DPI · CMYK</p>
                <div className="flex gap-2 mt-3">
                  {tpl.formats.map((fmt) => (
                    <button
                      key={fmt}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-md border border-border text-xs font-medium text-ink-secondary hover:border-brand-400 hover:text-brand-700 transition-colors"
                    >
                      <Download className="w-3 h-3" />
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center p-8 rounded-2xl bg-brand-50 border border-brand-100">
          <h2 className="text-lg font-semibold text-ink mb-2">Need a custom size?</h2>
          <p className="text-sm text-ink-muted mb-4">
            Configure your product specs on the product page — we&apos;ll show the exact dimensions
            needed for your artwork.
          </p>
          <Link href="/products">
            <Button>Browse products</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
