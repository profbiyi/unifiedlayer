import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface SourceCardSkeletonProps {
  count?: number;
}

function SourceCardSkeleton({ count = 6 }: SourceCardSkeletonProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                {/* Icon container */}
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="space-y-1.5">
                  {/* Source name */}
                  <Skeleton className="h-5 w-32" />
                  {/* Type badge */}
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
              </div>
              {/* Action buttons */}
              <div className="flex gap-1">
                <Skeleton className="h-8 w-8 rounded-md" />
                <Skeleton className="h-8 w-8 rounded-md" />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Description */}
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-3/4 mb-2" />
            {/* Created date */}
            <Skeleton className="h-3 w-28" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export { SourceCardSkeleton };
