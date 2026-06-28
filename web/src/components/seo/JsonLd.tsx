export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

const SITE_URL = "https://www.printoka.com";

export const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Printoka",
  url: SITE_URL,
  logo: `${SITE_URL}/logo.png`,
  description:
    "Professional online printing services in Malaysia, Singapore and Brunei. Business cards, flyers, brochures, stickers, banners and more.",
  contactPoint: {
    "@type": "ContactPoint",
    contactType: "customer service",
    availableLanguage: ["English", "Malay"],
    areaServed: ["MY", "SG", "BN"],
  },
  areaServed: [
    { "@type": "Country", name: "Malaysia" },
    { "@type": "Country", name: "Singapore" },
    { "@type": "Country", name: "Brunei" },
  ],
  sameAs: [],
};

export const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "Printoka",
  url: SITE_URL,
  description: "Online printing services in Malaysia, Singapore and Brunei",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: `${SITE_URL}/products?search={search_term_string}`,
    },
    "query-input": "required name=search_term_string",
  },
};

export const localBusinessSchema = {
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "@id": `${SITE_URL}/#business`,
  name: "Printoka",
  url: SITE_URL,
  description:
    "Online print shop serving Malaysia, Singapore and Brunei. Instant pricing, fast turnaround, delivered to your door.",
  priceRange: "RM",
  currenciesAccepted: "MYR, SGD",
  paymentAccepted: "Credit Card, Online Transfer",
  areaServed: [
    { "@type": "Country", name: "Malaysia" },
    { "@type": "Country", name: "Singapore" },
    { "@type": "Country", name: "Brunei Darussalam" },
  ],
  hasOfferCatalog: {
    "@type": "OfferCatalog",
    name: "Print Products",
    itemListElement: [
      { "@type": "Offer", itemOffered: { "@type": "Service", name: "Business Card Printing" } },
      { "@type": "Offer", itemOffered: { "@type": "Service", name: "Flyer Printing" } },
      { "@type": "Offer", itemOffered: { "@type": "Service", name: "Brochure Printing" } },
      { "@type": "Offer", itemOffered: { "@type": "Service", name: "Sticker Printing" } },
      { "@type": "Offer", itemOffered: { "@type": "Service", name: "Banner Printing" } },
      { "@type": "Offer", itemOffered: { "@type": "Service", name: "Booklet Printing" } },
    ],
  },
  aggregateRating: {
    "@type": "AggregateRating",
    ratingValue: "4.9",
    reviewCount: "500",
    bestRating: "5",
  },
};
