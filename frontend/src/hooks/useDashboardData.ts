import { useCallback, useEffect, useState } from "react";
import type { DashboardData } from "@/lib/api";
import { fetchDashboard, getCachedDashboard } from "@/lib/api";

const MAX_STALE_RETRIES = 10;
const STALE_RETRY_BASE_MS = 10000;
const STALE_RETRY_FACTOR = 1.5;
const STALE_RETRY_CAP_MS = 60000;

export interface DashboardDataState {
  data: DashboardData | null;
  loading: boolean;
  refreshing: boolean;
  error: string;
  stale: boolean;
  cachedAt: string | undefined;
}

export function useDashboardData(token: string): DashboardDataState & { load: () => Promise<void> } {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const [cachedAt, setCachedAt] = useState<string | undefined>();
  const [retryCount, setRetryCount] = useState(0);

  const load = useCallback(async () => {
    try {
      setError("");

      setData((prev) => {
        if (prev) {
          setRefreshing(true);
          return prev;
        }
        const cached = getCachedDashboard(token);
        if (cached) {
          setLoading(false);
          setRefreshing(true);
          setStale(true);
          setCachedAt(cached.cachedAt);
          return cached.data;
        }
        setLoading(true);
        return null;
      });

      const result = await fetchDashboard(token);
      setData(result.data);
      setStale(result.stale);
      setCachedAt(result.cachedAt);
      if (!result.stale) {
        setRetryCount(0);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load dashboard.";
      setData((prev) => {
        if (!prev) {
          setError(message);
        }
        return prev;
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!stale || retryCount >= MAX_STALE_RETRIES) return;
    const backoffMs = Math.min(
      STALE_RETRY_BASE_MS * Math.pow(STALE_RETRY_FACTOR, retryCount),
      STALE_RETRY_CAP_MS
    );
    const timer = window.setTimeout(() => {
      setRetryCount((count) => count + 1);
      load();
    }, backoffMs);

    return () => window.clearTimeout(timer);
  }, [stale, retryCount, load]);

  return { data, loading, refreshing, error, stale, cachedAt, load };
}
