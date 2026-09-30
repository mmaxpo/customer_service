# Tajeran Workflow Builder Roadmap --- Phase A (Information Architecture)

## Goal

Design the world's best AI-native workflow builder for business
automation.

The builder should make users feel:

-   Powerful
-   Safe
-   Intelligent
-   Confident
-   Productive

It should **not** feel like programming. It should feel like designing
business logic.

------------------------------------------------------------------------

# Core Mental Model

The builder is **not a graph editor**.

It is a **Business Capability Composer**.

Users assemble capabilities such as:

-   Understand customer
-   Search knowledge
-   Find Shopify order
-   Think
-   Decide
-   Request approval
-   Refund
-   Reply
-   Wait
-   Finish

React Flow is only the rendering engine.

The product is a Business IDE.

------------------------------------------------------------------------

# Capability Taxonomy

## Intelligence

-   Understand
-   Classify
-   Extract
-   Summarize
-   Think
-   Plan
-   Decide
-   Generate Reply

## Customer

-   Conversation
-   Customer
-   Ticket
-   Tags
-   SLA
-   Routing

## Commerce

-   Shopify
-   Refund
-   Cancel
-   Shipping
-   Inventory
-   Order Lookup

## Knowledge

-   Search
-   Retrieve
-   Memory
-   Documents
-   MCP

## Communication

-   Email
-   Chat
-   WhatsApp
-   Instagram
-   SMS
-   Slack

## Human

-   Approval
-   Assignment
-   Escalation
-   Review

## Flow

-   Wait
-   Loop
-   Split
-   Merge
-   Retry
-   Branch
-   Parallel

## Integrations

-   HTTP
-   API
-   Database
-   Webhook
-   Storage

------------------------------------------------------------------------

# Node Inspector

Every node should contain:

1.  Overview
2.  Inputs
3.  Outputs
4.  Examples
5.  Runtime
6.  Advanced

The first screen should explain *why* the capability exists, not only
configuration.

------------------------------------------------------------------------

# Execution Experience

Execution should animate capability progress.

States:

-   Waiting
-   Running
-   Thinking
-   Calling Tool
-   Waiting Human
-   Completed
-   Failed

Each node exposes:

-   Input
-   Output
-   Variables
-   Memory
-   Tool calls
-   Events
-   Runtime
-   Cost
-   Replay

------------------------------------------------------------------------

# Design Principle

Every future feature must answer:

> Does this make business automation feel simpler while increasing
> capability?

If not, it does not belong in the builder.

------------------------------------------------------------------------

# Deliverable of Phase A

Before implementing new UI, define:

-   Capability catalog
-   Palette taxonomy
-   Inspector specification
-   Execution visualization
-   Debugging experience
-   Interaction rules

Only after these are stable should implementation begin.
