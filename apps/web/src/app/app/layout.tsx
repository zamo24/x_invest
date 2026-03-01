import Link from "next/link";

import { AppNav } from "@/components/app-nav";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50/60 via-slate-50 to-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Link href="/app/library" className="text-sm font-semibold tracking-tight text-slate-900 sm:text-base">
              X Investor Copilot
            </Link>
            <Separator orientation="vertical" className="hidden h-5 sm:block" />
            <Badge variant="outline" className="hidden sm:inline-flex">
              Dashboard
            </Badge>
          </div>
          <AppNav />
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
