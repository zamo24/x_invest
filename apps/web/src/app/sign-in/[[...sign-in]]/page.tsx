export default function SignInPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <p style={{ padding: 24 }}>Set Clerk keys in .env to enable sign-in.</p>;
  }

  const { SignIn } = require("@clerk/nextjs");
  return (
    <main className="landing">
      <SignIn />
    </main>
  );
}
