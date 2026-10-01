"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { authButton, authInput, authLabel, AuthShell, AuthStatus } from "@/components/marketing/AuthShell";
import { SALES_EMAIL, SUPPORT_EMAIL } from "@/components/marketing/brand";
import { cn } from "@/platform/utils";

const TOPICS = [
  { id: "sales", label: "Plans and Enterprise" },
  { id: "support", label: "Help with my workspace" },
] as const;

type Topic = (typeof TOPICS)[number]["id"];

export default function ContactPage() {
  const [topic, setTopic] = useState<Topic>("sales");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, name, email, message }),
      });
      if (res.ok) {
        setSent(true);
        return;
      }
      const body = await res.json().catch(() => null);
      setError(typeof body?.detail === "string" ? body.detail : "We could not send your message. Check the form and try again.");
    } catch {
      setError("We could not send your message. Check your connection and try again.");
    } finally {
      setSending(false);
    }
  }

  const fallback = topic === "sales" ? SALES_EMAIL : SUPPORT_EMAIL;

  return (
    <AuthShell
      title={sent ? "Message sent" : "Contact us"}
      subtitle={sent ? `Thanks, ${name.trim()}. A person on our team will reply to ${email}.` : "Tell us what you need and a person on our team will reply by email."}
      footer={
        sent ? (
          <p><Link href="/" className="font-medium text-primary hover:underline">Back to the home page</Link></p>
        ) : (
          <p>Prefer email? Write to <a href={`mailto:${fallback}`} className="font-medium text-primary hover:underline">{fallback}</a></p>
        )
      }
    >
      {sent ? null : (
        <form onSubmit={submit} className="mt-7 space-y-4">
          <fieldset>
            <legend className={authLabel}>What is it about?</legend>
            <div className="mt-1.5 grid grid-cols-2 gap-2">
              {TOPICS.map((item) => (
                <label
                  key={item.id}
                  className={cn(
                    "flex min-h-11 cursor-pointer items-center justify-center rounded-control border px-3 py-2 text-center text-[13.5px] font-medium transition-colors",
                    "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-focus has-[:focus-visible]:ring-offset-2",
                    topic === item.id ? "border-primary bg-primary/10 text-primary" : "border-border text-text-secondary hover:text-foreground",
                  )}
                >
                  <input type="radio" name="topic" value={item.id} checked={topic === item.id} onChange={() => setTopic(item.id)} className="sr-only" />
                  {item.label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className={authLabel}>Your name
            <input className={authInput} value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} autoComplete="name" />
          </label>
          <label className={authLabel}>Work email
            <input className={authInput} value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoComplete="email" placeholder="jane@mystore.com" />
          </label>
          <label className={authLabel}>Message
            <textarea className={cn(authInput, "h-32 resize-y py-2.5 leading-6")} value={message} onChange={(e) => setMessage(e.target.value)} required maxLength={5000} />
          </label>
          <button disabled={sending} className={authButton}>{sending ? "Sending…" : "Send message"}</button>
        </form>
      )}
      <AuthStatus message={error} tone="error" />
    </AuthShell>
  );
}
