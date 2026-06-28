import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/providers";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { JsonLd, organizationSchema, websiteSchema, localBusinessSchema } from "@/components/seo/JsonLd";

const SITE_URL = "https://www.printoka.com";
const SITE_NAME = "Printoka";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Printoka — Online Printing Malaysia, Singapore & Brunei | Instant Pricing",
    template: "%s | Printoka Online Printing",
  },
  description:
    "Professional online printing in Malaysia, Singapore & Brunei. Business cards, flyers, brochures, stickers, banners & more. Instant live pricing, 48-hour turnaround, nationwide delivery.",
  keywords: [
    // Core service
    "online printing", "printing services", "custom printing", "print online",
    // Products
    "business card printing", "flyer printing", "brochure printing", "sticker printing",
    "banner printing", "booklet printing", "namecard printing", "letterhead printing",
    // Malaysia
    "online printing Malaysia", "printing Malaysia", "percetakan online Malaysia",
    "cetak online Malaysia", "printing KL", "printing Kuala Lumpur", "printing Selangor",
    "printing Penang", "printing Johor", "cheap printing Malaysia",
    "business card printing Malaysia", "flyer printing Malaysia",
    // Singapore
    "printing Singapore", "online printing Singapore", "business card printing Singapore",
    "flyer printing Singapore", "cheap printing Singapore", "printing services Singapore",
    // Brunei
    "printing Brunei", "online printing Brunei", "printing Brunei Darussalam",
    "business card printing Brunei",
    // Brand
    "Printoka", "printoka.com",
  ],
  authors: [{ name: "Printoka", url: SITE_URL }],
  creator: "Printoka",
  publisher: "Printoka",
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    type: "website",
    locale: "en_MY",
    alternateLocale: ["en_SG", "ms_MY"],
    url: SITE_URL,
    siteName: SITE_NAME,
    title: "Printoka — Online Printing Malaysia, Singapore & Brunei",
    description:
      "Instant live pricing on 50+ print products. Business cards, flyers, stickers, banners & more. Fast turnaround, delivered to Malaysia, Singapore & Brunei.",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "Printoka — Professional Online Printing",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Printoka — Online Printing Malaysia, Singapore & Brunei",
    description: "Instant pricing on 50+ print products. 48-hour turnaround.",
    images: ["/og-image.jpg"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  verification: {
    // Add Google Search Console / Bing verification codes here when available
    // google: "your-verification-code",
  },
  category: "business",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full scroll-smooth">
      <head>
        <JsonLd data={organizationSchema} />
        <JsonLd data={websiteSchema} />
        <JsonLd data={localBusinessSchema} />
        <meta name="geo.region" content="MY" />
        <meta name="geo.placename" content="Malaysia" />
        <link rel="alternate" hrefLang="en-my" href="https://www.printoka.com" />
        <link rel="alternate" hrefLang="en-sg" href="https://www.printoka.com" />
        <link rel="alternate" hrefLang="en-bn" href="https://www.printoka.com" />
        <link rel="alternate" hrefLang="x-default" href="https://www.printoka.com" />
      </head>
      <body className="min-h-full flex flex-col antialiased">
        <Providers>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
