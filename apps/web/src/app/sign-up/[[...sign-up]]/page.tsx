export default function SignUpPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <p style={{ padding: 24 }}>Set Clerk keys in .env to enable sign-up.</p>;
  }

  const { SignUp } = require("@clerk/nextjs");
  return (
    <main className="landing">
      <SignUp />
    </main>
  );
}
