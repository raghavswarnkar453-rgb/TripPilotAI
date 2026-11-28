/**
 * API contract for TripPilot AI - mirrors backend/app/schemas/trip.py and saved.py.
 * Change both together. Every API response is parsed with these schemas before it is shown.
 */
import { z } from "zod";

export const MAX_TRIP_DAYS = 14;
export const INTERESTS = [
  "Adventure",
  "Nature",
  "Food",
  "Culture",
  "History",
  "Shopping",
  "Relaxation",
  "Nightlife",
] as const;

export const TRAVEL_STYLES = [
  { value: "relaxed", label: "Relaxed", hint: "Slow pace" },
  { value: "balanced", label: "Balanced", hint: "Mix of both" },
  { value: "packed", label: "Packed", hint: "See it all" },
] as const;

export type TravelStyle = (typeof TRAVEL_STYLES)[number]["value"];

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TEXT_RE = /^[\w\s,.'()&\-]+$/;

function dayNumber(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d) / 86_400_000;
}

/** Form validation (runs in the browser before calling the API). `today` is passed in, never read here. */
export function makeTripFormSchema(today: string) {
  return z
    .object({
      destination: z
        .string()
        .trim()
        .min(2, "Enter a destination (at least 2 characters)")
        .max(100, "Destination is too long")
        .regex(TEXT_RE, "Use letters, numbers and basic punctuation only"),
      origin: z
        .string()
        .trim()
        .max(100, "Too long")
        .refine((v) => v === "" || TEXT_RE.test(v), "Use letters, numbers and basic punctuation only"),
      start_date: z.string().regex(DATE_RE, "Pick a start date"),
      end_date: z.string().regex(DATE_RE, "Pick an end date"),
      budget: z
        .number({ error: "Enter your total budget in INR" })
        .positive("Budget must be more than 0")
        .max(100_000_000, "Budget is too large"),
      travelers: z.number({ error: "Enter number of travellers" }).int().min(1, "At least 1 traveller").max(50, "Maximum 50"),
      interests: z.array(z.string()).max(8),
      travel_style: z.enum(["relaxed", "balanced", "packed"]),
    })
    .superRefine((v, ctx) => {
      if (!DATE_RE.test(v.start_date) || !DATE_RE.test(v.end_date)) return;
      if (today && v.start_date < today) {
        ctx.addIssue({ code: "custom", path: ["start_date"], message: "Start date can't be in the past" });
      }
      if (v.end_date < v.start_date) {
        ctx.addIssue({ code: "custom", path: ["end_date"], message: "End date must be on or after the start date" });
      } else if (dayNumber(v.end_date) - dayNumber(v.start_date) + 1 > MAX_TRIP_DAYS) {
        ctx.addIssue({ code: "custom", path: ["end_date"], message: `Trips are limited to ${MAX_TRIP_DAYS} days` });
      }
    });
}

export type TripFormValues = z.infer<ReturnType<typeof makeTripFormSchema>>;

// ------------------------------------------------------------------ response
const timeSlot = z.enum(["morning", "afternoon", "evening"]);
const dataStatus = z.enum(["ok", "unavailable"]);

const tripRequest = z.object({
  destination: z.string(),
  origin: z.string().nullish(),
  start_date: z.string(),
  end_date: z.string(),
  budget: z.number(),
  travelers: z.number(),
  interests: z.array(z.string()).default([]),
  travel_style: z.enum(["relaxed", "balanced", "packed"]).default("balanced"),
});

const itineraryItem = z.object({
  time_slot: timeSlot,
  title: z.string(),
  description: z.string().default(""),
  duration_minutes: z.number().nullish(),
  estimated_cost: z.number().default(0),
  place_ref: z.number().nullish(),
  latitude: z.number().nullish(),
  longitude: z.number().nullish(),
});

const dayPlan = z.object({
  day_number: z.number(),
  date: z.string().nullish(),
  title: z.string().default(""),
  summary: z.string().default(""),
  items: z.array(itineraryItem),
});

const itineraryPlan = z.object({
  summary: z.string().default(""),
  days: z.array(dayPlan),
  cost_estimates: z.record(z.string(), z.number()).default({}),
  tips: z.array(z.string()).default([]),
});

const destination = z.object({
  query: z.string(),
  display_name: z.string(),
  latitude: z.number(),
  longitude: z.number(),
});

const weatherDay = z.object({
  date: z.string(),
  temp_max_c: z.number().nullish(),
  temp_min_c: z.number().nullish(),
  precipitation_mm: z.number().nullish(),
  precipitation_probability: z.number().nullish(),
  condition: z.string().nullish(),
});

const weather = z.object({
  status: dataStatus,
  source: z.enum(["forecast", "historical"]).nullish(),
  note: z.string().nullish(),
  days: z.array(weatherDay).default([]),
});

const attraction = z.object({
  name: z.string(),
  category: z.string().nullish(),
  latitude: z.number(),
  longitude: z.number(),
});

export const EXPENSE_CATEGORIES = ["transport", "accommodation", "food", "tickets", "local_travel", "misc"] as const;

const budgetSummary = z.object({
  currency: z.string().default("INR"),
  lines: z.array(z.object({ category: z.string(), amount: z.number() })),
  total_estimated: z.number(),
  per_traveler: z.number(),
  budget: z.number(),
  remaining: z.number(),
  over_budget: z.boolean(),
  is_estimate: z.boolean().default(true),
  disclaimer: z.string().default("These are estimates, not confirmed booking prices."),
});

export const generateResponseSchema = z.object({
  request: tripRequest,
  destination: destination.nullable(),
  weather,
  attractions: z.array(attraction).default([]),
  attractions_status: dataStatus,
  itinerary: itineraryPlan,
  budget: budgetSummary,
  warnings: z.array(z.string()).default([]),
  model: z.string(),
  generated_at: z.string(),
});

export const saveTripResponseSchema = z.object({ id: z.string(), already_saved: z.boolean().default(false) });

export const savedTripSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  destination: z.string(),
  start_date: z.string(),
  end_date: z.string(),
  budget: z.number(),
  travelers: z.number(),
  created_at: z.string(),
});

export type GenerateResponse = z.infer<typeof generateResponseSchema>;
export type DayPlan = z.infer<typeof dayPlan>;
export type ItineraryItem = z.infer<typeof itineraryItem>;
export type WeatherDay = z.infer<typeof weatherDay>;
export type SavedTripSummary = z.infer<typeof savedTripSummarySchema>;
