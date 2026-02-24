"use client";

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ChartConfig } from "@/types/ai";
import { Card } from "@/components/ui/card";

interface ResultsChartProps {
  data: Record<string, unknown>[];
  config: ChartConfig;
}

const COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
];

export function ResultsChart({ data, config }: ResultsChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-muted-foreground">
        No data to display
      </div>
    );
  }

  const formatValue = (value: unknown, format?: string): string => {
    if (value === null || value === undefined) return "-";

    const num = Number(value);
    if (isNaN(num)) return String(value);

    switch (format) {
      case "currency":
        return new Intl.NumberFormat("en-GB", {
          style: "currency",
          currency: "GBP",
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(num);
      case "percent":
        return `${num.toFixed(1)}%`;
      case "integer":
        return Math.round(num).toLocaleString();
      default:
        return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
  };

  // Big Number display
  if (config.type === "number") {
    const value = data[0]?.[config.y_axis as string] ?? data[0]?.[Object.keys(data[0])[0]];
    const format = config.format?.[config.y_axis as string] || config.format?.value;

    return (
      <Card className="p-6 text-center">
        {config.title && (
          <p className="text-sm text-muted-foreground mb-2">{config.title}</p>
        )}
        <p className="text-4xl font-bold">{formatValue(value, format)}</p>
      </Card>
    );
  }

  // Line Chart
  if (config.type === "line") {
    const yAxes = Array.isArray(config.y_axis) ? config.y_axis : [config.y_axis];

    return (
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey={config.x_axis}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                // Format dates
                if (typeof value === "string" && value.match(/^\d{4}-\d{2}-\d{2}/)) {
                  return new Date(value).toLocaleDateString("en-GB", {
                    month: "short",
                    day: "numeric",
                  });
                }
                return value;
              }}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => formatValue(value, config.format?.[yAxes[0] as string])}
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                formatValue(value, config.format?.[name]),
                name,
              ]}
            />
            <Legend />
            {yAxes.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key as string}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Bar Chart
  if (config.type === "bar") {
    return (
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey={config.x_axis} tick={{ fontSize: 12 }} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(value) =>
                formatValue(value, config.format?.[config.y_axis as string])
              }
            />
            <Tooltip
              formatter={(value: number) => [
                formatValue(value, config.format?.[config.y_axis as string]),
                config.y_axis,
              ]}
            />
            <Bar dataKey={config.y_axis as string} fill={COLORS[0]} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Pie Chart
  if (config.type === "pie") {
    return (
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
              outerRadius={100}
              dataKey={config.y_axis as string}
              nameKey={config.x_axis}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [
                formatValue(value, config.format?.[config.y_axis as string]),
                config.y_axis,
              ]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Default to nothing (table is handled separately)
  return null;
}
