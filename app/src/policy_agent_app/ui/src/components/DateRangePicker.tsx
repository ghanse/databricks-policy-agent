import { useEffect, useRef, useState } from "react";
import { CalendarIcon } from "./icons";

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

export interface DateRange {
  from: string;
  to: string;
}

function parse(v: string): Date {
  const d = v ? new Date(`${v}T00:00:00`) : new Date();
  return Number.isNaN(d.getTime()) ? new Date() : d;
}
function fmt(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function short(v: string): string {
  return v ? parse(v).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
}
function label(r: DateRange): string {
  if (!r.from && !r.to) return "Any date";
  if (r.from && r.to) return `${short(r.from)} – ${short(r.to)}`;
  return short(r.from || r.to);
}

/** A themed range picker: click a start day then an end day (drag across days highlights
 *  the range as you go). */
export function DateRangePicker({ value, onChange }: { value: DateRange; onChange: (r: DateRange) => void }) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState(() => parse(value.from));
  const [hover, setHover] = useState<string>("");
  const [dragging, setDragging] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const year = view.getFullYear();
  const month = view.getMonth();
  const startDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (string | null)[] = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(fmt(new Date(year, month, d)));

  // The range currently being previewed (committed range, or start + hovered end).
  const previewEnd = dragging && value.from && !value.to ? hover : value.to;
  const lo = value.from && previewEnd ? (value.from < previewEnd ? value.from : previewEnd) : value.from;
  const hi = value.from && previewEnd ? (value.from < previewEnd ? previewEnd : value.from) : "";

  const onDay = (day: string) => {
    if (!value.from || (value.from && value.to)) {
      onChange({ from: day, to: "" });
      setDragging(true);
    } else {
      const from = day < value.from ? day : value.from;
      const to = day < value.from ? value.from : day;
      onChange({ from, to });
      setDragging(false);
    }
  };

  const inRange = (day: string) => lo && hi && day >= lo && day <= hi;

  return (
    <div className="datepick" ref={ref}>
      <button type="button" className="datepick-btn" onClick={() => setOpen((v) => !v)}>
        <CalendarIcon size={14} />
        <span className={value.from || value.to ? "" : "faint"}>{label(value)}</span>
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
            {cells.map((day, i) =>
              day === null ? (
                <span key={i} />
              ) : (
                <button
                  key={i}
                  type="button"
                  className={`dp-day ${day === value.from || day === value.to ? "sel" : ""} ${
                    inRange(day) ? "in-range" : ""
                  }`}
                  onMouseEnter={() => setHover(day)}
                  onClick={() => onDay(day)}
                >
                  {Number(day.slice(-2))}
                </button>
              ),
            )}
          </div>
          <div className="dp-foot">
            <button type="button" className="linkbtn" onClick={() => onChange({ from: "", to: "" })}>
              Clear
            </button>
            <button type="button" className="action tiny" onClick={() => setOpen(false)}>
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
