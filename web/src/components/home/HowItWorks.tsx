import {
  SlidersHorizontal,
  DollarSign,
  Upload,
  Truck,
} from "lucide-react";

const STEPS = [
  {
    icon: SlidersHorizontal,
    step: "01",
    title: "Configure your specs",
    desc: "Choose size, paper, finishing, and quantity. Our smart configurator only shows valid combinations.",
  },
  {
    icon: DollarSign,
    step: "02",
    title: "See the price instantly",
    desc: "Live pricing updates as you configure. No waiting, no quotes — the exact price with all four membership tiers.",
  },
  {
    icon: Upload,
    step: "03",
    title: "Upload or design artwork",
    desc: "Upload your print-ready file or use our online design tool. We validate dimensions, bleed, and resolution automatically.",
  },
  {
    icon: Truck,
    step: "04",
    title: "We print & deliver",
    desc: "Track every stage — artwork check, printing, finishing, packing, and delivery — from your dashboard.",
  },
];

export function HowItWorks() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-widest mb-2">
            How it works
          </p>
          <h2 className="text-3xl font-bold text-ink">
            From idea to doorstep in four steps
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 relative">
          {/* Connector line */}
          <div className="hidden lg:block absolute top-12 left-[12.5%] right-[12.5%] h-px bg-gradient-to-r from-transparent via-brand-200 to-transparent" />

          {STEPS.map(({ icon: Icon, step, title, desc }) => (
            <div key={step} className="relative flex flex-col items-center text-center">
              <div className="relative mb-6">
                <div className="w-24 h-24 rounded-2xl bg-brand-50 border border-brand-100 flex items-center justify-center">
                  <Icon className="w-9 h-9 text-brand-600" />
                </div>
                <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center">
                  {step}
                </div>
              </div>
              <h3 className="text-base font-semibold text-ink mb-2">{title}</h3>
              <p className="text-sm text-ink-muted leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
