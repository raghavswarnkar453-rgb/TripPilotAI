import { z } from "zod";
import {
  generateResponseSchema,
  saveTripResponseSchema,
  savedTripSummarySchema,
  type GenerateResponse,
  type TripFormValues,
} from "@/lib/trip-schema";
import { getAccessToken } from "@/lib/supabase";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      // FastAPI validation errors: [{ loc, msg }]
      return detail
        .slice(0, 2)
        .map((d: { msg?: string }) => String(d.msg ?? "Invalid input").replace(/^Value error, /, ""))
        .join(". ");
    }
  } catch {
    /* fall through */
  }
  return `The server responded with an error (${res.status}).`;
}

async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit & { auth?: boolean; timeoutMs?: number } = {},
): Promise<T> {
  const { auth, timeoutMs = 30_000, ...fetchInit } = init;
  const headers = new Headers(fetchInit.headers);
  if (fetchInit.body) headers.set("Content-Type", "application/json");
  if (auth) {
    const token = await getAccessToken();
    if (!token) throw new ApiError("Please sign in first.", 401);
    headers.set("Authorization", `Bearer ${token}`);
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchInit,
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "TimeoutError") {
      throw new ApiError("This is taking too long. Please try again in a moment.", 504);
    }
    throw new ApiError("Can't reach the TripPilot server. Make sure the backend is running.", 0);
  }

  if (!res.ok) throw new ApiError(await errorMessage(res), res.status);

  const parsed = schema.safeParse(await res.json().catch(() => null));
  if (!parsed.success) throw new ApiError("The server sent a response we couldn't understand.", 502);
  return parsed.data;
}

// --------------------------------------------------------------------- health
export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  supabase_configured: boolean;
  gemini_configured: boolean;
  groq_configured: boolean;
  weather_configured: boolean;
};

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Backend responded with ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------- trips
export function generateTrip(values: TripFormValues): Promise<GenerateResponse> {
  return request("/api/trips/generate", generateResponseSchema, {
    method: "POST",
    body: JSON.stringify({
      destination: values.destination,
      origin: values.origin || null,
      start_date: values.start_date,
      end_date: values.end_date,
      budget: values.budget,
      travelers: values.travelers,
      interests: values.interests,
      travel_style: values.travel_style,
    }),
    timeoutMs: 120_000,
  });
}

export function saveTrip(result: GenerateResponse) {
  return request("/api/trips", saveTripResponseSchema, {
    method: "POST",
    body: JSON.stringify({ result }),
    auth: true,
  });
}

export function listTrips() {
  return request("/api/trips", z.array(savedTripSummarySchema), { auth: true });
}

export function getTrip(id: string) {
  return request(`/api/trips/${encodeURIComponent(id)}`, generateResponseSchema, { auth: true });
}
