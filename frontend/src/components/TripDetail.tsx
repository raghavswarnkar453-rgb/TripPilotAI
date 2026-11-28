"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";
import { ApiError, getTrip } from "@/lib/api";
import type { GenerateResponse } from "@/lib/trip-schema";
import { useSession } from "@/lib/use-session";
import { TripResult } from "@/components/TripResult";

export function TripDetail({ id }: { id: string }) {
  const session = useSession();
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session.email) return;
    let active = true;
    getTrip(id)
      .then((r) => active && setResult(r))
      .catch((e) => active && setError(e instanceof ApiError ? e.message : "Couldn't load this trip."));
    return () => {
      active = false;
    };
  }, [id, session.email]);

  return (
    <div className="space-y-5">
      <Link href="/trips" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-teal-700">
        <ArrowLeft className="h-4 w-4" aria-hidden /> My trips
      </Link>
      {session.loading && <Loader2 className="h-6 w-6 animate-spin text-slate-400" aria-label="Loading" />}
      {!session.loading && !session.email && (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-slate-700">
          Please <Link href="/login" className="font-semibold text-teal-700 underline">sign in</Link> to view this trip.
        </p>
      )}
      {error && <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{error}</p>}
      {result && <TripResult result={result} showSave={false} />}
      {session.email && !result && !error && <Loader2 className="h-6 w-6 animate-spin text-slate-400" aria-label="Loading" />}
    </div>
  );
}
