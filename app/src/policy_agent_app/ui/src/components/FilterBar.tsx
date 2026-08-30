export interface FilterSpec {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

/** A search box plus a set of dropdown filters, shared across the data tables. */
export function FilterBar({
  search,
  onSearch,
  placeholder,
  filters,
}: {
  search: string;
  onSearch: (value: string) => void;
  placeholder?: string;
  filters?: FilterSpec[];
}) {
  return (
    <div className="filterbar">
      <input
        className="search"
        type="search"
        placeholder={placeholder ?? "Search…"}
        value={search}
        onChange={(e) => onSearch(e.target.value)}
      />
      {(filters ?? []).map((f) => (
        <label key={f.label} className="filter">
          <span>{f.label}</span>
          <select value={f.value} onChange={(e) => f.onChange(e.target.value)}>
            <option value="">All</option>
            {f.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      ))}
    </div>
  );
}
