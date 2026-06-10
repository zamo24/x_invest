import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@clerk/nextjs/server";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PRODUCT_NAME } from "@/lib/product";

const workflow = [
  {
    step: "01",
    title: "Save the source",
    description: "Connect X and sync bookmarks through the official API.",
  },
  {
    step: "02",
    title: "Organize the thesis",
    description: "Group research by company, sector, or investing theme instead of losing it in bookmarks.",
  },
  {
    step: "03",
    title: "Ask with evidence",
    description: "Question your personal research library and follow every answer back to its original source.",
  },
];

export default async function Home() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  if (clerkEnabled) {
    const { userId } = await auth();
    if (userId) {
      redirect("/app/library");
    }
  }

  return (
    <main className="min-h-screen">
      <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/" className="font-semibold tracking-tight text-slate-950 dark:text-white">
          {PRODUCT_NAME}
        </Link>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link href="/beta">Join beta</Link>
          </Button>
          {clerkEnabled ? (
            <Button asChild variant="outline" size="sm">
              <Link href="/sign-in">Sign in</Link>
            </Button>
          ) : null}
        </div>
      </nav>

      <section className="mx-auto grid w-full max-w-6xl gap-12 px-5 pb-20 pt-14 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:pt-24">
        <div>
          <Badge variant="outline" className="mb-5">
            Private beta for research-driven investors
          </Badge>
          <h1 className="max-w-3xl text-5xl font-semibold leading-[1.05] tracking-[-0.045em] text-slate-950 dark:text-white sm:text-6xl">
            Never lose an investment thesis.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600 dark:text-slate-300">
            Connect your X account and turn bookmarks and saved posts into a searchable, source-cited research library.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/beta">Apply for the private beta</Link>
            </Button>
            {clerkEnabled ? (
              <Button asChild variant="outline" size="lg">
                <Link href="/sign-in">Existing user sign in</Link>
              </Button>
            ) : null}
          </div>
          <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
            Official X API connection required. Threads are reconstructed on a best-effort basis.
          </p>
        </div>

        <Card className="overflow-hidden border-slate-200/90 shadow-xl shadow-slate-300/25 dark:shadow-none">
          <CardHeader className="border-b border-slate-200 bg-slate-950 text-white dark:border-slate-800">
            <CardDescription className="font-mono text-xs uppercase tracking-[0.2em] text-emerald-300">
              Research question
            </CardDescription>
            <CardTitle className="text-xl leading-relaxed">
              What changed in my HBM supply thesis since the first thread I saved?
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5 p-6">
            <p className="leading-7 text-slate-700 dark:text-slate-200">
              Your later research points to improving packaging capacity, while demand remains above available supply.
              The original thesis was more focused on persistent packaging constraints.
            </p>
            <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-100">
              <p className="font-semibold">Cited from your saved research</p>
              <p className="mt-1 text-emerald-800 dark:text-emerald-200">
                Two source threads, including the preserved original capture.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="border-y border-slate-200 bg-white/70 dark:border-slate-800 dark:bg-slate-950/60">
        <div className="mx-auto w-full max-w-6xl px-5 py-20 sm:px-8">
          <div className="max-w-2xl">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-emerald-700 dark:text-emerald-300">
              A research memory, not a stock picker
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">
              Keep the source. Keep the context. Revisit the thesis.
            </h2>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {workflow.map((item) => (
              <Card key={item.step}>
                <CardHeader>
                  <span className="font-mono text-xs text-emerald-700 dark:text-emerald-300">{item.step}</span>
                  <CardTitle className="text-lg">{item.title}</CardTitle>
                  <CardDescription className="leading-6">{item.description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-4xl px-5 py-20 text-center sm:px-8">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">
          Help shape the research workflow you want to use.
        </h2>
        <p className="mx-auto mt-4 max-w-2xl leading-7 text-slate-600 dark:text-slate-300">
          The private beta is for active retail investors who regularly research on X. Early users receive direct
          onboarding and a founding-user offer when the beta ends.
        </p>
        <Button asChild size="lg" className="mt-8">
          <Link href="/beta">Apply for the private beta</Link>
        </Button>
      </section>

      <footer className="border-t border-slate-200 dark:border-slate-800">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap gap-x-6 gap-y-2 px-5 py-8 text-sm text-slate-500 sm:px-8 dark:text-slate-400">
          <span>{PRODUCT_NAME}</span>
          <span>Not affiliated with X.</span>
          <Link href="/privacy" className="hover:text-slate-950 dark:hover:text-white">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-slate-950 dark:hover:text-white">
            Terms
          </Link>
          <span>Not investment advice.</span>
        </div>
      </footer>
    </main>
  );
}
