"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, GitBranch, Loader2, Users, Workflow, ListChecks } from "lucide-react";

import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { Badge } from "@/ui/primitives/badge";
import { Button } from "@/ui/primitives/button";
import { ProductNotice, ProductPanel, ProductStatCard } from "@/ui/product";
import {
  customerServiceApi,
  type Agent,
  type Queue,
  type RoutingPolicy,
  type Team,
} from "@/domains/customer-service/api/customer-service";

function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase();

  return (
    <Badge
      variant={
        normalized === "active" || normalized === "available"
          ? "success"
          : normalized === "inactive" || normalized === "offline"
            ? "muted"
            : "default"
      }
      className="capitalize"
    >
      {value.replaceAll("_", " ")}
    </Badge>
  );
}

export default function RoutingPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [queues, setQueues] = useState<Queue[]>([]);
  const [policies, setPolicies] = useState<RoutingPolicy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const availableAgents = useMemo(
    () => agents.filter((agent) => agent.availability === "available" && agent.status === "active"),
    [agents],
  );


  async function refreshRoutingWorkspace() {
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

  async function seedRoutingWorkspace() {
    try {
      setIsSeeding(true);
      setError(null);

      const refundAgent = await customerServiceApi.createAgent({
        agent_user_id: crypto.randomUUID(),
        display_name: "Refund Specialist",
        email: "refunds@tajeran.ai",
        status: "active",
        availability: "available",
        skills: ["refunds", "damaged-items", "shopify"],
        channels: ["email", "chat", "shopify"],
        languages: ["en"],
        max_open_tickets: 30,
      });

      const shippingAgent = await customerServiceApi.createAgent({
        agent_user_id: crypto.randomUUID(),
        display_name: "Shipping Specialist",
        email: "shipping@tajeran.ai",
        status: "active",
        availability: "available",
        skills: ["shipping", "tracking", "delays"],
        channels: ["email", "chat", "whatsapp"],
        languages: ["en"],
        max_open_tickets: 35,
      });

      const refundTeam = await customerServiceApi.createTeam({
        name: "Refund Team",
        description: "Handles refund, return, damaged item, and approval workflows.",
        is_active: true,
      });

      const shippingTeam = await customerServiceApi.createTeam({
        name: "Shipping Team",
        description: "Handles tracking, delivery delays, address changes, and reshipments.",
        is_active: true,
      });

      const refundQueue = await customerServiceApi.createQueue({
        name: "Refund Queue",
        description: "High-value refunds and damaged item cases.",
        team_id: refundTeam.id,
        channel: "shopify",
        intent: "refund",
        priority: "high",
        priority_rank: 10,
        is_default: false,
        is_active: true,
      });

      const shippingQueue = await customerServiceApi.createQueue({
        name: "Shipping Queue",
        description: "Where-is-my-order and delivery issue conversations.",
        team_id: shippingTeam.id,
        channel: "shopify",
        intent: "shipping",
        priority: "normal",
        priority_rank: 20,
        is_default: false,
        is_active: true,
      });

      await customerServiceApi.createRoutingPolicy({
        name: "Refund requests → Refund Team",
        channel: "shopify",
        intent: "refund",
        priority: "high",
        strategy: "least_loaded",
        candidate_assignee_ids: [refundAgent.id],
        candidate_team_ids: [refundTeam.id],
        candidate_queue_ids: [refundQueue.id],
        priority_rank: 10,
        is_fallback: false,
        is_active: true,
      });

      await customerServiceApi.createRoutingPolicy({
        name: "Shipping questions → Shipping Team",
        channel: "shopify",
        intent: "shipping",
        priority: "normal",
        strategy: "least_loaded",
        candidate_assignee_ids: [shippingAgent.id],
        candidate_team_ids: [shippingTeam.id],
        candidate_queue_ids: [shippingQueue.id],
        priority_rank: 20,
        is_fallback: false,
        is_active: true,
      });

      await refreshRoutingWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not seed routing workspace.");
    } finally {
      setIsSeeding(false);
    }
  }


  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setIsLoading(true);
        setError(null);

        if (!alive) return;

        await refreshRoutingWorkspace();
      } catch (err) {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Could not load routing workspace.");
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
        title="Agents, teams, queues & routing"
        description="Route every customer conversation to the right human or workflow based on channel, intent, priority, availability, and load."
        actions={
          <Button
            onClick={seedRoutingWorkspace}
            disabled={isSeeding}
          >
            {isSeeding ? "Creating..." : "Create Shopify routing setup"}
          </Button>
        }
      />

      {error && (
        <ProductNotice variant="danger">{error}</ProductNotice>
      )}

      {isLoading ? (
        <ProductPanel>
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <Loader2 className="animate-spin" size={16} />
            Loading routing workspace...
          </div>
        </ProductPanel>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <ProductStatCard label="Agents" value={agents.length} icon={Bot} />
            <ProductStatCard label="Available" value={availableAgents.length} icon={Users} />
            <ProductStatCard label="Queues" value={queues.length} icon={ListChecks} />
            <ProductStatCard label="Policies" value={policies.length} icon={GitBranch} />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
            <ProductPanel
              title="Agents"
              description="People or AI-assisted operators who can receive assigned tickets."
            >
              <div className="space-y-3">
                {agents.length === 0 ? (
                  <ProductNotice>No agents created yet.</ProductNotice>
                ) : (
                  agents.map((agent) => (
                    <div
                      key={agent.id}
                      className="rounded-2xl border border-border bg-surface p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-foreground">
                            {agent.display_name}
                          </div>
                          <div className="mt-1 text-sm text-text-secondary">
                            {agent.email || "No email"}
                          </div>
                        </div>

                        <div className="flex gap-2">
                          <StatusPill value={agent.status} />
                          <StatusPill value={agent.availability} />
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {agent.skills.slice(0, 5).map((skill) => (
                          <span key={skill} className="rounded-full bg-muted px-2 py-1 text-xs text-text-secondary">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ProductPanel>

            <ProductPanel
              title="Teams"
              description="Group agents by function like refunds, shipping, VIP, or technical support."
            >
              <div className="space-y-3">
                {teams.length === 0 ? (
                  <ProductNotice>No teams created yet.</ProductNotice>
                ) : (
                  teams.map((team) => (
                    <div key={team.id} className="rounded-2xl border border-border bg-surface p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-foreground">{team.name}</div>
                          <div className="mt-1 text-sm text-text-secondary">
                            {team.description || "No description"}
                          </div>
                        </div>
                        <StatusPill value={team.is_active ? "active" : "inactive"} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ProductPanel>

            <ProductPanel
              title="Queues"
              description="Queues collect conversations by channel, intent, or priority before assignment."
            >
              <div className="space-y-3">
                {queues.length === 0 ? (
                  <ProductNotice>No queues created yet.</ProductNotice>
                ) : (
                  queues.map((queue) => (
                    <div key={queue.id} className="rounded-2xl border border-border bg-surface p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-foreground">{queue.name}</div>
                          <div className="mt-1 text-sm text-text-secondary">
                            {queue.description || "No description"}
                          </div>
                        </div>
                        <StatusPill value={queue.is_default ? "default" : queue.is_active ? "active" : "inactive"} />
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2 text-xs">
                        {queue.channel && <StatusPill value={queue.channel} />}
                        {queue.intent && <StatusPill value={queue.intent} />}
                        {queue.priority && <StatusPill value={queue.priority} />}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ProductPanel>

            <ProductPanel
              title="Routing policies"
              description="Policies decide where support work goes based on intent, priority, channel, and load."
            >
              <div className="space-y-3">
                {policies.length === 0 ? (
                  <ProductNotice>No routing policies created yet.</ProductNotice>
                ) : (
                  policies.map((policy) => (
                    <div key={policy.id} className="rounded-2xl border border-border bg-surface p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-foreground">{policy.name}</div>
                          <div className="mt-1 text-sm text-text-secondary">
                            {policy.strategy.replaceAll("_", " ")} · rank {policy.priority_rank}
                          </div>
                        </div>
                        <StatusPill value={policy.is_fallback ? "fallback" : policy.is_active ? "active" : "inactive"} />
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2 text-xs">
                        {policy.channel && <StatusPill value={policy.channel} />}
                        {policy.intent && <StatusPill value={policy.intent} />}
                        {policy.priority && <StatusPill value={policy.priority} />}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ProductPanel>
          </div>

          <ProductPanel
            title="Workflow routing advantage"
            description="This is where Tajeran becomes different from normal helpdesks."
          >
            <div className="grid gap-4 md:grid-cols-3">
              {[
                ["Intent-aware", "Refunds, shipping, VIP complaints, and urgent issues can route differently."],
                ["Agent-aware", "Availability, skills, team membership, and capacity control assignment."],
                ["Workflow-aware", "Some requests can go to automation first, then human approval only when needed."],
              ].map(([title, body]) => (
                <div key={title} className="rounded-2xl border border-ai-100 bg-ai-50 p-4">
                  <Workflow className="text-ai-accent" size={18} />
                  <div className="mt-3 font-semibold text-ai-accent">{title}</div>
                  <p className="mt-2 text-sm leading-6 text-ai-accent">{body}</p>
                </div>
              ))}
            </div>
          </ProductPanel>
        </>
      )}
    </AppContainer>
  );
}
