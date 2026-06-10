import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const applicationUrl = process.env.NEXT_PUBLIC_BETA_APPLICATION_URL;
const supportEmail = process.env.NEXT_PUBLIC_SUPPORT_EMAIL;

export default function BetaPage() {
  const applicationsEnabled = Boolean(applicationUrl);

  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-5 py-12 sm:px-8">
      <Button asChild variant="ghost" size="sm" className="-ml-3 mb-6">
        <Link href="/">Back to overview</Link>
      </Button>

      <Badge variant="outline">Private beta application</Badge>
      <h1 className="mt-5 text-4xl font-semibold tracking-tight text-slate-950 dark:text-white">
        Build a better memory for your investment research.
      </h1>
      <p className="mt-4 max-w-2xl leading-7 text-slate-600 dark:text-slate-300">
        We are onboarding active retail investors who regularly save research from X. Selected beta users receive a
        guided setup and direct access to the founder.
      </p>

      <Card className="mt-10">
        <CardHeader>
          <CardTitle>Tell us about your workflow</CardTitle>
          <CardDescription>Applications are reviewed for fit with the current private beta.</CardDescription>
        </CardHeader>
        <CardContent>
          {applicationsEnabled ? (
            <form action={applicationUrl} method="post" className="space-y-5">
              <label className="block space-y-2 text-sm font-medium">
                Name
                <Input name="name" autoComplete="name" required />
              </label>
              <label className="block space-y-2 text-sm font-medium">
                Email
                <Input name="email" type="email" autoComplete="email" required />
              </label>
              <label className="block space-y-2 text-sm font-medium">
                How often do you use X for investment research?
                <Select name="x_research_frequency" required defaultValue="">
                  <option value="" disabled>
                    Select one
                  </option>
                  <option value="daily">Daily</option>
                  <option value="several-times-weekly">Several times per week</option>
                  <option value="weekly">About once per week</option>
                  <option value="occasionally">Occasionally</option>
                </Select>
              </label>
              <label className="block space-y-2 text-sm font-medium">
                How do you currently save and revisit research?
                <Textarea name="current_workflow" rows={4} required />
              </label>
              <label className="block space-y-2 text-sm font-medium">
                What is the biggest problem with your current workflow?
                <Textarea name="primary_pain_point" rows={4} required />
              </label>
              <label className="flex gap-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
                <input name="research_fit" value="confirmed" type="checkbox" required className="mt-1 size-4" />
                I actively conduct my own investment research and understand that Investor Research Copilot does not provide
                investment advice.
              </label>
              <Button type="submit" size="lg">
                Submit application
              </Button>
            </form>
          ) : supportEmail ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
              Beta applications are currently handled by email. Contact{" "}
              <a className="font-semibold underline" href={`mailto:${supportEmail}?subject=Investor Research Copilot beta`}>
                {supportEmail}
              </a>{" "}
              with a short description of how you currently save investment research from X.
            </div>
          ) : (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
              Beta applications are not currently open. Check back after the private beta contact channel is published.
            </div>
          )}
        </CardContent>
      </Card>

      <p className="mt-6 text-xs leading-5 text-slate-500 dark:text-slate-400">
        By applying, you agree that we may contact you about the beta. Review the <Link href="/privacy" className="underline">privacy policy</Link>.
      </p>
    </main>
  );
}
