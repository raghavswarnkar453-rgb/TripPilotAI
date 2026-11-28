"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Compass, LogIn, LogOut } from "lucide-react";
import { getSupabase } from "@/lib/supabase";
import { useSession } from "@/lib/use-session";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const session = useSession();

  const link = (href: string, label: string) => (
    <Link
      href={href}
      className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
        pathname === href ? "bg-teal-50 text-teal-700" : "text-slate-600 hover:bg-slate-100"
      }`}
    >
      {label}
    </Link>
  );

  async function signOut() {
    await getSupabase()?.auth.signOut();
    router.push("/");
  }

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-2 px-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-slate-900">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-teal-600 text-white">
            <Compass className="h-5 w-5" aria-hidden />
          </span>
          <span>
            TripPilot <span className="text-teal-600">AI</span>
          </span>
        </Link>
        <div className="flex items-center gap-1">
          {link("/", "Plan")}
          {link("/trips", "My trips")}
          {session.email ? (
            <button
              onClick={signOut}
              className="ml-1 flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              title={session.email}
            >
              <LogOut className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          ) : (
            <Link
              href="/login"
              className="ml-1 flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              <LogIn className="h-4 w-4" aria-hidden />
              Sign in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
