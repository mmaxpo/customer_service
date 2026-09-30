"use client";

import {
  eventBus,
} from "./EventBus";

export function usePublish() {

  return eventBus.publish.bind(
    eventBus,
  );

}
