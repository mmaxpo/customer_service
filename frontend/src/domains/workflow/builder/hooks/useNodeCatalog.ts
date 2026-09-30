import { useEffect, useState } from "react";
import type {
    CatalogItem,
    CatalogResponse,
} from "@/domains/workflow/builder/types/catalog";
import { workflowApi } from "@/platform/api";

export function useNodeCatalog() {
    const [catalog, setCatalog] = useState<CatalogItem[]>([]);
    const [catalogStatus, setCatalogStatus] = useState(
        "Loading node catalog..."
    );

    useEffect(() => {
        let cancelled = false;

        async function loadCatalog() {
            try {
                const data = (await workflowApi.catalogNodes()) as CatalogResponse;

                if (!cancelled) {
                    setCatalog(data.items ?? []);
                    setCatalogStatus(`OK (${(data.items ?? []).length} nodes)`);
                }
            } catch (e: any) {
                if (!cancelled) {
                    setCatalogStatus(`Catalog error: ${String(e?.message ?? e)}`);
                }
            }
        }

        loadCatalog();

        return () => {
            cancelled = true;
        };
    }, []);

    return {
        catalog,
        catalogStatus,
    };
}