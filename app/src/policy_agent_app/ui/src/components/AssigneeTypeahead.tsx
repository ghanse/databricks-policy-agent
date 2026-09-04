import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AccountUser } from "../types";
import { UserIcon } from "./icons";

/** A styled typeahead that limits assignment to real account users. It debounces a lookup
 *  against the account-user search API and renders its own themed option list (a native
 *  datalist can't be styled). The chosen value is always a user's email. */
export function AssigneeTypeahead({
  value,
  onChange,
  placeholder = "Search account users…",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<AccountUser[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => setQuery(value), [value]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  // Debounce the lookup so we don't fire a request on every keystroke.
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    const handle = setTimeout(() => {
      api
        .searchUsers(query.trim())
        .then((users) => {
          setResults(users);
          setActive(0);
        })
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 200);
    return () => clearTimeout(handle);
  }, [query]);

  const pick = (user: AccountUser) => {
    onChange(user.user_name);
    setQuery(user.user_name);
    setOpen(false);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (!open || !results.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(results[active]);
    }
  };

  return (
    <div className={`typeahead ${open ? "open" : ""}`} ref={ref}>
      <div className="typeahead-input">
        <UserIcon className="ico" size={15} />
        <input
          value={query}
          placeholder={placeholder}
          onChange={(e) => {
            setQuery(e.target.value);
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKey}
          autoComplete="off"
        />
      </div>
      {open && query.trim() && (
        <div className="typeahead-menu">
          {loading && !results.length ? (
            <div className="typeahead-empty">Searching…</div>
          ) : results.length ? (
            results.map((user, i) => (
              <button
                type="button"
                key={user.user_name}
                className={`typeahead-opt ${i === active ? "on" : ""}`}
                onMouseEnter={() => setActive(i)}
                onClick={() => pick(user)}
              >
                <span className="typeahead-name">{user.display_name}</span>
                <span className="typeahead-mail">{user.user_name}</span>
              </button>
            ))
          ) : (
            <div className="typeahead-empty">No matching account users.</div>
          )}
        </div>
      )}
    </div>
  );
}
