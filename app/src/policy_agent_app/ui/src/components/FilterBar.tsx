import { Select } from "./Select";

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
          <Select
            ariaLabel={f.label}
            value={f.value}
            onChange={f.onChange}
            options={[{ value: "", label: "All" }, ...f.options]}
          />
        </label>
      ))}
    </div>
  );
}
