import { LoginForm } from "@/components/LoginForm";

export const metadata = { title: "Sign in - TripPilot AI" };

export default function LoginPage() {
  return (
    <main className="mx-auto max-w-md px-4 py-12">
      <LoginForm />
    </main>
  );
}
