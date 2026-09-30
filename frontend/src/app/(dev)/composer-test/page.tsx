"use client";

import { useMemo } from "react";
import Link from "next/link";

import { compileToRuntimeWorkflow } from "@/domains/workflow/composer/utils/compileToRuntimeWorkflow";
import { connectComposerBlocks } from "@/domains/workflow/composer/utils/connectBlocks";
import { createComposerBlock } from "@/domains/workflow/composer/utils/createBlock";
import type {
    ComposerEdge,
    ComposerNode,
} from "@/domains/workflow/composer/types/composer";

export default function ComposerTestPage() {
    const { nodes, edges, runtime } = useMemo(() => {
        const trigger = createComposerBlock(
            "customer_message_trigger",
            { x: 0, y: 0 },
            {
                id: "test-trigger",
                config: {
                    input: "Refund order ORD-991 for 149",
                },
            }
        );

        const agent = createComposerBlock(
            "ai_agent",
            { x: 300, y: 0 },
            {
                id: "test-agent",
                label: "Refund Agent",
                config: {
                    name: "Refund Agent",
                    responsibility:
                        "You are a refund agent. If the customer asks for a refund, call fake_refund_order.",
                    save_as: "refund_result",
                    tools: ["fake_refund_order"],
                    max_steps: 5,
                },
            }
        );

        const response = createComposerBlock(
            "send_response",
            { x: 600, y: 0 },
            {
                id: "test-response",
                label: "Final Response",
            }
        );

        const blockNodes: ComposerNode[] = [trigger, agent, response];

        let blockEdges: ComposerEdge[] = [];

        blockEdges = connectComposerBlocks(
            {
                source: trigger.id,
                target: agent.id,
                sourceHandle: null,
                targetHandle: null,
            },
            blockNodes,
            blockEdges
        );

        blockEdges = connectComposerBlocks(
            {
                source: agent.id,
                target: response.id,
                sourceHandle: null,
                targetHandle: null,
            },
            blockNodes,
            blockEdges
        );

        const compiled = compileToRuntimeWorkflow(blockNodes, blockEdges);

        return {
            nodes: blockNodes,
            edges: blockEdges,
            runtime: compiled,
        };
    }, []);

    return (
        <main className="min-h-screen bg-slate-50 p-6 text-slate-950">
            <div className="mx-auto max-w-6xl space-y-6">
                <div>
                    <Link href="/dev-console" className="text-sm text-slate-500 hover:text-slate-950">
                        ← Back to Dev Console
                    </Link>

                    <h1 className="mt-3 text-2xl font-bold">Composer Compiler Test</h1>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                        This proves business-level workflow blocks can compile into your existing runtime workflow format.
                    </p>
                </div>

                <section className="grid gap-4 lg:grid-cols-2">
                    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                        <h2 className="font-semibold">Composer Blocks</h2>
                        <pre className="mt-4 max-h-[520px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">
              {JSON.stringify({ nodes, edges }, null, 2)}
            </pre>
                    </div>

                    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                        <h2 className="font-semibold">Compiled Runtime Workflow</h2>
                        <pre className="mt-4 max-h-[520px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">
              {JSON.stringify(runtime, null, 2)}
            </pre>
                    </div>
                </section>
            </div>
        </main>
    );
}