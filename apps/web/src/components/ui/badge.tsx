import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950",
        secondary: "border-transparent bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100",
        destructive: "border-transparent bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-200",
        outline: "border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

function Badge({ className, variant, ...props }: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
