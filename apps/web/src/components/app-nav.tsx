"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/app/library", label: "Library" },
  { href: "/app/chat", label: "Chat" },
  { href: "/app/settings/tokens", label: "API Tokens" },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="app-nav">
      {links.map((link) => {
        const isActive = pathname.startsWith(link.href);
        return (
          <Link key={link.href} href={link.href} className={isActive ? "active" : ""}>
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
