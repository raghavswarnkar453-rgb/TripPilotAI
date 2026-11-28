"use client";

import Link from "next/link";
import { useState } from "react";
import { BookmarkCheck, BookmarkPlus, Loader2 } from "lucide-react";
import { ApiError, saveTrip } from "@/lib/api";
import type { GenerateResponse } from "@/lib/trip-schema";
import { useSession } from "@/lib/use-session";

export const PENDING_KEY = "trippilot:last-result";

type State = { kind: "idle" } | { kind: "saving" } | { kind: "saved"; id: string; already: boolean } | { kind: "error"; message: string };

export function SaveTripButton({ result }: { result: GenerateResponse }) {
  const session = useSession();
  const [state, setState] = useState<State>({ kind: "idle" });

  if (!session.loading && !session.email) {
    return (
      <Link
        href="/login?next=/"
        onClick={() => {
          try {
            sessionStorage.setItem(PENDING_KEY, JSON.stringify(result));
          } catch {
            /* storage unavailable - user will just regenerate */
          }
        }}
        className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
      >
        <BookmarkPlus className="h-4 w-4" aria-hidden />
        Sign in to save this trip
      </Link>
    );
  }

  async function save() {
    setState({ kind: "saving" });
    try {
      const res = await saveTrip(result);
      setState({ kind: "saved", id: res.id, already: res.already_saved });
    } catch (e) {
      setState({ kind: "error", message: e instanceof ApiError ? e.message : "Couldn't save the trip. Please try again." });
    }
  }

  if (state.kind === "saved") {
    return (
      <Link href={`/trips/${state.id}`} className="inline-flex items-center gap-2 rounded-xl bg-teal-50 px-4 py-2.5 text-sm font-semibold text-teal-800 ring-1 ring-teal-200">
        <BookmarkCheck className="h-4 w-4" aria-hidden />
        {state.already ? "Already saved - open it" : "Saved - view in My trips"}
      </Link>
    );
  }

  return (
    <div>
      <button
        onClick={save}
        disabled={state.kind === "saving" || session.loading}
        className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-60"
      >
        {state.kind === "saving" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <BookmarkPlus className="h-4 w-4" aria-hidden />}
        Save trip
      </button>
      {state.kind === "error" && <p className="mt-2 text-sm text-red-600">{state.message}</p>}
    </div>
  );
}
