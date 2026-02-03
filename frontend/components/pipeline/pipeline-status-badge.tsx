import { Badge } from "@/components/ui/badge";

interface PipelineStatusBadgeProps {
  isActive: boolean;
}

export default function PipelineStatusBadge({
  isActive,
}: PipelineStatusBadgeProps) {
  return (
    <Badge variant={isActive ? "success" : "secondary"}>
      {isActive ? "Active" : "Inactive"}
    </Badge>
  );
}
