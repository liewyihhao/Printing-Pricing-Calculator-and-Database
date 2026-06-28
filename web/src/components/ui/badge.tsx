import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-brand-100 text-brand-700",
        secondary: "bg-surface-subtle text-ink-secondary border border-border",
        success: "bg-green-50 text-green-700",
        warning: "bg-amber-50 text-amber-700",
        destructive: "bg-red-50 text-red-700",
        outline: "border border-border text-ink-muted",
        silver: "bg-slate-100 text-slate-600",
        gold: "bg-amber-50 text-amber-600",
        platinum: "bg-purple-50 text-purple-600",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
