
export type CatalogItem = {
  node_type: string;
  title: string;
  icon: string;
  group: string;
  category: string;
  default_config: Record<string, any>;
  schema: any;
};

export type CatalogResponse = {
  items: CatalogItem[];
};