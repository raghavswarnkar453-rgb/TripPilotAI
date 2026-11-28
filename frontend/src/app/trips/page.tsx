import { TripsList } from "@/components/TripsList";

export const metadata = { title: "My trips - TripPilot AI" };

export default function TripsPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="mb-6 text-3xl font-bold text-slate-900">My trips</h1>
      <TripsList />
    </main>
  );
}
