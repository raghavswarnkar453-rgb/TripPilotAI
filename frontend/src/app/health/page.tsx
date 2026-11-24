"use client";

import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "@/lib/api";

export default function HealthPage() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="mb-4 text-2xl font-bold">TripPilot AI - Health Check</h1>
      {error && (
        <p className="rounded bg-red-100 p-3 text-red-800">
          Backend unreachable: {error}
        </p>
      )}
      {!data && !error && <p>Checking backend...</p>}
      {data && (
        <pre className="rounded bg-slate-100 p-4 text-sm text-slate-900">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </main>
  );
}
