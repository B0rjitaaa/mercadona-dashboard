import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, qs } from "./client";
import type {
  GmailStatus,
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

export const useItem = (description: string) =>
  useQuery({
    queryKey: ["item", description],
    queryFn: () => api.get<ItemDetail>(`/analytics/items/detail/${qs({ description })}`),
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
