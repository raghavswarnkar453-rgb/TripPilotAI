"use client";

import dynamic from "next/dynamic";
import { ExternalLink, Info } from "lucide-react";
import type { GenerateResponse } from "@/lib/trip-schema";
import { DAY_COLORS } from "@/lib/day-colors";

// Leaflet touches `window`, so it must only load in the browser.
const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => <div className="grid h-full place-items-center rounded-2xl bg-slate-100 text-slate-500">Loading map...</div>,
});

const mapsLink = (lat: number, lon: number) => `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;

export function MapPanel({ result }: { result: GenerateResponse }) {
  const days = result.itinerary.days
    .map((d) => ({
      day: d.day_number,
      stops: d.items.filter((i) => i.latitude != null && i.longitude != null),
    }))
    .filter((d) => d.stops.length > 0);
  const hasStops = days.length > 0;

  return (
    <div className="space-y-4">
      {!hasStops && (
        <p className="flex items-start gap-2 rounded-xl bg-slate-100 p-3 text-sm text-slate-700">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          {result.attractions_status === "ok"
            ? "None of the planned activities matched a known place, so there are no pins. Nearby attractions are shown in grey."
            : "Nearby attractions couldn't be loaded, so activity pins aren't available for this plan."}
        </p>
      )}

      <div className="h-[420px] overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 shadow-sm sm:h-[520px]">
        <MapView result={result} />
      </div>

      <ul className="flex flex-wrap gap-3 text-xs text-slate-600">
        {result.itinerary.days.map((d) => (
          <li key={d.day_number} className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full" style={{ background: DAY_COLORS[(d.day_number - 1) % DAY_COLORS.length] }} />
            Day {d.day_number}
          </li>
        ))}
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-slate-400" />
          Other attractions
        </li>
      </ul>

      {hasStops && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-3 font-semibold text-slate-900">Stops on the map</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {days.map((d) => (
              <div key={d.day}>
                <p className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-slate-800">
                  <span className="h-3 w-3 rounded-full" style={{ background: DAY_COLORS[(d.day - 1) % DAY_COLORS.length] }} />
                  Day {d.day}
                </p>
                <ul className="space-y-1 text-sm text-slate-700">
                  {d.stops.map((s, i) => (
                    <li key={i}>
                      <a
                        href={mapsLink(s.latitude as number, s.longitude as number)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 hover:text-teal-700 hover:underline"
                      >
                        {s.title}
                        <ExternalLink className="h-3 w-3 shrink-0" aria-hidden />
                        <span className="sr-only">(opens Google Maps)</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
