import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@clerk/nextjs/server";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default async function Home() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  if (clerkEnabled) {
    const { userId } = await auth();
    if (userId) {
      redirect("/app/library");
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4 py-10 sm:px-6">
      <Card className="w-full max-w-3xl border-slate-200/90 shadow-lg shadow-slate-300/25">
        <CardHeader className="space-y-3">
          <Badge variant="outline" className="w-fit">
            X Investor Copilot
          </Badge>
          <CardTitle className="text-2xl sm:text-3xl">
            Your saved X threads, turned into a personal RAG copilot.
          </CardTitle>
          <CardDescription className="text-base leading-relaxed">
            Save tweets from the extension, then query your own source-grounded library with citations back to exact
            tweet URLs.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          B2C MVP with Clerk auth, PAT-based extension access, and source-cited investor chat over your personal corpus.
        </CardContent>
        <CardFooter className="flex flex-wrap gap-2">
          {clerkEnabled ? (
            <>
              <Button asChild>
                <Link href="/sign-up">Create account</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href="/sign-in">Sign in</Link>
              </Button>
            </>
          ) : (
            <p className="w-full text-sm text-slate-600">Set Clerk keys in `.env` to enable sign-in and sign-up.</p>
          )}
          <Button asChild variant="outline">
            <Link href="/app/library">Open dashboard</Link>
          </Button>
        </CardFooter>
      </Card>
    </main>
  );
}
