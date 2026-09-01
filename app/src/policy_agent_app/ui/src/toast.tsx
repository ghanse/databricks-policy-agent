import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

export type ToastKind = "save" | "delete" | "error" | "info";

interface Toast {
  id: number;
  message: ReactNode;
  kind: ToastKind;
}

const TITLES: Record<ToastKind, string> = {
  save: "Success",
  delete: "Removed",
  error: "Error",
  info: "Note",
};

interface ToastApi {
  push: (message: ReactNode, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastApi>({ push: () => {} });

export function useToast(): ToastApi {
  return useContext(ToastContext);
}

/** Renders transient confirmation pop-ups in the bottom-right corner, bordered by action. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const push = useCallback((message: ReactNode, kind: ToastKind = "info") => {
    const id = nextId.current++;
    setToasts((t) => [...t, { id, message, kind }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3800);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="toasts">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`} onClick={() => setToasts((c) => c.filter((x) => x.id !== t.id))}>
            <div className="toast-title">{TITLES[t.kind]}</div>
            <div className="toast-msg">{t.message}</div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
