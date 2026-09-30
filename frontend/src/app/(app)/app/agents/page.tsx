"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, GitBranch, Loader2, Users, Workflow } from "lucide-react";

import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { Badge } from "@/ui/primitives/badge";
import { Button } from "@/ui/primitives/button";
import { Input } from "@/ui/primitives/input";
import { ProductNotice, ProductPanel, ProductStatCard } from "@/ui/product";
import {
  customerServiceApi,
  type Agent,
  type Queue,
  type RoutingPolicy,
  type Team,
} from "@/domains/customer-service/api/customer-service";

function statusVariant(value: string) {
  const normalized = value.toLowerCase();

  if (normalized === "active" || normalized === "available") return "success";
  if (normalized === "inactive" || normalized === "offline") return "muted";
  if (normalized === "busy") return "warning";

  return "default";
}

function StatusBadge({ value }: { value: string }) {
  return (
    <Badge variant={statusVariant(value) as "success" | "warning" | "muted" | "default"} className="capitalize">
      {value.replaceAll("_", " ")}
    </Badge>
  );
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [queues, setQueues] = useState<Queue[]>([]);
  const [policies, setPolicies] = useState<RoutingPolicy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [isCreatingAgent, setIsCreatingAgent] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [agentName, setAgentName] = useState("Support Agent");
  const [agentEmail, setAgentEmail] = useState("support-agent@tajeran.ai");
  const [agentSkills, setAgentSkills] = useState("refunds, shipping, shopify");

  const [isCreatingTeam, setIsCreatingTeam] = useState(false);
  const [teamName, setTeamName] = useState("Refund Team");
  const [teamDescription, setTeamDescription] = useState("Handles refunds, damaged items, exchanges, and approval workflows.");

  const [isCreatingQueue, setIsCreatingQueue] = useState(false);
  const [queueName, setQueueName] = useState("Refund Queue");
  const [queueIntent, setQueueIntent] = useState("refund");
  const [queuePriority, setQueuePriority] = useState("high");

  const [isCreatingPolicy, setIsCreatingPolicy] = useState(false);
  const [policyName, setPolicyName] = useState("Refund requests → best available owner");
  const [policyIntent, setPolicyIntent] = useState("refund");
  const [policyPriority, setPolicyPriority] = useState("high");

  const availableAgents = useMemo(
    () => agents.filter((agent) => agent.status === "active" && agent.availability === "available"),
    [agents],
  );

  const activeTeams = useMemo(
    () => teams.filter((team) => team.is_active),
    [teams],
  );

  const activeQueues = useMemo(
    () => queues.filter((queue) => queue.is_active),
    [queues],
  );

  async function refresh() {
    const [agentData, teamData, queueData, policyData] = await Promise.all([
      customerServiceApi.agents().catch(() => []),
      customerServiceApi.teams().catch(() => []),
      customerServiceApi.queues().catch(() => []),
      customerServiceApi.routingPolicies().catch(() => []),
    ]);

    setAgents(agentData);
    setTeams(teamData);
    setQueues(queueData);
    setPolicies(policyData);
  }

  async function createAgent() {
    const skills = agentSkills
      .split(",")
      .map((skill) => skill.trim())
      .filter(Boolean);

    if (!agentName.trim()) {
      setStatus("Agent name is required.");
      return;
    }

    try {
      setIsCreatingAgent(true);
      setStatus(null);

      await customerServiceApi.createAgent({
        agent_user_id: crypto.randomUUID(),
        display_name: agentName.trim(),
        email: agentEmail.trim() || null,
        status: "active",
        availability: "available",
        skills,
        channels: ["email", "chat", "shopify"],
        languages: ["en"],
        max_open_tickets: 30,
      });

      await refresh();
      setStatus(`Created agent: ${agentName.trim()}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create agent.");
    } finally {
      setIsCreatingAgent(false);
    }
  }

  async function createTeam() {
    if (!teamName.trim()) {
      setStatus("Team name is required.");
      return;
    }

    try {
      setIsCreatingTeam(true);
      setStatus(null);

      await customerServiceApi.createTeam({
        name: teamName.trim(),
        description: teamDescription.trim() || null,
        is_active: true,
      });

      await refresh();
      setStatus(`Created team: ${teamName.trim()}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create team.");
    } finally {
      setIsCreatingTeam(false);
    }
  }

  async function createQueue() {
    if (!queueName.trim()) {
      setStatus("Queue name is required.");
      return;
    }

    try {
      setIsCreatingQueue(true);
      setStatus(null);

      await customerServiceApi.createQueue({
        name: queueName.trim(),
        description: `${queueName.trim()} for ${queueIntent || "general"} support work.`,
        channel: "shopify",
        intent: queueIntent.trim() || null,
        priority: queuePriority.trim() || null,
        priority_rank: queuePriority === "high" ? 10 : 50,
        is_default: false,
        is_active: true,
      });

      await refresh();
      setStatus(`Created queue: ${queueName.trim()}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create queue.");
    } finally {
      setIsCreatingQueue(false);
    }
  }

  async function createRoutingPolicy() {
    if (!policyName.trim()) {
      setStatus("Routing policy name is required.");
      return;
    }

    try {
      setIsCreatingPolicy(true);
      setStatus(null);

      await customerServiceApi.createRoutingPolicy({
        name: policyName.trim(),
        channel: "shopify",
        intent: policyIntent.trim() || null,
        priority: policyPriority.trim() || null,
        strategy: "least_loaded",
        candidate_assignee_ids: agents.slice(0, 3).map((agent) => agent.id),
        candidate_team_ids: teams.slice(0, 3).map((team) => team.id),
        candidate_queue_ids: queues.slice(0, 3).map((queue) => queue.id),
        priority_rank: policyPriority === "high" ? 10 : 50,
        is_fallback: false,
        is_active: true,
      });

      await refresh();
      setStatus(`Created routing policy: ${policyName.trim()}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create routing policy.");
    } finally {
      setIsCreatingPolicy(false);
    }
  }

  async function seedDemoAgents() {
    try {
      setIsSeeding(true);
      setStatus(null);

      await customerServiceApi.createAgent({
        agent_user_id: crypto.randomUUID(),
        display_name: "AI Refund Specialist",
        email: "ai-refunds@tajeran.ai",
        status: "active",
        availability: "available",
        skills: ["refunds", "damaged-items", "shopify", "approval-review"],
        channels: ["email", "chat", "shopify"],
        languages: ["en"],
        max_open_tickets: 30,
      }).catch(() => null);

      await customerServiceApi.createAgent({
        agent_user_id: crypto.randomUUID(),
        display_name: "Shipping Copilot",
        email: "shipping-copilot@tajeran.ai",
        status: "active",
        availability: "available",
        skills: ["shipping", "tracking", "delivery-delay", "reshipment"],
        channels: ["email", "chat", "whatsapp"],
        languages: ["en"],
        max_open_tickets: 35,
      }).catch(() => null);

      await refresh();
      setStatus("Agent workspace is ready.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not seed agents.");
    } finally {
      setIsSeeding(false);
    }
  }

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setIsLoading(true);
        await refresh();
      } finally {
        if (alive) setIsLoading(false);
      }
    }

    load();

    return () => {
      alive = false;
    };
  }, []);

  return (
    <AppContainer>
      <PageHeader
        eyebrow="Operations"
        title="Agent dashboard"
        description="Manage human agents, AI copilots, teams, queues, availability, capacity, and routing readiness."
        actions={
          <Button onClick={seedDemoAgents} disabled={isSeeding}>
            {isSeeding ? "Creating..." : "Create demo agents"}
          </Button>
        }
      />

      {status && <ProductNotice>{status}</ProductNotice>}

      <div className="grid gap-4 md:grid-cols-4">
        <ProductStatCard label="Agents" value={isLoading ? "—" : agents.length} icon={Bot} />
        <ProductStatCard label="Available" value={isLoading ? "—" : availableAgents.length} icon={Users} />
        <ProductStatCard label="Active teams" value={isLoading ? "—" : activeTeams.length} icon={GitBranch} />
        <ProductStatCard label="Active queues" value={isLoading ? "—" : activeQueues.length} icon={Workflow} />
      </div>

      <ProductPanel
        title="Agentic operations pipeline"
        description="This is the framework control path from customer event to assigned work and workflow execution."
      >
        <div className="grid gap-3 md:grid-cols-6">
          {[
            ["1", "Inbound", "Conversation, chat, email, Shopify event"],
            ["2", "Intelligence", "Intent, priority, sentiment, context"],
            ["3", "Routing", "Policy chooses owner or work container"],
            ["4", "Queue / Team", "Work waits in the right operational lane"],
            ["5", "Agent", "Human, AI, or hybrid worker owns the task"],
            ["6", "Workflow", "Tools, approvals, replies, and run trace"],
          ].map(([step, title, body]) => (
            <div key={step} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-950 text-xs font-bold text-white">
                {step}
              </div>
              <div className="mt-3 font-semibold text-slate-950">{title}</div>
              <p className="mt-2 text-xs leading-5 text-slate-500">{body}</p>
            </div>
          ))}
        </div>
      </ProductPanel>

      {isLoading ? (
        <ProductPanel>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="animate-spin" size={16} />
            Loading agent workspace...
          </div>
        </ProductPanel>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
          <ProductPanel
            title="Agents & AI copilots"
            description="Operators who can own tickets, review AI replies, approve actions, or handle escalations."
          >
            {agents.length === 0 ? (
              <ProductNotice>No agents created yet.</ProductNotice>
            ) : (
              <div className="space-y-3">
                {agents.map((agent) => (
                  <div key={agent.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                      <div>
                        <div className="font-semibold text-slate-950">{agent.display_name}</div>
                        <div className="mt-1 text-sm text-slate-500">{agent.email || "No email"}</div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <StatusBadge value={agent.status} />
                        <StatusBadge value={agent.availability} />
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {agent.skills.slice(0, 8).map((skill) => (
                        <Badge key={skill} variant="default">
                          {skill}
                        </Badge>
                      ))}
                    </div>

                    <div className="mt-3 text-xs text-slate-500">
                      Max open tickets: {agent.max_open_tickets ?? "—"} · Channels: {agent.channels.join(", ") || "—"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ProductPanel>

          <div className="space-y-6">
            <ProductPanel
              title="Quick create agent"
              description="Create a human agent or AI-assisted operator without leaving the dashboard."
            >
              <div className="space-y-3">
                <Input
                  value={agentName}
                  onChange={(event) => setAgentName(event.target.value)}
                  placeholder="Agent display name"
                />
                <Input
                  value={agentEmail}
                  onChange={(event) => setAgentEmail(event.target.value)}
                  placeholder="Agent email"
                />
                <Input
                  value={agentSkills}
                  onChange={(event) => setAgentSkills(event.target.value)}
                  placeholder="Skills separated by commas"
                />
                <Button
                  onClick={createAgent}
                  disabled={isCreatingAgent}
                  className="w-full"
                >
                  {isCreatingAgent ? "Creating..." : "Create agent"}
                </Button>
              </div>
            </ProductPanel>

            <ProductPanel
              title="Quick create team"
              description="Create a responsibility group that agents or workflows can route work into."
            >
              <div className="space-y-3">
                <Input
                  value={teamName}
                  onChange={(event) => setTeamName(event.target.value)}
                  placeholder="Team name"
                />
                <Input
                  value={teamDescription}
                  onChange={(event) => setTeamDescription(event.target.value)}
                  placeholder="Team description"
                />
                <Button
                  onClick={createTeam}
                  disabled={isCreatingTeam}
                  className="w-full"
                >
                  {isCreatingTeam ? "Creating..." : "Create team"}
                </Button>
              </div>
            </ProductPanel>

            <ProductPanel
              title="Quick create queue"
              description="Create a work container for conversations before assignment."
            >
              <div className="space-y-3">
                <Input
                  value={queueName}
                  onChange={(event) => setQueueName(event.target.value)}
                  placeholder="Queue name"
                />
                <Input
                  value={queueIntent}
                  onChange={(event) => setQueueIntent(event.target.value)}
                  placeholder="Intent, e.g. refund"
                />
                <Input
                  value={queuePriority}
                  onChange={(event) => setQueuePriority(event.target.value)}
                  placeholder="Priority, e.g. high"
                />
                <Button
                  onClick={createQueue}
                  disabled={isCreatingQueue}
                  className="w-full"
                >
                  {isCreatingQueue ? "Creating..." : "Create queue"}
                </Button>
              </div>
            </ProductPanel>

            <ProductPanel
              title="Quick create routing policy"
              description="Connect intent and priority to available agents, teams, and queues."
            >
              <div className="space-y-3">
                <Input
                  value={policyName}
                  onChange={(event) => setPolicyName(event.target.value)}
                  placeholder="Policy name"
                />
                <Input
                  value={policyIntent}
                  onChange={(event) => setPolicyIntent(event.target.value)}
                  placeholder="Intent, e.g. refund"
                />
                <Input
                  value={policyPriority}
                  onChange={(event) => setPolicyPriority(event.target.value)}
                  placeholder="Priority, e.g. high"
                />
                <ProductNotice>
                  Uses first {Math.min(agents.length, 3)} agent(s), {Math.min(teams.length, 3)} team(s), and {Math.min(queues.length, 3)} queue(s) as candidates.
                </ProductNotice>
                <Button
                  onClick={createRoutingPolicy}
                  disabled={isCreatingPolicy}
                  className="w-full"
                >
                  {isCreatingPolicy ? "Creating..." : "Create routing policy"}
                </Button>
              </div>
            </ProductPanel>

            <ProductPanel
              title="Teams"
              description="Functional groups for refunds, shipping, VIP customers, and escalations."
            >
              {teams.length === 0 ? (
                <ProductNotice>No teams created yet.</ProductNotice>
              ) : (
                <div className="space-y-3">
                  {teams.map((team) => (
                    <div key={team.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-slate-950">{team.name}</div>
                          <p className="mt-1 text-sm leading-6 text-slate-500">{team.description || "No description"}</p>
                        </div>
                        <StatusBadge value={team.is_active ? "active" : "inactive"} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ProductPanel>

            <ProductPanel
              title="Queues"
              description="Work containers where conversations wait before assignment."
            >
              {queues.length === 0 ? (
                <ProductNotice>No queues created yet.</ProductNotice>
              ) : (
                <div className="space-y-3">
                  {queues.map((queue) => (
                    <div key={queue.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-slate-950">{queue.name}</div>
                          <p className="mt-1 text-sm leading-6 text-slate-500">{queue.description || "No description"}</p>
                        </div>
                        <StatusBadge value={queue.is_default ? "default" : queue.is_active ? "active" : "inactive"} />
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {queue.channel && <Badge variant="default">{queue.channel}</Badge>}
                        {queue.intent && <Badge variant="default">{queue.intent}</Badge>}
                        {queue.priority && <Badge variant="default">{queue.priority}</Badge>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ProductPanel>

            <ProductPanel
              title="Routing policies"
              description="Decision rules that connect channel, intent, priority, agents, teams, and queues."
            >
              {policies.length === 0 ? (
                <ProductNotice>No routing policies created yet.</ProductNotice>
              ) : (
                <div className="space-y-3">
                  {policies.map((policy) => (
                    <div key={policy.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-slate-950">{policy.name}</div>
                          <p className="mt-1 text-sm leading-6 text-slate-500">
                            {policy.strategy.replaceAll("_", " ")} · rank {policy.priority_rank}
                          </p>
                        </div>
                        <StatusBadge value={policy.is_fallback ? "fallback" : policy.is_active ? "active" : "inactive"} />
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {policy.channel && <Badge variant="default">{policy.channel}</Badge>}
                        {policy.intent && <Badge variant="default">{policy.intent}</Badge>}
                        {policy.priority && <Badge variant="default">{policy.priority}</Badge>}
                        <Badge variant="muted">{policy.candidate_assignee_ids.length} agents</Badge>
                        <Badge variant="muted">{policy.candidate_team_ids.length} teams</Badge>
                        <Badge variant="muted">{policy.candidate_queue_ids.length} queues</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ProductPanel>
          </div>
        </div>
      )}
    </AppContainer>
  );
}
