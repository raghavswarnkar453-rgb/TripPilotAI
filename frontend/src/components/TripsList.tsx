"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Calendar, ChevronRight, Loader2, Users, Wallet } from "lucide-react";
import { ApiError, listTrips } from "@/lib/api";
import type { SavedTripSummary } from "@/lib/trip-schema";
import { formatDay, formatINR } from "@/lib/format";
import { useSession } from "@/lib/use-session";

export function TripsList() {
  const session = useSession();
  const [trips, setTrips] = useState<SavedTripSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session.email) return;
    let active = true;
    listTrips()
      .then((t) => active && setTrips(t))
      .catch((e) => active && setError(e instanceof ApiError ? e.message : "Couldn't load your trips."));
    return () => {
      active = false;
    };
  }, [session.email]);

  if (session.loading) return <Loader2 className="mx-auto h-6 w-6 animate-spin text-slate-400" aria-label="Loading" />;

  if (!session.email) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center">
        <p className="text-slate-700">{session.configured ? "Sign in to see your saved trips." : "Sign-in isn't configured yet (missing Supabase keys in frontend/.env.local)."}</p>
        {session.configured && (
          <Link href="/login" className="mt-4 inline-block rounded-xl bg-teal-600 px-5 py-2.5 font-semibold text-white hover:bg-teal-700">
            Sign in
          </Link>
        )}
      </div>
    );
  }

  if (error) return <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{error}</p>;
  if (!trips) return <Loader2 className="mx-auto h-6 w-6 animate-spin text-slate-400" aria-label="Loading" />;

  if (trips.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center">
        <p className="text-slate-700">No saved trips yet.</p>
        <Link href="/" className="mt-4 inline-block rounded-xl bg-teal-600 px-5 py-2.5 font-semibold text-white hover:bg-teal-700">
          Plan your first trip
        </Link>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {trips.map((t) => (
        <li key={t.id}>
          <Link href={`/trips/${t.id}`} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-teal-400">
            <div className="min-w-0">
              <p className="truncate text-lg font-bold text-slate-900">{t.title}</p>
              <p className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
                <span className="flex items-center gap-1"><Calendar className="h-4 w-4" aria-hidden />{formatDay(t.start_date)} - {formatDay(t.end_date)}</span>
                <span className="flex items-center gap-1"><Users className="h-4 w-4" aria-hidden />{t.travelers}</span>
                <span className="flex items-center gap-1"><Wallet className="h-4 w-4" aria-hidden />{formatINR(t.budget)}</span>
              </p>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-slate-400" aria-hidden />
          </Link>
        </li>
      ))}
    </ul>
  );
}
