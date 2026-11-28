"use client";

import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { GenerateResponse } from "@/lib/trip-schema";
import { DAY_COLORS } from "@/lib/day-colors";

// Public tile servers are sometimes blocked (college Wi-Fi) or slow, so there is a second provider.
const TILE_PROVIDERS = [
  {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    subdomains: "abc",
  },
  {
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
  },
] as const;

const ERRORS_BEFORE_SWITCH = 4;

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    map.invalidateSize();
    if (points.length > 1) map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 14 });
    else if (points.length === 1) map.setView(points[0], 11);
  }, [map, points]);
  return null;
}

export default function MapView({ result }: { result: GenerateResponse }) {
  const [provider, setProvider] = useState(0);
  const [tileErrors, setTileErrors] = useState(0);

  const dest = result.destination;
  const center: [number, number] = dest ? [dest.latitude, dest.longitude] : [20.59, 78.96];

  const stops = result.itinerary.days.flatMap((day) =>
    day.items
      .filter((i) => i.latitude != null && i.longitude != null)
      .map((i) => ({ day: day.day_number, title: i.title, pos: [i.latitude as number, i.longitude as number] as [number, number] })),
  );
  const plannedKeys = new Set(stops.map((s) => `${s.pos[0]},${s.pos[1]}`));
  const others = result.attractions.filter((a) => !plannedKeys.has(`${a.latitude},${a.longitude}`)).slice(0, 25);
  const fit: [number, number][] = [center, ...stops.map((s) => s.pos)];

  function onTileError() {
    setTileErrors((n) => {
      const next = n + 1;
      if (next === ERRORS_BEFORE_SWITCH && provider === 0) {
        setProvider(1);
        return 0;
      }
      return next;
    });
  }

  const tiles = TILE_PROVIDERS[provider];
  const backgroundFailed = provider === 1 && tileErrors >= ERRORS_BEFORE_SWITCH;

  return (
    <div className="relative h-full w-full">
      <MapContainer center={center} zoom={dest ? 11 : 4} scrollWheelZoom={false} className="h-full w-full">
        <TileLayer
          key={provider}
          attribution={tiles.attribution}
          url={tiles.url}
          subdomains={tiles.subdomains}
          eventHandlers={{ tileerror: onTileError, tileload: () => setTileErrors(0) }}
        />
        <FitBounds points={fit} />
        {dest && (
          <CircleMarker center={center} radius={7} pathOptions={{ color: "#0f172a", fillColor: "#0f172a", fillOpacity: 1 }}>
            <Tooltip>{dest.display_name.split(",")[0]}</Tooltip>
          </CircleMarker>
        )}
        {others.map((a) => (
          <CircleMarker key={`${a.name}-${a.latitude}`} center={[a.latitude, a.longitude]} radius={5} pathOptions={{ color: "#64748b", fillColor: "#94a3b8", fillOpacity: 0.8, weight: 1 }}>
            <Tooltip>{a.name}</Tooltip>
          </CircleMarker>
        ))}
        {stops.map((s, i) => (
          <CircleMarker key={i} center={s.pos} radius={9} pathOptions={{ color: "#fff", weight: 2, fillColor: DAY_COLORS[(s.day - 1) % DAY_COLORS.length], fillOpacity: 1 }}>
            <Tooltip>
              Day {s.day}: {s.title}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      {backgroundFailed && (
        <p className="pointer-events-none absolute inset-x-3 bottom-8 z-[500] rounded-lg bg-amber-50/95 p-2.5 text-xs text-amber-900 shadow">
          The map background couldn&apos;t load (your network may be blocking the map servers). Pins are still placed, and every stop is listed below.
        </p>
      )}
    </div>
  );
}
