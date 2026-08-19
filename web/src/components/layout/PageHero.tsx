import Link from "next/link";
import { ChevronRight } from "lucide-react";

/** Branded page header used across the marketing / content pages. */
export function PageHero({
  title,
  subtitle,
  crumb,
}: {
  title: string;
  subtitle?: string;
  crumb?: string;
}) {
  return (
    <section className="bg-surface-muted border-b border-border pt-28 pb-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex items-center gap-1.5 text-sm text-ink-muted mb-4">
          <Link href="/" className="hover:text-ink">Home</Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <span className="text-ink font-medium">{crumb ?? title}</span>
        </nav>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-ink tracking-tight">{title}</h1>
        {subtitle && (
          <p className="mt-3 text-lg text-ink-muted max-w-2xl leading-relaxed">{subtitle}</p>
        )}
      </div>
    </section>
  );
}
