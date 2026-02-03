"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowRight, CreditCard, Database, Globe, MessageCircle, ShoppingBag, Smartphone, Table } from "lucide-react";
import Link from "next/link";
import { TemplateInfo } from "@/hooks/queries/useTemplates";

const ICON_MAP: Record<string, React.ElementType> = {
  "shopping-bag": ShoppingBag,
  "credit-card": CreditCard,
  "smartphone": Smartphone,
  "globe": Globe,
  "database": Database,
  "message-circle": MessageCircle,
  "table": Table,
};

interface TemplateCardProps {
  template: TemplateInfo;
  compact?: boolean;
}

export default function TemplateCard({ template, compact }: TemplateCardProps) {
  const Icon = ICON_MAP[template.icon] || Database;

  if (compact) {
    return (
      <Link href={`/templates/${template.id}`}>
        <Card className="hover:border-primary transition-colors cursor-pointer h-full">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 shrink-0">
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{template.name}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {template.source_type} → {template.destination_type}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </Link>
    );
  }

  return (
    <Card className="hover:border-primary transition-colors h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <Badge variant="secondary" className="text-xs">
            {template.category}
          </Badge>
        </div>
        <CardTitle className="text-base mt-3">{template.name}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">{template.description}</p>
          <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
            <Badge variant="outline" className="text-xs">
              {template.source_type}
            </Badge>
            <ArrowRight className="h-3 w-3" />
            <Badge variant="outline" className="text-xs">
              {template.destination_type}
            </Badge>
          </div>
        </div>
        <Link href={`/templates/${template.id}`}>
          <Button className="w-full" size="sm">
            Deploy
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
