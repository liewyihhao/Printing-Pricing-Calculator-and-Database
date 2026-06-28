import { Star } from "lucide-react";

const TESTIMONIALS = [
  {
    name: "Ahmad Razif",
    company: "Razif Creative Studio",
    body: "Finally an online print shop that gives real pricing upfront. No more emailing back and forth for quotes. Printoka saves me hours every week.",
    rating: 5,
    avatar: "AR",
  },
  {
    name: "Priya Nair",
    company: "Priya Events KL",
    body: "Ordered 2,000 flyers and 500 business cards. Delivered in 4 days, quality is excellent. The live configurator is incredibly easy to use.",
    rating: 5,
    avatar: "PN",
  },
  {
    name: "Lee Wei Xian",
    company: "WX Marketing",
    body: "The Gold tier discount pays for itself. Great value, predictable pricing, and reorders are instant. My go-to print supplier now.",
    rating: 5,
    avatar: "LW",
  },
  {
    name: "Nurul Hana",
    company: "Hana Stationery",
    body: "The artwork validation is a lifesaver — it caught a bleed issue before printing. Saved a whole reprint run. Would recommend to any business owner.",
    rating: 5,
    avatar: "NH",
  },
];

export function Testimonials() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-widest mb-2">
            Testimonials
          </p>
          <h2 className="text-3xl font-bold text-ink">
            Trusted by businesses across Malaysia
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {TESTIMONIALS.map(({ name, company, body, rating, avatar }) => (
            <div
              key={name}
              className="bg-surface-muted rounded-xl border border-border p-6 flex flex-col gap-4"
            >
              {/* Stars */}
              <div className="flex gap-0.5">
                {Array.from({ length: rating }).map((_, i) => (
                  <Star
                    key={i}
                    className="w-4 h-4 fill-amber-400 text-amber-400"
                  />
                ))}
              </div>
              <p className="text-sm text-ink-secondary leading-relaxed flex-1">
                &ldquo;{body}&rdquo;
              </p>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center shrink-0">
                  {avatar}
                </div>
                <div>
                  <div className="text-sm font-semibold text-ink">{name}</div>
                  <div className="text-xs text-ink-muted">{company}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
