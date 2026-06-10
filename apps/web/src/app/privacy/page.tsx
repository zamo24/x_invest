import Link from "next/link";

const supportEmail = process.env.NEXT_PUBLIC_SUPPORT_EMAIL;

export default function PrivacyPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-5 py-12 sm:px-8">
      <Link href="/" className="text-sm text-emerald-700 hover:underline dark:text-emerald-300">
        Back to X Investor Copilot
      </Link>
      <h1 className="mt-6 text-4xl font-semibold tracking-tight">Privacy Policy</h1>
      <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">Last updated: June 8, 2026</p>

      <div className="mt-10 space-y-8 leading-7 text-slate-700 dark:text-slate-200">
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Information we process</h2>
          <p className="mt-2">
            X Investor Copilot processes account information, saved X tweets, threads and articles, folders, chat
            messages, cited answers, model settings, and operational request metadata needed to provide the service.
            If you provide your own model API key, it is encrypted before storage.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">How information is used</h2>
          <p className="mt-2">
            Information is used to authenticate you, save and organize your research, retrieve relevant saved sources,
            generate requested answers, maintain security, diagnose failures, and improve the product. We do not sell
            your personal information or saved research.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Chrome Limited Use disclosure</h2>
          <p className="mt-2">
            The extension captures only content you explicitly choose to save from visible X pages. Use and transfer of
            information received from Google APIs follows the Chrome Web Store User Data Policy, including its Limited
            Use requirements. The extension does not sell user data, use it for advertising, or capture browsing
            activity unrelated to the product&apos;s single purpose.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Service providers and models</h2>
          <p className="mt-2">
            Authentication providers, hosting providers, databases, and configured AI model providers may process data
            only as needed to deliver their services. When hosted or bring-your-own-key AI models are enabled, relevant
            prompts and retrieved source excerpts may be sent to the selected model provider.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Retention and control</h2>
          <p className="mt-2">
            We retain information while your account is active and as needed for security, legal, and operational
            purposes. You may revoke extension tokens at any time. Contact us to request access, correction, or deletion
            of your account information.
          </p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Contact</h2>
          {supportEmail ? (
            <p className="mt-2">
              Questions or privacy requests can be sent to{" "}
              <a className="text-emerald-700 underline dark:text-emerald-300" href={`mailto:${supportEmail}`}>
                {supportEmail}
              </a>
              .
            </p>
          ) : (
            <p className="mt-2">A privacy contact will be published before public launch.</p>
          )}
        </section>
      </div>
    </main>
  );
}
