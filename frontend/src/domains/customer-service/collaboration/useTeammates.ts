"use client";

import { useSyncExternalStore } from "react";

import { apiJson } from "@/platform/api/client";

export type Teammate = { user_id: string; name: string; email: string; role: string };

// One shared list of the workspace's active members (assigning, mentioning, routing).
let teammates: Teammate[] | null = null;
let started = false;
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (!started) {
    started = true;
    apiJson<Teammate[]>("/api/customer-service/studio/teammates")
      .then((result) => {
        teammates = result;
        listeners.forEach((notify) => notify());
      })
      .catch(() => {
        started = false;
      });
  }
  return () => {
    listeners.delete(listener);
  };
}

/** Active team members; null until loaded. */
export function useTeammates() {
  return useSyncExternalStore(subscribe, () => teammates, () => null);
}
