import type { ReactNode } from "react";

type AuthShellProps = {
  message?: string;
  children?: ReactNode;
};

export function AuthShell({ message, children }: AuthShellProps) {
  return (
    <main className="grid min-h-screen place-items-center px-4 py-8">
      <section className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        {message ? <p className="text-sm text-slate-700">{message}</p> : children}
      </section>
    </main>
  );
}
