import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface PipelineCardSkeletonProps {
  count?: number;
}

function PipelineCardSkeleton({ count = 3 }: PipelineCardSkeletonProps) {
  return (
    <div className="grid gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-3">
                  {/* Pipeline name */}
                  <Skeleton className="h-6 w-48" />
                  {/* Status badge */}
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
                {/* Description */}
                <Skeleton className="h-4 w-72" />
                {/* Source -> Destination */}
                <div className="flex gap-4">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-4" />
                  <Skeleton className="h-4 w-36" />
                </div>
                {/* Created date */}
                <Skeleton className="h-3 w-56" />
              </div>
              {/* Action buttons */}
              <div className="flex gap-2">
                <Skeleton className="h-8 w-8 rounded-md" />
                <Skeleton className="h-8 w-8 rounded-md" />
                <Skeleton className="h-8 w-8 rounded-md" />
              </div>
            </div>
          </CardHeader>
        </Card>
      ))}
    </div>
  );
}

export { PipelineCardSkeleton };
