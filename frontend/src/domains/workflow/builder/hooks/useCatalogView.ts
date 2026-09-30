import { useMemo } from "react";
import type { CatalogItem } from "@/domains/workflow/builder/types/catalog";

export function useCatalogView(catalog: CatalogItem[]) {
    const catalogByType = useMemo(() => {
        const map = new Map<string, CatalogItem>();

        for (const item of catalog ?? []) {
            map.set(item.node_type, item);
        }

        return map;
    }, [catalog]);

    const groupedCatalog = useMemo(() => {
        const items = [...(catalog ?? [])].sort((a, b) => {
            const groupCompare = (a.group || "Other").localeCompare(
                b.group || "Other"
            );

            if (groupCompare !== 0) return groupCompare;

            return (a.title || a.node_type).localeCompare(b.title || b.node_type);
        });

        const grouped = new Map<string, CatalogItem[]>();

        for (const item of items) {
            const group = item.group || "Other";
            grouped.set(group, [...(grouped.get(group) ?? []), item]);
        }

        return grouped;
    }, [catalog]);

    return {
        catalogByType,
        groupedCatalog,
    };
}