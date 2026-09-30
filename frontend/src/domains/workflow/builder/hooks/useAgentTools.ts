
import { useEffect, useState } from "react";
import { toolsApi, type AgentToolCatalogItem } from "@/platform/api";

export function useAgentTools() {
    const [tools, setTools] = useState<AgentToolCatalogItem[]>([]);
    const [status, setStatus] = useState("");

    useEffect(() => {
        let cancelled = false;

        async function load() {
            setStatus("Loading tools...");

            try {
                const data = await toolsApi.list();

                if (!cancelled) {
                    setTools(data.tools || []);
                    setStatus(`Loaded ${data.tools?.length ?? 0} tools`);
                }
            } catch (e: any) {
                if (!cancelled) {
                    setStatus(`Tools error: ${String(e?.message ?? e)}`);
                }
            }
        }

        load();

        return () => {
            cancelled = true;
        };
    }, []);

    return { tools, status };
}