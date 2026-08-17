import type { Metadata } from "next";
import Link from "next/link";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Zap, ShieldCheck, Truck, HeartHandshake } from "lucide-react";

export const metadata: Metadata = {
  title: "About Printoka — Malaysia's Online Printing Company",
  description:
    "Printoka is Malaysia's most affordable online printing company. Configure your print, see the exact price instantly, and we deliver across Malaysia, Singapore & Brunei.",
  alternates: { canonical: "https://www.printoka.com/about" },
};

const VALUES = [
  { icon: Zap, title: "Instant, honest pricing", body: "No quotes, no back-and-forth. Configure your job and see the exact price update live — every option, every quantity." },
  { icon: ShieldCheck, title: "Print you can trust", body: "Our print experts check every artwork file from A to Z before it goes to press, so what you approve is what you get." },
  { icon: Truck, title: "Delivered to your door", body: "Scheduled, trackable delivery across Malaysia, Singapore and Brunei — even for large, bulky orders." },
  { icon: HeartHandshake, title: "Service that cares", body: "Responsive, passionate support that treats your project like our own. Corporate credit terms available." },
];

export default function AboutPage() {
  return (
    <>
      <PageHero
        title="Print. Create. Elevate."
        subtitle="Printoka is a modern print & design company built for creators and businesses who value precision, colour and impact — turning ideas into beautifully crafted prints with seamless service."
      />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="prose-none max-w-3xl">
          <h2 className="text-2xl font-bold text-ink mb-4">Malaysia&apos;s most affordable online printing</h2>
          <p className="text-ink-muted leading-relaxed mb-4">
            We started Printoka with one goal: make professional printing effortless and
            transparent. With more than 100 products online — business cards, stickers &amp;
            labels, flyers, brochures, booklets, banners, packaging and more — you can configure
            exactly what you need, see the price the moment you change an option, upload your
            artwork, and let us handle the rest.
          </p>
          <p className="text-ink-muted leading-relaxed">
            No hidden fees, no waiting days for a quote. Just high quality at an affordable price,
            delivered fast across Malaysia, Singapore and Brunei.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-6 mt-14">
          {VALUES.map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-lg border border-border bg-white p-6">
              <div className="w-10 h-10 rounded-sm bg-brand-50 flex items-center justify-center mb-4">
                <Icon className="w-5 h-5 text-brand-500" />
              </div>
              <h3 className="font-semibold text-ink mb-1.5">{title}</h3>
              <p className="text-sm text-ink-muted leading-relaxed">{body}</p>
            </div>
          ))}
        </div>

        <div className="mt-16 rounded-xl printoka-gradient p-[1.5px]">
          <div className="rounded-xl bg-white px-8 py-10 text-center">
            <h2 className="text-2xl font-bold text-ink mb-2">Ready to print something beautiful?</h2>
            <p className="text-ink-muted mb-6">Get an instant price on any product — no quote needed.</p>
            <Link href="/products">
              <Button size="lg">Browse all products</Button>
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
