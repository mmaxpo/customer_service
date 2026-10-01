"use client";

import { useSyncExternalStore } from "react";

import { workspaceApi } from "./api/workspace";

export type Role = "agent" | "manager" | "admin" | "owner";

const RANK: Record<string, number> = { agent: 1, manager: 2, admin: 3, owner: 4 };

// One shared lookup of the signed-in person's role in the current workspace.
let role: Role | null = null;
let started = false;
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (!started) {
    started = true;
    workspaceApi
      .current()
      .then((workspace) => {
        role = (workspace.role as Role) ?? null;
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

/** The current role; null until it is known. */
export function useWorkspaceRole() {
  return useSyncExternalStore(subscribe, () => role, () => null);
}

/** True when `role` is at least `needed`. An unknown role allows nothing extra. */
export function roleAtLeast(current: Role | null, needed: Role | undefined) {
  return !needed || (current !== null && (RANK[current] ?? 0) >= RANK[needed]);
}
