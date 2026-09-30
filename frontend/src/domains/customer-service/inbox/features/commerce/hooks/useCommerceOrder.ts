"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiErrorMessage } from "@/platform/api/client";
import { Events, useEvent } from "@/platform/events";
import type { CommerceOrder } from "../model";
import { CommerceService } from "../services";

export function useCommerceOrder(orderRef: string | null) {
  const [order, setOrder] = useState<CommerceOrder | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeRef = useRef(orderRef);
  activeRef.current = orderRef;

  const load = useCallback(async (target: string) => {
    setLoading(true);
    try {
      const result = await CommerceService.order(target);
      if (activeRef.current !== target) return;
      setOrder(result);
      setError(null);
    } catch (err) {
      if (activeRef.current !== target) return;
      setError(apiErrorMessage(err, "Unable to load the order"));
    } finally {
      if (activeRef.current === target) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setOrder(null);
    setError(null);
    if (orderRef) void load(orderRef);
  }, [orderRef, load]);

  const refresh = useCallback(async () => {
    if (orderRef) await load(orderRef);
  }, [orderRef, load]);

  const onCommerceChanged = useCallback((payload?: { orderRef?: string }) => {
    if (!orderRef) return;
    if (payload?.orderRef && payload.orderRef !== orderRef) return;
    void load(orderRef);
  }, [orderRef, load]);

  useEvent<{ orderRef?: string } | undefined>(Events.CommerceChanged, onCommerceChanged);

  return { order, loading, error, refresh };
}
