"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

// ReactFlow + dagre are heavy graph libraries (~65KB). Loading the lineage
// view dynamically keeps them out of the initial bundle so the route paints
// a skeleton immediately and the graph streams in.
const LineageView = dynamic(() => import("@/components/lineage/LineageView"), {
  ssr: false,
  loading: () => (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-[600px] w-full" />
    </div>
  ),
});

export default function LineagePage() {
  return <LineageView />;
}
