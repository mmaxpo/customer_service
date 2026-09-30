"use client";

import { useEffect } from "react";
import { useRunStore, type RunHydration } from "../store/runStore";
import { workflowApi } from "@/platform/api";

export function useRunHydration(runId: string) {
    const setHydration = useRunStore((s) => s.setHydration);
    const reset = useRunStore((s) => s.reset);
    useEffect(() => {
        let cancelled = false;
        reset();
        (async () => {
            const data = (await workflowApi.runState(runId)) as RunHydration;
            console.log("RUN RESPONSE", data);
            if (!cancelled) setHydration(data);
        })().catch(() => {});

        return () => {
            cancelled = true;
        };
    }, [runId, setHydration, reset]);
}