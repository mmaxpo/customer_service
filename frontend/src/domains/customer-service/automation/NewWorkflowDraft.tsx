"use client";

import { useState } from "react";

import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";

import { MiniGraph } from "./WorkflowGraph";
import { studioApi, type WorkflowDraft } from "./api";

const TOPICS = [
  { value: "", label: "Any topic" },
  { value: "general", label: "General questions" },
  { value: "shipping", label: "Shipping" },
  { value: "refund", label: "Refunds" },
];

/** A workflow TCOS drafted from a prompt: review it, adjust when it runs, save it switched off. */
export function NewWorkflowDraft({ draft, onSaved, onDiscard }: { draft: WorkflowDraft; onSaved: () => void; onDiscard: () => void }) {
  const [name, setName] = useState(draft.name);
  const [keywords, setKeywords] = useState(draft.keywords.join(", "));
  const [topic, setTopic] = useState(draft.topic ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const keywordList = keywords.split(",").map((word) => word.trim()).filter(Boolean);
  const field = "mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-[13.5px] font-normal text-foreground";

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await studioApi.createWorkflow({ name, description: draft.description, topic: topic || null, keywords: keywordList, workflow: draft.workflow });
      onSaved();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save this workflow."));
      setSaving(false);
    }
  };

  return (
    <form onSubmit={save} className="rounded-container border border-ai-accent/40 bg-surface p-4">
      <h2 className="text-[15px] font-semibold text-foreground">New workflow drafted by TCOS</h2>
      <p className="mt-1 text-[13px] text-text-secondary">{draft.description}</p>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <label className="text-[12.5px] font-medium text-foreground">Name<input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} required className={field} /></label>
        <label className="text-[12.5px] font-medium text-foreground">
          Runs when a message contains
          <input value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="gift wrap, gift note" required className={field} />
        </label>
        <label className="text-[12.5px] font-medium text-foreground">
          And the topic is
          <select value={topic} onChange={(e) => setTopic(e.target.value)} className={field}>
            {TOPICS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
      </div>
      <p className="mt-1.5 text-[12.5px] text-text-secondary">Keywords are separated by commas. Short words match more messages. Cancellations and damaged items always go to your team.</p>
      <div className="mt-3"><MiniGraph graph={draft.graph} /></div>
      <ol className="mt-3 flex flex-wrap gap-x-2 gap-y-1 text-[12.5px] text-text-secondary">
        {draft.graph.nodes.map((node, index) => <li key={node.id}>{index + 1}. {node.label}</li>)}
      </ol>
      {draft.validation_errors.length ? (
        <p role="alert" className="mt-3 text-[13px] text-danger">This draft can't be saved yet: {draft.validation_errors.join(" ")}</p>
      ) : null}
      {error ? <p role="alert" className="mt-3 text-[13px] text-danger">{error}</p> : null}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button type="submit" size="sm" disabled={saving || !keywordList.length || draft.validation_errors.length > 0}>{saving ? "Saving…" : "Save"}</Button>
        <Button type="button" size="sm" variant="ghost" onClick={onDiscard}>Discard</Button>
        <span className="text-[12.5px] text-text-secondary">It is saved switched off. You can edit its steps, then turn it on.</span>
      </div>
    </form>
  );
}
