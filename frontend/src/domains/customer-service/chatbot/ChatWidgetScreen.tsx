"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  getChatWidgetSettings,
  updateChatWidgetSettings,
} from "@/domains/customer-service/api/customer-service";
import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";
import { Input } from "@/ui/primitives/input";
import { Textarea } from "@/ui/primitives/textarea";

const WIDGET_HOST = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

// Buttons the customer sees when the chat opens.
const SELF_SERVICE = [
  { key: "track_order", label: "Track my order", description: "Shows order status and the tracking link from Shopify. The customer enters the order number and the email it was placed with." },
  { key: "report_problem", label: "Report a problem", description: "Collects the order number and what went wrong, then hands it to your team." },
  { key: "start_return", label: "Start a return", description: "Collects the order number and the reason, then hands it to your team." },
] as const;

// Must match LANGUAGES in backend .../runtime/nodes/conversation_history.py.
const LANGUAGES = [
  ["en", "English"], ["de", "German"], ["fr", "French"], ["es", "Spanish"], ["it", "Italian"],
  ["nl", "Dutch"], ["pt", "Portuguese"], ["tr", "Turkish"], ["ar", "Arabic"], ["fa", "Persian"],
] as const;

type ReplyLanguage = { customer_language: boolean; languages: string[] };

type SelfServiceKey = (typeof SELF_SERVICE)[number]["key"];

type Form = {
  enabled: boolean;
  title: string;
  assistant_name: string;
  welcome_message: string;
  brand_color: string;
  position: string;
  logo: string | null;
  reply_language: ReplyLanguage;
  self_service: Record<SelfServiceKey, boolean>;
};

const LOGO_MAX_BYTES = 200 * 1024;

const labelClass = "block text-[12.5px] font-medium text-foreground";

