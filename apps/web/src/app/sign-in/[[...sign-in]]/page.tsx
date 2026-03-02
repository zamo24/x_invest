import { SignIn } from "@clerk/nextjs";

import { AuthShell } from "@/components/auth/auth-shell";

export default function SignInPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <AuthShell message="Set Clerk keys in .env to enable sign-in." />;
  }

  return (
    <AuthShell>
      <SignIn forceRedirectUrl="/app/library" fallbackRedirectUrl="/app/library" />
    </AuthShell>
  );
}
