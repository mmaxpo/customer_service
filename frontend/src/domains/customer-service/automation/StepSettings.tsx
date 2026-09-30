"use client";

import { useEffect, useState } from "react";

import type { JsonSchemaProperty, LibraryItem, RawNode } from "./api";
import { humanizeId } from "./graphEdits";

// Engine plumbing that admins don't need to see.
const HIDDEN = new Set(["nodeType", "node_type", "name", "label", "retries", "retry_backoff_ms", "timeout_ms"]);
const LONG_TEXT = new Set(["prompt", "system", "instruction", "system_prompt", "question", "message", "text", "value", "provider_failure_fallback"]);

function fieldType(prop: JsonSchemaProperty): string {
  if (prop.enum) return "enum";
  if (prop.type) return prop.type;
  return prop.anyOf?.find((option) => option.type && option.type !== "null")?.type ?? "string";
}

function JsonField({ id, value, onChange }: { id: string; value: unknown; onChange: (value: unknown) => void }) {
  const [text, setText] = useState(() => JSON.stringify(value ?? null, null, 2));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setText(JSON.stringify(value ?? null, null, 2)), [value]);

  return (
    <>
      <textarea
        id={id}
        value={text}
        rows={4}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          try {
            onChange(JSON.parse(text));
            setError(null);
          } catch {
            setError("This isn't valid JSON yet.");
          }
        }}
        className="w-full rounded-control border border-border px-2 py-1.5 font-mono text-[12px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      />
      {error ? <p className="mt-1 text-[12px] text-danger">{error}</p> : null}
    </>
  );
}

const inputClass =
  "w-full rounded-control border border-border bg-surface px-2 py-1.5 text-[13px] text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

export function StepSettings({
  node,
  item,
  onChange,
}: {
  node: RawNode;
  item: LibraryItem | undefined;
  onChange: (data: RawNode["data"]) => void;
}) {
  const properties = Object.entries(item?.schema.properties ?? {}).filter(([key]) => !HIDDEN.has(key));
  // Keys already set on the node but not described by the schema still need a place to live.
  const extra = Object.keys(node.data).filter((key) => !HIDDEN.has(key) && !item?.schema.properties?.[key]);
  const set = (key: string, value: unknown) => onChange({ ...node.data, [key]: value });

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor="step-name" className="text-[12.5px] font-medium text-foreground">Step name</label>
        <input
          id="step-name"
          value={typeof node.data.label === "string" ? node.data.label : ""}
          placeholder={humanizeId(node.id)}
          onChange={(e) => set("label", e.target.value)}
          className={`mt-1 ${inputClass}`}
        />
      </div>

      {properties.map(([key, prop]) => {
        const id = `field-${key}`;
        const label = prop.title && prop.title !== key ? prop.title : humanizeId(key);
        const value = node.data[key];
        const type = fieldType(prop);

        return (
          <div key={key}>
            {type === "boolean" ? (
              <label className="flex items-center gap-2 text-[12.5px] font-medium text-foreground">
                <input type="checkbox" checked={Boolean(value ?? prop.default)} onChange={(e) => set(key, e.target.checked)} />
                {label}
              </label>
            ) : (
              <>
                <label htmlFor={id} className="text-[12.5px] font-medium text-foreground">{label}</label>
                <div className="mt-1">
                  {type === "enum" ? (
                    <select id={id} value={String(value ?? prop.default ?? "")} onChange={(e) => set(key, e.target.value)} className={inputClass}>
                      {prop.enum!.map((option) => (
                        <option key={String(option)} value={String(option)}>{String(option)}</option>
                      ))}
                    </select>
                  ) : type === "integer" || type === "number" ? (
                    <input
                      id={id}
                      type="number"
                      value={value === undefined || value === null ? "" : String(value)}
                      placeholder={prop.default !== undefined && prop.default !== null ? String(prop.default) : undefined}
                      onChange={(e) => set(key, e.target.value === "" ? undefined : Number(e.target.value))}
                      className={inputClass}
                    />
                  ) : type === "array" || type === "object" ? (
                    <JsonField id={id} value={value ?? prop.default} onChange={(next) => set(key, next)} />
                  ) : LONG_TEXT.has(key) ? (
                    <textarea
                      id={id}
                      rows={key === "prompt" || key === "system" ? 6 : 3}
                      value={typeof value === "string" ? value : ""}
                      onChange={(e) => set(key, e.target.value)}
                      className={`${inputClass} leading-5`}
                    />
                  ) : (
                    <input
                      id={id}
                      value={typeof value === "string" ? value : value === undefined || value === null ? "" : String(value)}
                      placeholder={typeof prop.default === "string" ? prop.default : undefined}
                      onChange={(e) => set(key, e.target.value)}
                      className={inputClass}
                    />
                  )}
                </div>
              </>
            )}
            {prop.description ? <p className="mt-1 text-[11.5px] leading-4 text-text-secondary">{prop.description}</p> : null}
          </div>
        );
      })}

      {extra.map((key) => (
        <div key={key}>
          <label htmlFor={`field-${key}`} className="text-[12.5px] font-medium text-foreground">{humanizeId(key)}</label>
          <div className="mt-1">
            <JsonField id={`field-${key}`} value={node.data[key]} onChange={(next) => set(key, next)} />
          </div>
        </div>
      ))}
    </div>
  );
}
