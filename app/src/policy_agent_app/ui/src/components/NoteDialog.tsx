import { useEffect, useState } from "react";

export interface NoteRequest {
  title: string;
  description?: string;
  confirmLabel: string;
  withAssignee?: boolean;
  onConfirm: (note: string, assignee?: string) => void;
}

/** A small modal for capturing a note (and optional assignee) for a workflow action,
 *  replacing window.prompt with a keyboard-friendly dialog. */
export function NoteDialog({ request, onClose }: { request: NoteRequest | null; onClose: () => void }) {
  const [note, setNote] = useState("");
  const [assignee, setAssignee] = useState("");

  useEffect(() => {
    setNote("");
    setAssignee("");
  }, [request]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!request) return null;

  const confirm = () => {
    request.onConfirm(note, request.withAssignee ? assignee || undefined : undefined);
    onClose();
  };

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{request.title}</h3>
        {request.description && <div className="desc">{request.description}</div>}
        {request.withAssignee && (
          <div style={{ marginBottom: 12 }}>
            <label className="field">Assignee (email)</label>
            <input
              placeholder="owner@example.com"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
            />
          </div>
        )}
        <label className="field">Note</label>
        <textarea
          style={{ minHeight: 90 }}
          placeholder="Optional context recorded on the audit trail…"
          value={note}
          autoFocus
          onChange={(e) => setNote(e.target.value)}
        />
        <div className="actions">
          <button className="action secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="action" onClick={confirm}>
            {request.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
