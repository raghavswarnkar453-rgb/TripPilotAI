"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { getSupabase } from "@/lib/supabase";

const input =
  "w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-200";

export function LoginForm() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const supabase = getSupabase();
    if (!supabase) {
      setError("Sign-in isn't configured yet (missing Supabase keys in frontend/.env.local).");
      return;
    }
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError("Enter a valid email address.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");

    setBusy(true);
    setError(null);
    setInfo(null);
    if (mode === "signin") {
      const { error: err } = await supabase.auth.signInWithPassword({ email, password });
      setBusy(false);
      if (err) return setError(err.message);
      router.push("/");
    } else {
      const { data, error: err } = await supabase.auth.signUp({ email, password });
      setBusy(false);
      if (err) return setError(err.message);
      if (data.session) router.push("/");
      else setInfo("Account created. Check your email to confirm it, then sign in.");
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-bold text-slate-900">{mode === "signin" ? "Welcome back" : "Create your account"}</h1>
      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-slate-700">Email</span>
        <input type="email" autoComplete="email" className={input} value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-slate-700">Password</span>
        <input type="password" autoComplete={mode === "signin" ? "current-password" : "new-password"} className={input} value={password} onChange={(e) => setPassword(e.target.value)} />
      </label>
      {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
      {info && <p className="rounded-lg bg-teal-50 p-3 text-sm text-teal-800">{info}</p>}
      <button type="submit" disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 font-semibold text-white hover:bg-teal-700 disabled:bg-teal-400">
        {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {mode === "signin" ? "Sign in" : "Sign up"}
      </button>
      <button
        type="button"
        onClick={() => {
          setMode(mode === "signin" ? "signup" : "signin");
          setError(null);
          setInfo(null);
        }}
        className="w-full text-center text-sm text-slate-600 hover:text-teal-700"
      >
        {mode === "signin" ? "New here? Create an account" : "Already have an account? Sign in"}
      </button>
    </form>
  );
}
