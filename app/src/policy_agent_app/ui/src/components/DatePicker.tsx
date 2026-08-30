import { useEffect, useRef, useState } from "react";
import { CalendarIcon } from "./icons";

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function fromValue(v: string): Date {
  const d = v ? new Date(`${v}T00:00:00`) : new Date();
  return Number.isNaN(d.getTime()) ? new Date() : d;
}
function toValue(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}
function label(v: string): string {
  if (!v) return "Any date";
  return fromValue(v).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

/** Fully themed date picker — a styled trigger plus a month-grid popover, so it matches the
 *  app in both light and dark instead of falling back to the OS calendar. */
export function DatePicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState(() => fromValue(value));
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  useEffect(() => {
    if (open) setView(fromValue(value));
  }, [open, value]);

  const year = view.getFullYear();
  const month = view.getMonth();
  const startDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  const sel = value ? fromValue(value) : null;
  const isSel = (d: number) =>
    sel != null && sel.getFullYear() === year && sel.getMonth() === month && sel.getDate() === d;

  return (
    <div className="datepick" ref={ref}>
      <button type="button" className="datepick-btn" onClick={() => setOpen((v) => !v)}>
        <CalendarIcon size={14} />
        <span className={value ? "" : "faint"}>{label(value)}</span>
      </button>
      {open && (
        <div className="datepick-pop">
          <div className="dp-head">
            <button type="button" className="dp-nav" onClick={() => setView(new Date(year, month - 1, 1))}>
              ‹
            </button>
            <span>{view.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</span>
            <button type="button" className="dp-nav" onClick={() => setView(new Date(year, month + 1, 1))}>
              ›
            </button>
          </div>
          <div className="dp-grid dp-wd">
            {WEEKDAYS.map((w) => (
              <span key={w}>{w}</span>
            ))}
          </div>
          <div className="dp-grid">
            {cells.map((d, i) =>
              d === null ? (
                <span key={i} />
              ) : (
                <button
                  key={i}
                  type="button"
                  className={`dp-day ${isSel(d) ? "sel" : ""}`}
                  onClick={() => {
                    onChange(toValue(new Date(year, month, d)));
                    setOpen(false);
                  }}
                >
                  {d}
                </button>
              ),
            )}
          </div>
        </div>
      )}
    </div>
  );
}
