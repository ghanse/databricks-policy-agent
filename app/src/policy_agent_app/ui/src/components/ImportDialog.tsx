import { useRef, useState } from "react";
import { api } from "../api";

/** Modal for importing one or more policies from OPA-style YAML — paste text or upload a file. */
export function ImportDialog({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [yaml, setYaml] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const pickFile = (file: File | undefined) => {
    if (!file) return;
    file.text().then(setYaml);
  };

  const submit = async () => {
    setError("");
    setBusy(true);
    try {
      const result = await api.importPolicies(yaml);
      if (result.count === 0) {
        setError("No policies found in that YAML.");
        return;
      }
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
      <div className="modal" style={{ maxWidth: 640 }} onClick={(e) => e.stopPropagation()}>
        <h3>Import policies from YAML</h3>
        <div className="desc">
          Paste one or more OPA-style policy documents (separated by <code>---</code>), or upload a
          <code>.yaml</code> file. Imported policies are saved as drafts for review.
        </div>
        {error && <div className="error">{error}</div>}
        <div className="row" style={{ marginBottom: 8 }}>
          <button className="action secondary tiny" onClick={() => fileRef.current?.click()}>
            Upload file…
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".yaml,.yml,text/yaml"
            style={{ display: "none" }}
            onChange={(e) => pickFile(e.target.files?.[0])}
          />
          <span className="faint" style={{ fontSize: 12 }}>or paste below</span>
        </div>
        <textarea
          style={{ minHeight: 220 }}
          placeholder={"policy: my-policy\nresource_type: sql_warehouse\neffect: allow\n…"}
          value={yaml}
          onChange={(e) => setYaml(e.target.value)}
        />
        <div className="actions">
          <button className="action secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="action" onClick={submit} disabled={busy || !yaml.trim()}>
            {busy ? "Importing…" : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
