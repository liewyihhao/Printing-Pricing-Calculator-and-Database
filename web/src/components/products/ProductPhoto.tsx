"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Real product photo (extracted from the printoka.com media library to
 * /public/product-photos/<id>.jpg). Falls back to the category emoji for the
 * products that don't have a photo yet (mugs, apparel, foamboard, …).
 */
export function ProductPhoto({
  id,
  icon,
  alt,
  className,
  imgClassName,
}: {
  id: number;
  icon: string;
  alt: string;
  className?: string;
  imgClassName?: string;
}) {
  const [failed, setFailed] = useState(false);

  return (
    <div className={cn("relative overflow-hidden bg-surface-muted flex items-center justify-center", className)}>
      {failed ? (
        <span className="text-5xl select-none">{icon}</span>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={`/product-photos/${id}.jpg`}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          className={cn("w-full h-full object-cover object-center", imgClassName)}
        />
      )}
    </div>
  );
}
