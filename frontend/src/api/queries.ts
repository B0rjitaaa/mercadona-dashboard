import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, qs } from "./client";
import type {
  CatalogStatus,
  CategorySpend,
  Comparison,
  Overview,
  GmailStatus,
  ProductSummary,
  ReviewItem,
  Item,
  ItemDetail,
  JobRun,
  MonthSpend,
  WeekSpend,
  PriceWatch,
  ReportStatus,
  Paginated,
  ReceiptDetail,
  ReceiptSummary,
  Summary,
} from "./types";

export const useSummary = () =>
  useQuery({ queryKey: ["summary"], queryFn: () => api.get<Summary>("/analytics/summary/") });

/** Period and section filter as API query params (FR-14). */
export interface FilterQuery {
  from?: string;
  to?: string;
  sections?: string;
}

export const useMonthly = (filters: FilterQuery) =>
  useQuery({
    queryKey: ["monthly", filters],
    queryFn: () =>
      api.get<MonthSpend[]>(
        `/analytics/monthly/${qs({ ...filters, months: filters.from || filters.to ? undefined : "all" })}`,
      ),
    placeholderData: keepPreviousData,
  });

export const useWeekly = (filters: FilterQuery, enabled = true) =>
  useQuery({
    queryKey: ["weekly", filters],
    queryFn: () => api.get<WeekSpend[]>(`/analytics/weekly/${qs({ ...filters })}`),
    enabled,
    placeholderData: keepPreviousData,
  });

export const useOverview = (filters: FilterQuery) =>
  useQuery({
    queryKey: ["overview", filters],
    queryFn: () => api.get<Overview>(`/analytics/overview/${qs({ ...filters })}`),
    placeholderData: keepPreviousData,
  });

export interface CompareQuery {
  a_from: string;
  a_to: string;
  b_from: string;
  b_to: string;
  sections?: string;
}

export const useCompare = (params: CompareQuery | null) =>
  useQuery({
    queryKey: ["compare", params],
    queryFn: () => api.get<Comparison>(`/analytics/compare/${qs({ ...params })}`),
    enabled: params !== null,
    placeholderData: keepPreviousData,
  });

export interface ItemsQuery extends FilterQuery {
  search?: string;
  sort?: string;
  status?: string;
  min_purchases?: string;
  trend?: string;
}

export const useItems = (filters: ItemsQuery) =>
  useQuery({
    queryKey: ["items", filters],
    queryFn: () => api.get<Item[]>(`/analytics/items/${qs({ ...filters })}`),
    placeholderData: keepPreviousData,
  });

/** "p123" -> catalogue product 123; "d:LECHE DESN" -> unidentified receipt description. */
export const useItem = (key: string) =>
  useQuery({
    queryKey: ["item", key],
    queryFn: () =>
      key.startsWith("p")
        ? api.get<ItemDetail>(`/analytics/products/${key.slice(1)}/`)
        : api.get<ItemDetail>(`/analytics/items/detail/${qs({ description: key.slice(2) })}`),
  });

export const usePriceWatch = (days = 30) =>
  useQuery({
    queryKey: ["prices", days],
    queryFn: () => api.get<PriceWatch>(`/analytics/prices/${qs({ days })}`),
    placeholderData: keepPreviousData,
  });

/** All-time sections with their ids: the options of the section filter. */
export const useSections = () =>
  useQuery({
    queryKey: ["categories", "all"],
    queryFn: () => api.get<CategorySpend>("/analytics/categories/"),
    staleTime: 5 * 60 * 1000,
  });

export const useReview = () =>
  useQuery({ queryKey: ["review"], queryFn: () => api.get<ReviewItem[]>("/review/") });

export const useCatalogStatus = () =>
  useQuery({
    queryKey: ["catalog-status"],
    queryFn: () => api.get<CatalogStatus>("/catalog/status/"),
    refetchInterval: (query) => (query.state.data?.last_sync?.status === "running" ? 3000 : false),
  });

