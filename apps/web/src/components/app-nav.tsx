"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { href: "/app/library", label: "Library" },
  { href: "/app/chat", label: "Chat" },
  { href: "/app/settings/tokens", label: "API Tokens" },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap items-center gap-2">
      {links.map((link) => {
        const isActive = pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              buttonVariants({ variant: isActive ? "secondary" : "ghost", size: "sm" }),
              isActive && "bg-emerald-50 text-emerald-800 hover:bg-emerald-100",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
