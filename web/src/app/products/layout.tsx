import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "All Print Products — Business Cards, Flyers, Stickers & More",
  description:
    "Browse 50+ print products available online in Malaysia, Singapore & Brunei. Instant live pricing on business cards, flyers, brochures, stickers, banners, booklets and more.",
  keywords: [
    "print products Malaysia", "online printing catalogue", "business card printing",
    "flyer printing Malaysia", "sticker printing", "banner printing Malaysia",
    "brochure printing Singapore", "namecard printing Brunei",
  ],
  alternates: { canonical: "https://www.printoka.com/products" },
  openGraph: {
    title: "All Print Products | Printoka",
    description: "50+ products. Instant pricing. Malaysia, Singapore & Brunei.",
    url: "https://www.printoka.com/products",
  },
};

export default function ProductsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
