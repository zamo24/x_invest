import Link from "next/link";

import { AppNav } from "@/components/app-nav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="dashboard-shell">
      <header className="dashboard-header">
        <Link href="/app/library" className="brand">
          X Investor Copilot
        </Link>
        <AppNav />
        <span className="muted">Dashboard</span>
      </header>
      <main className="dashboard-main">{children}</main>
    </div>
  );
}
