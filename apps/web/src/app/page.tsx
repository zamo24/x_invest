import Link from "next/link";

export default function Home() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  return (
    <main className="landing">
      <section className="landing-card">
        <p className="eyebrow">X Investor Copilot</p>
        <h1>Your saved X threads, turned into a personal RAG copilot.</h1>
        <p>
          Save tweets from the extension, then query your own source-grounded library with citations back to exact
          tweet URLs.
        </p>

        <div className="actions">
          {clerkEnabled ? (
            <>
              <Link href="/sign-up" className="primary">
                Create account
              </Link>
              <Link href="/sign-in" className="secondary">
                Sign in
              </Link>
            </>
          ) : (
            <p>Set Clerk keys in `.env` to enable sign-in/up routes.</p>
          )}
          <Link href="/app/library" className="secondary">
            Open dashboard
          </Link>
        </div>
      </section>
    </main>
  );
}
