import { apiJson, jsonBody } from "@/platform/api/client";

export type Workspace = {
  id: string;
  name: string;
  slug: string;
  business_name?: string | null;
  support_email?: string | null;
  default_sender_name?: string | null;
  default_sender_email?: string | null;
  default_locale: string;
  timezone: string;
  business_hours: Record<string, unknown>;
  role?: string | null;
  status: string;
};

export type WorkspaceMember = {
  id: string;
  user_id: string;
  role: string;
  status: string;
  state?: string;
  joined_at?: string | null;
  email?: string;
  display_name?: string;
};

export type WorkspaceInvitation = {
  id: string;
  email: string;
  role: string;
  status: string;
  expires_at: string;
};

const base = "/api/workspaces";

export const workspaceApi = {
  current() {
    return apiJson<Workspace>(`${base}/current`);
  },

  update(workspaceId: string, payload: Record<string, unknown>) {
    return apiJson<Workspace>(`${base}/${workspaceId}`, {
      method: "PATCH",
      body: jsonBody(payload),
    });
  },

  team(workspaceId: string) {
    return apiJson<WorkspaceMember[]>(`${base}/${workspaceId}/team`);
  },

  invite(workspaceId: string, payload: { email: string; role: string }) {
    return apiJson<WorkspaceInvitation>(`${base}/${workspaceId}/invitations`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },

  updateMember(workspaceId: string, userId: string, payload: { role?: string; status?: string }) {
    return apiJson<WorkspaceMember>(`${base}/${workspaceId}/members/${userId}`, {
      method: "PATCH",
      body: jsonBody(payload),
    });
  },
};
