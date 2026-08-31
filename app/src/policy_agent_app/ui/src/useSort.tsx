import { useState, type CSSProperties } from "react";

type Dir = "asc" | "desc";
type Accessor<T> = (row: T) => string | number;

export interface Sorter<T> {
  key: string;
  dir: Dir;
  toggle: (key: string) => void;
  apply: (rows: T[], accessors: Record<string, Accessor<T>>) => T[];
}

/** Column-sort state shared by the data tables. */
export function useSort<T>(defaultKey = ""): Sorter<T> {
  const [key, setKey] = useState(defaultKey);
  const [dir, setDir] = useState<Dir>("asc");

  const toggle = (k: string) => {
    if (k === key) setDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setKey(k);
      setDir("asc");
    }
  };

  const apply = (rows: T[], accessors: Record<string, Accessor<T>>) => {
    const acc = accessors[key];
    if (!acc) return rows;
    return [...rows].sort((a, b) => {
      const x = acc(a);
      const y = acc(b);
      const c = x < y ? -1 : x > y ? 1 : 0;
      return dir === "asc" ? c : -c;
    });
  };

  return { key, dir, toggle, apply };
}

/** Clickable, sort-aware table header cell. */
export function SortTh({
  label,
  field,
  sort,
  style,
}: {
  label: string;
  field: string;
  sort: { key: string; dir: Dir; toggle: (key: string) => void };
  style?: CSSProperties;
}) {
  const active = sort.key === field;
  const ariaSort = active ? (sort.dir === "asc" ? "ascending" : "descending") : "none";
  return (
    <th className="sortable" style={style} aria-sort={ariaSort}>
      <button
        type="button"
        className="sort-btn"
        onClick={() => sort.toggle(field)}
      >
        {label}
        <span className="sort-ind">{active ? (sort.dir === "asc" ? "▲" : "▼") : ""}</span>
      </button>
    </th>
  );
}

export const ENFORCEMENT_RANK: Record<string, number> = { advisory: 0, soft: 1, hard: 2 };
