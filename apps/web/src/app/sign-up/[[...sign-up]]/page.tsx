import { SignUp } from "@clerk/nextjs";

import { AuthShell } from "@/components/auth/auth-shell";

export default function SignUpPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <AuthShell message="Set Clerk keys in .env to enable sign-up." />;
  }

  return (
    <AuthShell>
      <SignUp />
    </AuthShell>
  );
}
