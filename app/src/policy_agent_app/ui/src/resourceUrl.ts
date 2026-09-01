/** Build a link back to a resource in the Databricks workspace UI. */
export function resourceUrl(host: string, type: string, id: string): string | null {
  if (!host || !id) return null;
  const base = host.replace(/\/$/, "");
  switch (type) {
    case "job":
      return `${base}/jobs/${id}`;
    case "cluster":
      return `${base}/compute/clusters/${id}`;
    case "sql_warehouse":
      return `${base}/sql/warehouses/${id}`;
    case "app":
      return `${base}/apps/${id}`;
    case "serving_endpoint":
      return `${base}/ml/endpoints/${id}`;
    default:
      return null;
  }
}
