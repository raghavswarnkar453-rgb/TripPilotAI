"use client";

import { useState } from "react";
import { Clock, Lightbulb, Moon, Sun, Sunrise, Droplets } from "lucide-react";
import type { DayPlan, GenerateResponse, ItineraryItem } from "@/lib/trip-schema";
import { formatDay, formatDuration, formatINR } from "@/lib/format";

const SLOTS = {
  morning: { label: "Morning", Icon: Sunrise, tone: "bg-amber-50 text-amber-700" },
  afternoon: { label: "Afternoon", Icon: Sun, tone: "bg-orange-50 text-orange-700" },
  evening: { label: "Evening", Icon: Moon, tone: "bg-indigo-50 text-indigo-700" },
} as const;

function Item({ item }: { item: ItineraryItem }) {
  const slot = SLOTS[item.time_slot];
  const duration = formatDuration(item.duration_minutes);
  return (
    <li className="flex gap-3">
      <span className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full ${slot.tone}`} title={slot.label}>
        <slot.Icon className="h-4.5 w-4.5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1 border-b border-slate-100 pb-4 last:border-0">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <h4 className="font-semibold text-slate-900">{item.title}</h4>
          {item.estimated_cost > 0 && <span className="text-sm font-medium text-slate-600">~{formatINR(item.estimated_cost)}</span>}
        </div>
        {item.description && <p className="mt-1 text-sm text-slate-600">{item.description}</p>}
        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
          <span className="font-medium">{slot.label}</span>
          {duration && (
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" aria-hidden />
              {duration}
            </span>
          )}
        </div>
      </div>
    </li>
  );
}

function DayCard({ day, weather }: { day: DayPlan; weather?: GenerateResponse["weather"]["days"][number] }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
            Day {day.day_number}
            {day.date ? ` - ${formatDay(day.date)}` : ""}
          </p>
          <h3 className="text-lg font-bold text-slate-900">{day.title || `Day ${day.day_number}`}</h3>
          {day.summary && <p className="mt-1 text-sm text-slate-600">{day.summary}</p>}
        </div>
        {weather && (
          <div className="rounded-xl bg-sky-50 px-3 py-2 text-xs text-sky-900">
            <p className="font-semibold">{weather.condition ?? "Weather"}</p>
            <p>
              {weather.temp_min_c != null && weather.temp_max_c != null ? `${Math.round(weather.temp_min_c)}-${Math.round(weather.temp_max_c)} °C` : "-"}
              {weather.precipitation_mm ? (
                <span className="ml-2 inline-flex items-center gap-0.5">
                  <Droplets className="h-3 w-3" aria-hidden />
                  {weather.precipitation_mm.toFixed(1)} mm
                </span>
              ) : null}
            </p>
          </div>
        )}
      </header>
      <ul className="space-y-4">
        {day.items.map((item, i) => (
          <Item key={i} item={item} />
        ))}
      </ul>
    </article>
  );
}

export function ItineraryView({ result }: { result: GenerateResponse }) {
  const [active, setActive] = useState<number | "all">("all");
  const { days, tips, summary } = result.itinerary;
  const weatherByDate = new Map(result.weather.days.map((d) => [d.date, d]));
  const shown = active === "all" ? days : days.filter((d) => d.day_number === active);

  return (
    <div className="space-y-5">
      {summary && <p className="rounded-2xl bg-teal-50 p-4 text-slate-700">{summary}</p>}

      <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Filter by day">
        {(["all", ...days.map((d) => d.day_number)] as const).map((v) => (
          <button
            key={v}
            role="tab"
            aria-selected={active === v}
            onClick={() => setActive(v)}
            className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium ${
              active === v ? "bg-slate-900 text-white" : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50"
            }`}
          >
            {v === "all" ? "All days" : `Day ${v}`}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {shown.map((day) => (
          <DayCard key={day.day_number} day={day} weather={day.date ? weatherByDate.get(day.date) : undefined} />
        ))}
      </div>

      {tips.length > 0 && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <h3 className="mb-2 flex items-center gap-2 font-semibold text-amber-900">
            <Lightbulb className="h-5 w-5" aria-hidden />
            Travel tips
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">
            {tips.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
