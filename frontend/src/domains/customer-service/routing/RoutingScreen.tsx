"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { TOPIC_LABELS } from "@/domains/customer-service/model/topics";
import { workspaceApi, type WorkspaceMember } from "@/domains/workspace/api/workspace";
import { apiErrorMessage, apiJson, jsonBody } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";

const ENDPOINT = "/api/customer-service/studio/assignment-rules";
const LEAST_BUSY = "least_busy";
const NOBODY = "";

type Rules = { topics: { topic: string; assignee: string }[]; default: string | null };

const select = "h-9 min-w-0 rounded-control border border-border bg-surface px-2 text-[13.5px] text-foreground";

/** Who gets what: a topic goes to one person; everything else has one rule. */
export default function RoutingScreen() {
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [rules, setRules] = useState<Rules | null>(null);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      workspaceApi.current().then((workspace) => workspaceApi.team(workspace.id)),
      apiJson<Rules>(ENDPOINT),
    ])
      .then(([team, saved]) => {
        setMembers(team.filter((member) => (member.state ?? member.status) === "active" && member.user_id));
        setRules(saved);
      })
      .catch((err) => setError(apiErrorMessage(err, "Could not load the routing rules.")));
  }, []);

  if (!rules) {
    return error
      ? <p role="alert" className="mt-5 text-sm text-danger">{error}</p>
      : <div className="mt-5 h-40 animate-pulse rounded bg-muted" />;
  }

  const change = (next: Rules) => {
    setRules(next);
    setStatus(null);
  };
  const usedTopics = new Set(rules.topics.map((rule) => rule.topic));
  const freeTopic = Object.keys(TOPIC_LABELS).find((topic) => !usedTopics.has(topic));
  const people = members.map((member) => (
    <option key={member.user_id} value={member.user_id}>{member.display_name || member.email}</option>
  ));

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!rules) return;
    setSaving(true);
    setError(null);
    try {
      setRules(await apiJson<Rules>(ENDPOINT, { method: "PUT", body: jsonBody(rules) }));
      setStatus("Saved. New conversations follow these rules.");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save the routing rules."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="mt-5 max-w-2xl space-y-6">
      {members.length < 2 ? (
        <p className="rounded-container border border-border bg-muted px-4 py-3 text-[13px] text-text-secondary">
          You're the only team member, so every conversation that needs a person comes to you.{" "}
          <Link href="/app/settings" className="font-medium text-primary hover:underline">Invite teammates</Link> to share the work.
        </p>
      ) : null}

      <section>
        <h2 className="text-sm font-semibold text-foreground">By topic</h2>
        <p className="mt-1 text-[13px] text-text-secondary">A new conversation about a topic is assigned to that person.</p>
        <ul className="mt-2.5 space-y-2">
          {rules.topics.map((rule, index) => (
            <li key={rule.topic} className="flex flex-wrap items-center gap-2">
              <select
                aria-label="Topic"
                value={rule.topic}
                onChange={(e) => change({ ...rules, topics: rules.topics.map((item, i) => (i === index ? { ...item, topic: e.target.value } : item)) })}
                className={select}
              >
                {Object.entries(TOPIC_LABELS)
                  .filter(([topic]) => topic === rule.topic || !usedTopics.has(topic))
                  .map(([topic, label]) => <option key={topic} value={topic}>{label}</option>)}
              </select>
              <span className="text-[13px] text-text-secondary">goes to</span>
              <select
                aria-label="Team member"
                value={rule.assignee}
                onChange={(e) => change({ ...rules, topics: rules.topics.map((item, i) => (i === index ? { ...item, assignee: e.target.value } : item)) })}
                className={select}
              >
                {people}
              </select>
              <Button type="button" size="sm" variant="ghost" onClick={() => change({ ...rules, topics: rules.topics.filter((_, i) => i !== index) })}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
        {freeTopic && members.length ? (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="mt-2.5"
            onClick={() => change({ ...rules, topics: [...rules.topics, { topic: freeTopic, assignee: members[0].user_id }] })}
          >
            Add a topic rule
          </Button>
        ) : null}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Everything else</h2>
        <label className="mt-2 flex flex-wrap items-center gap-2 text-[13px] text-text-secondary">
          Other conversations go to
          <select
            value={rules.default ?? NOBODY}
            onChange={(e) => change({ ...rules, default: e.target.value === NOBODY ? null : e.target.value })}
            className={select}
          >
            <option value={NOBODY}>Nobody (stay unassigned)</option>
            <option value={LEAST_BUSY}>Whoever has the fewest open conversations</option>
            {people}
          </select>
        </label>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="sm" disabled={saving}>{saving ? "Saving…" : "Save rules"}</Button>
        {status ? <p role="status" className="text-[13px] text-text-secondary">{status}</p> : null}
        {error ? <p role="alert" className="text-[13px] text-danger">{error}</p> : null}
      </div>
      <p className="text-[12.5px] text-text-secondary">
        A conversation is assigned once, when its topic is known. You can always change the assignee in the Inbox.
      </p>
    </form>
  );
}
