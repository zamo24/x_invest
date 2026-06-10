import Link from "next/link";
import { PRODUCT_NAME } from "@/lib/product";

const supportEmail = process.env.NEXT_PUBLIC_SUPPORT_EMAIL;

export default function PrivacyPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-5 py-12 sm:px-8">
      <Link href="/" className="text-sm text-emerald-700 hover:underline dark:text-emerald-300">
        Back to {PRODUCT_NAME}
      </Link>
      <h1 className="mt-6 text-4xl font-semibold tracking-tight">Privacy Policy</h1>
      <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">Last updated: June 8, 2026</p>

      <div className="mt-10 space-y-8 leading-7 text-slate-700 dark:text-slate-200">
        <section>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">Information we process</h2>
          <p className="mt-2">
            {PRODUCT_NAME} processes account information, encrypted X OAuth tokens, X API post and bookmark content,
            folders, chat messages, cited answers, model settings, source-verification results, and operational usage
            metadata. If you provide your own model API key, it is encrypted before storage.
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
            The extension reads only the active X post URL after an explicit save action and sends no page DOM content.
            It does not inject scripts into X pages. Use and transfer of information received from Google APIs follows
            the Chrome Web Store User Data Policy, including its Limited Use requirements.
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
            Disconnecting X deletes stored X OAuth tokens but preserves the saved library. Source revalidation may mark
            current content unavailable. During this phase, historical snapshots, embeddings, and persisted chat
            citations are intentionally retained and deletion or modification events are not propagated through them.
            This retention model requires legal review and written X approval before the service can be described as
            fully compliant with X policies.
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
