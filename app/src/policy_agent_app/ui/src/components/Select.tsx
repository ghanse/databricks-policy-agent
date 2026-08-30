import { useEffect, useRef, useState } from "react";
import { ChevronIcon } from "./icons";

export interface Option {
  value: string;
  label: string;
}

/** A custom dropdown that styles its option list (native <select> options fall back to
 *  the OS renderer and can't be themed). */
export function Select({
  value,
  options,
  onChange,
  ariaLabel,
  block,
}: {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  ariaLabel?: string;
  block?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const current = options.find((o) => o.value === value);

  return (
    <div className={`sel ${open ? "open" : ""} ${block ? "sel-block" : ""}`} ref={ref}>
      <button type="button" className="sel-btn" aria-label={ariaLabel} onClick={() => setOpen((v) => !v)}>
        <span className={current ? "" : "faint"}>{current ? current.label : "All"}</span>
        <ChevronIcon className="sel-chev" size={14} />
      </button>
      {open && (
        <div className="sel-menu">
          {options.map((o) => (
            <button
              type="button"
              key={o.value || "__all"}
              className={`sel-opt ${o.value === value ? "on" : ""}`}
              onClick={() => {
                onChange(o.value);
                setOpen(false);
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
