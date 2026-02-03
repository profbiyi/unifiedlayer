/**
 * Local currency display utilities.
 *
 * Provides currency conversion helpers and localStorage persistence
 * for showing plan prices in local African currencies.
 */

export interface CurrencyInfo {
  code: string;
  symbol: string;
  name: string;
  flag: string;
  rate: number; // Approximate rate vs 1 USD
}

export const CURRENCIES: CurrencyInfo[] = [
  { code: "USD", symbol: "$", name: "US Dollar", flag: "🇺🇸", rate: 1 },
  { code: "NGN", symbol: "₦", name: "Nigerian Naira", flag: "🇳🇬", rate: 1550 },
  { code: "KES", symbol: "KSh", name: "Kenyan Shilling", flag: "🇰🇪", rate: 153 },
  { code: "GHS", symbol: "GH₵", name: "Ghanaian Cedi", flag: "🇬🇭", rate: 15.5 },
  { code: "ZAR", symbol: "R", name: "South African Rand", flag: "🇿🇦", rate: 18.5 },
  { code: "XOF", symbol: "CFA", name: "West African CFA Franc", flag: "🇸🇳", rate: 610 },
  { code: "XAF", symbol: "FCFA", name: "Central African CFA Franc", flag: "🇨🇲", rate: 610 },
];

const STORAGE_KEY = "preferred_currency";

export function getSelectedCurrency(): string {
  if (typeof window === "undefined") return "USD";
  return localStorage.getItem(STORAGE_KEY) || "USD";
}

export function setSelectedCurrency(code: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, code);
}

export function getCurrencyInfo(code: string): CurrencyInfo {
  return CURRENCIES.find((c) => c.code === code) || CURRENCIES[0];
}

export function formatPrice(usdAmount: number, currencyCode: string): string {
  const currency = getCurrencyInfo(currencyCode);
  const converted = usdAmount * currency.rate;

  if (currency.code === "USD") {
    return `$${converted.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  }

  // For large numbers, use compact notation
  if (converted >= 1_000_000) {
    return `${currency.symbol}${(converted / 1_000_000).toFixed(1)}M`;
  }
  if (converted >= 1_000) {
    return `${currency.symbol}${(converted / 1_000).toFixed(0)}K`;
  }
  return `${currency.symbol}${converted.toFixed(0)}`;
}
