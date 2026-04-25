export const DELIVERY_FEE = 49;
export const FREE_THRESHOLD = 599;

export interface SearchResult {
  sku_id: string;
  category: "food" | "supplement" | "medicine";
  brand_name: string;
  product_name: string;
  name?: string;
  pack_size: string;
  mrp: number;
  discounted_price: number;
  in_stock: boolean;
  medicine_type?: string;
  notes?: string;
  [key: string]: any;
}

export interface GroupedResult {
  brand: string;
  productName: string;
  skus: SearchResult[];
}

export function groupSearchResults(results: SearchResult[]): GroupedResult[] {
  const groups: Record<string, SearchResult[]> = {};

  for (const r of results) {
    const key = `${r.brand_name}||${r.product_name}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(r);
  }

  return Object.entries(groups).map(([key, skus]) => {
    const [brand, productName] = key.split("||");
    return { brand, productName, skus };
  });
}
