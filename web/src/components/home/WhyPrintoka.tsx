import {
  Zap,
  Eye,
  Clock,
  Award,
  HeadphonesIcon,
  RefreshCw,
} from "lucide-react";

const REASONS = [
  {
    icon: Zap,
    title: "Instant live pricing",
    desc: "No forms, no waiting. See the exact price for every configuration as you type, including all four membership tiers.",
  },
  {
    icon: Eye,
    title: "Full transparency",
    desc: "Unit price, total, delivery, tax — all broken down before you pay. No surprise fees at checkout.",
  },
  {
    icon: Clock,
    title: "Fast turnaround",
    desc: "Most orders ship within 3–5 working days. Express options available for urgent jobs.",
  },
  {
    icon: Award,
    title: "Commercial grade quality",
    desc: "The same print production used by professional agencies. CMYK printing on premium substrates.",
  },
  {
    icon: HeadphonesIcon,
    title: "Artwork support",
    desc: "We validate your files automatically and flag any issues before printing begins.",
  },
  {
    icon: RefreshCw,
    title: "Easy reorders",
    desc: "Reorder any past job in two clicks. Your specs are saved; just confirm and checkout.",
  },
];

export function WhyPrintoka() {
  return (
    <section className="py-24 bg-surface-muted">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-widest mb-2">
            Why Printoka
          </p>
          <h2 className="text-3xl font-bold text-ink">
            Printing without the headache
          </h2>
          <p className="text-ink-muted mt-3 max-w-xl mx-auto">
            We&apos;ve automated everything a traditional print shop gets wrong.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {REASONS.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="bg-white rounded-xl border border-border p-6 hover:shadow-card-hover transition-shadow duration-200"
            >
              <div className="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center mb-4">
                <Icon className="w-5 h-5 text-brand-600" />
              </div>
              <h3 className="text-sm font-semibold text-ink mb-1.5">{title}</h3>
              <p className="text-sm text-ink-muted leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
