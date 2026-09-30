import type { CatalogItem } from "../types/catalog";

export function pickEditableProps(schema: any): string[] {
    const props = schema?.properties ?? {};
    const keys = Object.keys(props);
    return keys.filter((k) => k !== "node_type" && k !== "nodeType");
}

export function safeNodeLabel(item: CatalogItem) {
    const icon = item.icon || "⬛";
    const title = item.title || item.node_type;
    return `${icon} ${title}`;
}

export function buildDefaultConfig(item: CatalogItem) {
    const cfg = item.default_config ? { ...item.default_config } : {};

    if (!cfg.nodeType) cfg.nodeType = item.node_type;
    if (cfg.node_type && !cfg.nodeType) cfg.nodeType = cfg.node_type;

    delete (cfg as any).node_type;

    return cfg;
}