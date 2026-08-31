import { Fragment, type ReactNode } from "react";

/** Minimal, dependency-free tokenizers that wrap JSON / YAML in themed spans for
 *  read-only display. They never throw — unmatched text is emitted as-is. */

interface Token {
  cls: string;
  text: string;
}

function render(tokens: Token[]): ReactNode {
  return tokens.map((t, i) =>
    t.cls ? (
      <span key={i} className={`tok-${t.cls}`}>
        {t.text}
      </span>
    ) : (
      <Fragment key={i}>{t.text}</Fragment>
    ),
  );
}

const JSON_RE =
  /("(?:\\.|[^"\\])*"\s*:)|("(?:\\.|[^"\\])*")|(\b-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|(\btrue\b|\bfalse\b|\bnull\b)|([{}[\],:])/g;

export function highlightJson(text: string): ReactNode {
  const tokens: Token[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  JSON_RE.lastIndex = 0;
  while ((m = JSON_RE.exec(text))) {
    if (m.index > last) tokens.push({ cls: "", text: text.slice(last, m.index) });
    if (m[1]) tokens.push({ cls: "key", text: m[1] });
    else if (m[2]) tokens.push({ cls: "str", text: m[2] });
    else if (m[3]) tokens.push({ cls: "num", text: m[3] });
    else if (m[4]) tokens.push({ cls: "bool", text: m[4] });
    else if (m[5]) tokens.push({ cls: "punc", text: m[5] });
    last = JSON_RE.lastIndex;
  }
  if (last < text.length) tokens.push({ cls: "", text: text.slice(last) });
  return render(tokens);
}

export function highlightYaml(text: string): ReactNode {
  const lines = text.split("\n");
  return lines.map((line, i) => (
    <Fragment key={i}>
      {highlightYamlLine(line)}
      {i < lines.length - 1 ? "\n" : ""}
    </Fragment>
  ));
}

function highlightYamlLine(line: string): ReactNode {
  const comment = line.indexOf("#");
  if (comment === 0 || (comment > 0 && /^\s*#/.test(line))) {
    return <span className="tok-comment">{line}</span>;
  }
  // key: value  (optionally starting with a list dash)
  const m = line.match(/^(\s*(?:-\s+)?)([A-Za-z0-9_.-]+)(:)(\s*)(.*)$/);
  if (!m) return line;
  const [, indent, key, colon, space, value] = m;
  return (
    <>
      {indent}
      <span className="tok-key">{key}</span>
      <span className="tok-punc">{colon}</span>
      {space}
      {value && <span className="tok-str">{value}</span>}
    </>
  );
}
