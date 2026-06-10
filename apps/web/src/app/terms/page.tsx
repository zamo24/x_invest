import Link from "next/link";

const supportEmail = process.env.NEXT_PUBLIC_SUPPORT_EMAIL;

export default function TermsPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-5 py-12 sm:px-8">
      <Link href="/" className="text-sm text-emerald-700 hover:underline dark:text-emerald-300">
        Back to X Investor Copilot
      </Link>
      <h1 className="mt-6 text-4xl font-semibold tracking-tight">Terms of Service</h1>
      <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">Last updated: June 8, 2026</p>

      <div className="mt-10 space-y-8 leading-7 text-slate-700 dark:text-slate-200">
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Service purpose</h2>
          <p className="mt-2">
            X Investor Copilot is a research organization and retrieval tool. It helps users save, organize, and ask
            questions about sources they selected.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Not investment advice</h2>
          <p className="mt-2">
            The service does not provide investment, legal, tax, or financial advice. Generated responses may be
            incomplete or incorrect. You are solely responsible for verifying sources and making investment decisions.
            Past performance and third-party statements do not guarantee future results.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Your responsibilities</h2>
          <p className="mt-2">
            You must use the service lawfully, protect your account and extension tokens, respect third-party rights,
            and avoid attempting to disrupt, reverse engineer, or misuse the service. Only save and process content you
            are permitted to use.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Beta availability</h2>
          <p className="mt-2">
            During the private beta, features may change, fail, or be discontinued. The service is provided as available
            without guarantees of uninterrupted operation, accuracy, or fitness for a particular purpose.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Account suspension</h2>
          <p className="mt-2">
            We may limit or suspend access when reasonably necessary to protect users, the service, third parties, or
            legal compliance.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Contact</h2>
          {supportEmail ? (
            <p className="mt-2">
              Questions about these terms can be sent to{" "}
              <a className="text-emerald-700 underline dark:text-emerald-300" href={`mailto:${supportEmail}`}>
                {supportEmail}
              </a>
              .
            </p>
          ) : (
            <p className="mt-2">A support contact will be published before public launch.</p>
          )}
        </section>
      </div>
    </main>
  );
}
