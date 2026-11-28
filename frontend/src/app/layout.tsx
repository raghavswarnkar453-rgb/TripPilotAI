import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "TripPilot AI - Explore more. Plan smarter. Travel better.",
  description: "AI-powered travel planner: day-wise itineraries, weather, maps and budget estimates in seconds.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <Suspense fallback={<div className="h-16 border-b border-slate-200 bg-white" />}>
          <Navbar />
        </Suspense>
        <div className="flex-1">{children}</div>
        <footer className="border-t border-slate-200 bg-white py-6 text-center text-sm text-slate-500">
          TripPilot AI - plans and prices are AI-generated estimates. Check real prices before you book.
        </footer>
      </body>
    </html>
  );
}
