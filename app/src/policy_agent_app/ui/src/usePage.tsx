import { useEffect, useState } from "react";

export interface Pager<T> {
  pageRows: T[];
  page: number;
  pageCount: number;
  total: number;
  prev: () => void;
  next: () => void;
  canPrev: boolean;
  canNext: boolean;
}

/** Client-side pagination over an already-filtered/sorted list. Resets to page 1 whenever
 *  the row count changes (e.g. a filter narrows the results). */
export function usePage<T>(rows: T[], pageSize = 10): Pager<T> {
  const [page, setPage] = useState(0);
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));

  useEffect(() => {
    setPage((p) => Math.min(p, pageCount - 1));
  }, [pageCount]);

  const start = page * pageSize;
  const pageRows = rows.slice(start, start + pageSize);

  return {
    pageRows,
    page,
    pageCount,
    total: rows.length,
    prev: () => setPage((p) => Math.max(0, p - 1)),
    next: () => setPage((p) => Math.min(pageCount - 1, p + 1)),
    canPrev: page > 0,
    canNext: page < pageCount - 1,
  };
}

/** Previous / Next footer, bottom-left of a table. */
export function PagerBar({ pager }: { pager: Pager<unknown> }) {
  if (pager.pageCount <= 1) return null;
  return (
    <div className="pager">
      <button className="linkbtn" onClick={pager.prev} disabled={!pager.canPrev}>
        Previous
      </button>
      <button className="linkbtn" onClick={pager.next} disabled={!pager.canNext}>
        Next
      </button>
      <span className="pageinfo">
        Page {pager.page + 1} of {pager.pageCount}
      </span>
    </div>
  );
}
