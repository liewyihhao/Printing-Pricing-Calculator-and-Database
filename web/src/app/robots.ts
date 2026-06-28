import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/account/", "/cart", "/checkout", "/order-success"],
      },
    ],
    sitemap: "https://www.printoka.com/sitemap.xml",
  };
}
