"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { AlertTriangle } from "lucide-react";
import type { GenerateResponse } from "@/lib/trip-schema";
import { CATEGORY_LABELS, formatINR } from "@/lib/format";

const COLORS = ["#0d9488", "#f59e0b", "#6366f1", "#ec4899", "#0ea5e9", "#84cc16"];

function Stat({ label, value, tone = "text-slate-900" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-xl font-bold ${tone}`}>{value}</p>
    </div>
  );
}

export function BudgetView({ budget, travelers }: { budget: GenerateResponse["budget"]; travelers: number }) {
  const data = budget.lines
    .filter((l) => l.amount > 0)
    .map((l) => ({ name: CATEGORY_LABELS[l.category] ?? l.category, value: l.amount }));
  const pct = budget.budget > 0 ? Math.min(100, Math.round((budget.total_estimated / budget.budget) * 100)) : 0;

  return (
    <div className="space-y-5">
      {budget.over_budget && (
        <p className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          The estimate is {formatINR(Math.abs(budget.remaining))} over your budget. Try fewer days, a calmer style or a larger budget.
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Estimated total" value={formatINR(budget.total_estimated)} />
        <Stat label={`Per traveller (${travelers})`} value={formatINR(budget.per_traveler)} />
        <Stat label="Your budget" value={formatINR(budget.budget)} />
        <Stat
          label={budget.remaining >= 0 ? "Remaining" : "Over budget by"}
          value={formatINR(Math.abs(budget.remaining))}
          tone={budget.remaining >= 0 ? "text-teal-700" : "text-red-600"}
        />
      </div>

      <div className="h-2.5 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Budget used">
        <div className={`h-full ${budget.over_budget ? "bg-red-500" : "bg-teal-500"}`} style={{ width: `${pct}%` }} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-2 font-semibold text-slate-900">Where the money goes</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={95} paddingAngle={2} isAnimationActive={false}>
                  {data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatINR(Number(v))} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-2 font-semibold text-slate-900">Breakdown (whole group)</h3>
          <table className="w-full text-sm">
            <tbody>
              {budget.lines.map((l, i) => (
                <tr key={l.category} className="border-b border-slate-100 last:border-0">
                  <td className="py-2">
                    <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: COLORS[i % COLORS.length] }} />
                    {CATEGORY_LABELS[l.category] ?? l.category}
                  </td>
                  <td className="py-2 text-right font-medium">{formatINR(l.amount)}</td>
                </tr>
              ))}
              <tr>
                <td className="pt-3 font-semibold">Total (estimate)</td>
                <td className="pt-3 text-right font-bold">{formatINR(budget.total_estimated)}</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-4 text-xs text-slate-500">{budget.disclaimer}</p>
        </div>
      </div>
    </div>
  );
}
