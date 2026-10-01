"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";
import { Input } from "@/ui/primitives/input";

import { workspaceApi, type Workspace, type WorkspaceMember } from "./api/workspace";

// What each role may do (mirrors the backend's role permissions).
const ROLES = [
  { value: "agent", label: "Agent", can: "Reads the inbox, replies to customers, assigns and resolves conversations, looks up orders." },
  { value: "manager", label: "Manager", can: "Everything an agent can, plus workflows, routing, macros and the Desk reports." },
  { value: "admin", label: "Admin", can: "Everything a manager can, plus settings, connections, billing and the team." },
] as const;

const roleLabel = (role: string) => (role === "owner" ? "Owner" : ROLES.find((item) => item.value === role)?.label ?? role);
const select = "h-9 rounded-control border border-border bg-surface px-2 text-[13.5px] text-foreground";

export default function TeamScreen() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [team, setTeam] = useState<WorkspaceMember[] | null>(null);
  const [invite, setInvite] = useState({ email: "", role: "agent" });
  const [link, setLink] = useState<{ email: string; url: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const current = workspace ?? (await workspaceApi.current());
    setWorkspace(current);
    setTeam(await workspaceApi.team(current.id));
  };

  useEffect(() => {
    load().catch((err) => setError(apiErrorMessage(err, "Could not load the team.")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Runs a change, then reloads the list; shows the invite link when there is one.
  const run = async (action: () => Promise<{ invite_link?: string | null; email?: string } | unknown>, fallback: string) => {
    setBusy(true);
    setError(null);
    try {
      const result = (await action()) as { invite_link?: string | null; email?: string } | null;
      if (result?.invite_link && result.email) {
        setLink({ email: result.email, url: result.invite_link });
        setCopied(false);
      }
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, fallback));
    } finally {
      setBusy(false);
    }
  };

  if (!team || !workspace) {
    return error
      ? <p role="alert" className="mt-5 text-sm text-danger">{error}</p>
      : <div className="mt-5 h-40 animate-pulse rounded bg-muted" />;
  }

  const sendInvite = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      const created = await workspaceApi.invite(workspace.id, invite);
      setInvite({ email: "", role: "agent" });
      return created;
    }, "Could not invite this person.");
  };

  return (
    <div className="mt-5 max-w-3xl space-y-8">
      <section>
        <h2 className="text-sm font-semibold text-foreground">Invite a teammate</h2>
        <p className="mt-1 text-[13px] text-text-secondary">They get an email with a link and choose their own password. You can also copy the link and send it yourself.</p>
        <form onSubmit={sendInvite} className="mt-2.5 flex flex-wrap items-center gap-2">
          <label htmlFor="invite-email" className="sr-only">Email</label>
          <Input id="invite-email" type="email" required value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} placeholder="name@yourstore.com" className="w-full sm:w-64" />
          <label htmlFor="invite-role" className="sr-only">Role</label>
          <select id="invite-role" value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })} className={select}>
            {ROLES.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
          </select>
          <Button type="submit" size="sm" disabled={busy}>Invite</Button>
        </form>
        {link ? (
          <div className="mt-3 rounded-container border border-border bg-muted px-3 py-2.5">
            <p className="text-[13px] text-foreground">Invite link for {link.email} (valid for 7 days):</p>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <code className="min-w-0 flex-1 truncate rounded border border-border bg-surface px-2 py-1 text-xs text-foreground">{link.url}</code>
              <Button type="button" size="sm" variant="secondary" onClick={() => { void navigator.clipboard.writeText(link.url); setCopied(true); }}>
                {copied ? "Copied" : "Copy link"}
              </Button>
            </div>
          </div>
        ) : null}
        {error ? <p role="alert" className="mt-2 text-[13px] text-danger">{error}</p> : null}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">Team members</h2>
        <ul className="mt-2.5 divide-y divide-border border-y border-border">
          {team.map((member) => {
            const invited = member.state === "invited" || !member.user_id;
            const suspended = member.state === "deactivated";
            return (
              <li key={member.id} className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3">
                <div className="min-w-0 flex-1 basis-48">
                  <p className="truncate text-sm font-medium text-foreground">{member.display_name || member.email}</p>
                  <p className="truncate text-[12.5px] text-text-secondary">
                    {member.display_name ? `${member.email} · ` : ""}
                    {invited ? "Invited, not joined yet" : suspended ? "Deactivated" : "Active"}
                  </p>
                </div>
                {member.role === "owner" || invited ? (
                  <span className="text-[13px] text-text-secondary">{roleLabel(member.role)}</span>
                ) : (
                  <select
                    aria-label={`Role of ${member.display_name || member.email}`}
                    value={member.role}
                    disabled={busy}
                    onChange={(e) => void run(() => workspaceApi.updateMember(workspace.id, member.user_id, { role: e.target.value }), "Could not change the role.")}
                    className={select}
                  >
                    {ROLES.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
                  </select>
                )}
                {invited && member.invitation_id ? (
                  <>
                    <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => void run(() => workspaceApi.resendInvitation(workspace.id, member.invitation_id!), "Could not resend the invitation.")}>
                      Resend
                    </Button>
                    <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => void run(() => workspaceApi.revokeInvitation(workspace.id, member.invitation_id!), "Could not cancel the invitation.")}>
                      Cancel invite
                    </Button>
                  </>
                ) : null}
                {!invited && member.role !== "owner" ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => void run(() => workspaceApi.updateMember(workspace.id, member.user_id, { status: suspended ? "active" : "suspended" }), "Could not change this member.")}
                  >
                    {suspended ? "Reactivate" : "Deactivate"}
                  </Button>
                ) : null}
              </li>
            );
          })}
        </ul>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-foreground">What each role can do</h2>
        <dl className="mt-2.5 space-y-2 text-[13px]">
          {ROLES.map((role) => (
            <div key={role.value} className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
              <dt className="w-20 shrink-0 font-medium text-foreground">{role.label}</dt>
              <dd className="text-text-secondary">{role.can}</dd>
            </div>
          ))}
          <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
            <dt className="w-20 shrink-0 font-medium text-foreground">Owner</dt>
            <dd className="text-text-secondary">Everything. There is one owner per workspace.</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
