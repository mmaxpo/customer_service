##################################################################
@@@@@@@@@@@@@@@@@@ cognitive adaptation intelligence: @@@@@@@@@@@@@@@@@@@@

Goal
 ↓
Retrieve relevant memory
 ↓
Generate multiple candidate plans
 ↓
Predict which plan is most promising
 ↓
Choose plan
 ↓
Execute
 ↓
Observe results
 ↓
Detect failure or poor outcome
 ↓
Repair or replan
 ↓
Evaluate outcome
 ↓
Extract learning
 ↓
Persist reusable lesson
 ↓
Use that learning to improve future planning,
capability selection, and repair

That last loop is what makes Tajeran genuinely learn from execution instead of merely being a very powerful durable orchestrator.



((((((((((((((((((((((((((((((((
you could build products for:
Sales operations
Order management
Logistics and warehousing
Procurement
Finance operations
HR workflows
IT operations
Compliance workflows
Claims processing
Booking and travel operations

^^^^^^^^^^^^^^^^^^^^^^^^^^^
### Your strongest possible positioning is:
- Tajeran is an autonomous business-operations platform that understands objectives,
- plans and executes durable workflows, verifies real outcomes, repairs incomplete work,
- and learns safely from proven business results.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

“We need to make the backend tell one coherent story.”

                    TAJERAN

User / Event / API / Customer Message
                    │
                    ▼
              COGNITIVE ENGINE
     "What is the actual objective?"
                    │
                    ▼
              DOMAIN INTERPRETER
     "What does this mean for this business?"
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
  Need clarification?      Enough information
          │                   │
          ▼                   ▼
      WAIT / ASK             PLANNER
                              │
                              ▼
                       BUSINESS PLAN / IR
                              │
                              ▼
                           COMPILER
                              │
                              ▼
                       EXECUTION GRAPH
                              │
                              ▼
                   SEMANTIC CAPABILITIES
                              │
                              ▼
                    PROVIDER RESOLUTION
                              │
                              ▼
                    DURABLE WORKFLOW
                              │
                              ▼
                         REAL WORLD
                              │
                              ▼
                         OUTCOME
                              │
                              ▼
                        VERIFICATION
                         │        │
                    resolved   incomplete
                         │        │
                         │      REPAIR
                         │        │
                         │    re-execute
                         │        │
                         └────┬───┘
                              ▼
                         RESOLUTION
                              │
                              ▼
                           LEARNING

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TAJERAN
│
├── 1. CORE ENGINE / PLATFORM
│      reusable autonomous machinery
│
├── 2. PRODUCTS / BUSINESS DOMAINS
│      customer service today
│      logistics / sales / procurement / ... later
│
└── 3. PROVIDERS / INTEGRATIONS
       Shopify today
       Wix / WooCommerce / ERP / CRM / ... later

**********************

Folder architecture should mirror the mindset

app/
│
├── core/
│   └── providers/
│       └── llm/
│
├── platform/
│   ├── events/
│   ├── jobs/
│   ├── webhooks/
│   └── infrastructure/
│
├── runtime/
│   ├── engine/
│   ├── nodes/
│   ├── services/
│   │   └── capabilities/
│   └── objective_lifecycle/
│
├── tcos/
│   ├── cognitive/
│   ├── planner/
│   ├── compiler/
│   ├── planning_ir/
│   ├── execution/
│   ├── verification/
│   ├── repair/
│   └── learning/
│
├── domains/
│   ├── customer_service/
│   │   ├── application/
│   │   ├── objectives/
│   │   ├── clarification/
│   │   ├── verification/
│   │   ├── repair/
│   │   ├── learning/
│   │   ├── inbox/
│   │   ├── routing/
│   │   └── ...
│   │
│   ├── logistics/
│   └── future_product/
│
└── integrations/
    ├── shopify/
    ├── wix/
    └── future_provider/

$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

┌─────────────────────────────────────────────┐
│ 1. AUTONOMOUS CORE                         │
│                                             │
│ TCOS                                        │
│   cognition                                 │
│   planner                                   │
│   Business IR                               │
│   compiler                                  │
│                                             │
│ Runtime                                     │
│   capability system                         │
│   durable execution                         │
│   waits / retries / replay                  │
│   objective lifecycle                       │
│                                             │
│ Agent Runtime                               │
│   LLM/tool execution                        │
└─────────────────────────────────────────────┘
                      ▲
                      │ contracts
                      ▼
┌─────────────────────────────────────────────┐
│ 2. PRODUCTS                                 │
│                                             │
│ Customer Service                            │
│   objective semantics                       │
│   clarification                             │
│   support policies                          │
│   commerce context                          │
│   review strategy                           │
│   verification semantics                    │
│   repair strategy                           │
│                                             │
│ Product features                            │
│   inbox                                     │
│   routing                                   │
│   SLA                                       │
│   suggested actions                         │
│   workflows                                 │
│   analytics                                 │
└─────────────────────────────────────────────┘
                      │
                semantic request
                      ▼
┌─────────────────────────────────────────────┐
│ 3. PROVIDERS                                │
│                                             │
│ Shopify                                     │
│ Wix                                         │
│ WooCommerce                                 │
│ ...                                         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 4. PLATFORM                                 │
│                                             │
│ events / jobs / schedules / webhooks        │
│ realtime / persistence / infra              │
└─────────────────────────────────────────────┘


===================================================================
app/
│
├── tcos/                         ← AUTONOMOUS CORE
│   ├── cognitive/
│   ├── planner/
│   │   ├── product_planning/
│   │   ├── business_ir/
│   │   ├── planning_ir/
│   │   └── runtime/
│   ├── compiler/
│   ├── verification/
│   ├── repair/
│   ├── learning/
│   └── execution/
│
├── runtime/                      ← AUTONOMOUS CORE
│   ├── engine/
│   ├── nodes/
│   ├── catalog/
│   └── services/
│       ├── capability_registry/
│       └── capability_execution/
│
├── agents_runtime/               ← AUTONOMOUS CORE
│
│
├── domains/                      ← PRODUCT DOMAINS
│   └── customer_service/
│       ├── services/
│       ├── workflows/
│       ├── models/
│       ├── repositories/
│       ├── schemas/
│       ├── routers/
│       ├── objectives/
│       ├── chat/
│       ├── inbox/
│       ├── omnichannel/
│       ├── routing/
│       ├── sla/
│       └── quality/
│
│
├── runtime/services/
│   ├── capability_registry/
│   │   └── providers/            ← PROVIDER REGISTRATION
│   └── capability_execution/
│       └── providers/            ← PROVIDER EXECUTION
│
├── domains/customer_service/
│   ├── integrations/shopify/     ← PROVIDER INTEGRATION
│   └── providers/shopify.py      ← PROVIDER INTEGRATION
│
│
├── platform/                     ← PLATFORM INFRASTRUCTURE
│   └── events/
│
├── jobs/                         ← PLATFORM INFRASTRUCTURE
├── schedules/                    ← PLATFORM INFRASTRUCTURE
├── webhooks/                     ← PLATFORM INFRASTRUCTURE
└── realtime/                     ← PLATFORM INFRASTRUCTURE
---------------------------------------------------------------
CORE
"Who understands this request?"
        ↓

PRODUCT
"This is Customer Service shipping status.
I need ecommerce.orders.get."
        ↓

CORE
"Validate and compile that."
        ↓

PROVIDER
"ecommerce.orders.get resolves to Shopify."
        ↓

PLATFORM
"Persist, enqueue, retry, publish, stream,
schedule and durably record execution."


models.py       What data exists?
registry.py     What implementations are registered?
repository.py   How is it stored?
service.py      What does this subsystem do?
policy.py       What rules decide behavior?
builder.py      How is something constructed?
resolver.py     How is something chosen?
executor.py     How is something executed?
verification.py How is correctness checked?

FOLDER       = one subsystem/responsibility
FILE         = one clear part of that subsystem
CLASS        = one stateful concept or contract
FUNCTION     = one action


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
### What I understand about TCOS now

                         TCOS
                          │
                    CognitiveRuntime
                          │
                          ▼
                       Planner
                          │
                ┌─────────┴──────────┐
                │                    │
          Product Planner       Generic Planner
                │                    │
                └─────────┬──────────┘
                          ▼
                     BusinessPlan
                          │
                          ▼
                   PlanningBuilder
                          │
                          ▼
                     Planning IR
                          │
                          ▼
                       Compiler
                          │
                          ▼
                     Execution IR
                          │
                          ▼
                ExecutionCoordinator
                          │
                          ▼
                   Durable Runtime
***************************************************************
                         CORE ENGINE
                  generic reusable intelligence
                              │
             ┌────────────────┴────────────────┐
             │                                 │
             ▼                                 ▼
         PRODUCT A                         PRODUCT B
     Customer Service                  Future Product
             │                                 │
             └──────────────┬──────────────────┘
                            │
                            ▼
                     semantic capability
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          Shopify          Wix        WooCommerce
         PROVIDER        PROVIDER       PROVIDER


CORE
  knows:
    capability
    objective
    planning
    execution
    verification
    repair
    learning

  does NOT know:
    customer service
    Shopify
    Wix
    refunds as a Shopify API detail
    tickets as a customer-service implementation detail


PRODUCT
  knows:
    its business language
    its workflows
    its objectives
    which semantic capabilities it needs

  example:
    customer_service
      "customer asks where order is"
      -> ecommerce.orders.get


PROVIDER
  knows:
    external API mechanics

  example:
    Shopify
      ecommerce.orders.get
      -> Shopify GraphQL / REST mechanics


                   app/node_registration.py
                     /        |        \
                    /         |         \
                   v          v          v
                CORE       PRODUCT    PROVIDERdocke


### At the architecture level, these major responsibilities already exist:

TAJERAN

1. Core intelligence / orchestration
   ├── TCOS planning
   ├── Business IR
   ├── Planning IR
   ├── Compiler
   ├── Verification
   ├── Repair
   ├── Learning
   ├── Cognitive runtime
   └── agents_runtime integration

2. Durable Runtime
   ├── DAG/workflow execution
   ├── nodes
   ├── pause/resume
   ├── waits
   ├── retries
   ├── replay
   ├── idempotency
   ├── jobs/events
   └── durable state

3. Capability system
   ├── semantic capability definitions
   ├── registry
   ├── provider bindings
   ├── resolver
   ├── capability.invoke
   ├── executor registry
   ├── failover
   ├── health
   ├── performance
   └── provider selection

4. Product layer
   └── Customer Service

5. Provider layer
   └── Shopify

6. Business outcome loop
   ├── outcome recording
   ├── evaluation
   ├── objective resolution
   ├── repair/reverification
   └── learning




PHASE E — DEVELOPMENT FLOW TRACING
          lightweight wrappers/tracer

REAL CUSTOMER SERVICE BEHAVIORS

## ###############################################################

A. Customer communication and inbox
1. Omnichannel inbox — Core
Support email
Storefront live chat
Shopify chat widget
Contact forms
Instagram comments and DMs
Facebook comments and Messenger
WhatsApp
SMS
Voice and phone
Unified conversation history
Cross-channel conversation continuity
Channel-independent customer identity
Attachments and images
Internal notes
Agent mentions
Conversation followers
Collision detection
Saved views and filters
Bulk conversation actions
Spam detection
Merge duplicate conversations
Split unrelated conversations
Scheduled follow-ups
Snooze until time or event
Delivery and read status where available
2. Ticket management — Core
Automatic ticket creation
Open, pending, snoozed, resolved and closed states
Ticket priority
Tags
Custom fields
Ticket categories
Intent classification
Parent and child tickets
Related-ticket linking
Duplicate-ticket detection
Merge and reopen tickets
Assignment history
Complete activity timeline
Ticket and message search
Bulk assignment, tagging and resolution
B. Shopify customer context and operations
3. Complete Shopify context — Core
Customer profile
Contact details
Customer tags and notes
Customer lifetime value
Order count
Current and previous orders
Order items and variants
Payment status
Fulfilment status
Tracking information
Shipping and billing addresses
Discounts
Refund history
Return history
Subscription information
Inventory availability
Product catalogue
Customer risk indicators
Previous support conversations
4. Order tracking — Core
Find an order by email, phone or order number
Explain order status
Show live fulfilment status
Provide tracking links
Read carrier events
Detect delayed shipments
Detect stalled tracking
Detect failed delivery
Identify potentially lost packages
Estimate the next expected event
Automatically answer WISMO questions
5. Order management — Core
Cancel eligible orders
Change shipping address
Change customer contact information
Change product or variant
Add or remove eligible items
Change quantities
Add order notes and tags
Apply authorized discounts
Duplicate orders
Create draft orders
Create replacement orders
Send invoices or payment links
Check fulfilment state before modifications
6. Refunds and compensation — Core
Full refund
Partial refund
Shipping refund
Item-level refund
Restock or do not restock
Store credit
Gift-card compensation
Discount-code compensation
Refund-reason recording
Refund status tracking
Financial approval limits
Duplicate-refund prevention
7. Returns and exchanges — Core
Check return eligibility
Validate return window
Apply product-specific policies
Collect return reasons
Collect photographs and evidence
Create return requests
Approve or reject returns
Generate return labels
Provide shipping instructions
Track returned products
Exchange products and variants
Exchange sizes and colours
Handle partial returns
Refund after inspection
Issue store credit
Send return-progress notifications
8. Replacement and reshipment — Core
Handle missing packages
Handle damaged products
Handle incorrect products
Collect supporting evidence
Validate replacement policy
Check replacement inventory
Create replacement orders
Coordinate replacement fulfilment
Select shipping method
Produce new tracking information
Prevent duplicate reshipments
C. Human support operations
9. Teams and routing — Core
Teams and departments
Specialized queues
Manual assignment
Round-robin assignment
Load-balanced assignment
Skills-based routing
Intent-based routing
Language-based routing
Channel-based routing
Store and brand routing
Product-based routing
VIP-customer routing
Subscriber routing
Sentiment-based prioritization
Financial-risk routing
Time-sensitive request detection
Overflow queues
Agent availability and capacity
Escalation between teams
10. SLA management — Core
First-response SLA
Next-response SLA
Resolution SLA
SLAs by channel
SLAs by customer tier
SLAs by intent and priority
Business hours
Holiday calendars
SLA pause conditions
Warning thresholds
Breach detection
Automatic escalation
Team and agent SLA reporting
Durable SLA violation records
11. Agent productivity — Core
Suggested replies
Reply generation
Rewrite, shorten and expand
Tone adjustment
Translation
Conversation summarization
Customer-intent detection
Sentiment detection
Recommended actions
One-click Shopify actions
Reusable macros
Dynamic customer variables
Action-capable macros
Internal AI assistant
Knowledge search inside tickets
Previous-ticket search
Automatic internal notes
Automatic classification and tagging
Keyboard shortcuts
Complete handoff summaries
12. Human handoff — Core
Confidence-based escalation
Policy-based escalation
Customer-requested escalation
Transfer with complete context
AI-generated case summary
Actions already attempted
Evidence already collected
Remaining objective
Recommended next step
Correct destination team
Priority preservation
Return to automation after human input
D. Customer self-service
13. Self-service portal — Core
Branded help centre
Searchable FAQs
AI question answering
Order lookup
Order tracking
Cancellation requests
Address-change requests
Return requests
Exchange requests
Return-label access
Subscription management
Evidence uploads
Case-status tracking
Refund-status tracking
Replacement tracking
Human escalation
Multilingual support
14. Customer resolution centre — Tajeran advantage
Show the customer’s stated objective
Display identity-verification status
Show required information
Show completed actions
Show pending approvals
Show external-provider status
Display the next expected step
Display expected completion time
Request additional evidence
Allow customer corrections
Let customers confirm successful resolution
Reopen an incomplete objective
Maintain one timeline across every channel
E. Knowledge and intelligence
15. Knowledge management — Core
Import websites and help centres
Import Shopify policies
Import documents and PDFs
Product-catalogue knowledge
Internal SOPs
Structured FAQs
Previous resolved tickets
Knowledge synchronization
Hybrid keyword and semantic search
Source citations
Brand-specific knowledge
Product-specific knowledge
Language-specific knowledge
Source permissions
Knowledge versioning
Outdated-content detection
Conflicting-policy detection
Knowledge-gap detection
Suggested knowledge articles
Human approval before publishing
Pre-deployment answer testing
16. AI customer-service agent — Core
Understand natural-language requests
Answer product and policy questions
Use live Shopify information
Personalize replies
Follow merchant tone
Follow merchant policies
Ask clarification questions
Execute approved actions
Operate continuously
Support multiple languages
Detect low confidence
Escalate safely
Preserve context during handoff
17. Multiple specialized agents — Tajeran advantage
Customer-support agent
Order-management agent
Shipping-exception agent
Returns and exchanges agent
Refund agent
Subscription agent
Shopping assistant
Quality-review agent
Knowledge agent
Operational analyst
Planning agent
Verification agent
Repair agent
Learning agent
Each agent receives only the capabilities, knowledge and authority required for its responsibility.
F. Customer-objective intelligence
18. Objective understanding — Tajeran advantage
Identify what the customer wants achieved
Separate multiple objectives in one message
Detect missing information
Identify business constraints
Determine completion criteria
Connect the objective to tickets and conversations
Preserve the original request
Track objective status independently from ticket status
Re-evaluate the objective after every action
Distinguish conversation closure from actual resolution
Example:
“Where is my order?” is a question.
“Make sure I receive my missing order” is the real objective.
19. Objective lifecycle — Tajeran advantage
Objective discovered
Information required
Identity verification required
Plan prepared
Approval required
Execution started
Waiting for provider
Waiting for customer
Partially achieved
Repairing
Achieved
Failed
Unknown and requiring investigation
Reopened after new evidence
G. Agentic planning and workflow automation
20. AI planning — Tajeran advantage
Convert an objective into an executable plan
Select semantic capabilities
Determine action dependencies
Add verification steps
Add approval steps
Add wait conditions
Run independent steps in parallel
Estimate plan risk
Explain the plan
Allow human modification
Replan when external state changes
Save successful plans as templates
21. Visual and natural-language workflow builder — Tajeran advantage
Generate workflows from natural language
Visual DAG editor
Triggers
Conditions and branches
Capability actions
Parallel execution
Wait nodes
Approval nodes
Human tasks
Subworkflows
Error branches
Retry rules
Compensation steps
Dry-run mode
Historical simulation
Testing environment
Versioning
Publish and rollback
Reusable templates
Live execution visualization
22. Durable workflow runtime — Major Tajeran advantage
Persistent workflow runs
Long-running execution
Pause and resume
Wait until a specific time
Wait for an external event
Human-approval pauses
Durable workflow state
Atomic resume claims
Worker leases
Safe cancellation
Automatic retries
Dead-letter handling
Subworkflows
Workflow snapshots
Workflow comparison
Replay protection
Real-time timeline and SSE updates
Recovery after application restart
H. Safe autonomous actions
23. Customer verification — Core plus Tajeran advantage
Email OTP
SMS OTP
Channel-independent verification
Order-detail verification
Risk-based verification
Verification expiration
Verified identity artifact
Reuse verification across authorized channels
Require stronger verification for risky actions
Complete verification audit history
24. Policy and authority controls — Tajeran advantage
Merchant-defined action permissions
Role-based execution authority
Financial thresholds
Product restrictions
Geographic restrictions
Customer-segment rules
Required evidence
Approval requirements
Multi-stage approvals
Approval expiration
Delegated approval
Approve, reject or modify
Resume automatically after approval
Record who approved and why
25. Side-effect safety — Major Tajeran advantage
Idempotency keys
Duplicate-action prevention
Replay guards
Advisory locking
Precondition checks
Before-action policy validation
Before-action authorization
Before-action identity verification
Post-action provider verification
Durable provider receipts
External transaction IDs
Safe retry classification
Compensation actions
Complete action audit trail
This prevents dangerous outcomes such as duplicate refunds, cancellations or replacements.
I. Cross-provider orchestration
26. Semantic capability system — Major Tajeran advantage
Business workflows use stable capabilities rather than hardcoded vendors:
ecommerce.orders.get
ecommerce.orders.cancel
ecommerce.orders.update_address
commerce.refunds.issue
commerce.returns.create
fulfilment.shipment.stop
fulfilment.replacement.create
subscriptions.pause
subscriptions.cancel
customer.credit.issue
notifications.send
27. Provider management — Tajeran advantage
Multiple providers for one capability
Provider registration
Merchant-specific bindings
Provider eligibility
Provider priority
Automatic provider selection
Provider health monitoring
Performance observations
Reliability summaries
Latency tracking
Failure-rate tracking
Read-only fallback
Safe provider failover
Capability coverage validation
Custom merchant providers
28. Multi-system customer resolutions — Major Tajeran advantage
One objective can coordinate:
Shopify
Warehouse or 3PL
Shipping carrier
Returns platform
Subscription platform
Payment provider
Loyalty platform
Communication provider
Custom merchant system
Example:
Verify customer
→ Read Shopify order
→ Stop warehouse fulfilment
→ Update shipping address
→ Verify warehouse accepted the change
→ Notify customer
→ Confirm final objective
J. Failure recovery and repair
29. Failure classification — Tajeran advantage
Timeout
Rate limit
Provider unavailable
Circuit open
Authentication failure
Authorization failure
Policy rejection
Invalid external state
Missing customer information
Permanent provider error
Unknown integration error
Partial execution
Conflicting external state
30. Automatic repair agent — Major Tajeran advantage
Identify the failed workflow step
Inspect completed side effects
Avoid repeating successful actions
Determine whether retry is safe
Retry temporary failures
Select another provider
Generate a revised plan
Request missing customer information
Request human approval
Execute compensation actions
Reverify the business objective
Preserve original and repaired plans
Explain the failure and repair
Escalate only when safe repair is impossible
Example:
The refund succeeded but customer notification failed. Tajeran retries the notification without issuing another refund.
K. Outcomes, evaluation and proof
31. Durable business-outcome records — Major Tajeran advantage
For every objective, record:
Original customer objective
Conversation and ticket
Workflow run
Applied policy and revision
Actions attempted
Actions achieved
Actions failed
Pending operations
Unknown external states
Shopify and provider confirmations
Financial amounts
Supporting evidence
Approval history
Outcome status
Confidence
Reason code
Final summary
Customer confirmation
32. Objective evaluation — Major Tajeran advantage
Compare execution with success criteria
Count achieved operations
Count failed operations
Count pending operations
Detect unknown operations
Determine whether the objective succeeded
Detect partial resolution
Detect falsely closed tickets
Determine whether retry is appropriate
Evaluate repeat contact
Re-evaluate when evidence changes
Version evaluation logic
Preserve evaluation history
33. Verified resolution analytics — Major Tajeran advantage
Verified objective-achievement rate
Partial-outcome rate
Failed-outcome rate
Unknown-outcome rate
Repair success rate
Provider-confirmed action rate
Duplicate side effects prevented
Repeat contact after resolution
Customer-confirmed resolution
Cost per verified outcome
L. Merchant policies and simulation
34. Natural-language policy engine — Tajeran advantage
Merchants can describe rules such as:
Replace damaged items below $100 after receiving a photograph. Higher-value replacements require manager approval.
Tajeran converts this into:
Structured eligibility rules
Required evidence
Financial limits
Approval boundaries
Escalation conditions
Effective dates
Store-specific rules
Product-specific rules
Customer-tier rules
Immutable policy revisions
Complete policy lineage
35. Policy simulation — Major Tajeran advantage
Test policies against historical cases
Compare policy revisions
Estimate automation rate
Estimate refund and replacement cost
Show decisions that would change
Identify cases requiring approval
Find risky edge cases
Preview customer communications
Predict operational impact
Publish after review
Roll back safely
M. Learning and continuous improvement
36. Governed objective learning — Major Tajeran advantage
Learn from:
Successful outcomes
Failed outcomes
Partial outcomes
Effective repairs
Repeat contacts
Provider performance
Human corrections
Escalation causes
Customer satisfaction
Policy results
Generate:
Workflow-improvement candidates
Policy-improvement candidates
Knowledge updates
New automation opportunities
Better provider recommendations
Better escalation conditions
Governance requirements:
Preserve source evidence
Preserve outcome lineage
Human review
Approve or reject candidates
Version accepted improvements
Never silently weaken policies
Never give learned suggestions automatic execution authority
N. Proactive customer operations
37. Proactive support — Tajeran advantage
Detect and respond to:
Shipment delays
Stalled tracking
Failed delivery
Lost package
Oversold product
Fulfilment delay
Back order
Refund delay
Unprocessed return
Subscription-payment failure
Inventory problem
Product defect
Carrier disruption
Tajeran can:
Identify affected customers
Create objectives automatically
Select policy-approved resolutions
Request approval where necessary
Contact customers proactively
Execute corrective actions
Measure prevented tickets
38. Operational root-cause intelligence — Tajeran advantage
Cluster related customer problems
Detect unusual ticket spikes
Find problematic products
Find misleading product information
Compare warehouse performance
Compare carrier performance
Detect policies causing escalation
Detect failing automations
Identify common refund causes
Calculate operational impact
Provide supporting conversation evidence
Recommend corrective action
Convert approved recommendations into workflows
O. Analytics and quality management
39. Standard support analytics — Core
Ticket volume
Volume by intent
Volume by channel
Volume by product
Volume by brand and store
First-response time
Resolution time
SLA performance
Backlog
Agent productivity
Team performance
CSAT
Repeat-contact rate
40. AI analytics — Core plus Tajeran advantage
AI participation rate
AI answer rate
Handoff rate
Handoff reasons
Clarification rate
Approval rate
Hallucination rate
Policy-compliance rate
Incorrect-action rate
Cost per AI interaction
Cost per verified outcome
Agent and model comparisons
41. AI quality assurance — Core plus Tajeran advantage
Review all AI conversations
Review human conversations
Grounding evaluation
Citation verification
Policy-compliance review
Tone evaluation
Action-correctness evaluation
Sensitive-data detection
Hallucination detection
Weighted quality rules
Evidence for every score
Human correction
AI-versus-human comparison
Deployment regression testing
P. Sales and conversational commerce
42. Shopping assistant — Core
Product questions
Product comparison
Live inventory lookup
Variant recommendations
Personalized recommendations
Cross-selling
Upselling
Cart-aware assistance
Checkout assistance
Back-in-stock alternatives
Discount generation
Sales-to-support handoff
Support-to-sales handoff
Revenue attribution
43. Economically intelligent resolution — Tajeran advantage
Evaluate permitted resolutions using:
Product value
Replacement cost
Return-shipping cost
Inventory
Customer lifetime value
Churn probability
Fraud risk
Handling cost
Merchant policy
Recommend or execute:
Refund without return
Replacement without return
Exchange
Store credit
Partial refund
Discount
Standard return
Human escalation
Every decision should include its evidence, policy justification and estimated cost.
Q. Multi-brand, enterprise and security
44. Multi-store and multi-brand — Core
Multiple Shopify stores
Brand-specific inboxes
Brand-specific agents
Separate knowledge
Separate policies
Separate teams
Shared support teams
Store-aware workflows
Store-aware permissions
Consolidated parent-company reporting
Multiple languages
Multiple currencies
Multiple time zones
45. Security and tenant isolation — Core
Strict tenant and user scoping
Store-level isolation
Role-based permissions
Least-privilege access
Sensitive-action permissions
Shopify OAuth HMAC verification
Webhook signature verification
Token encryption
Secrets rotation
Complete audit logs
Two-factor authentication
Enterprise SSO/SAML
Data-retention controls
Customer-data export and deletion
Encryption in transit and at rest
Suspicious-action detection
R. Integration and platform infrastructure
46. Integration platform — Core plus Tajeran advantage
OAuth installation
Provider credential management
Signed webhooks
Event normalization
Event subscriptions
Webhook retries
Dead-letter handling
Custom API actions
Custom webhooks
Integration health dashboard
Rate-limit handling
Sandbox integrations
Public API
Developer SDK
MCP-compatible knowledge and capabilities
Integration marketplace
47. Durable jobs, events and schedules — Tajeran advantage
Background job queues
Worker leases
Retry policies
Dead-letter queues
Manual replay
Scheduled jobs
Recurring workflows
Event-driven execution
Delayed actions
Wait-until-time conditions
Wait-for-event conditions
Idempotent event processing
Job and event observability
S. Deployment and adoption
48. Incremental AI deployment — Tajeran advantage
Historical evaluation
Offline testing
Dry-run mode
Shadow mode
Suggested-reply mode
Human-approval mode
Limited-autonomy mode
Intent-by-intent rollout
Customer-segment rollout
Full-autonomy mode
Instant rollback
Compare performance between versions
49. Migration — Core
Import Gorgias data
Import Intercom data
Import Zendesk data
Import customers
Import conversations and tickets
Import macros
Import tags
Import routing rules
Import help-centre content
Preserve historical context
50. Overlay mode — Major Tajeran advantage
Tajeran can work beside an existing helpdesk:
Read Gorgias, Intercom or Zendesk tickets
Add suggested replies
Execute Tajeran workflows
Write results back
Preserve the existing agent inbox
Provide Tajeran outcome records
Provide repair and reliability analytics
Gradually move workloads to Tajeran
Allow full migration later
Final product definition
Tajeran is the combination of:
Shopify-native omnichannel helpdesk
AI support and shopping agents
Durable agentic workflow runtime
Cross-provider capability orchestration
Policy and human-approval system
Automatic failure repair
Verified business outcomes
Governed learning and operational intelligence
The main competitive promise is:
Tajeran does not count an AI reply or closed ticket as success. It understands the customer’s objective, safely completes the necessary actions across Shopify and connected systems, repairs failures, and proves whether the business outcome was achieved.
### ########################################################

Claude.md should contain stable decisions, architecture rules, and progress summaries.
Think of it like the source of truth that makes every prompt shorter and shorter. 
Save decisions, not conversations. 
Every architectural call that you store there is a paragraph 
that you never have to type again.

include: your tech stack,coding conversations discion , 
build command's, 95% confidence rule < 200 lines

Claude 3.5 Sonnet: Recommended as the default model for the majority of coding tasks.
Claude 3 Haiku: Best used for sub-agents, formatting, and simpler, one-off tasks to save on token costs.
Claude 3 Opus: Reserved specifically for deep architectural planning and complex challenges where Sonnet 
may not be sufficient. It is advised to keep Opus usage under 20% of your total work.

Claude.md file acts as a system constitution for your projects. 
    To keep it effective as a "source of truth" and minimize token waste, 
    it recommends storing the following:
Stable decisions: Core architectural choices that shouldn't change.
Architecture rules: Established project guidelines and coding standards.
Progress summaries: Key updates so the AI doesn't have to re-parse entire histories.
The overall strategy is to save decisions, not conversations. By maintaining a lean, 
well-organized Claude.md (kept under 200 lines), you prevent the AI from needing to re-read long, 
redundant chat logs in every session.

add context rules directly into it,: "use subagents for any exploration or research,if a task need 3+

 or multi-file  analysis spawn a subagent and return only summarized insights  "


((((((((((((((((((((((((((((((((((((((((()))))))))))))))))))))))))))))))))))))))))
# TAJERAN V1 — DETAILED FEATURE SPECIFICATIONS

---

# 1. FEATURE

## Account & Workspace

### What problem?

A merchant needs a secure identity and workspace where their business, team members, Shopify connection, customer conversations, configuration, and data are isolated from other merchants.

### Who uses it?

- Merchant
- Workspace administrator
- Support agent

### Desired outcome

A merchant can create an account, create or access a workspace, configure basic business information, and securely manage team access.

---

# USER FLOW

### Step 1

User opens Tajeran.

### Step 2

User signs up or logs in.

### Step 3

New user verifies their email.

### Step 4

User creates a workspace.

### Step 5

User enters:

- Business name
- Timezone
- Business hours

### Step 6

Workspace administrator invites team members.

### Step 7

Invited member accepts the invitation and creates/accesses their account.

### Step 8

Administrator manages basic roles and permissions.

### Step 9

Users can log out and later securely return to the workspace.

---

# DOMAIN

## Entities

- User
- Account
- Workspace
- Workspace Membership
- Invitation
- Role
- Permission
- Business Profile
- Business Hours
- Session
- Email Verification Token
- Password Reset Token

## States

### Invitation

```text
PENDING
   ↓
ACCEPTED
```

Possible:

```text
EXPIRED
REVOKED
```

### Session

```text
ACTIVE
   ↓
REVOKED / EXPIRED
```

## Rules

- A user can belong to one or more workspaces if supported by the model.
- Every workspace-owned resource must be tenant-scoped.
- Workspace members must only access resources they are authorized to access.
- Admin and agent permissions must be distinguishable.
- Passwords must never be stored in plaintext.
- Sessions must be securely managed.
- Email verification must be validated.
- Password-reset tokens must expire.
- Removing a member must invalidate their workspace access.

---

# SYSTEM

## Frontend

- Sign-up page
- Login page
- Email verification
- Password reset
- Workspace creation
- Workspace settings
- Business profile
- Business hours
- Team management
- Invite member
- Role management

## API

- Register
- Login
- Logout
- Verify email
- Request password reset
- Reset password
- Session management
- Create workspace
- Get workspace
- Update workspace
- Invite member
- Accept invitation
- Remove member
- Update role

## Domain

- Authentication
- Identity
- Workspace lifecycle
- Membership
- Authorization
- Business configuration

## Database

- Users
- Workspaces
- Memberships
- Invitations
- Sessions
- Verification tokens
- Reset tokens
- Business settings

## Runtime

Not required for basic account/workspace management.

---

# FAILURES

- Invalid credentials
- Duplicate email
- Expired verification
- Invalid reset token
- Expired invitation
- Unauthorized workspace access
- Session expired
- Member removed while logged in
- Database failure
- Email delivery failure

---

# DONE

- User can sign up.
- User can log in.
- User can log out.
- Email verification works.
- Password reset works.
- Sessions are secure.
- User can create a workspace.
- Workspace settings can be changed.
- Business name is stored.
- Timezone is stored.
- Business hours are stored.
- Admin can invite members.
- Admin can remove members.
- Admin and agent roles work.
- Authorization prevents cross-workspace access.
- Automated tests cover success and failure paths.

---

# DEPLOY

Production verification:

1. Create a real account.
2. Verify email.
3. Create workspace.
4. Configure business information.
5. Invite another user.
6. Accept invitation.
7. Verify agent permissions.
8. Verify admin permissions.
9. Log out.
10. Log back in.
11. Verify unauthorized workspace access is blocked.
12. Verify sessions and authentication events are logged safely.

### Production success condition

> A real merchant can securely create and operate a workspace with authorized team members without cross-tenant access.

---

# 2. FEATURE

## Shopify Store Connection

### What problem?

A Shopify merchant needs to securely connect their store so Tajeran can access the commerce context and capabilities required for customer service.

### Who uses it?

- Shopify merchant
- Workspace administrator

### Desired outcome

A verified Shopify store is securely connected to the correct workspace and is available to Tajeran's Shopify capabilities.

---

# USER FLOW

### Step 1

Merchant opens:

**Settings → Integrations → Shopify**

### Step 2

Merchant selects:

**Connect Shopify**

### Step 3

Tajeran starts Shopify OAuth.

### Step 4

Merchant authorizes requested permissions.

### Step 5

Shopify redirects to Tajeran.

### Step 6

Tajeran validates OAuth state and installation.

### Step 7

Tajeran securely stores credentials.

### Step 8

Tajeran verifies the connection.

### Step 9

Merchant sees:

**Shopify connected**

with store information and connection health.

---

# DOMAIN

## Entities

- Shopify Store
- Shopify Installation
- Shopify Connection
- Shopify Credential
- Integration
- Webhook

## States

```text
DISCONNECTED
    ↓
CONNECTING
    ↓
CONNECTED
```

Possible:

```text
FAILED
REVOKED
EXPIRED
```

## Rules

- Connection belongs to exactly one workspace.
- Credentials are never exposed to frontend.
- OAuth state must be validated.
- Store identity must be verified.
- Required permissions must be checked.
- Connection health must be testable.
- Disconnect invalidates access.
- Shopify webhooks must be verified and tenant-scoped.

---

# SYSTEM

## Frontend

- Integration page
- Connect button
- Connection status
- Store information
- Health status
- Disconnect
- Reconnect
- Error states

## API

- OAuth start
- OAuth callback
- Connection status
- Health check
- Disconnect
- Reconnect

## Domain

- Installation management
- Connection lifecycle
- Permission validation

## Database

- Installation
- Connection
- Encrypted credential
- Webhook registration
- Connection status
- Timestamps
- Workspace ownership

## External services

- Shopify OAuth
- Shopify Admin API
- Shopify Webhooks

---

# FAILURES

- Authorization cancelled
- Invalid OAuth state
- Invalid store
- Duplicate connection
- Missing permission
- Token storage failure
- Encryption failure
- Shopify API unavailable
- Verification failure
- Webhook registration failure
- Token revoked

---

# DONE

- OAuth works.
- State is validated.
- Store identity is verified.
- Credential is encrypted.
- Frontend never receives raw credential.
- Correct workspace owns installation.
- Connection status is persisted.
- Health can be checked.
- Disconnect works.
- Reconnect works.
- Tenant isolation is enforced.
- Tests cover success/failure.

---

# DEPLOY

1. Connect a real Shopify development/test store.
2. Verify OAuth.
3. Verify credential storage.
4. Verify connection health.
5. Perform safe Shopify read.
6. Verify workspace isolation.
7. Verify webhook verification.
8. Disconnect.
9. Verify access is revoked.
10. Check logs for credential leakage.

### Production success condition

> A real Shopify merchant can securely connect their store and Tajeran can perform an authenticated tenant-scoped Shopify operation.

---

# 3. FEATURE

## Shopify Commerce Context

### What problem?

Customer-service AI cannot provide useful answers if it cannot retrieve the merchant's actual commerce data.

### Who uses it?

- AI agent
- Human support agent
- Customer-service workflows

### Desired outcome

Tajeran can retrieve accurate, current Shopify context for the customer, order, product, fulfillment, tracking, return, and refund relevant to a conversation.

---

# USER FLOW

### Step 1

A conversation requires commerce information.

### Step 2

Tajeran identifies the required entity.

### Step 3

Tajeran resolves the Shopify store/workspace.

### Step 4

Tajeran retrieves the relevant Shopify data.

### Step 5

Tajeran normalizes the result into Tajeran's domain representation.

### Step 6

The AI or support agent receives the relevant context.

### Step 7

The retrieval is recorded where appropriate for observability/audit.

---

# DOMAIN

## Entities

- Customer
- Order
- Product
- Variant
- Fulfillment
- Shipment
- Tracking
- Return
- Refund

## Rules

- Every request must be tenant-scoped.
- Shopify credentials must remain inside the provider/capability boundary.
- AI should receive only relevant context.
- Missing data must be represented explicitly.
- Stale data must not be presented as current without indication.
- Shopify identifiers must remain traceable.
- External failures must not corrupt internal state.

---

# SYSTEM

## Frontend

- Customer context
- Order context
- Product information
- Fulfillment/tracking information
- Returns/refunds

## API / Domain

- Customer retrieval
- Order retrieval
- Product retrieval
- Fulfillment retrieval
- Tracking retrieval
- Return retrieval
- Refund retrieval

## Capability layer

Example:

```text
get_customer
get_order
get_product
get_fulfillment
get_tracking
get_return
get_refund
```

## Database

Store only the internal data required for product operation, caching, relationships, and audit.

## External

- Shopify Admin API

---

# FAILURES

- Customer not found
- Order not found
- Product not found
- Fulfillment unavailable
- Tracking unavailable
- Shopify API unavailable
- Rate limit
- Permission error
- Stale data
- Tenant mismatch

---

# DONE

- Customer retrieval works.
- Order retrieval works.
- Product retrieval works.
- Variant information works.
- Fulfillment information works.
- Tracking information works.
- Return information works where available.
- Refund information works where available.
- Tenant isolation is enforced.
- Errors are represented safely.
- AI can consume normalized context.
- Tests cover provider failures and isolation.

---

# DEPLOY

Verify with a real Shopify store:

1. Retrieve customer.
2. Retrieve order.
3. Retrieve product.
4. Retrieve fulfillment.
5. Retrieve tracking.
6. Retrieve refund.
7. Test missing entities.
8. Test API failure.
9. Test tenant isolation.

### Production success condition

> Tajeran can reliably retrieve the commerce context required to answer a real customer-service request.

---

# 4. FEATURE

## Shopify Events

### What problem?

Tajeran needs to react to important Shopify changes without waiting for a customer or human to manually initiate the process.

### Who uses it?

- Tajeran automation
- AI agent
- Workflow system
- Merchant

### Desired outcome

Important Shopify events enter Tajeran securely, are associated with the correct workspace, and can trigger supported automation.

---

# USER FLOW

### Step 1

Shopify generates an event.

### Step 2

Shopify sends the webhook to Tajeran.

### Step 3

Tajeran verifies the webhook.

### Step 4

Tajeran identifies the store/workspace.

### Step 5

Tajeran normalizes the event.

### Step 6

Tajeran persists/processes the event.

### Step 7

Automation may react to it.

---

# DOMAIN

## Events

- New order
- Order updated
- Fulfillment updated
- Refund
- Customer updated

## Rules

- Webhook authenticity must be verified.
- Events must be tenant-scoped.
- Duplicate events must be handled safely.
- Processing must be idempotent.
- Invalid events must not trigger actions.
- Failed processing must be observable.

---

# SYSTEM

## API

- Shopify webhook endpoints

## Domain

- Event verification
- Event normalization
- Event routing
- Idempotency

## Runtime

Events may trigger workflows.

## Database

- Event record
- Event ID
- Event type
- Workspace
- Processing status
- Timestamp
- Failure information

---

# FAILURES

- Invalid webhook signature
- Unknown store
- Duplicate event
- Malformed payload
- Processing failure
- Database failure
- Downstream workflow failure

---

# DONE

- All required V1 events are received.
- Verification works.
- Tenant is resolved correctly.
- Duplicate delivery is safe.
- Events are persisted/processed.
- Failures are observable.
- Events can trigger supported automation.

---

# DEPLOY

Send real Shopify events from a test store and verify:

- Delivery
- Verification
- Tenant resolution
- Persistence
- Idempotency
- Workflow triggering
- Failure handling

### Production success condition

> A real Shopify event can safely enter Tajeran and trigger the correct tenant-scoped behavior exactly once from Tajeran's business perspective.

---

# 5. FEATURE

## Shopify Actions

### What problem?

Customer service often requires doing something, not simply reading information.

### Who uses it?

- AI agent
- Human agent
- Workflow
- Approved automation

### Desired outcome

Tajeran can execute a small, controlled set of Shopify operations safely and verify their result.

---

# USER FLOW

### Step 1

AI or human determines an action is required.

### Step 2

Tajeran validates the action and permissions.

### Step 3

If required, human approval is requested.

### Step 4

The action executes through the Shopify capability/provider.

### Step 5

Result is returned.

### Step 6

Tajeran verifies the result where possible.

### Step 7

Outcome is recorded.

---

# DOMAIN

## Actions

- Get customer
- Get order
- Get product
- Get fulfillment/tracking
- Add order note
- Cancel order
- Refund order

## Action categories

```text
READ
WRITE
DESTRUCTIVE
```

## Rules

- Actions must be tenant-scoped.
- AI cannot bypass authorization.
- Destructive actions may require approval.
- Actions must be auditable.
- Idempotency must be considered.
- Results must be verified where possible.
- Failed actions must not be represented as successful.

---

# SYSTEM

## Capability layer

Each action should have:

- Capability name
- Input schema
- Authorization requirements
- Risk level
- Execution
- Result schema
- Verification
- Audit information

## Runtime

Actions can be invoked by:

- AI
- Workflow
- Human-triggered operation

## External

- Shopify Admin API

---

# FAILURES

- Invalid input
- Unauthorized action
- Shopify permission error
- Shopify API failure
- Duplicate action
- Timeout
- Partial result
- Verification failure
- Resource no longer exists

---

# DONE

- Read operations work.
- Add order note works.
- Cancel order works under defined authorization.
- Refund order works under defined authorization.
- Risk levels exist.
- Approval integration works.
- Actions are audited.
- Results are verified.
- Failed actions are not falsely reported as successful.
- Tests cover safe and failure paths.

---

# DEPLOY

Run controlled production tests:

1. Read customer.
2. Read order.
3. Add safe order note.
4. Test approval-required cancellation.
5. Test approval-required refund.
6. Verify actual Shopify result.
7. Verify audit record.
8. Verify failure handling.

### Production success condition

> Tajeran can safely execute and verify authorized Shopify actions without bypassing tenant, permission, or approval controls.

---

# 6. FEATURE

## Inbox

### What problem?

Support agents need one place to see, search, filter, prioritize, assign, and resolve customer conversations.

### Who uses it?

- Support agent
- Workspace administrator
- AI agent

### Desired outcome

The inbox becomes the operational center of Tajeran customer service.

---

# USER FLOW

### Step 1

Agent opens Inbox.

### Step 2

Agent sees conversation list.

### Step 3

Agent selects a conversation.

### Step 4

Agent can search/filter conversations.

### Step 5

Agent assigns or reassigns the conversation.

### Step 6

Agent changes:

- Status
- Priority
- Tags
- Assignee
- Team

### Step 7

Agent can snooze, close, reopen, or escalate.

---

# DOMAIN

## Entities

- Conversation
- Conversation Assignment
- Team
- User
- Tag
- Conversation Status
- Priority
- Channel

## States

```text
OPEN
PENDING
RESOLVED
```

Additional operational states may include:

```text
UNASSIGNED
ESCALATED
```

## Rules

- Conversation belongs to exactly one workspace.
- Assignment must reference valid workspace members.
- Agents only access authorized conversations.
- Closing a conversation must preserve history.
- Reopening must preserve previous history.
- AI/human handling state must be distinguishable.

---

# SYSTEM

## Frontend

- Inbox list
- Conversation panel
- Search
- Filters
- Assignment
- Status controls
- Priority
- Tags
- Snooze
- Close/reopen
- Escalation

## API

- List conversations
- Search
- Filter
- Assign
- Reassign
- Update status
- Update priority
- Add/remove tag
- Snooze
- Close
- Reopen
- Escalate

## Database

- Conversations
- Assignments
- Messages
- Tags
- Teams
- Status history

---

# FAILURES

- Conversation not found
- Unauthorized access
- Invalid assignee
- Concurrent update
- Search failure
- Database failure
- Message synchronization failure

---

# DONE

- Inbox displays conversations.
- All required filters work.
- Search works.
- Assignment works.
- Status changes work.
- Priority works.
- Tags work.
- Snooze works.
- Close/reopen works.
- Escalation works.
- AI/human states are visible.
- Tenant isolation works.
- Tests cover core operations.

---

# DEPLOY

Create real conversations and verify:

- List
- Search
- Filter
- Assignment
- Status
- Priority
- Tags
- Close/reopen
- Multi-user access
- Tenant isolation

### Production success condition

> A support agent can operate their daily customer-service workload entirely from the Tajeran inbox.

---

# 7. FEATURE

## Customer Conversation

### What problem?

Agents need to understand the complete conversation and communicate with customers without leaving Tajeran.

### Who uses it?

- Customer
- AI agent
- Human agent

### Desired outcome

Every conversation contains reliable message history, communication controls, and the context needed to resolve the customer's request.

---

# USER FLOW

### Step 1

Agent opens a conversation.

### Step 2

Tajeran loads message history.

### Step 3

Agent sees attachments and delivery status.

### Step 4

AI may provide:

- Summary
- Suggested response
- Relevant context

### Step 5

Agent writes or edits a response.

### Step 6

Agent sends it.

### Step 7

Tajeran records delivery status.

### Step 8

Internal notes remain internal.

---

# DOMAIN

## Entities

- Conversation
- Message
- Attachment
- Internal Note
- Message Delivery
- Customer
- AI Draft

## Rules

- Incoming and outgoing messages must be distinguishable.
- Internal notes must never be sent to customers.
- Message history is immutable after sending except for permitted metadata.
- Attachments require secure handling.
- Sending requires authorization.
- Delivery status must not be confused with successful delivery.

---

# SYSTEM

## Frontend

- Message timeline
- Composer
- Internal note mode
- Attachments
- Drafts
- Delivery state
- AI suggestions
- Context panel

## API

- Get messages
- Send message
- Save draft
- Add internal note
- Upload attachment
- Get delivery status

## Database

- Conversations
- Messages
- Attachments
- Drafts
- Delivery records

## External

- Email provider
- Chat infrastructure

---

# FAILURES

- Send failure
- Attachment upload failure
- Invalid attachment
- Duplicate send
- Delivery failure
- Network interruption
- Unauthorized send

---

# DONE

- Full history is visible.
- Incoming/outgoing messages work.
- Attachments work.
- Internal notes work.
- Drafts work.
- Editing before send works.
- Delivery state is shown.
- Messages cannot leak across tenants.
- Tests cover send/failure behavior.

---

# DEPLOY

Test:

1. Receive message.
2. Open conversation.
3. Send reply.
4. Add internal note.
5. Upload attachment.
6. Verify delivery.
7. Simulate send failure.
8. Verify no duplicate message.

### Production success condition

> A human agent can conduct a complete customer conversation from Tajeran without losing message history or context.

---

# 8. FEATURE

## Customer Profile

### What problem?

Agents need customer and commerce context without switching between support software and Shopify.

### Who uses it?

- Human agent
- AI agent

### Desired outcome

The agent sees a useful Customer 360 view directly beside the conversation.

---

# USER FLOW

### Step 1

Agent opens conversation.

### Step 2

Tajeran identifies customer.

### Step 3

Tajeran loads customer profile.

### Step 4

Profile displays:

- Identity
- Orders
- Fulfillment
- Refunds
- Returns
- Previous conversations
- Tags

### Step 5

Agent can navigate from profile to relevant records.

---

# DOMAIN

## Entities

- Customer
- Customer Identity
- Order
- Conversation
- Ticket
- Refund
- Return
- Tag

## Rules

- Customer data must be tenant-scoped.
- Identity matching must avoid unsafe merges.
- Commerce data must reflect Shopify source of truth where appropriate.
- Sensitive information must be appropriately protected.

---

# SYSTEM

## Frontend

- Customer panel
- Customer details
- Orders
- Commerce summary
- Support history
- Tags

## API

- Get customer
- Get orders
- Get support history
- Get commerce summary

## Domain

- Customer identity resolution
- Customer context aggregation

## External

- Shopify

---

# FAILURES

- Customer not found
- Ambiguous customer identity
- Shopify unavailable
- Partial profile data
- Stale data

---

# DONE

- Customer identity is displayed.
- Orders are displayed.
- Order value is available.
- Last order is available.
- Fulfillment is visible.
- Refunds/returns are visible.
- Previous conversations are visible.
- Tags work.
- Tenant isolation works.

---

# DEPLOY

Verify against real Shopify customer/order data and multiple customer scenarios.

### Production success condition

> An agent can understand who the customer is and their relevant commerce/support history without leaving Tajeran.

---

# 9. FEATURE

## AI Customer-Service Agent

### What problem?

Human agents cannot manually investigate and respond to every customer request efficiently.

### Who uses it?

- Customer
- Human agent
- Merchant

### Desired outcome

Tajeran can understand a customer request, gather relevant context, decide what should happen, and produce an appropriate response or escalation.

---

# USER FLOW

### Step 1

Customer sends a message.

### Step 2

AI identifies:

- Intent
- Customer
- Order
- Language
- Urgency
- Basic sentiment

### Step 3

AI retrieves relevant context.

### Step 4

AI determines the next step:

```text
Answer
Ask question
Retrieve more
Take action
Ask human
Escalate
```

### Step 5

AI generates response or action plan.

### Step 6

If action is required, controlled capabilities execute.

### Step 7

AI verifies the result.

### Step 8

AI responds or escalates.

---

# DOMAIN

## Entities

- AI Interaction
- Intent
- Entity
- AI Decision
- AI Response
- AI Action
- AI Escalation
- AI Summary

## Rules

- AI cannot access another tenant.
- AI cannot perform unauthorized capabilities.
- AI should not claim an action succeeded without verification.
- AI should ask for clarification when required.
- AI should escalate when confidence/context is insufficient.
- AI decisions and important actions must be observable.

---

# SYSTEM

## AI pipeline

```text
Message
 ↓
Understand
 ↓
Retrieve
 ↓
Decide
 ↓
Act / Answer / Escalate
 ↓
Verify
 ↓
Outcome
```

## Capability layer

AI invokes capabilities rather than directly accessing infrastructure.

## Runtime

- Agent execution
- Tool/capability invocation
- State
- Errors
- Approval
- Outcome recording

---

# FAILURES

- Intent misclassification
- Customer mismatch
- Order mismatch
- Missing context
- Knowledge unavailable
- Tool failure
- Wrong action
- Hallucinated answer
- AI timeout
- AI uncertainty
- Escalation failure

---

# DONE

- AI understands supported V1 intents.
- Customer/order can be identified.
- Relevant context is retrieved.
- AI can answer.
- AI can ask clarification.
- AI can invoke supported actions.
- AI can escalate.
- AI generates human-readable summaries.
- AI does not falsely claim success.
- AI outcomes are recorded.
- Tests cover representative customer scenarios.

---

# DEPLOY

Run real-world scenario tests:

- Order status
- Product question
- Refund
- Cancellation
- Missing context
- Unknown question
- Policy conflict
- Shopify failure
- Human escalation

### Production success condition

> Tajeran can autonomously handle defined customer-service scenarios while safely escalating anything outside its reliable operating boundary.

---

# 10. FEATURE

## AI Knowledge

### What problem?

AI needs merchant-specific policies and information to answer accurately.

### Who uses it?

- Merchant
- AI agent
- Human agent

### Desired outcome

A merchant can provide trusted knowledge that Tajeran retrieves and uses when answering customer questions.

---

# USER FLOW

### Step 1

Merchant opens Knowledge.

### Step 2

Merchant adds a source.

Examples:

- FAQ
- Policy
- Product information
- Website URL
- Custom text

### Step 3

Tajeran processes the source.

### Step 4

Knowledge becomes searchable.

### Step 5

AI retrieves relevant knowledge during customer conversations.

### Step 6

Merchant can edit or delete knowledge.

---

# DOMAIN

## Entities

- Knowledge Source
- Knowledge Document
- Knowledge Chunk
- Knowledge Version
- Knowledge Metadata
- Embedding

## States

```text
DRAFT
PROCESSING
READY
FAILED
DELETED
```

## Rules

- Knowledge belongs to workspace.
- Deleted knowledge must no longer be retrieved.
- Retrieval must be tenant-scoped.
- Source changes must be reflected in searchable knowledge.
- AI should distinguish retrieved knowledge from assumptions.

---

# SYSTEM

## Frontend

- Knowledge list
- Add source
- Edit
- Delete
- Processing status
- Search/test

## API

- Create source
- Update source
- Delete source
- Search knowledge
- Retrieve relevant knowledge

## Processing

```text
Source
 ↓
Extract
 ↓
Normalize
 ↓
Chunk
 ↓
Embed
 ↓
Index
```

## Database

- Sources
- Documents
- Chunks
- Embeddings
- Versions

---

# FAILURES

- Invalid URL
- Website unavailable
- Parsing failure
- Embedding failure
- Index failure
- Duplicate source
- Stale source
- Tenant leakage

---

# DONE

- All V1 source types work.
- Sources can be added.
- Sources can be edited.
- Sources can be deleted.
- Search works.
- Relevant knowledge can be retrieved.
- AI can use retrieved knowledge.
- Deleted knowledge is not retrieved.
- Tenant isolation works.
- Tests cover ingestion and retrieval.

---

# DEPLOY

Add real merchant policies and test:

- Exact policy question
- Irrelevant question
- Conflicting knowledge
- Updated policy
- Deleted source
- Website source
- Knowledge retrieval latency

### Production success condition

> A merchant can provide their own knowledge and Tajeran reliably uses it when handling customer questions.

---

# 11. FEATURE

## AI → Human Handoff

### What problem?

AI cannot reliably handle every customer-service situation. When it reaches its boundary, a human must take over without losing context.

### Who uses it?

- AI agent
- Human agent
- Merchant

### Desired outcome

AI can escalate a conversation with enough context that the human can continue immediately.

---

# USER FLOW

### Step 1

AI determines human intervention is required.

### Step 2

AI creates escalation.

### Step 3

AI records:

- Why
- What customer requested
- What it tried
- What it found
- What failed
- Recommended next action

### Step 4

Conversation is assigned/escalated.

### Step 5

Human opens conversation.

### Step 6

Human reviews AI summary.

### Step 7

Human takes over.

### Step 8

Human resolves or returns control to AI.

---

# DOMAIN

## Entities

- Escalation
- Conversation
- AI Summary
- Handoff
- Assignment

## States

```text
REQUESTED
 ↓
ASSIGNED
 ↓
HUMAN_ACTIVE
 ↓
RESOLVED
```

Possible:

```text
RETURNED_TO_AI
CANCELLED
```

## Rules

- Escalation must preserve conversation history.
- Human must see AI context.
- AI must stop acting when human control is active unless explicitly allowed.
- Returning control to AI must be explicit.

---

# SYSTEM

## Frontend

- Escalation indicator
- AI summary
- Handoff reason
- Recommended action
- Take over
- Return to AI

## API

- Create escalation
- Assign
- Take over
- Return to AI
- Resolve

## Runtime

- Pause AI
- Handoff state
- Resume

---

# FAILURES

- Escalation not assigned
- AI continues after handoff
- Summary unavailable
- Agent unavailable
- Conversation state conflict

---

# DONE

- AI can escalate.
- Reason is visible.
- Summary is visible.
- Actions already attempted are visible.
- Human can take over.
- AI stops appropriately.
- Human can resolve.
- Human can return control to AI.
- Tests cover handoff state transitions.

---

# DEPLOY

Test real conversations where:

- AI knows answer.
- AI does not know answer.
- AI action fails.
- Customer requests human.
- Human takes over.
- Human returns control to AI.

### Production success condition

> A human can take over an AI-handled conversation without repeating the investigation already performed by AI.

---

# 12. FEATURE

## AI Actions

### What problem?

Customer-service automation becomes valuable when Tajeran can complete work instead of only generating text.

### Who uses it?

- AI agent
- Workflow
- Human agent

### Desired outcome

Tajeran can execute controlled customer-service operations and verify their outcomes.

---

# USER FLOW

### Example: Order status

```text
Customer request
 ↓
Identify customer
 ↓
Find order
 ↓
Find fulfillment
 ↓
Find tracking
 ↓
Verify current state
 ↓
Generate answer
```

### Example: Refund

```text
Customer request
 ↓
Identify order
 ↓
Check policy
 ↓
Determine eligibility
 ↓
Request approval if needed
 ↓
Refund
 ↓
Verify refund
 ↓
Respond
 ↓
Record outcome
```

---

# DOMAIN

## Entities

- Action Request
- Capability
- Action Execution
- Approval
- Verification
- Action Result
- Outcome

## Rules

- Every action has an explicit capability.
- Input must be validated.
- Authorization must be checked.
- Risk must be known.
- Destructive actions require configured authorization.
- Verification is required where technically possible.
- Failure cannot be represented as success.

---

# SYSTEM

```text
AI
 ↓
Capability Resolver
 ↓
Capability
 ↓
Provider
 ↓
External System
 ↓
Result
 ↓
Verification
 ↓
Outcome
```

---

# FAILURES

- Wrong entity
- Invalid input
- Policy conflict
- Unauthorized action
- External API failure
- Timeout
- Partial completion
- Verification failure

---

# DONE

- V1 supported action scenarios work end-to-end.
- Actions use controlled capabilities.
- Authorization works.
- Approval works.
- Verification works.
- Outcomes are recorded.
- Failures are recoverable/escalatable.
- Tests cover complete customer scenarios.

---

# DEPLOY

Run end-to-end production-safe scenarios for:

- Order lookup
- Tracking
- Order note
- Refund
- Cancellation

### Production success condition

> Tajeran can complete a real customer-service task from customer request through verified business outcome.

---

# 13. FEATURE

## Human Approval

### What problem?

Some actions are too sensitive to execute autonomously without merchant or agent approval.

### Who uses it?

- AI agent
- Human agent
- Workspace administrator

### Desired outcome

Tajeran can pause an operation, request approval, and safely continue or cancel based on the decision.

---

# USER FLOW

### Step 1

AI determines approval is required.

### Step 2

Tajeran creates approval request.

### Step 3

Authorized human receives notification.

### Step 4

Human reviews:

- Customer request
- Context
- Proposed action
- Risk
- Expected result

### Step 5

Human selects:

**Approve / Reject / Cancel**

### Step 6

Runtime continues or terminates.

### Step 7

Decision is recorded.

---

# DOMAIN

## Entities

- Approval Request
- Approval Decision
- Approver
- Action
- Conversation
- Workflow Run

## States

```text
PENDING
 ↓
APPROVED
```

or

```text
REJECTED
CANCELLED
EXPIRED
```

## Rules

- Only authorized users can approve.
- Approval must be tied to a specific action/context.
- Approval cannot be reused for unrelated actions.
- Approval decisions are immutable/auditable.
- Runtime must not continue before required approval.

---

# SYSTEM

## Frontend

- Approval queue
- Approval detail
- Approve
- Reject
- Cancel
- History

## API

- Create approval
- List approvals
- Approve
- Reject
- Cancel
- Get history

## Runtime

- Pause
- Wait for approval
- Resume
- Cancel

---

# FAILURES

- Unauthorized approval
- Approval timeout
- Duplicate decision
- Action changed after approval
- Runtime unavailable
- Approver removed

---

# DONE

- Approval can be requested.
- Authorized user can approve.
- User can reject.
- User can cancel.
- Runtime waits correctly.
- Approval is audited.
- Action cannot execute without required approval.
- Tests cover race conditions and duplicate decisions.

---

# DEPLOY

Test a real approval-required refund/cancellation flow.

### Production success condition

> A sensitive AI action cannot execute until an authorized human explicitly approves it.

---

# 14. FEATURE

## Basic Automation

### What problem?

Merchants need predictable rules for repetitive support operations without manually handling every conversation.

### Who uses it?

- Merchant
- Administrator
- Support manager

### Desired outcome

A merchant can create simple trigger → condition → action automations.

---

# USER FLOW

### Step 1

Merchant opens Automation.

### Step 2

Creates automation.

### Step 3

Selects trigger.

### Step 4

Adds optional conditions.

### Step 5

Selects action.

### Step 6

Saves and activates automation.

### Step 7

Matching event occurs.

### Step 8

Tajeran evaluates rule.

### Step 9

Action executes.

### Step 10

Execution is recorded.

---

# DOMAIN

## Entities

- Automation
- Trigger
- Condition
- Action
- Automation Run

## Triggers

- New conversation
- New message
- Customer reply
- Shopify event

## Conditions

- Intent
- Customer
- Order
- Tag
- Channel
- Priority

## Actions

- Assign
- Tag
- Reply
- Escalate
- Start AI handling
- Create task
- Change status

---

# SYSTEM

## Frontend

- Automation list
- Automation editor
- Trigger selector
- Condition builder
- Action selector
- Enable/disable
- Execution history

## Runtime

Automation execution should use the existing runtime/capability architecture where appropriate.

---

# FAILURES

- Invalid condition
- Invalid action
- Automation loop
- Duplicate execution
- Action failure
- Conflicting automations
- Disabled automation still executing

---

# DONE

- Triggers work.
- Conditions work.
- Actions work.
- Automations can be enabled/disabled.
- Execution is recorded.
- Duplicate execution is prevented.
- Errors are visible.
- Tests cover representative automations.

---

# DEPLOY

Create real automations:

- Auto-tag refund requests.
- Route VIP customer.
- Start AI handling.
- Escalate high-priority conversation.

### Production success condition

> A merchant can automate repetitive support behavior reliably without manually operating each conversation.

---

# 15. FEATURE

## Basic Workflow

### What problem?

Some customer-service tasks require multiple coordinated steps rather than a single automation rule.

### Who uses it?

- Merchant
- Administrator
- AI agent
- Workflow runtime

### Desired outcome

A merchant can create and execute a small workflow containing AI, conditions, Shopify actions, messaging, assignment, approval, waiting, and completion.

---

# USER FLOW

### Step 1

Merchant creates workflow.

### Step 2

Selects trigger.

### Step 3

Adds nodes.

### Step 4

Connects nodes.

### Step 5

Validates workflow.

### Step 6

Publishes workflow.

### Step 7

Trigger occurs.

### Step 8

Runtime executes nodes.

### Step 9

Workflow pauses when necessary.

### Step 10

Workflow resumes after approval/wait.

### Step 11

Workflow completes.

### Step 12

Execution history is available.

---

# DOMAIN

## Node types

```text
Trigger
AI
Condition
Shopify
Send message
Assign
Human approval
Wait
End
```

## Entities

- Workflow
- Workflow Version
- Workflow Node
- Workflow Edge
- Workflow Run
- Run State
- Workflow Event

## States

```text
DRAFT
 ↓
PUBLISHED
 ↓
DISABLED
```

Run:

```text
PENDING
RUNNING
WAITING
COMPLETED
FAILED
CANCELLED
```

## Rules

- Published workflows are versioned.
- Running workflows retain their execution state.
- Invalid workflows cannot be published.
- Side effects must be controlled/idempotent.
- Tenant isolation applies to every execution.
- Failed runs must be observable.

---

# SYSTEM

## Frontend

- Workflow builder
- Node palette
- Canvas
- Configuration panels
- Validation
- Publish
- Enable/disable
- Run history
- Execution timeline

## Runtime

```text
Trigger
 ↓
RunState
 ↓
Node execution
 ↓
Persist state
 ↓
Next node
 ↓
Complete / Wait / Fail
```

## Database

- Workflow
- Version
- Nodes
- Edges
- Runs
- Snapshots/events

---

# FAILURES

- Invalid graph
- Missing configuration
- Node failure
- Shopify failure
- AI failure
- Approval timeout
- Duplicate side effect
- Runtime crash
- Resume failure

---

# DONE

- All V1 nodes work.
- Workflow can be created.
- Workflow can be validated.
- Workflow can be published.
- Workflow can execute.
- Wait works.
- Approval works.
- Failed runs are visible.
- Execution state survives interruption.
- Runs are tenant-scoped.
- Tests cover representative workflows.

---

# DEPLOY

Deploy at least these workflows:

```text
New conversation
 ↓
AI
 ↓
Condition
 ↓
Send response
```

and:

```text
Refund request
 ↓
AI
 ↓
Policy check
 ↓
Approval
 ↓
Refund
 ↓
Verify
 ↓
Customer response
```

### Production success condition

> A merchant can publish and run a real multi-step customer-service workflow and inspect exactly what happened.

---

# 16. FEATURE

## Website Chat + Channel Abstraction

### What problem?

V1 needs a customer-facing communication channel while keeping Tajeran's internal conversation model independent from any specific channel.

### Who uses it?

- Customer
- AI agent
- Human agent
- Merchant

### Desired outcome

A Shopify customer can contact the merchant through website chat and the resulting conversation enters the same Tajeran conversation system used by email and future channels.

---

# USER FLOW

### Step 1

Merchant enables website chat.

### Step 2

Merchant configures basic widget settings.

### Step 3

Widget is installed on Shopify.

### Step 4

Customer opens chat.

### Step 5

Customer identifies themselves where possible.

### Step 6

Conversation is created.

### Step 7

AI or human responds.

### Step 8

Conversation is stored in the unified conversation model.

---

# DOMAIN

## Entities

- Channel
- Channel Connection
- Conversation
- Customer Identity
- Message
- Channel Session

## Rules

- Channel-specific details must not contaminate the core conversation model.
- Customer identity must be handled safely.
- Messages must retain channel metadata.
- Future channels should be able to use the same conversation abstraction.

---

# SYSTEM

## Frontend

- Chat widget
- Greeting
- Logo
- Name
- Color
- Business hours
- Customer identification

## Backend

- Chat session
- Message ingestion
- Conversation creation
- Message delivery
- Customer identity

## Architecture

```text
Channel
   ↓
Conversation
   ↓
AI / Human
```

---

# FAILURES

- Widget unavailable
- Message delivery failure
- Customer identity failure
- Duplicate message
- Session expiration
- Backend unavailable

---

# DONE

- Widget installs.
- Widget opens.
- Customer can send message.
- Conversation is created.
- AI can respond.
- Human can respond.
- Handoff works.
- Customer identification works where available.
- Basic customization works.
- Channel abstraction is preserved.

---

# DEPLOY

Install widget on a real Shopify test store and verify:

- Load
- Message
- Conversation creation
- AI response
- Human response
- Customer identification
- Reconnect/reload behavior

### Production success condition

> A real Shopify customer can open the widget, communicate with Tajeran, and have the conversation handled through the same core support system.

---

# 17. FEATURE

## Email

### What problem?

Many Shopify merchants already receive customer-service requests through email and need those conversations inside Tajeran.

### Who uses it?

- Customer
- Support agent
- AI agent
- Merchant

### Desired outcome

Incoming support emails become conversations, and Tajeran can send replies while preserving threading and attachments.

---

# USER FLOW

### Step 1

Merchant connects/configures support email.

### Step 2

Customer sends email.

### Step 3

Tajeran receives email.

### Step 4

Tajeran identifies or creates customer/conversation.

### Step 5

Email becomes a message.

### Step 6

AI or human prepares response.

### Step 7

Tajeran sends reply.

### Step 8

Thread remains connected to the same conversation.

---

# DOMAIN

## Entities

- Email Channel
- Email Account
- Email Message
- Conversation
- Thread
- Attachment
- Customer Identity

## Rules

- Email thread must map correctly to conversation.
- Incoming email must be tenant-scoped.
- Attachments must be secure.
- Outgoing messages must use the correct merchant identity.
- Duplicate email delivery must be handled safely.

---

# SYSTEM

## API

- Email ingestion
- Email sending
- Thread mapping
- Attachment handling

## External

- Email provider
- SMTP/API provider

## Domain

- Email → conversation mapping
- Customer identity resolution
- Thread management

---

# FAILURES

- Email provider unavailable
- Invalid email
- Duplicate message
- Thread mismatch
- Attachment failure
- Send failure
- Bounce
- Delivery failure

---

# DONE

- Support email receives messages.
- Messages become conversations.
- Threads are preserved.
- AI can respond.
- Human can respond.
- Attachments work.
- Customer identity is resolved.
- Delivery state is tracked.
- Tenant isolation works.

---

# DEPLOY

Send real emails into production and verify:

- Inbound
- Threading
- AI response
- Human response
- Attachments
- Delivery
- Failure handling

### Production success condition

> A real merchant can operate their support email from Tajeran's unified inbox.

---

# 18. FEATURE

## Basic Ticketing

### What problem?

Some support work needs an explicit case/ticket lifecycle beyond the conversation itself.

### Who uses it?

- Support agent
- Team
- Administrator

### Desired outcome

Agents can create and manage a basic ticket linked to a conversation.

---

# USER FLOW

### Step 1

Agent creates ticket from conversation.

### Step 2

Tajeran links ticket to conversation/customer.

### Step 3

Agent sets:

- Status
- Priority
- Assignee
- Team

### Step 4

Agent works the issue.

### Step 5

Ticket is resolved.

### Step 6

Ticket can be reopened if necessary.

---

# DOMAIN

## Entities

- Ticket
- Conversation
- Customer
- Assignment
- Team
- Priority
- Ticket Status

## States

```text
OPEN
PENDING
RESOLVED
```

## Rules

- Ticket belongs to workspace.
- Ticket can reference conversation.
- Status changes are auditable.
- Resolution does not delete history.
- Reopening preserves history.

---

# SYSTEM

## Frontend

- Ticket creation
- Ticket details
- Status
- Priority
- Assignment
- Team
- Resolve/reopen

## API

- Create ticket
- Update ticket
- Assign
- Resolve
- Reopen
- Link conversation

## Database

- Tickets
- Status history
- Assignment
- Conversation relationship

---

# FAILURES

- Invalid conversation
- Invalid assignee
- Unauthorized access
- Concurrent update
- Database failure

---

# DONE

- Ticket can be created.
- Ticket links to conversation.
- Status works.
- Priority works.
- Assignment works.
- Team works.
- Resolve works.
- Reopen works.
- Audit history works.

---

# DEPLOY

Create and resolve real tickets from real conversations.

### Production success condition

> Agents can explicitly track customer issues as tickets without creating a second disconnected support system.

---

# 19. FEATURE

## Basic Routing

### What problem?

Customer requests need to reach the right AI, agent, team, or queue without manual intervention every time.

### Who uses it?

- Merchant
- Administrator
- Support manager
- AI system

### Desired outcome

Tajeran automatically assigns conversations according to simple routing rules.

---

# USER FLOW

### Step 1

Conversation arrives.

### Step 2

Routing system evaluates rules.

### Step 3

System determines destination.

### Step 4

Conversation is assigned.

### Step 5

Assignment is recorded.

### Step 6

If no rule matches, default routing applies.

---

# DOMAIN

## Entities

- Routing Rule
- Assignment
- Team
- Agent
- AI Handler
- Queue

## Rules

- Rules are evaluated deterministically.
- Rule priority/order must be defined.
- Invalid targets cannot be assigned.
- Assignment must be tenant-scoped.
- Fallback routing must exist.

---

# SYSTEM

## Routing inputs

- Intent
- Customer
- Order
- Tag
- Channel
- Priority

## Routing targets

- AI
- Agent
- Team
- Queue

## Frontend

- Routing rules
- Rule order
- Destination
- Enable/disable

---

# FAILURES

- No matching rule
- Invalid target
- Conflicting rules
- Agent unavailable
- Assignment failure
- Routing loop

---

# DONE

- AI assignment works.
- Human assignment works.
- Team assignment works.
- Round robin works.
- Rule-based routing works.
- Default route exists.
- Routing history is recorded.
- Tests cover conflicting/no-match rules.

---

# DEPLOY

Create:

- AI-first rule
- VIP/customer rule
- Team rule
- Round-robin rule
- Default fallback

### Production success condition

> New conversations consistently reach an appropriate handler without manual assignment.

---

# 20. FEATURE

## Basic SLA

### What problem?

Merchants need to know when customer conversations require attention and when support commitments are being missed.

### Who uses it?

- Support agent
- Support manager
- Administrator

### Desired outcome

Tajeran tracks response and resolution commitments and warns/escalates when they are approaching or exceeding their limits.

---

# USER FLOW

### Step 1

Merchant configures business hours.

### Step 2

Merchant configures:

- First response SLA
- Resolution SLA

### Step 3

Conversation starts.

### Step 4

SLA timer begins.

### Step 5

Tajeran calculates remaining time.

### Step 6

Warning is generated.

### Step 7

If deadline passes, SLA breach is recorded.

### Step 8

Escalation may occur.

---

# DOMAIN

## Entities

- SLA Policy
- SLA Timer
- Business Calendar
- SLA Event
- SLA Breach

## States

```text
RUNNING
WARNING
BREACHED
PAUSED
COMPLETED
```

## Rules

- Business hours must be respected.
- Timer behavior must be deterministic.
- Response SLA and resolution SLA are separate.
- Resolution should stop the appropriate timer.
- SLA state must survive system restart.

---

# SYSTEM

## Frontend

- SLA configuration
- Timer
- Warning
- Breach
- Conversation indicator

## Backend

- SLA calculation
- Timer persistence
- Business-hour calculation
- Escalation

---

# FAILURES

- Incorrect business hours
- Timezone error
- Timer restart error
- Status transition race
- SLA calculation error

---

# DONE

- Business hours work.
- First-response SLA works.
- Resolution SLA works.
- Timers work.
- Warnings work.
- Breaches work.
- Escalation works.
- Timezones are handled correctly.
- Tests cover boundary cases.

---

# DEPLOY

Test:

- Business-hours conversation
- Outside-hours conversation
- Weekend
- SLA warning
- SLA breach
- Resolution before breach

### Production success condition

> Merchant can reliably see which conversations are approaching or exceeding their support commitments.

---

# 21. FEATURE

## Analytics

### What problem?

Merchants need to understand whether customer service is improving and whether AI is actually solving customer problems.

### Who uses it?

- Merchant
- Administrator
- Support manager

### Desired outcome

Tajeran provides a simple, trustworthy operational dashboard for support, AI, and team performance.

---

# USER FLOW

### Step 1

Merchant opens Analytics.

### Step 2

Selects time range.

### Step 3

Tajeran calculates metrics.

### Step 4

Merchant sees:

### Support

- Conversations
- Open
- Resolved
- Response time
- Resolution time

### AI

- AI handled
- AI escalated
- AI failed
- Action success
- Resolution rate

### Team

- Conversations per agent
- Response time
- Resolution time

---

# DOMAIN

## Metrics

- Conversation volume
- Open count
- Resolution count
- First response time
- Resolution time
- AI handling rate
- AI escalation rate
- AI failure rate
- Action success rate
- Resolution rate
- Agent workload

## Rules

- Metrics must have defined meanings.
- Time windows must be consistent.
- AI metrics must distinguish generated response from successful resolution.
- Missing data must not silently become misleading zeros.

---

# SYSTEM

## Frontend

- Analytics dashboard
- Date range
- Metric cards
- Tables/charts
- Basic filters

## Backend

- Metric aggregation
- Time-window calculation
- AI outcome aggregation
- Team aggregation

## Database

May use operational data initially; dedicated analytics infrastructure is not required for V1.

---

# FAILURES

- Incorrect aggregation
- Timezone errors
- Duplicate events
- Missing outcome
- Slow queries

---

# DONE

- Support metrics work.
- AI metrics work.
- Team metrics work.
- Date range works.
- Metrics match source data.
- Basic performance is acceptable.
- Tests verify metric calculations.

---

# DEPLOY

Compare dashboard values against known production data and manually verify calculations.

### Production success condition

> Merchant can open Analytics and trust that the displayed numbers accurately represent what happened in support.

---

# 22. FEATURE

## AI Quality / Outcomes

### What problem?

Traditional support metrics cannot tell Tajeran whether an AI interaction actually solved the customer's problem.

### Who uses it?

- AI system
- Merchant
- Support manager
- Future learning/repair systems

### Desired outcome

Every meaningful AI interaction produces a structured outcome that can later be evaluated and used to improve the system.

---

# USER FLOW

### Step 1

Customer request arrives.

### Step 2

AI understands request.

### Step 3

AI makes decision.

### Step 4

AI performs action or generates response.

### Step 5

Result is obtained.

### Step 6

Result is verified where possible.

### Step 7

Outcome is recorded.

### Step 8

Later signals may update/evaluate the outcome.

---

# DOMAIN

## Entities

- AI Interaction
- Request
- Decision
- Action
- Result
- Outcome
- Evaluation
- Correction
- Escalation

## Outcome states

```text
SUCCESSFUL
FAILED
ESCALATED
HUMAN_CORRECTED
CUSTOMER_REOPENED
ACTION_FAILED
POLICY_CONFLICT
```

## Evaluation

- Answer correctness
- Action correctness
- Issue resolution

## Rules

- Outcome must represent actual result, not AI assumption.
- Human corrections must be distinguishable.
- Customer reopening is an important negative signal.
- Action failure must not equal successful resolution.
- Outcome records must be traceable to the interaction.

---

# SYSTEM

## Runtime

Capture:

```text
Request
 ↓
Decision
 ↓
Action
 ↓
Result
 ↓
Outcome
```

## Database

- Interaction
- Decision
- Action execution
- Result
- Outcome
- Evaluation

## Analytics

Outcome data feeds AI/support analytics.

## Future

This becomes the foundation for:

- Learning
- Repair
- Quality evaluation
- Optimization

---

# FAILURES

- Outcome missing
- Incorrect outcome
- Action/result mismatch
- Human correction not recorded
- Customer reopening not linked
- Evaluation failure

---

# DONE

- Every supported AI interaction has an outcome lifecycle.
- Success/failure/escalation are distinguishable.
- Human correction is recorded.
- Customer reopen is recorded.
- Action success is separate from answer success.
- Basic evaluation exists.
- Outcome is traceable to conversation/run/action.
- Tests cover outcome transitions.

---

# DEPLOY

Take real AI conversations and inspect:

1. Request
2. Decision
3. Action
4. Result
5. Outcome
6. Human correction where applicable

### Production success condition

> Tajeran can tell not merely what its AI did, but whether the customer-service task actually succeeded.

---

# 23. FEATURE

## Notifications

### What problem?

Users need to know when something requires their attention without constantly watching Tajeran.

### Who uses it?

- Merchant
- Admin
- Support agent
- Customer

### Desired outcome

Important support, AI, approval, and SLA events generate appropriate notifications while avoiding unnecessary noise.

---

# USER FLOW

### Internal example

```text
AI escalation
 ↓
Notification event
 ↓
Assigned agent notified
 ↓
Agent opens conversation
```

### Approval example

```text
AI requests refund approval
 ↓
Approval notification
 ↓
Admin reviews
 ↓
Approves/rejects
```

### Customer example

```text
Customer message
 ↓
Merchant response
 ↓
Customer receives response
```

---

# DOMAIN

## Entities

- Notification
- Notification Event
- Recipient
- Notification Preference
- Delivery
- Template

## Internal events

- New conversation
- Assignment
- Mention
- Approval request
- SLA warning
- SLA breach
- AI escalation
- AI failure

## Customer events

- Conversation received
- Reply
- Status update
- Resolution

## Rules

- Notifications must be tenant-scoped.
- Recipient must be authorized.
- Duplicate notifications should be prevented where appropriate.
- Customer/internal notifications must be separated.
- Failed delivery must be observable.

---

# SYSTEM

## Frontend

- Notification center
- Unread state
- Notification preferences

## Backend

- Event generation
- Notification creation
- Recipient resolution
- Delivery
- Read/unread state

## External

- Email
- Browser notifications where supported
- Customer email/chat notification mechanisms

---

# FAILURES

- Wrong recipient
- Duplicate notification
- Delivery failure
- Provider unavailable
- Notification storm
- Customer notification accidentally sent internally

---

# DONE

- Required internal notifications work.
- Customer notifications work.
- Recipients are correct.
- Read/unread works.
- Delivery failures are tracked.
- Internal and customer notifications are separated.
- Tenant isolation works.
- Tests cover recipient and delivery behavior.

---

# DEPLOY

Trigger real:

- New conversation
- Assignment
- Approval
- SLA warning
- SLA breach
- AI escalation
- AI failure
- Customer reply

Verify correct recipient and delivery.

### Production success condition

> The right person receives the right notification when meaningful customer-service work requires attention.

---

# 24. FEATURE

## Audit & Security

### What problem?

Tajeran handles customer data, commerce data, AI decisions, and potentially financial/destructive actions. The merchant needs confidence that access is controlled and important activity can be traced.

### Who uses it?

- Workspace administrator
- Merchant
- Security/operations
- Tajeran system

### Desired outcome

All sensitive operations are authorized, tenant-isolated, securely stored, and auditable.

---

# USER FLOW

### Step 1

User performs an action.

### Step 2

Tajeran authenticates the user/system.

### Step 3

Authorization is checked.

### Step 4

Action executes.

### Step 5

Important activity is recorded.

### Step 6

Administrator can inspect audit history.

---

# DOMAIN

## Audit events

- User login
- Configuration change
- AI action
- Human action
- Shopify action
- Approval
- Workflow execution
- Membership change
- Integration change

## Security boundaries

```text
User
 ↓
Workspace
 ↓
Domain resource
 ↓
Capability
 ↓
External provider
```

## Rules

- Every workspace resource is tenant-scoped.
- Authorization is enforced server-side.
- Credentials are encrypted.
- Shopify tokens are protected.
- Webhooks are verified.
- Sessions are secured.
- Sensitive secrets are never logged.
- Audit records cannot be silently modified/deleted by ordinary users.

---

# SYSTEM

## Authentication

- Secure sessions
- API authentication
- Authorization

## Authorization

- Workspace membership
- Role
- Permission
- Resource ownership

## Audit

- Event
- Actor
- Workspace
- Resource
- Action
- Timestamp
- Result
- Metadata

## Security

- Encryption
- Secret management
- Token protection
- Webhook verification
- Secure headers/configuration
- Logging controls

---

# FAILURES

- Unauthorized access
- Cross-tenant access attempt
- Token leakage
- Secret leakage
- Invalid webhook
- Session compromise
- Incorrect permission
- Audit event missing

---

# DONE

- Tenant isolation is enforced.
- Authorization is server-side.
- Admin/agent permissions work.
- Credentials are encrypted.
- Shopify tokens are secure.
- Webhooks are verified.
- Sessions are secure.
- Sensitive data does not appear in logs.
- Important actions are audited.
- Security tests exist.
- Cross-tenant tests exist.

---

# DEPLOY

Perform production security verification:

1. Attempt cross-tenant access.
2. Attempt unauthorized action.
3. Verify Shopify token protection.
4. Inspect logs for secrets.
5. Verify webhook validation.
6. Verify audit events.
7. Verify session expiration/revocation.
8. Verify removed users lose access.

### Production success condition

> A merchant's customer, commerce, AI, and operational data remains isolated and important actions can be traced to an authorized actor.

---

# 25. FEATURE

## Billing & Usage

### What problem?

A commercial product needs to know which workspace is subscribed, what limits apply, and how much of the product is being used.

### Who uses it?

- Merchant
- Workspace administrator
- Tajeran billing system

### Desired outcome

A merchant can start a trial/subscription, see basic usage and billing status, upgrade/cancel, and Tajeran can enforce the applicable limits.

---

# USER FLOW

### Step 1

Merchant creates workspace.

### Step 2

Workspace receives trial/plan.

### Step 3

Merchant views:

- Current plan
- Trial status
- Usage
- Limits
- Billing status

### Step 4

Merchant upgrades if required.

### Step 5

Subscription status changes.

### Step 6

Usage is recorded.

### Step 7

Limits are enforced.

### Step 8

Merchant can cancel according to billing rules.

---

# DOMAIN

## Entities

- Plan
- Subscription
- Trial
- Usage Record
- Usage Limit
- Billing Customer
- Invoice/Payment Status

## Usage

V1 may track:

- AI usage
- Conversation usage
- Other defined billable units

## States

### Subscription

```text
TRIAL
ACTIVE
PAST_DUE
CANCELLED
EXPIRED
```

## Rules

- Billing belongs to workspace.
- Usage must be attributed to the correct workspace.
- Limits must be deterministic.
- Billing state must not be inferred from frontend state.
- Subscription changes must be auditable.
- Product access must reflect actual billing state.

---

# SYSTEM

## Frontend

- Billing page
- Current plan
- Trial
- Usage
- Limits
- Upgrade
- Cancel
- Billing status

## API

- Get billing status
- Get usage
- Create/change subscription
- Cancel subscription
- Enforce limits

## Database

- Plans
- Subscriptions
- Usage
- Limits
- Billing customer
- Subscription events

## External

- Payment/billing provider

---

# FAILURES

- Payment failure
- Provider unavailable
- Subscription state mismatch
- Duplicate billing event
- Usage attribution error
- Limit calculation error
- Cancellation failure

---

# DONE

- Trial works.
- Subscription state works.
- Plan is stored.
- Usage is recorded.
- Limits are enforced.
- Billing status is visible.
- Upgrade works.
- Cancel works.
- Billing events are idempotent.
- Workspace isolation works.
- Tests cover subscription/usage transitions.

---

# DEPLOY

Production verification:

1. Create test workspace.
2. Verify trial.
3. Verify plan.
4. Generate usage.
5. Verify usage attribution.
6. Verify limits.
7. Test upgrade.
8. Test cancellation.
9. Test billing-provider event.
10. Verify final access state.

### Production success condition

> A real merchant can use Tajeran under a defined commercial plan, and Tajeran can accurately track usage and enforce the associated limits.

---

# V1 CROSS-FEATURE PRODUCTION ACCEPTANCE

The individual features above should not be considered independently complete until the complete V1 customer-service loop works.

## End-to-end scenario

```text
Merchant
   ↓
Create account
   ↓
Create workspace
   ↓
Connect Shopify
   ↓
Configure knowledge
   ↓
Install chat / connect email
   ↓
Customer contacts merchant
   ↓
Conversation created
   ↓
Routing
   ↓
AI understands request
   ↓
Retrieve customer/order context
   ↓
Retrieve knowledge
   ↓
AI decides
   ├── Answer
   │
   ├── Ask question
   │
   ├── Escalate
   │
   └── Take action
            ↓
       Human approval
            ↓
       Shopify action
            ↓
         Verify
            ↓
        Customer reply
            ↓
        Resolve
            ↓
      Record outcome
            ↓
         Analytics
```

# V1 FINAL PRODUCT SUCCESS CONDITION

> A real Shopify merchant can connect their store, receive a real customer request through chat or email, allow Tajeran to understand the request, retrieve the correct customer/order/knowledge context, answer or perform a supported action, obtain human approval when required, verify the result, communicate with the customer, resolve the conversation, and record whether the customer-service task actually succeeded.

# V1 SCOPE BOUNDARY

The following are intentionally **not required to block V1**:

- WhatsApp
- Instagram
- Facebook Messenger
- SMS
- Voice
- Advanced help center
- Advanced customer segmentation
- Advanced omnichannel identity
- Enterprise SSO/SCIM
- Large integration marketplace
- Advanced workflow marketplace
- Advanced AI learning
- Autonomous AI repair
- Advanced predictive analytics
- Mobile native application
- Complex enterprise billing
- Huge workflow node library

Those belong to later expansion.

# V1 PRODUCT PRINCIPLE

The product should not be judged by how many features exist.

It should be judged by whether this loop works reliably:

```text
UNDERSTAND
    ↓
CONTEXT
    ↓
DECIDE
    ↓
ACT
    ↓
VERIFY
    ↓
RESOLVE
    ↓
MEASURE OUTCOME
```

That loop is the actual core of Tajeran V1.

*****************************************************
TAJERAN
│
├── 1. Workspace / Account
├── 2. Shopify Connection
├── 3. Inbox
├── 4. Conversations
├── 5. AI Customer Service
├── 6. Knowledge
├── 7. Routing / Teams
├── 8. Tickets
├── 9. Workflows / Automation
├── 10. Human Approval
├── 11. Shopify Actions
├── 12. Channels
├── 13. Chatbot
├── 14. Analytics
├── 15. AI Quality / Outcomes
├── 16. Billing / Usage
├── 17. Settings / Security
└── 18. Runtime / Operations


INBOX
│
├── View conversations
├── Search conversations
├── Filter conversations
├── Assign conversation
├── Change status
├── Reply
├── AI reply
├── Internal note
├── Customer information
├── Order information
├── Conversation history
└── Escalation
## #######################################################################
complete feature map of a world-class customer-service product. Then we decide V1/V2/later,
after that we take each feature through your detailed implementation page.

especially ecommerce-focused Gorgias and broader Zendesk-style support platforms,


Tajeran Customer Service — Complete Feature Map
1. Workspace & Account
Account
- Sign up
- Login
- Logout
- Password reset
- Email verification
- Session management
- MFA / 2FA
- SSO later
Workspace
- Create workspace
- Workspace profile
- Workspace settings
- Multiple stores
- Multiple brands
- Workspace timezone
- Business hours
- Holidays
Team
- Invite team members
- Teams
- Roles
- Permissions
- Agent status
- Agent availability
- Admin permissions
- Manager permissions
- Agent permissions
2. Shopify Integration
This is extremely important for your Shopify-first positioning.
Connection
- Connect Shopify
- OAuth
- Disconnect
- Reconnect
- Connection health
- Permission management
Shopify data
- Customers
- Orders
- Products
- Variants
- Inventory
- Fulfillments
- Shipping
- Discounts
- Returns
- Refunds
- Customer history
Shopify actions
- View order
- Cancel order
- Edit order
- Refund
- Partial refund
- Duplicate order
- Update customer
- Update order
- Add order note
- Create discount
- Product lookup
- Fulfillment lookup
- Tracking lookup
Current ecommerce helpdesks already put much of this directly inside the support workspace rather than forcing agents to switch to Shopify. Gorgias
3. Unified Inbox
This should be one of the core Tajeran screens.
Conversation list
- All conversations
- My conversations
- Unassigned
- Assigned
- Open
- Pending
- Resolved
- Snoozed
- Priority
- AI handled
- Human handled
- Failed AI
- Escalated
Search
- Customer
- Email
- Order number
- Conversation
- Message
- Ticket
- Tag
- Intent
Filters
- Channel
- Status
- Agent
- Team
- Priority
- Intent
- Sentiment
- Customer
- Order
- Date
- SLA
- AI/human
Conversation actions
- Assign
- Reassign
- Change status
- Change priority
- Tag
- Merge
- Split
- Snooze
- Close
- Reopen
- Escalate
- Add internal note
4. Conversation
The actual customer-service workspace.
Conversation view
- Full message history
- Customer identity
- Channel
- Attachments
- Images
- Links
- Order context
- Customer context
- Previous conversations
- Internal notes
- Events
- AI actions
- Workflow events
Agent composer
- Reply
- Internal note
- Templates/macros
- Attachments
- Emoji
- Variables
- AI rewrite
- AI expand
- AI shorten
- AI translate
- Tone adjustment
- Suggested response
Conversation intelligence
- Summary
- Intent
- Sentiment
- Priority
- Customer value
- Suggested next action
- Suggested response
- Relevant knowledge
- Relevant orders
- Relevant previous conversations
5. Customer Profile
A good customer-service system should give the agent the whole customer, not just the current message.
Customer profile
- Name
- Email
- Phone
- Location
- Tags
- Customer status
- Lifetime value
- Number of orders
- Last order
- Average order value
- Subscription status
- Loyalty status
Customer history
- Orders
- Conversations
- Tickets
- Refunds
- Returns
- Reviews
- Previous issues
- Previous AI interactions
- Previous human interactions
Customer timeline
Something like:
Customer
│
├── Order #1023
├── Conversation
├── Refund
├── Order #1041
├── Email
├── Conversation
└── New order
6. Ticket Management
Even if Tajeran becomes more conversation-oriented than traditional helpdesks, structured tickets are useful.
Tickets
- Create ticket
- Convert conversation → ticket
- Ticket status
- Priority
- Assignment
- Team
- Due date
- Tags
- Custom fields
- Ticket history
- Ticket relationships
Ticket lifecycle
New
 ↓
Open
 ↓
Pending
 ↓
Resolved
 ↓
Closed
With escalation/reopening paths.
7. Routing
A serious support product needs intelligent routing.
Basic routing
- Round robin
- Team routing
- Agent routing
- Channel routing
- Priority routing
Rule-based routing
- Intent
- Language
- Customer value
- Product
- Order value
- Issue type
- Sentiment
- Geography
- Business hours
AI routing
- AI determines intent
- AI determines complexity
- AI determines urgency
- AI determines required skill
- AI chooses team
- AI chooses human vs automation
8. SLA
SLA configuration
- First response SLA
- Resolution SLA
- Priority-based SLA
- Customer-based SLA
- Business-hours SLA
- Holiday calendar
SLA behavior
- Countdown
- Warning
- Breach
- Escalation
- Notifications
- Reporting
9. Macros / Templates
Templates
- Saved replies
- Variables
- Dynamic customer information
- Dynamic order information
- Conditional content
Macro actions
A macro shouldn't only send text.
It could:
Send response
+
Tag conversation
+
Assign team
+
Change status
+
Update order
This is where Tajeran can start becoming more powerful than traditional canned responses.
10. Rules & Automation
Triggers
- New conversation
- New message
- Customer reply
- Order created
- Order shipped
- Order delivered
- Refund
- Return
- Negative sentiment
- SLA approaching
- SLA breached
Conditions
- Customer
- Order
- Intent
- Sentiment
- Tags
- Channel
- Time
- Product
- Value
- Previous conversation
Actions
- Tag
- Assign
- Reply
- Escalate
- Create ticket
- Change priority
- Start workflow
- Call capability
- Update Shopify
- Notify team
- Wait
- Close
11. AI Agent
This is where Tajeran should eventually differentiate itself.
Current products already have AI agents that handle support across channels and can use brand knowledge, workflows, and actions. Gorgias
Tajeran's AI should have:
Understand
- Intent detection
- Entity extraction
- Customer identification
- Order identification
- Sentiment
- Urgency
- Language
Understand context
- Conversation history
- Customer history
- Orders
- Products
- Policies
- Previous resolutions
- Business rules
Decide
- Answer
- Ask question
- Retrieve information
- Execute action
- Start workflow
- Escalate
- Request approval
Act
- Shopify action
- Send message
- Create ticket
- Assign
- Tag
- Refund
- Cancel
- Update
- Notify
Verify
This is particularly important for your vision.
After an action:
AI intended action
       ↓
Action executed
       ↓
Verify result
       ↓
Did business outcome happen?
       ↓
Yes → continue
No → repair/escalate
That is much more interesting than simply generating text.
12. Human-in-the-Loop
Approval
- Request approval
- Approval queue
- Approve
- Reject
- Modify
- Expire
- Escalate
Human handoff
- AI → human
- Human → AI
- Preserve context
- AI summary
- Reason for escalation
- Recommended next action
Control
Merchant should be able to decide:
AI can answer
AI can recommend
AI can act
AI must ask approval
AI cannot perform
13. Knowledge Base
Knowledge sources
- FAQ
- Policies
- Website
- Help center
- Documents
- PDFs
- Product catalog
- Shopify data
- Custom text
- URLs
Knowledge management
- Create
- Edit
- Delete
- Version
- Publish
- Unpublish
- Categories
- Sources
- Permissions
AI retrieval
- Semantic search
- Keyword search
- Context retrieval
- Source relevance
- Citation/reference
- Knowledge freshness
14. Self-Service / Help Center
Customer-facing
- Help center
- Search
- FAQ
- Articles
- Contact form
- AI answer
- Order lookup
- Return request
- Human escalation
AI self-service
Customer:
Where is my order?

Tajeran:
Identify customer
↓
Find order
↓
Find fulfillment
↓
Find tracking
↓
Explain status
If resolved → no human ticket required.
This type of automated deflection is already a major part of modern ecommerce support products. Gorgias Help Center
15. Chat / Website Widget
Widget
- Chat
- Branding
- Logo
- Colors
- Greeting
- Business hours
- AI/human handoff
- File upload
- Customer identification
Chat flows
- Order status
- Returns
- Refunds
- Product questions
- Contact support
- Human handoff
Proactive
- Page-based triggers
- Cart behavior
- Checkout behavior
- Customer segmentation
16. Email Support
- Connect support email
- Receive emails
- Send emails
- Threading
- Attachments
- Signatures
- Templates
- AI replies
- AI summaries
- Routing
- Auto-response
- Email-to-ticket
17. Social / Messaging Channels
Potentially:
- Instagram
- Facebook Messenger
- WhatsApp
- SMS
- Other messaging channels
The current ecommerce leaders increasingly provide unified support across email, chat, social, SMS and voice. Gorgias
These don't all need to be V1.
But they belong on the product map.
18. Voice
Later:
- Phone support
- Incoming calls
- AI voice agent
- Human handoff
- Call transcription
- Call summary
- Customer context
- Call recording
- Voice analytics
19. Returns & Refunds
For Shopify ecommerce, this deserves its own feature group.
Returns
- Return request
- Return eligibility
- Return policy
- Return label
- Return status
- Exchange
- Return tracking
Refunds
- Refund eligibility
- Full refund
- Partial refund
- Refund approval
- Refund execution
- Refund verification
AI
Customer request
↓
Find order
↓
Check policy
↓
Check eligibility
↓
Determine action
↓
Approval?
↓
Execute
↓
Verify
↓
Inform customer
20. Order Management
- Order lookup
- Order status
- Tracking
- Cancel
- Edit
- Address change
- Product change
- Quantity change
- Discount
- Refund
- Duplicate
- Fulfillment information
- Delivery issue
21. Pre-Sales Customer Service
This is becoming increasingly important in ecommerce.
Not just:
"Where is my order?"

But:
"Which size should I buy?"

"Will this work for my skin type?"

"Which product is better?"

Features:
- Product recommendations
- Product comparison
- Product questions
- Inventory lookup
- Shipping questions
- Discount assistance
- Cart assistance
- Upsell
- Cross-sell
- Checkout assistance
Modern ecommerce platforms increasingly position AI support as covering both pre-sale and post-sale conversations. Gorgias
22. Notifications
Internal
- New ticket
- Assignment
- Mention
- SLA warning
- SLA breach
- Approval request
- AI failure
- Escalation
Customer
- Ticket received
- Status update
- Refund
- Shipping update
- Human response
- Resolution
23. Analytics
Support metrics
- Ticket volume
- Conversation volume
- Response time
- First response time
- Resolution time
- Backlog
- SLA
- Agent workload
AI metrics
- AI resolution rate
- AI escalation rate
- AI failure rate
- AI action success
- AI accuracy
- Human takeover
- Automation rate
Customer metrics
- CSAT
- Customer sentiment
- Repeat contacts
- Resolution quality
Business metrics
- Revenue influenced
- Conversion
- Refund rate
- Retention
- Customer value
24. AI Quality / QA
This should be a major Tajeran area.
Automatic evaluation
- Correctness
- Policy compliance
- Tone
- Resolution
- Hallucination
- Action correctness
- Customer satisfaction
Conversation QA
- Score conversations
- Detect bad responses
- Detect missed opportunities
- Detect policy violations
- Detect unnecessary escalation
Human feedback
- 👍 / 👎
- Correct / incorrect
- Edit AI response
- Report issue
- Explain failure
25. Customer Feedback
- CSAT
- Satisfaction survey
- Feedback
- Thumbs up/down
- Resolution feedback
- AI feedback
- Agent feedback
26. Voice of Customer
Turn support conversations into business intelligence.
For example:
500 conversations
       ↓
AI analyzes
       ↓
"Shipping delays increased 38%"
       ↓
"Product X generates 3× more complaints"
       ↓
"Customers repeatedly ask about sizing"
Features:
- Topic detection
- Trend detection
- Complaint detection
- Product issues
- Shipping issues
- Policy confusion
- Emerging problems
- Customer requests
- Sentiment trends
Gorgias, for example, currently exposes "Voice of Customer," AutoQA and trend analysis as product capabilities. Gorgias
27. Workflow Builder
Now your existing workflow work fits here.
Builder
- Visual workflow
- Trigger
- Nodes
- Conditions
- Variables
- Branches
- Actions
- AI steps
- Human approval
- Wait
- Events
- Sub-workflows
Execution
- Run
- Pause
- Resume
- Retry
- Cancel
- History
- Logs
- Timeline
Versioning
- Draft
- Published
- Version
- Rollback
- Test
28. AI / Capability System
This is more Tajeran's internal product engine than a conventional helpdesk feature.
Your capabilities could include:
Find customer
Find order
Find product
Check policy
Search knowledge
Analyze sentiment
Classify intent
Generate response
Send response
Refund order
Cancel order
Create ticket
Assign ticket
Request approval
And eventually:
Planner
Resolver
Executor
Verifier
Repair
Outcome
Learning
This is where your existing architecture becomes strategically relevant.
29. Integrations
Beyond Shopify:
- Shipping providers
- Returns platforms
- Subscription platforms
- Loyalty
- CRM
- Marketing
- Reviews
- Payment
- Analytics
- Slack
- Email
- Calendar
- External APIs
- Webhooks
- API
Modern ecommerce helpdesks are increasingly ecosystems rather than isolated helpdesks. Gorgias, for example, currently advertises 100+ integrations. Shopify App Store
30. Security & Permissions
- Roles
- Permissions
- Team access
- Store access
- Action permissions
- AI permissions
- Approval permissions
- Audit logs
- MFA
- SSO
- API keys
- Webhook security
- Tenant isolation
- Data encryption
31. Admin / Configuration
- Business hours
- Holidays
- Brands
- Stores
- Teams
- Agents
- Tags
- Custom fields
- Policies
- AI settings
- Automation settings
- Notification settings
- Channel settings
32. Billing & Usage
- Subscription
- Plans
- Trial
- Usage
- AI usage
- Conversation usage
- Agent usage
- Limits
- Quotas
- Billing portal
- Invoices
- Upgrade
- Downgrade
- Cancellation
33. Developer / Platform
Eventually:
- Public API
- Webhooks
- API keys
- OAuth apps
- Custom integrations
- Custom capabilities
- Workflow API
- External actions
- Developer logs
The important part: don't build all of this
This list is the universe of what a very good customer-service platform can contain.
It is not a V1 checklist.
I would divide it into four levels after we've finished the feature inventory:
                    TAJERAN
                       │
        ┌──────────────┼──────────────┐
        │              │              │
       V1           V1.5           FUTURE
        │              │              │
   Must ship      Important       Expansion
        │
        ▼
First paying
customers
And I would make another distinction:
Commodity customer-service features
These are things users simply expect:
- Inbox
- Email
- Tickets
- Assignment
- Tags
- Search
- Macros
- Teams
- SLA
- Customer profile
- Shopify data
- Analytics
- Knowledge base
We should not try to reinvent these unnecessarily.
Tajeran differentiation
This is where I'd put disproportionate design effort:
UNDERSTAND
     ↓
CONTEXT
     ↓
REASON
     ↓
DECIDE
     ↓
ACT
     ↓
VERIFY
     ↓
REPAIR
     ↓
LEARN
     ↓
OUTCOME
For example, instead of:
"AI generated a reply."

Tajeran's fundamental unit could eventually be:
"Tajeran resolved the customer's problem."

That means the system can know:
Customer asked for refund
        ↓
Order found
        ↓
Policy checked
        ↓
Eligible
        ↓
Refund required approval
        ↓
Human approved
        ↓
Refund executed
        ↓
Shopify confirmed refund
        ↓
Customer notified
        ↓
Conversation resolved
        ↓
Outcome = successful
That is the feature map I would build around.
And importantly, we should not yet decide implementation or Temporal vs your runtime vs workflow builder. First we finish the product inventory. Then we can go through this list with you and mark each item:
Must have / Nice to have / Later / Not Tajeran
and only after that turn every Must have into your detailed FEATURE → USER FLOW → DOMAIN → SYSTEM → FAILURES → DONE → DEPLOY specification.