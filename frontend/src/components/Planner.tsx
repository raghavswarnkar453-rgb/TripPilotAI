"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle } from "lucide-react";
import { ApiError, generateTrip } from "@/lib/api";
import { generateResponseSchema, type GenerateResponse, type TripFormValues } from "@/lib/trip-schema";
import { TripForm } from "@/components/TripForm";
import { TripResult } from "@/components/TripResult";
import { PENDING_KEY } from "@/components/SaveTripButton";

const STEPS = [
  "Finding your destination...",
  "Checking the weather...",
  "Looking up nearby attractions...",
  "Writing your day-by-day plan...",
  "Adding up the budget...",
];

export function Planner() {
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const resultRef = useRef<HTMLDivElement>(null);

  // Restore a plan the user generated before going to sign in.
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(PENDING_KEY);
      if (!raw) return;
      const parsed = generateResponseSchema.safeParse(JSON.parse(raw));
      if (parsed.success) queueMicrotask(() => setResult(parsed.data));
    } catch {
      /* ignore corrupted storage */
    }
  }, []);

  useEffect(() => {
    if (!loading) return;
    const id = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 4500);
    return () => clearInterval(id);
  }, [loading]);

  async function onSubmit(values: TripFormValues) {
    setLoading(true);
    setError(null);
    setStep(0);
    try {
      const data = await generateTrip(values);
      setResult(data);
      try {
        sessionStorage.setItem(PENDING_KEY, JSON.stringify(data));
      } catch {
        /* storage full/unavailable - saving still works from memory */
      }
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="bg-gradient-to-b from-teal-600 to-teal-700 px-4 pb-28 pt-12 text-center text-white sm:pt-16">
        <p className="text-sm font-semibold uppercase tracking-widest text-teal-100">Explore more. Plan smarter. Travel better.</p>
        <h1 className="mx-auto mt-3 max-w-3xl text-3xl font-extrabold leading-tight sm:text-5xl">Your AI trip planner, ready in seconds</h1>
        <p className="mx-auto mt-3 max-w-xl text-teal-50">
          Tell us where, when and how much. Get a day-by-day plan with weather, a map and a budget estimate.
        </p>
      </section>

      <div className="mx-auto -mt-20 max-w-3xl px-4">
        <TripForm onSubmit={onSubmit} loading={loading} />
        {loading && (
          <p className="mt-4 text-center text-sm text-slate-600" role="status" aria-live="polite">
            {STEPS[step]} <span className="text-slate-400">(this can take up to 30 seconds)</span>
          </p>
        )}
        {error && (
          <p className="mt-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            {error}
          </p>
        )}
      </div>

      {result && (
        <div ref={resultRef} className="mx-auto mt-12 max-w-6xl scroll-mt-20 px-4 pb-16">
          <TripResult result={result} />
        </div>
      )}
    </main>
  );
}
