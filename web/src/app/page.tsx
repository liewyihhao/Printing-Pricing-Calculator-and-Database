import type { Metadata } from "next";
import { HeroCarousel } from "@/components/home/HeroCarousel";
import { PopularProducts } from "@/components/home/PopularProducts";
import { HowItWorks } from "@/components/home/HowItWorks";
import { WhyPrintoka } from "@/components/home/WhyPrintoka";
import { Testimonials } from "@/components/home/Testimonials";
import { FAQ } from "@/components/home/FAQ";
import { CTABanner } from "@/components/home/CTABanner";
import { JsonLd } from "@/components/seo/JsonLd";

export const metadata: Metadata = {
  title: "Online Printing Malaysia, Singapore & Brunei — Instant Price, Fast Delivery",
  description:
    "Printoka is your trusted online print shop in Malaysia, Singapore & Brunei. Business cards, flyers, brochures, stickers, banners — configure your specs, see instant pricing, we deliver fast.",
  alternates: { canonical: "https://www.printoka.com" },
  openGraph: {
    title: "Printoka — Online Printing Malaysia, Singapore & Brunei",
    description:
      "50+ print products. Instant live pricing. 48-hour turnaround. Delivered across Malaysia, Singapore & Brunei.",
    url: "https://www.printoka.com",
  },
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Do you deliver to Singapore and Brunei?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes! Printoka ships to Malaysia, Singapore, and Brunei. International shipping rates apply for Singapore and Brunei orders.",
      },
    },
    {
      "@type": "Question",
      name: "How long does printing take?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Most standard products are ready within 48 hours after artwork approval. Delivery adds 1–3 business days depending on your location within Malaysia, Singapore, or Brunei.",
      },
    },
    {
      "@type": "Question",
      name: "Can I see the price before ordering?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes — Printoka shows you live pricing instantly as you configure your product. No need to request a quote; the price updates in real time as you change options and quantity.",
      },
    },
    {
      "@type": "Question",
      name: "What file formats do you accept for artwork?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "We accept PDF, AI, EPS, and high-resolution JPEG/PNG files. All artwork should be at 300 DPI with 3mm bleed. We also offer free artwork templates for download.",
      },
    },
    {
      "@type": "Question",
      name: "Do you offer membership discounts?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes! Printoka has 4 membership tiers: Cash (standard price), Silver (−4%), Gold (−8%), and Platinum (−14%). Prices for all tiers are shown transparently on every product page.",
      },
    },
  ],
};

export default function HomePage() {
  return (
    <>
      <JsonLd data={faqSchema} />
      <HeroCarousel />
      <PopularProducts />
      <HowItWorks />
      <WhyPrintoka />
      <Testimonials />
      <FAQ />
      <CTABanner />
    </>
  );
}
