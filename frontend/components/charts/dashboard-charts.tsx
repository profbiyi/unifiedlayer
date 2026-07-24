"use client";

// Recharts is heavy (~100KB+). Keeping every chart here lets the dashboard
// pages dynamic-import this module so Recharts code-splits out of their
// initial bundle — the page shell paints immediately, charts fill in a beat
// later. See usage in overview/insights pages via next/dynamic.
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export function RunsLineChart({
  data,
}: {
  data: { date: string; completed: number; failed: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis allowDecimals={false} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="completed" stroke="#10b981" strokeWidth={2} name="Completed" />
        <Line type="monotone" dataKey="failed" stroke="#ef4444" strokeWidth={2} name="Failed" />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function VolumeAreaChart({
  data,
}: {
  data: { date: string; rows: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="rows" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" fontSize={12} />
        <YAxis tickFormatter={fmt} fontSize={12} />
        <Tooltip formatter={(v: number) => [v.toLocaleString(), "rows"]} />
        <Area type="monotone" dataKey="rows" stroke="#2563eb" strokeWidth={2} fill="url(#rows)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function SourcesBarChart({
  data,
}: {
  data: { name: string; sources: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
        <XAxis type="number" hide allowDecimals={false} />
        <YAxis type="category" dataKey="name" width={90} fontSize={12} />
        <Tooltip />
        <Bar dataKey="sources" fill="#2563eb" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// Stacked completed/failed runs per day — the real Analytics timeline chart.
export function RunsTimelineChart({
  data,
}: {
  data: { date: string; completed: number; failed: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" fontSize={11} interval="preserveStartEnd" />
        <YAxis allowDecimals={false} fontSize={12} />
        <Tooltip />
        <Legend />
        <Bar dataKey="completed" stackId="a" fill="#10b981" name="Completed" radius={[0, 0, 0, 0]} />
        <Bar dataKey="failed" stackId="a" fill="#ef4444" name="Failed" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// Rows synced by source type — horizontal bar for the Analytics breakdown.
export function SourceVolumeChart({
  data,
}: {
  data: { name: string; rows: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 44)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
        <XAxis type="number" tickFormatter={fmt} fontSize={12} />
        <YAxis type="category" dataKey="name" width={110} fontSize={12} />
        <Tooltip formatter={(v: number) => [v.toLocaleString(), "rows"]} />
        <Bar dataKey="rows" fill="#2563eb" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
