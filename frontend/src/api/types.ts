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
  product: number | null;
  product_name: string | null;
  product_thumbnail: string | null;
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

/** An item is a catalogue product, or a receipt description not yet identified. */
export interface ItemIdentity {
  key: string;
  product_id: number | null;
  name: string;
  packaging: string;
  thumbnail: string;
  section: string | null;
  description: string | null;
}

export interface TopItem extends ItemIdentity {
  spent: Money;
  purchases: number;
  quantity: string;
}

export interface TopItems {
  month: string;
  by_spend: TopItem[];
  by_purchases: TopItem[];
}

export interface Item extends ItemIdentity {
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
  product: {
    mercadona_id: string | null;
    share_url: string;
    unit_price: Money | null;
    bulk_price: Money | null;
    reference_price: string | null;
    reference_format: string;
    is_active: boolean;
    is_manual: boolean;
    category_path: string[];
  } | null;
  aliases: { description: string; source: "auto" | "manual"; score: string | null }[];
  catalog_prices: { date: string; price: Money }[];
  monthly: { month: string; spent: Money; quantity: string }[];
  history: {
    date: string;
    receipt_id: number;
    description: string;
    quantity: string;
    unit: Unit;
    unit_price: Money;
    amount: Money;
  }[];
}

/** `id: null` groups lines without a catalogue category (filter token "none"). */
export interface SectionSpend {
  id: number | null;
  section: string | null;
  spent: Money;
  share: string;
  items: number;
}

export interface CategorySpend {
  month: string | null;
  total: Money;
  sections: SectionSpend[];
}

export interface PeriodTotals {
  from: string | null;
  to: string | null;
  total: Money;
  receipts: number;
  average_receipt: Money;
}

export interface Overview extends PeriodTotals {
  sections_filter: (number | "none")[];
  months: number;
  average_month: Money;
  previous: PeriodTotals | null;
  by_spend: TopItem[];
  by_purchases: TopItem[];
  sections: SectionSpend[];
}

export interface ItemChange extends ItemIdentity {
  a_spent: Money;
  b_spent: Money;
  diff: Money;
  a_purchases: number;
  b_purchases: number;
  a_quantity: string;
  b_quantity: string;
  /** null when the item was only bought in one of the periods */
  price_effect: Money | null;
  quantity_effect: Money | null;
}

export interface Comparison {
  a: PeriodTotals;
  b: PeriodTotals;
  diff: Money;
  diff_pct: string | null;
  sections_filter: (number | "none")[];
  sections: { id: number | null; section: string | null; a: Money; b: Money; diff: Money }[];
  increases: ItemChange[];
  decreases: ItemChange[];
  new_items: number;
  dropped_items: number;
}

export interface ProductSummary {
  id: number;
  mercadona_id: string | null;
  name: string;
  packaging: string;
  thumbnail: string;
  share_url: string;
  unit_price: Money | null;
  bulk_price: Money | null;
  reference_price: string | null;
  reference_format: string;
  is_active: boolean;
  is_manual: boolean;
  category_path: string[];
}

export interface ReviewItem {
  description: string;
  purchases: number;
  spent: Money;
  last_purchase: string;
  last_price: Money | null;
  unit: Unit;
  suggestions: { score: string; product: ProductSummary }[];
}

export interface CatalogStatus {
  products: number;
  active: number;
  manual: number;
  aliases: number;
  unmatched: number;
  last_sync: JobRun | null;
}

export interface GmailStatus {
  credentials_configured: boolean;
  authorised: boolean;
  query: string;
  last_run: JobRun | null;
}

export interface PriceRow extends ItemIdentity {
  unit: Unit;
  variable_weight: boolean;
  catalog_per_kg: boolean;
  purchases: number;
  quantity_12m: string;
  spent_12m: Money;
  last_paid: Money;
  last_paid_at: string;
  catalog_price: Money;
  diff: Money | null;
  diff_pct: string | null;
  impact_12m: Money | null;
  is_active: boolean;
  catalog_previous: Money | null;
  catalog_changed_at: string | null;
  catalog_change_pct: string | null;
}

export interface PriceWatch {
  regular_products: number;
  summary: {
    up: number;
    down: number;
    impact_12m: Money;
    inflation_12m: string | null;
    inflation_products: number;
  };
  alerts: PriceRow[];
  check_links: PriceRow[];
  recent_changes: PriceRow[];
  recent_days: number;
  rules: { min_purchases: number; within_days: number; min_pct: string; suspicious_pct: string };
}
