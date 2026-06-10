"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignOutButton } from "@clerk/nextjs";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { href: "/app/library", label: "Library" },
  { href: "/app/chat", label: "Chat" },
  { href: "/app/settings/models", label: "Models" },
  { href: "/app/settings/tokens", label: "API Tokens" },
  { href: "/app/settings/x", label: "X Integration" },
];

export function AppNav() {
  const pathname = usePathname();
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  return (
    <nav className="flex flex-wrap items-center gap-2">
      <ThemeToggle />
      {links.map((link) => {
        const isActive = pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              buttonVariants({ variant: isActive ? "secondary" : "ghost", size: "sm" }),
              isActive && "bg-emerald-50 text-emerald-800 hover:bg-emerald-100 dark:bg-emerald-950 dark:text-emerald-200 dark:hover:bg-emerald-900",
            )}
          >
            {link.label}
          </Link>
        );
      })}
      {clerkEnabled ? (
        <SignOutButton redirectUrl="/">
          <Button variant="outline" size="sm">
            Sign out
          </Button>
        </SignOutButton>
      ) : null}
    </nav>
  );
}
