import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, qs } from "./client";
import type {
  CatalogStatus,
  CategorySpend,
  GmailStatus,
  ProductSummary,
  ReviewItem,
  Item,
  ItemDetail,
  JobRun,
  MonthSpend,
  Paginated,
  ReceiptDetail,
  ReceiptSummary,
  Summary,
  TopItems,
} from "./types";

export const useSummary = () =>
  useQuery({ queryKey: ["summary"], queryFn: () => api.get<Summary>("/analytics/summary/") });

export const useMonthly = (months: string) =>
  useQuery({
    queryKey: ["monthly", months],
    queryFn: () => api.get<MonthSpend[]>(`/analytics/monthly/${qs({ months })}`),
    placeholderData: keepPreviousData,
  });

export const useTopItems = (month: string) =>
  useQuery({
    queryKey: ["top-items", month],
    queryFn: () => api.get<TopItems>(`/analytics/top-items/${qs({ month })}`),
    placeholderData: keepPreviousData,
  });

export const useItems = (search: string, sort: string) =>
  useQuery({
    queryKey: ["items", search, sort],
    queryFn: () => api.get<Item[]>(`/analytics/items/${qs({ search, sort })}`),
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

export const useCategories = (month?: string) =>
  useQuery({
    queryKey: ["categories", month],
    queryFn: () => api.get<CategorySpend>(`/analytics/categories/${qs({ month })}`),
    placeholderData: keepPreviousData,
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

export function useCatalogSync() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: () => api.post("/catalog/sync/"),
    onSuccess: () => setTimeout(invalidate, 1500),
  });
}
