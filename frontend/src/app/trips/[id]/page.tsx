import { Suspense } from "react";
import { TripDetail } from "@/components/TripDetail";

export default function TripPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <Suspense fallback={<p className="text-slate-500">Loading...</p>}>
        {params.then(({ id }) => (
          <TripDetail id={id} />
        ))}
      </Suspense>
    </main>
  );
}
