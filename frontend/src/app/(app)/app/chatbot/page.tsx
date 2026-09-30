"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Clipboard,
  Globe2,
  Palette,
  Save,
  Zap,
} from "lucide-react";

import {
  ChatWidgetSettings,
  WorkflowTemplate,
  customerServiceApi,
  getChatWidgetSettings,
  updateChatWidgetSettings,
} from "@/domains/customer-service/api/customer-service";
import {
  Field,
  Toggle,
} from "@/domains/customer-service/chatbot/components/ChatbotUi";
import { ChatbotHero } from "@/domains/customer-service/chatbot/components/ChatbotHero";
import { StorefrontPreviewPanel } from "@/domains/customer-service/chatbot/components/StorefrontPreviewPanel";

const WIDGET_HOST = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export default function ChatbotPage() {
  const [settings, setSettings] = useState<ChatWidgetSettings | null>(null);
  const [draft, setDraft] = useState<Partial<ChatWidgetSettings>>({});
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [widget, workflowTemplates] = await Promise.all([
        getChatWidgetSettings(),
        customerServiceApi.workflowTemplates().catch(() => []),
      ]);
      setSettings(widget);
      setDraft(widget);
      setTemplates(workflowTemplates);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const brandColor = String(draft.brand_color || "#16a34a");
  const publicKey = settings?.public_key || "YOUR_PUBLIC_KEY";
  const publishedTemplates = templates.filter((template) => template.status === "published");
  const attachedTemplate = publishedTemplates.find((template) => template.id === draft.workflow_template_id);

  const isLocalWidgetHost = WIDGET_HOST.includes("localhost") || WIDGET_HOST.includes("127.0.0.1");

  const installScript = useMemo(
    () =>
      `<script src="${WIDGET_HOST}/tajeran-chat-widget.js" data-tajeran-public-key="${publicKey}" async></script>`,
    [publicKey],
  );

  async function save() {
    setSaving(true);
    try {
      await updateChatWidgetSettings({
        enabled: Boolean(draft.enabled),
        title: String(draft.title || "Chat with us"),
        welcome_message: String(draft.welcome_message || "Hi! How can we help you today?"),
        brand_color: brandColor,
        position: String(draft.position || "bottom-right"),
        assistant_name: String(draft.assistant_name || "Tajeran AI"),
        auto_answer_enabled: Boolean(draft.auto_answer_enabled),
        auto_answer_confidence_threshold: Number(draft.auto_answer_confidence_threshold ?? 0.75),
        human_handoff_enabled: Boolean(draft.human_handoff_enabled),
        human_handoff_message: String(
          draft.human_handoff_message || "I’ll connect you with our support team now.",
        ),
        workflow_template_id: draft.workflow_template_id || null,
        meta: draft.meta || null,
      });

      const refreshed = await getChatWidgetSettings();
      setSettings(refreshed);
      setDraft(refreshed);
    } finally {
      setSaving(false);
    }
  }

  async function copyInstallScript() {
    await navigator.clipboard.writeText(installScript);
  }

  async function loadTemplates() {
    setSeeding(true);
    try {
      await customerServiceApi.seedWebsiteChatWorkflowTemplates();
      setTemplates(await customerServiceApi.workflowTemplates());
    } finally {
      setSeeding(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-full bg-slate-950 p-6 text-white">
        <div className="rounded-[2rem] border border-white/10 bg-white/10 p-8">Loading chatbot workspace...</div>
      </main>
    );
  }

  return (
    <main className="min-h-full bg-slate-100 p-4 sm:p-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <ChatbotHero
          publicKey={publicKey}
          enabled={Boolean(draft.enabled)}
          autoAnswerAttached={Boolean(draft.auto_answer_enabled && draft.workflow_template_id)}
          hasPublicKey={Boolean(settings?.public_key)}
        />

        <div className="grid items-start gap-6 grid-cols-1">
          <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-xl shadow-slate-200/70">
            <div className="border-b border-slate-100 p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                    <Palette size={22} />
                  </div>
                  <h2 className="mt-3 text-2xl font-black text-slate-950">Widget control center</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    Brand the chat experience and connect it to your workflow automation.
                  </p>
                </div>

                <button
                  onClick={save}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2.5 text-sm font-black text-white shadow-lg shadow-slate-950/20 transition hover:-translate-y-0.5 hover:bg-slate-800 disabled:opacity-60"
                >
                  <Save size={16} />
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            </div>

            <div className="space-y-5 p-5">
              <Toggle
                title="Enable chatbot"
                description="Show the widget on your Shopify storefront when the install script is present."
                checked={Boolean(draft.enabled)}
                onChange={(checked) => setDraft((prev) => ({ ...prev, enabled: checked }))}
              />

              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Widget title" value={String(draft.title || "")} onChange={(value) => setDraft((prev) => ({ ...prev, title: value }))} />
                <Field
                  label="Assistant name"
                  value={String(draft.assistant_name || "")}
                  onChange={(value) => setDraft((prev) => ({ ...prev, assistant_name: value }))}
                />
              </div>

              <label className="grid gap-2">
                <span className="text-sm font-black text-slate-800">Welcome message</span>
                <textarea
                  value={String(draft.welcome_message || "")}
                  onChange={(event) => setDraft((prev) => ({ ...prev, welcome_message: event.target.value }))}
                  rows={4}
                  className="w-full resize-none rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 shadow-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                />
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Brand color" value={brandColor} onChange={(value) => setDraft((prev) => ({ ...prev, brand_color: value }))} />
                <label className="grid gap-2">
                  <span className="text-sm font-black text-slate-800">Position</span>
                  <select
                    value={String(draft.position || "bottom-right")}
                    onChange={(event) => setDraft((prev) => ({ ...prev, position: event.target.value }))}
                    className="h-12 w-full rounded-2xl border border-slate-300 bg-white px-4 text-sm text-slate-950 shadow-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                  >
                    <option value="bottom-right">Bottom right</option>
                    <option value="bottom-left">Bottom left</option>
                  </select>
                </label>
              </div>

              <div className="rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50 to-white p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 font-black text-slate-950">
                      <Zap size={18} className="text-emerald-700" />
                      Workflow auto-answer
                    </div>
                    <p className="mt-1 text-sm leading-6 text-slate-600">
                      Attach a published workflow to answer website chat messages automatically.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={Boolean(draft.auto_answer_enabled)}
                    onChange={(event) => setDraft((prev) => ({ ...prev, auto_answer_enabled: event.target.checked }))}
                    className="mt-1 h-5 w-5"
                  />
                </div>

                <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_180px]">
                  <label className="grid gap-2">
                    <span className="text-sm font-black text-slate-800">Automation workflow</span>
                    <select
                      value={String(draft.workflow_template_id || "")}
                      onChange={(event) => setDraft((prev) => ({ ...prev, workflow_template_id: event.target.value || null }))}
                      className="h-12 w-full rounded-2xl border border-slate-300 bg-white px-4 text-sm text-slate-950 shadow-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                    >
                      <option value="">No workflow attached</option>
                      {publishedTemplates.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="grid gap-2">
                    <span className="text-sm font-black text-slate-800">Min confidence</span>
                    <input
                      type="number"
                      min={0}
                      max={1}
                      step={0.05}
                      value={Number(draft.auto_answer_confidence_threshold ?? 0.75)}
                      onChange={(event) =>
                        setDraft((prev) => ({
                          ...prev,
                          auto_answer_confidence_threshold: Number(event.target.value),
                        }))
                      }
                      className="h-12 w-full rounded-2xl border border-slate-300 bg-white px-4 text-sm text-slate-950 shadow-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                    />
                  </label>
                </div>

                <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
                  <label className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-black text-slate-950">Human handoff</div>
                      <p className="mt-1 text-sm leading-6 text-slate-500">
                        If automation is low-confidence or needs human help, show a handoff message.
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={Boolean(draft.human_handoff_enabled)}
                      onChange={(event) =>
                        setDraft((prev) => ({
                          ...prev,
                          human_handoff_enabled: event.target.checked,
                        }))
                      }
                      className="mt-1 h-5 w-5"
                    />
                  </label>

                  <label className="mt-4 grid gap-2">
                    <span className="text-sm font-black text-slate-800">Handoff message</span>
                    <textarea
                      rows={2}
                      value={String(
                        draft.human_handoff_message || "I’ll connect you with our support team now.",
                      )}
                      onChange={(event) =>
                        setDraft((prev) => ({
                          ...prev,
                          human_handoff_message: event.target.value,
                        }))
                      }
                      className="w-full resize-none rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 shadow-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                    />
                  </label>
                </div>

                <div className="mt-5 grid gap-4 rounded-2xl border border-emerald-100 bg-white p-5 lg:grid-cols-[1fr_auto] lg:items-center">
                  <div className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">Attached workflow</div>
                  <div className="mt-2 text-sm font-black text-slate-950">{attachedTemplate?.name || "Manual support mode"}</div>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    {attachedTemplate
                      ? "When saved, Tajeran connects this workflow to customer.chat.message.created."
                      : "Agents can answer from Inbox. No automation will reply."}
                  </p>

                  <button
                    type="button"
                    onClick={loadTemplates}
                    disabled={seeding}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs font-black text-slate-700 transition hover:bg-slate-100 disabled:opacity-60 sm:w-auto"
                  >
                    {seeding ? "Loading..." : "Load chat template"}
                  </button>
                </div>
              </div>
            </div>
          </section>

            <StorefrontPreviewPanel
              brandColor={brandColor}
              draft={draft}
            />



          <section className="grid gap-5">
            <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-lg shadow-slate-200/60">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-950 text-white">
                    <Globe2 size={18} />
                  </div>
                  <div>
                    <h2 className="text-lg font-black text-slate-950">Install on Shopify storefront</h2>
                    <p className="text-sm text-slate-500">
                      Use this script in your Shopify theme or app embed. For real storefront testing, the host must be HTTPS.
                    </p>
                  </div>
                </div>

                <button
                  onClick={copyInstallScript}
                  className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-black text-slate-700 transition hover:-translate-y-0.5 hover:bg-slate-50"
                >
                  <Clipboard size={16} />
                  Copy script
                </button>
              </div>

              {isLocalWidgetHost && (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                  This script is using localhost. Shopify storefronts need an HTTPS host. Use a tunnel like Cloudflare Tunnel
                  during development, then set NEXT_PUBLIC_APP_URL to your production app URL before launch.
                </div>
              )}

              <div className="mt-4 grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 md:grid-cols-3">
                <div>
                  <div className="font-black text-slate-950">1. Enable widget</div>
                  <div className="mt-1 text-xs leading-5">Widget must be enabled and saved above.</div>
                </div>
                <div>
                  <div className="font-black text-slate-950">2. Install script</div>
                  <div className="mt-1 text-xs leading-5">Paste into Shopify theme or app embed block.</div>
                </div>
                <div>
                  <div className="font-black text-slate-950">3. Test message</div>
                  <div className="mt-1 text-xs leading-5">Send “I want to refund my order #1005”.</div>
                </div>
              </div>

              <pre className="mt-4 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950 p-4 text-xs leading-6 text-emerald-100 shadow-inner">
                <code>{installScript}</code>
              </pre>
            </div>


          </section>
        </div>
      </div>
    </main>
  );
}
