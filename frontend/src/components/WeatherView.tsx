import { CloudSun, Droplets, Info } from "lucide-react";
import type { GenerateResponse } from "@/lib/trip-schema";
import { formatDay } from "@/lib/format";

export function WeatherView({ weather }: { weather: GenerateResponse["weather"] }) {
  if (weather.status !== "ok" || weather.days.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-600">
        <p className="flex items-center gap-2 font-medium text-slate-800">
          <CloudSun className="h-5 w-5" aria-hidden /> Weather isn&apos;t available right now
        </p>
        <p className="mt-1 text-sm">{weather.note ?? "We couldn't load weather for these dates, so we haven't guessed."}</p>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <p className="flex items-start gap-2 rounded-xl bg-sky-50 p-3 text-sm text-sky-900">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        {weather.source === "historical"
          ? (weather.note ?? "A live forecast isn't available this far ahead, so these figures come from the same dates last year.")
          : "Live forecast from Open-Meteo."}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {weather.days.map((d) => (
          <div key={d.date} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-semibold text-slate-900">{formatDay(d.date)}</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {d.temp_max_c != null ? `${Math.round(d.temp_max_c)}°` : "-"}
              <span className="ml-1 text-base font-medium text-slate-500">{d.temp_min_c != null ? `/ ${Math.round(d.temp_min_c)}°C` : ""}</span>
            </p>
            <p className="text-sm text-slate-600">{d.condition ?? "No description"}</p>
            {d.precipitation_mm != null && (
              <p className="mt-1 flex items-center gap-1 text-xs text-sky-700">
                <Droplets className="h-3.5 w-3.5" aria-hidden />
                {d.precipitation_mm.toFixed(1)} mm
                {d.precipitation_probability != null ? ` - ${d.precipitation_probability}% chance` : ""}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
