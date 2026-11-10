/** Decimals come from the API as strings to keep them exact. */
export type Money = string;

export type ReceiptStatus = "pending" | "processed" | "needs_review" | "error";
export type ReceiptKind = "sale" | "return";
export type LineType = "product" | "discount" | "return" | "other";
export type Unit = "unit" | "kg";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Store {
  id: number;
  chain: string;
  code: string;
  address: string;
  postal_code: string;
  city: string;
  phone: string;
}

export interface ReceiptSummary {
  id: number;
  invoice_number: string | null;
  kind: ReceiptKind;
  issued_at: string | null;
  store: Store | null;
  total: Money | null;
  payment_method: string;
  status: ReceiptStatus;
  source: "upload" | "gmail";
  line_count: number;
  created_at: string;
}

export interface ReceiptLine {
  id: number;
  position: number;
  line_type: LineType;
  description: string;
  quantity: string;
  unit: Unit;
  unit_price: Money;
  amount: Money;
}

export interface VatRate {
  rate: string;
  base: Money;
  tax: Money;
  total: Money | "None" | null;
}

export interface ReceiptDetail extends ReceiptSummary {
  operation_number: string;
  original_invoice_number: string;
  vat_breakdown: VatRate[];
  warnings: string[];
  error_message: string;
  parsed_at: string | null;
  pdf: string;
  lines: ReceiptLine[];
}

export interface JobRun {
  id: number;
  job: string;
  status: "running" | "success" | "failed";
  started_at: string;
  finished_at: string | null;
  stats: Record<string, number>;
  error: string;
}

export interface MonthSpend {
  month: string; // YYYY-MM
  total: Money;
  receipts: number;
  average_receipt: Money;
}

export interface Summary {
  current_month: MonthSpend;
  previous_month: MonthSpend;
  average_month_12: Money;
  all_time: { total: Money; receipts: number };
  pending: { needs_review: number; error: number };
  last_sync: JobRun | null;
}

export interface TopItem {
  description: string;
  spent: Money;
  purchases: number;
  quantity: string;
}

export interface TopItems {
  month: string;
  by_spend: TopItem[];
  by_purchases: TopItem[];
}

export interface Item {
  description: string;
  unit: Unit;
  purchases: number;
  quantity: string;
  spent: Money;
  first_purchase: string;
  last_purchase: string;
  min_price: Money;
  max_price: Money;
  first_price: Money;
  last_price: Money;
  price_change: Money;
  price_change_pct: string | null;
  trend: Money[];
}

export interface ItemDetail extends Omit<Item, "trend"> {
  frequency_days: number | null;
  average_price: Money;
  monthly: { month: string; spent: Money; quantity: string }[];
  history: {
    date: string;
    receipt_id: number;
    quantity: string;
    unit: Unit;
    unit_price: Money;
    amount: Money;
  }[];
}

export interface GmailStatus {
  credentials_configured: boolean;
  authorised: boolean;
  query: string;
  last_run: JobRun | null;
}
