import type { Metadata } from "next";

const API_BASE = process.env.NEXT_PUBLIC_PRICING_API ?? "http://localhost:8020";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    const res = await fetch(`${API_BASE}/api/v1/products/${id}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) throw new Error("not found");
    const product = await res.json();
    const name: string = product.name ?? "Print Product";
    const category: string = product.category ?? "Printing";
    const title = `${name} — Online Printing Malaysia, Singapore & Brunei`;
    const description = `Order custom ${name.toLowerCase()} online. Instant live pricing, choose your specs and quantity, fast turnaround, delivered across Malaysia, Singapore & Brunei. ${category} printing from Printoka.`;
    return {
      title,
      description,
      keywords: [
        `${name} printing`, `${name} printing Malaysia`, `${name} printing Singapore`,
        `${name} printing Brunei`, `custom ${name.toLowerCase()}`, `online ${name.toLowerCase()}`,
        `cheap ${name.toLowerCase()} printing`, category,
      ],
      alternates: { canonical: `https://www.printoka.com/products/${id}` },
      openGraph: {
        title: `${name} | Printoka`,
        description,
        url: `https://www.printoka.com/products/${id}`,
      },
    };
  } catch {
    return {
      title: "Print Product | Printoka",
      description: "Configure and order print products online. Instant pricing, fast delivery to Malaysia, Singapore & Brunei.",
    };
  }
}

export default function ProductLayout({ children }: { children: React.ReactNode }) {
  return children;
}
