import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface StatsCardSkeletonProps {
  count?: number;
}

function StatsCardSkeleton({ count = 4 }: StatsCardSkeletonProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            {/* Title */}
            <Skeleton className="h-4 w-24" />
            {/* Icon */}
            <Skeleton className="h-4 w-4 rounded" />
          </CardHeader>
          <CardContent>
            {/* Value */}
            <Skeleton className="h-8 w-16 mb-1" />
            {/* Description */}
            <Skeleton className="h-3 w-28" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export { StatsCardSkeleton };
