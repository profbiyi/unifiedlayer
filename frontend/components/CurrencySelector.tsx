"use client";

import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CURRENCIES,
  getSelectedCurrency,
  setSelectedCurrency,
} from "@/lib/currency";

interface CurrencySelectorProps {
  onChange?: (code: string) => void;
}

export default function CurrencySelector({ onChange }: CurrencySelectorProps) {
  const [selected, setSelected] = useState("USD");

  useEffect(() => {
    setSelected(getSelectedCurrency());
  }, []);

  const handleChange = (code: string) => {
    setSelected(code);
    setSelectedCurrency(code);
    onChange?.(code);
  };

  return (
    <Select value={selected} onValueChange={handleChange}>
      <SelectTrigger className="w-[180px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {CURRENCIES.map((c) => (
          <SelectItem key={c.code} value={c.code}>
            <span className="flex items-center gap-2">
              <span>{c.flag}</span>
              <span>{c.code}</span>
              <span className="text-muted-foreground text-xs">({c.symbol})</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