export default function ChatWidgetScreen() {
  const [form, setForm] = useState<Form | null>(null);
  const [publicKey, setPublicKey] = useState("");
  const [meta, setMeta] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getChatWidgetSettings()
      .then((settings) => {
        const chosen = (settings.meta?.self_service ?? {}) as Partial<Record<SelfServiceKey, boolean>>;
        setPublicKey(settings.public_key);
        setMeta(settings.meta ?? {});
        setForm({
          enabled: settings.enabled,
          title: settings.title,
          assistant_name: settings.assistant_name,
          welcome_message: settings.welcome_message,
          brand_color: settings.brand_color,
          position: settings.position,
          logo: typeof settings.meta?.logo === "string" ? settings.meta.logo : null,
          reply_language: { customer_language: true, languages: [], ...((settings.meta?.reply_language ?? {}) as Partial<ReplyLanguage>) },
          self_service: {
            track_order: Boolean(chosen.track_order),
            report_problem: Boolean(chosen.report_problem),
            start_return: Boolean(chosen.start_return),
          },
        });
      })
      .catch((err) => setError(apiErrorMessage(err, "Could not load the chat widget settings.")));
  }, []);

  if (!form) {
    return error
      ? <p role="alert" className="mt-5 text-sm text-danger">{error}</p>
      : <div className="mt-5 h-40 animate-pulse rounded bg-muted" />;
  }

  const set = (values: Partial<Form>) => {
    setForm({ ...form, ...values });
    setStatus(null);
  };
  const installCode = `<script src="${WIDGET_HOST}/tajeran-chat-widget.js" data-tajeran-public-key="${publicKey}" async></script>`;

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!form) return;
    setSaving(true);
    setError(null);
    try {
      const { self_service, logo, reply_language, ...look } = form;
      // Other features keep their own keys in meta (for example the topic
      // suggestions), so merge into what is saved now, not what this tab loaded.
      const latest = await getChatWidgetSettings().then((settings) => settings.meta ?? {}).catch(() => meta);
      const nextMeta = { ...latest, self_service, logo, reply_language };
      await updateChatWidgetSettings({ ...look, meta: nextMeta });
      setMeta(nextMeta);
      setStatus("Saved.");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save the chat widget settings."));
    } finally {
      setSaving(false);
    }
  }

  function chooseLogo(file: File | undefined) {
    if (!file) return;
    if (file.size > LOGO_MAX_BYTES) {
      setError("The logo must be smaller than 200 KB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setError(null);
      set({ logo: String(reader.result) });
    };
    reader.readAsDataURL(file);
  }

  async function copy() {
    await navigator.clipboard.writeText(installCode);
    setCopied(true);
  }

  return (
    <form onSubmit={save} className="mt-5 max-w-2xl space-y-8">
      <section>
        <label className="flex items-start gap-3">
          <input type="checkbox" role="switch" checked={form.enabled} onChange={(e) => set({ enabled: e.target.checked })} className="mt-0.5 h-4 w-4" />
          <span>
            <span className="block text-sm font-semibold text-foreground">Show the chat on your store</span>
            <span className="block text-[13px] text-text-secondary">The chat bubble appears on pages that have the install code.</span>
          </span>
        </label>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Install code</h2>
        <p className="mt-1 text-[13px] text-text-secondary">Paste this into your Shopify theme, just before the closing body tag.</p>
        <pre className="mt-2.5 overflow-x-auto rounded border border-border bg-muted px-3 py-2.5 text-xs text-foreground"><code>{installCode}</code></pre>
        {WIDGET_HOST.includes("localhost") ? (
          <p className="mt-2 text-[13px] text-text-secondary">This code points at localhost, so it only works on this computer. A live store needs the app's public HTTPS address.</p>
        ) : null}
        <Button type="button" size="sm" variant="secondary" onClick={copy} className="mt-2.5">{copied ? "Copied" : "Copy code"}</Button>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Look and greeting</h2>
        <div className="mt-2.5 grid gap-3 sm:grid-cols-2">
          <label className={labelClass}>Title<Input className="mt-1" value={form.title} maxLength={120} onChange={(e) => set({ title: e.target.value })} required /></label>
          <label className={labelClass}>Assistant name<Input className="mt-1" value={form.assistant_name} maxLength={120} onChange={(e) => set({ assistant_name: e.target.value })} required /></label>
          <label className={labelClass}>
            Colour
            <span className="mt-1 flex gap-2">
              <input type="color" aria-label="Pick a colour" value={/^#[0-9a-f]{6}$/i.test(form.brand_color) ? form.brand_color : "#000000"} onChange={(e) => set({ brand_color: e.target.value })} className="h-9 w-11 shrink-0 rounded border border-border bg-surface p-1" />
              <Input value={form.brand_color} maxLength={32} onChange={(e) => set({ brand_color: e.target.value })} required />
            </span>
          </label>
          <label className={labelClass}>
            Position
            <select value={form.position} onChange={(e) => set({ position: e.target.value })} className="mt-1 h-9 w-full rounded border border-border bg-surface px-2 text-sm font-normal">
              <option value="bottom-right">Bottom right</option>
              <option value="bottom-left">Bottom left</option>
            </select>
          </label>
          <div className={`${labelClass} sm:col-span-2`}>
            Logo
            <div className="mt-1 flex flex-wrap items-center gap-3">
              {form.logo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={form.logo} alt="Your logo" className="h-10 w-10 rounded border border-border bg-surface object-cover" />
              ) : null}
              <input
                type="file"
                aria-label="Upload a logo"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => { chooseLogo(e.target.files?.[0]); e.target.value = ""; }}
                className="max-w-full text-[13px] font-normal text-text-secondary"
              />
              {form.logo ? <Button type="button" size="sm" variant="ghost" onClick={() => set({ logo: null })}>Remove</Button> : null}
            </div>
            <p className="mt-1 text-[13px] font-normal text-text-secondary">Shown at the top of the chat instead of "AI". PNG, JPG or WebP, square, up to 200 KB.</p>
          </div>
          <label className={`${labelClass} sm:col-span-2`}>Greeting<Textarea className="mt-1 font-normal" value={form.welcome_message} onChange={(e) => set({ welcome_message: e.target.value })} required /></label>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Language</h2>
        <label className="mt-2.5 flex items-start gap-3">
          <input
            type="checkbox"
            role="switch"
            checked={form.reply_language.customer_language}
            onChange={(e) => set({ reply_language: { ...form.reply_language, customer_language: e.target.checked } })}
            className="mt-0.5 h-4 w-4"
          />
          <span>
            <span className="block text-sm font-medium text-foreground">Reply in the customer's language</span>
            <span className="block text-[13px] text-text-secondary">When off, automated replies are always in your workspace language.</span>
          </span>
        </label>
        {form.reply_language.customer_language ? (
          <fieldset className="mt-3">
            <legend className="text-[13px] text-text-secondary">Only these languages (none selected means any language):</legend>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
              {LANGUAGES.map(([code, name]) => (
                <label key={code} className="flex items-center gap-1.5 text-[13px] text-foreground">
                  <input
                    type="checkbox"
                    checked={form.reply_language.languages.includes(code)}
                    onChange={(e) => set({
                      reply_language: {
                        ...form.reply_language,
                        languages: e.target.checked
                          ? [...form.reply_language.languages, code]
                          : form.reply_language.languages.filter((item) => item !== code),
                      },
                    })}
                    className="h-4 w-4"
                  />
                  {name}
                </label>
              ))}
            </div>
          </fieldset>
        ) : null}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Self-service buttons</h2>
        <p className="mt-1 text-[13px] text-text-secondary">Shown when a customer opens the chat. They work without AI.</p>
        <div className="mt-2.5 divide-y divide-border border-y border-border">
          {SELF_SERVICE.map((item) => (
            <label key={item.key} className="flex items-start gap-3 py-3">
              <input
                type="checkbox"
                role="switch"
                checked={form.self_service[item.key]}
                onChange={(e) => set({ self_service: { ...form.self_service, [item.key]: e.target.checked } })}
                className="mt-0.5 h-4 w-4"
              />
              <span>
                <span className="block text-sm font-medium text-foreground">{item.label}</span>
                <span className="block text-[13px] text-text-secondary">{item.description}</span>
              </span>
            </label>
          ))}
        </div>
      </section>

      <div className="flex items-center gap-3">
        <Button type="submit" size="sm" disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        {status ? <p role="status" className="text-[13px] text-text-secondary">{status}</p> : null}
        {error ? <p role="alert" className="text-[13px] text-danger">{error}</p> : null}
      </div>
    </form>
  );
}
