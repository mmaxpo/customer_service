"use client";

import { useSyncExternalStore } from "react";

import { liveApi, type WaitingConversation } from "./api";

const REFRESH_MS = 15_000;

// One shared poll for the whole app shell (menu badge + pop-up notice).
let waiting: WaitingConversation[] | null = null;
let timer: number | null = null;
const listeners = new Set<() => void>();

async function load() {
  try {
    waiting = (await liveApi.now()).waiting_for_person;
    listeners.forEach((listener) => listener());
  } catch {
    // Keep the last known list; the next poll retries.
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (timer === null) {
    void load();
    timer = window.setInterval(load, REFRESH_MS);
  }
  return () => {
    listeners.delete(listener);
    if (!listeners.size && timer !== null) {
      window.clearInterval(timer);
      timer = null;
    }
  };
}

/** Conversations waiting for a person; null until the first load. */
export function useWaitingForPerson() {
  return useSyncExternalStore(subscribe, () => waiting, () => null);
}