export const useCatalogSearch = (q: string) =>
  useQuery({
    queryKey: ["catalog-search", q],
    queryFn: () => api.get<ProductSummary[]>(`/catalog/search/${qs({ q })}`),
    enabled: q.trim().length >= 2,
    placeholderData: keepPreviousData,
  });

export interface ReceiptFilters {
  page?: number;
  search?: string;
  status?: string;
  kind?: string;
  date_from?: string;
  date_to?: string;
}

export const useReceipts = (filters: ReceiptFilters) =>
  useQuery({
    queryKey: ["receipts", filters],
    queryFn: () =>
      api.get<Paginated<ReceiptSummary>>(`/receipts/${qs({ ...filters })}`),
    placeholderData: keepPreviousData,
  });

export const useReceipt = (id: string) =>
  useQuery({
    queryKey: ["receipt", id],
    queryFn: () => api.get<ReceiptDetail>(`/receipts/${id}/`),
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 1500 : false),
  });

export const useGmailStatus = () =>
  useQuery({
    queryKey: ["gmail-status"],
    queryFn: () => api.get<GmailStatus>("/gmail/status/"),
    refetchInterval: (query) => (query.state.data?.last_run?.status === "running" ? 2000 : false),
  });

export const useJobs = () =>
  useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.get<Paginated<JobRun>>("/jobs/"),
  });

function useInvalidateAll() {
  const client = useQueryClient();
  return () => client.invalidateQueries();
}

export function useSyncNow() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: () => api.post<{ task_id: string }>("/gmail/sync/"),
    // The sync runs in the background; refresh shortly after and again later.
    onSuccess: () => {
      setTimeout(invalidate, 1500);
      setTimeout(invalidate, 8000);
    },
  });
}

export function useUploadReceipt() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api.post<ReceiptDetail>("/receipts/upload/", body);
    },
    onSuccess: () => setTimeout(invalidate, 1000),
  });
}

export function useReprocessReceipt(id: number) {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: () => api.post(`/receipts/${id}/reprocess/`),
    onSuccess: () => setTimeout(invalidate, 1000),
  });
}

export function useDeleteReceipt(id: number) {
  const invalidate = useInvalidateAll();
  return useMutation({ mutationFn: () => api.delete(`/receipts/${id}/`), onSuccess: invalidate });
}

function jsonBody(data: unknown): BodyInit {
  return new Blob([JSON.stringify(data)], { type: "application/json" });
}

export function useLinkDescription() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (v: { description: string; product_id: number }) => api.post("/review/link/", jsonBody(v)),
    onSuccess: invalidate,
  });
}

export function useUnlinkDescription() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (description: string) => api.post("/review/unlink/", jsonBody({ description })),
    onSuccess: () => {
      invalidate();
      setTimeout(invalidate, 2000);
    },
  });
}

export function useManualProduct() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (v: { description: string; name: string }) =>
      api.post<ProductSummary>("/review/manual/", jsonBody(v)),
    onSuccess: invalidate,
  });
}

export function useRematch() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: () => api.post("/review/rematch/"),
    onSuccess: () => {
      setTimeout(invalidate, 2000);
      setTimeout(invalidate, 8000);
    },
  });
}

export const useReportStatus = () =>
  useQuery({
    queryKey: ["report-status"],
    queryFn: () => api.get<ReportStatus>("/reports/weekly/"),
    refetchInterval: (query) => (query.state.data?.last_run?.status === "running" ? 2000 : false),
  });

export function useSendReport() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: () => api.post<{ task_id: string }>("/reports/weekly/send/"),
    onSuccess: () => {
      setTimeout(invalidate, 1500);
      setTimeout(invalidate, 6000);
    },
  });
}

export function useCatalogSync() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: () => api.post("/catalog/sync/"),
    onSuccess: () => setTimeout(invalidate, 1500),
  });
}
