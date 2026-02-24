"use client";

import { Button } from "@/components/ui/button";
import { Sparkles, TrendingUp, Receipt, Wallet, HelpCircle } from "lucide-react";
import type { SuggestedQuestion } from "@/types/ai";

interface SuggestedQuestionsProps {
  suggestions: SuggestedQuestion[];
  onSelect: (question: string) => void;
  isLoading?: boolean;
}

const categoryIcons: Record<string, React.ReactNode> = {
  revenue: <TrendingUp className="h-4 w-4" />,
  customers: <Sparkles className="h-4 w-4" />,
  payments: <Wallet className="h-4 w-4" />,
  trends: <TrendingUp className="h-4 w-4" />,
  invoices: <Receipt className="h-4 w-4" />,
  receivables: <Receipt className="h-4 w-4" />,
  banking: <Wallet className="h-4 w-4" />,
  expenses: <Wallet className="h-4 w-4" />,
  transactions: <Wallet className="h-4 w-4" />,
  setup: <HelpCircle className="h-4 w-4" />,
};

export function SuggestedQuestions({
  suggestions,
  onSelect,
  isLoading = false,
}: SuggestedQuestionsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-12 bg-muted/50 rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="p-6 space-y-4">
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">Ask AI about your data</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Try one of these questions or type your own
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
        {suggestions.map((suggestion, i) => (
          <Button
            key={i}
            variant="outline"
            className="h-auto py-3 px-4 justify-start text-left whitespace-normal"
            onClick={() => onSelect(suggestion.question)}
          >
            <span className="mr-2 shrink-0">
              {categoryIcons[suggestion.category] || <HelpCircle className="h-4 w-4" />}
            </span>
            <span className="text-sm">{suggestion.question}</span>
          </Button>
        ))}
      </div>
    </div>
  );
}
