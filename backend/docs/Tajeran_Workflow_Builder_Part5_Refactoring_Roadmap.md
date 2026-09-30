# Tajeran Workflow Builder - Part 5

# Refactoring & Implementation Roadmap

## Mission

Refactor the existing Workflow Builder into a scalable architecture
**without stopping feature development**.

------------------------------------------------------------------------

# Current Assets

Already implemented:

-   React Flow canvas
-   Workflow composer
-   Workflow builder
-   Runtime integration
-   Backend execution engine
-   Runtime streaming
-   Agent nodes
-   Shopify nodes
-   Human approval
-   Workflow execution
-   Catalog loading

These are valuable assets---not something to rewrite.

------------------------------------------------------------------------

# Target Architecture

    src/features/workflows/

    builder/
        shell/
        canvas/
        palette/
        inspector/
        runtime/
        validation/
        variables/
        ai/
        templates/
        shared/

Each module owns a single responsibility.

------------------------------------------------------------------------

# Refactor Phases

## Phase 1 --- Builder Shell

Goal:

Separate orchestration from UI.

Deliverables

-   BuilderShell
-   Layout manager
-   Shared builder context
-   Feature boundaries

Success:

The canvas can be replaced without changing inspector or palette.

------------------------------------------------------------------------

## Phase 2 --- Canvas

Responsibilities

-   Render graph
-   Selection
-   Drag
-   Zoom
-   Connect

Nothing else.

Business logic leaves the canvas.

------------------------------------------------------------------------

## Phase 3 --- Capability Palette

Replace node list with capability catalog.

Features

-   Categories
-   Search
-   Favorites
-   Recently used
-   AI suggested
-   Templates

------------------------------------------------------------------------

## Phase 4 --- Inspector

Replace configuration form with a capability workspace.

Sections

-   Overview
-   Configure
-   Runtime
-   Examples
-   Debug
-   Documentation

------------------------------------------------------------------------

## Phase 5 --- Runtime Experience

Real-time execution overlay.

Visual states

-   Thinking
-   Running
-   Waiting
-   Approval
-   Success
-   Failure

Clicking a node opens execution details.

------------------------------------------------------------------------

## Phase 6 --- Variables

Dedicated explorer.

Shows

-   Workflow variables
-   Agent memory
-   Customer context
-   Shopify context
-   Outputs

------------------------------------------------------------------------

## Phase 7 --- Validation

Live graph analysis.

Detect

-   Missing trigger
-   Invalid connections
-   Missing variables
-   Dead branches
-   Infinite loops
-   Unsafe actions

------------------------------------------------------------------------

## Phase 8 --- AI Builder

User types:

"Create refund workflow."

AI generates workflow using backend capabilities.

------------------------------------------------------------------------

# Engineering Rules

1.  No feature owns another feature.
2.  Canvas never contains business logic.
3.  Backend capabilities remain the source of truth.
4.  Every capability has documentation and examples.
5.  Runtime must always be inspectable.
6.  Every refactor must leave the application working.

------------------------------------------------------------------------

# Immediate Sprint

1.  Audit current builder files.
2.  Map every file to the new architecture.
3.  Remove oversized components.
4.  Extract shared hooks.
5.  Introduce BuilderShell.
6.  Move business logic out of React Flow.
7.  Continue feature development from the new foundation.

This is the milestone where the Workflow Builder evolves into the
primary interface for Tajeran's agentic platform.
