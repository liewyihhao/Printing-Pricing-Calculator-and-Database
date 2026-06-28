import type { MetadataRoute } from "next";

const BASE = "https://www.printoka.com";
const API = process.env.NEXT_PUBLIC_PRICING_API ?? "http://localhost:8020";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: new Date(), changeFrequency: "daily", priority: 1.0 },
    { url: `${BASE}/products`, lastModified: new Date(), changeFrequency: "daily", priority: 0.9 },
    { url: `${BASE}/templates`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.6 },
    { url: `${BASE}/track`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.4 },
    { url: `${BASE}/auth/login`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.3 },
    { url: `${BASE}/auth/register`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.3 },
  ];

  try {
    const res = await fetch(`${API}/api/v1/products`, { next: { revalidate: 3600 } });
    if (!res.ok) return staticPages;
    const data = await res.json();
    const products: Array<{ id: number }> = Array.isArray(data) ? data : data.products ?? [];
    const productPages: MetadataRoute.Sitemap = products.map((p) => ({
      url: `${BASE}/products/${p.id}`,
      lastModified: new Date(),
      changeFrequency: "weekly" as const,
      priority: 0.8,
    }));
    return [...staticPages, ...productPages];
  } catch {
    return staticPages;
  }
}
