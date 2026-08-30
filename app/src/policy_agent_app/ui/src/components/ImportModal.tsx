import { useRef, useState } from "react";
import { api } from "../api";
import { useToast } from "../toast";
import { TrashIcon } from "./icons";

interface Upload {
  name: string;
  text: string;
}

/** Drag-and-drop modal for importing policies from one or more YAML files. The user can
 *  add files, validate them, then save (imports every policy as a draft). */
export function ImportModal({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [files, setFiles] = useState<Upload[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [validation, setValidation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const combined = () => files.map((f) => f.text).join("\n---\n");

  const addFiles = async (list: FileList | null) => {
    if (!list) return;
    setValidation("");
    setError("");
    const added: Upload[] = [];
    for (const file of Array.from(list)) added.push({ name: file.name, text: await file.text() });
    setFiles((prev) => [...prev, ...added]);
  };

  const validate = async () => {
    setError("");
    setValidation("");
    try {
      const { policies } = await api.parsePolicies(combined());
      setValidation(
        policies.length ? `Looks good — ${policies.length} policy(ies) parsed.` : "No policies found in these files.",
      );
    } catch (e) {
      setError(String(e));
    }
  };

  const save = async () => {
    setError("");
    setBusy(true);
    try {
      const result = await api.importPolicies(combined());
      if (!result.count) {
        setError("No policies found in these files.");
        return;
      }
      toast.push(`Imported ${result.count} policy(ies) as drafts`, "save");
      onImported();
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
        <h3>Import policies from YAML</h3>
        <div className="desc">Drop one or more OPA-style policy files, then validate and save them as drafts.</div>
        {error && <div className="error">{error}</div>}

        <div
          className={`dropzone ${dragOver ? "over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            addFiles(e.dataTransfer.files);
          }}
          onClick={() => fileRef.current?.click()}
        >
          <div className="dz-title">Drag &amp; drop YAML files here</div>
          <div className="faint">or click to browse</div>
          <input
            ref={fileRef}
            type="file"
            accept=".yaml,.yml,text/yaml"
            multiple
            style={{ display: "none" }}
            onChange={(e) => {
              addFiles(e.target.files);
              if (fileRef.current) fileRef.current.value = "";
            }}
          />
        </div>

        {files.length > 0 && (
          <div className="stack" style={{ marginTop: 12 }}>
            {files.map((f, i) => (
              <div key={i} className="file-row">
                <span className="mono">{f.name}</span>
                <button
                  className="icon-btn act-danger"
                  title="Remove"
                  onClick={() => {
                    setFiles((prev) => prev.filter((_, j) => j !== i));
                    setValidation("");
                  }}
                >
                  <TrashIcon size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {validation && <div className="muted" style={{ marginTop: 10 }}>{validation}</div>}

        <div className="actions">
          <button className="action secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="action secondary" onClick={validate} disabled={!files.length}>
            Validate
          </button>
          <button className="action" onClick={save} disabled={!files.length || busy}>
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
