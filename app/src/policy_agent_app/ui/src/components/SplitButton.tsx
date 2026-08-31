import { useEffect, useRef, useState } from "react";
import { ChevronIcon } from "./icons";

export interface SplitOption {
  label: string;
  onSelect: () => void;
}

/** A primary button with an attached caret that opens secondary actions. */
export function SplitButton({
  label,
  onClick,
  options,
  disabled,
}: {
  label: string;
  onClick: () => void;
  options: SplitOption[];
  disabled?: boolean;
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

  return (
    <div className="split" ref={ref}>
      <button className="action split-main" onClick={onClick} disabled={disabled}>
        {label}
      </button>
      <button
        className="action split-caret"
        onClick={() => setOpen((v) => !v)}
        disabled={disabled}
        aria-label="More scan options"
      >
        <ChevronIcon size={15} />
      </button>
      {open && (
        <div className="split-menu">
          {options.map((o) => (
            <button
              key={o.label}
              className="menu-item"
              onClick={() => {
                setOpen(false);
                o.onSelect();
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
