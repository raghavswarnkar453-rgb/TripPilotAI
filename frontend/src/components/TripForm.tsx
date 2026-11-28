"use client";

import { useEffect, useState } from "react";
import { Calendar, Loader2, MapPin, Sparkles, Users, Wallet } from "lucide-react";
import { INTERESTS, TRAVEL_STYLES, makeTripFormSchema, type TravelStyle, type TripFormValues } from "@/lib/trip-schema";

type Errors = Partial<Record<keyof TripFormValues, string>>;

const EXAMPLES = ["Manali, Himachal Pradesh", "Goa", "Jaipur, Rajasthan", "Rishikesh, Uttarakhand"];

const input =
  "w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900 placeholder:text-slate-400 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-200";

function Field({ label, error, children, icon }: { label: string; error?: string; children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-slate-700">
        {icon}
        {label}
      </span>
      {children}
      {error && <span className="mt-1 block text-sm text-red-600">{error}</span>}
    </label>
  );
}

export function TripForm({ onSubmit, loading }: { onSubmit: (v: TripFormValues) => void; loading: boolean }) {
  const [destination, setDestination] = useState("");
  const [origin, setOrigin] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [budget, setBudget] = useState("");
  const [travelers, setTravelers] = useState("2");
  const [interests, setInterests] = useState<string[]>([]);
  const [style, setStyle] = useState<TravelStyle>("balanced");
  const [today, setToday] = useState("");
  const [errors, setErrors] = useState<Errors>({});

  // "Today" is read on the client after mount (keeps server output deterministic).
  useEffect(() => {
    const d = new Date();
    const iso = (x: Date) => `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
    const s = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 2);
    const e = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 5);
    queueMicrotask(() => {
      setToday(iso(d));
      setStart((v) => v || iso(s));
      setEnd((v) => v || iso(e));
    });
  }, []);

  function toggleInterest(name: string) {
    setInterests((cur) => (cur.includes(name) ? cur.filter((x) => x !== name) : [...cur, name]));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const parsed = makeTripFormSchema(today).safeParse({
      destination,
      origin,
      start_date: start,
      end_date: end,
      budget: budget.trim() === "" ? Number.NaN : Number(budget),
      travelers: travelers.trim() === "" ? Number.NaN : Number(travelers),
      interests,
      travel_style: style,
    });
    if (!parsed.success) {
      const next: Errors = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0] as keyof TripFormValues;
        next[key] ??= issue.message;
      }
      setErrors(next);
      return;
    }
    setErrors({});
    onSubmit(parsed.data);
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Where to?" error={errors.destination} icon={<MapPin className="h-4 w-4 text-teal-600" aria-hidden />}>
          <input className={input} value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="e.g. Manali, Goa, Jaipur" maxLength={100} />
        </Field>
        <Field label="Travelling from (optional)" error={errors.origin}>
          <input className={input} value={origin} onChange={(e) => setOrigin(e.target.value)} placeholder="e.g. Jaipur" maxLength={100} />
        </Field>
        <div className="flex flex-wrap items-center gap-2 sm:col-span-2" aria-label="Example destinations">
          <span className="text-xs font-medium text-slate-500">Try:</span>
          {EXAMPLES.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => setDestination(name)}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-teal-50 hover:text-teal-700"
            >
              {name}
            </button>
          ))}
        </div>
        <Field label="Start date" error={errors.start_date} icon={<Calendar className="h-4 w-4 text-teal-600" aria-hidden />}>
          <input type="date" className={input} value={start} min={today || undefined} onChange={(e) => setStart(e.target.value)} />
        </Field>
        <Field label="End date" error={errors.end_date} icon={<Calendar className="h-4 w-4 text-teal-600" aria-hidden />}>
          <input type="date" className={input} value={end} min={start || today || undefined} onChange={(e) => setEnd(e.target.value)} />
        </Field>
        <Field label="Total budget (INR)" error={errors.budget} icon={<Wallet className="h-4 w-4 text-teal-600" aria-hidden />}>
          <input type="number" inputMode="numeric" min={1} className={input} value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="e.g. 20000" />
        </Field>
        <Field label="Travellers" error={errors.travelers} icon={<Users className="h-4 w-4 text-teal-600" aria-hidden />}>
          <input type="number" inputMode="numeric" min={1} max={50} className={input} value={travelers} onChange={(e) => setTravelers(e.target.value)} />
        </Field>
      </div>

      <fieldset>
        <legend className="mb-2 text-sm font-medium text-slate-700">Interests</legend>
        <div className="flex flex-wrap gap-2">
          {INTERESTS.map((name) => {
            const on = interests.includes(name);
            return (
              <button
                key={name}
                type="button"
                aria-pressed={on}
                onClick={() => toggleInterest(name)}
                className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
                  on ? "border-teal-600 bg-teal-600 text-white" : "border-slate-300 bg-white text-slate-700 hover:border-teal-400"
                }`}
              >
                {name}
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-2 text-sm font-medium text-slate-700">Travel style</legend>
        <div className="grid grid-cols-3 gap-2">
          {TRAVEL_STYLES.map((s) => (
            <button
              key={s.value}
              type="button"
              aria-pressed={style === s.value}
              onClick={() => setStyle(s.value)}
              className={`rounded-xl border px-3 py-2.5 text-left transition-colors ${
                style === s.value ? "border-teal-600 bg-teal-50 ring-1 ring-teal-600" : "border-slate-300 bg-white hover:border-teal-400"
              }`}
            >
              <span className="block text-sm font-semibold text-slate-900">{s.label}</span>
              <span className="block text-xs text-slate-500">{s.hint}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <button
        type="submit"
        disabled={loading}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-5 py-3 text-base font-semibold text-white shadow-sm transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-teal-400"
      >
        {loading ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : <Sparkles className="h-5 w-5" aria-hidden />}
        {loading ? "Planning your trip..." : "Generate my itinerary"}
      </button>
    </form>
  );
}
