import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface TableRowSkeletonProps {
  count?: number;
}

function TableRowSkeleton({ count = 5 }: TableRowSkeletonProps) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                {/* Status icon */}
                <Skeleton className="h-5 w-5 rounded-full" />
                <div className="space-y-1">
                  {/* Title */}
                  <Skeleton className="h-5 w-48" />
                  {/* Timestamp */}
                  <Skeleton className="h-4 w-36" />
                </div>
              </div>
              {/* Status badge */}
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              {/* Started */}
              <div className="space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-24" />
              </div>
              {/* Duration */}
              <div className="space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-20" />
              </div>
              {/* Rows Written */}
              <div className="space-y-1">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-4 w-16" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export { TableRowSkeleton };
