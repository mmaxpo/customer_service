"use client";

import {
  useEffect,
} from "react";

import {
  eventBus,
} from "./EventBus";

export function useEvent<T>(
  type: string,
  handler: (payload:T)=>void,
) {

  useEffect(() => {

    return eventBus.subscribe(
      type,
      handler,
    );

  }, [type, handler]);

}
