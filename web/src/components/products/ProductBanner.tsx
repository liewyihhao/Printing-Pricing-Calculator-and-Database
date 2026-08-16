"use client";

import { useState } from "react";

/** Wide product hero banner (2000×300) from the printoka media library. Renders nothing
 *  if the product has no banner, so the layout stays clean. */
export function ProductBanner({ id, alt }: { id: number; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return (
    <div className="rounded-xl overflow-hidden border border-border mb-6">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/product-banners/${id}.jpg`}
        alt={alt}
        onError={() => setFailed(true)}
        className="w-full h-auto block"
        fetchPriority="high"
      />
    </div>
  );
}
