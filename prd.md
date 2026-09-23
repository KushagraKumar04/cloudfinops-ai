# CloudFinOps AI — Product Requirements Document (PRD)

## 1. Product Overview

**Product name:** CloudFinOps AI  
**Working tagline:** Autonomous cloud cost and architecture optimizer with human approval.

CloudFinOps AI is an AI-assisted FinOps platform that connects to AWS and Azure, ingests billing, usage, inventory, and configuration data, explains cost drivers, detects waste and under-utilization, forecasts spend, evaluates optimization opportunities, and creates evidence-backed optimization plans.

The system is intentionally **approval-gated**. AI agents may investigate, calculate, simulate, and propose changes, but infrastructure-changing actions require deterministic policy checks and explicit human approval.

### Core outcome

Turn:

> “Our cloud bill increased by 18%. Why?”

into an evidence-backed answer such as:

- what changed,
- which services/resources caused the change,
- whether the change is usage-, price-, architecture-, or configuration-driven,
- what can be optimized,
- estimated savings,
- operational/security risks,
- confidence and evidence,
- and which actions are safe to approve.

---

## 2. Problem Statement

Cloud cost data is fragmented across billing systems, resource inventories, monitoring systems, tags, regions, accounts/subscriptions, and configuration APIs.

Traditional dashboards answer **what was spent**, but often do not answer:

1. Why did spend change?
2. Which resources caused it?
3. Is the resource actually needed?
4. Is it oversized?
5. Is there a cheaper equivalent architecture?
6. What would happen if we changed it?
7. How much would we save?
8. What risk would the change introduce?
9. Can the recommendation be automatically executed safely?

CloudFinOps AI addresses this by combining:

- cloud APIs,
- data engineering,
- deterministic FinOps rules,
- LLM reasoning,
- forecasting,
- optimization algorithms,
- policy-as-code,
- and approval-controlled execution.

---

## 3. Goals

### P0 goals

- Support AWS and Azure as first-class cloud providers.
- Ingest billing/cost and resource inventory data.
- Normalize provider-specific data into a common cost/resource model.
- Detect common waste patterns.
- Explain cost anomalies with evidence.
- Forecast future spend.
- Generate optimization recommendations.
- Estimate savings using deterministic calculations.
- Assign risk and confidence.
- Provide an approval workflow.
- Maintain a complete audit trail.
- Provide a conversational AI interface for FinOps questions.
- Never allow an LLM to directly execute infrastructure mutations.

### P1 goals

- Multi-account / multi-subscription support.
- Kubernetes cost analysis.
- Commitment optimization.
- Storage lifecycle recommendations.
- Database rightsizing.
- Budget and policy monitoring.
- What-if scenario simulation.
- Automated execution of explicitly approved low-risk actions.

### P2 goals

- Cross-cloud optimization.
- Carbon-aware optimization.
- Advanced architecture redesign suggestions.
- Continuous optimization loops.
- Organization-wide policy learning from historical approvals.

---

## 4. Non-Goals

The initial version will not:

- replace a full cloud provider console,
- autonomously delete production infrastructure,
- autonomously modify networking/security controls,
- guarantee exact future savings,
- make architecture changes without approval,
- treat LLM output as authoritative financial truth,
- use an LLM to calculate financial totals when deterministic source data is available.

---

## 5. Target Users

### FinOps Engineer

Needs:

- spend visibility,
- anomaly explanations,
- savings opportunities,
- commitment recommendations,
- reporting.

### Cloud/Platform Engineer

Needs:

- resource utilization analysis,
- rightsizing,
- idle resource detection,
- architecture recommendations,
- safe remediation.

### Engineering Manager

Needs:

- team/application cost,
- trends,
- budgets,
- optimization progress,
- business impact.

### Cloud Architect

Needs:

- architecture-level cost analysis,
- what-if comparisons,
- cross-service optimization.

### Security/Compliance Reviewer

Needs:

- approval controls,
- policy violations,
- audit logs,
- execution history.

---

## 6. Product Principles

1. **Evidence before explanation**
2. **Deterministic calculations before LLM calculations**
3. **Read-only by default**
4. **Human approval before mutation**
5. **Least-privilege cloud access**
6. **Every recommendation must have evidence**
7. **Every action must be auditable**
8. **Confidence must be explicit**
9. **Provider abstraction must not hide provider-specific details**
10. **LLM proposes; policy engine decides whether it may proceed**

---

# 7. Core User Experience

## 7.1 Dashboard

Show:

- current monthly spend,
- month-over-month change,
- projected month-end spend,
- budget utilization,
- identified waste,
- estimated savings,
- realized savings,
- anomaly count,
- high-risk recommendations,
- cloud/provider breakdown,
- service breakdown,
- account/subscription breakdown.

---

## 7.2 Ask FinOps

Example questions:

> Why did AWS spend increase this month?

> Which resources are underutilized?

> Show me our top 10 savings opportunities.

> What can we safely optimize without affecting production?

> Why is Azure storage cost increasing?

> If we reduce compute spend by 20%, what actions are available?

The system should respond with:

- concise answer,
- evidence,
- calculations,
- affected resources,
- recommendation cards,
- confidence,
- risk,
- links to detailed analysis.

---

# 8. AI Agent System

The initial architecture uses specialized agents rather than one unrestricted autonomous agent.

## 8.1 Orchestrator Agent

Responsibilities:

- interpret user intent,
- create an investigation plan,
- invoke specialist agents,
- aggregate results,
- request clarification when necessary,
- produce a final evidence-backed response.

It must not execute cloud mutations.

## 8.2 Cost Analyst Agent

Analyzes:

- service costs,
- account/subscription costs,
- region costs,
- tags,
- daily/monthly trends,
- cost anomalies,
- usage-vs-cost relationships.

## 8.3 Resource Analyst Agent

Analyzes:

- resource inventory,
- utilization,
- idle resources,
- oversized resources,
- unattached resources,
- age/configuration.

## 8.4 Architecture Analyst Agent

Analyzes:

- architecture patterns,
- service relationships,
- workload characteristics,
- cheaper alternatives,
- architecture-level trade-offs.

## 8.5 Forecast Agent

Produces:

- month-end forecast,
- 7/30/90-day projections,
- budget breach estimates,
- scenario forecasts.

The numerical forecast should come from a statistical/ML component; the LLM explains it.

## 8.6 Optimization Agent

Creates:

- optimization candidates,
- savings estimates,
- risk classification,
- prerequisites,
- implementation plans.

## 8.7 Policy/Risk Agent

Evaluates:

- environment,
- resource criticality,
- production status,
- availability impact,
- security impact,
- compliance requirements,
- organizational policy.

This component should primarily use deterministic policy rules.

## 8.8 Execution Agent

Executes only approved actions through a tightly controlled tool layer.

Allowed examples:

- stop a known non-production idle resource,
- resize an explicitly approved instance,
- delete an explicitly approved unattached disk.

Every action requires:

1. recommendation ID,
2. approval,
3. policy check,
4. action allowlist,
5. dry-run where supported,
6. execution,
7. verification,
8. audit event.

---

# 9. Recommendation Types

## Compute

- VM/EC2 rightsizing
- idle compute
- stopped resources still incurring costs
- scheduling non-production workloads
- Savings Plans / Reserved Instances
- Spot candidate detection

## Storage

- unattached disks
- old snapshots
- unused volumes
- object storage lifecycle opportunities
- tiering opportunities

## Network

- unused public IPs
- expensive data transfer patterns
- NAT gateway optimization opportunities
- cross-region transfer analysis

## Database

- oversized databases
- idle databases
- storage optimization
- reserved capacity opportunities

## Kubernetes

- CPU/memory over-requesting
- underutilized nodes
- workload scheduling opportunities
- cluster idle capacity

---

# 10. Savings Calculation

Savings estimates must be deterministic.

Each recommendation should contain:

```json
{
  "current_monthly_cost": 580,
  "estimated_monthly_cost": 210,
  "estimated_monthly_savings": 370,
  "savings_confidence": 0.86,
  "calculation_basis": [
    "30-day average utilization",
    "current region",
    "target instance price"
  ]
}
```

The LLM may explain the calculation but must not invent the numeric values.

---

# 11. Risk Model

Recommendations use:

- LOW
- MEDIUM
- HIGH
- BLOCKED

Risk is based on deterministic signals.

### LOW

Examples:

- unused public IP,
- unattached volume,
- old snapshot beyond policy threshold.

### MEDIUM

Examples:

- rightsizing non-production compute,
- changing storage tier,
- scheduling development resources.

### HIGH

Examples:

- production compute resize,
- database changes,
- network architecture changes.

### BLOCKED

Examples:

- policy violation,
- protected resource,
- missing approval,
- insufficient evidence,
- insufficient permissions.

---

# 12. Approval Workflow

```text
Recommendation
      ↓
Evidence validation
      ↓
Savings calculation
      ↓
Risk assessment
      ↓
Policy evaluation
      ↓
Human approval
      ↓
Execution plan
      ↓
Dry run
      ↓
Apply
      ↓
Verify
      ↓
Audit
```

Approval should support:

- approve,
- reject,
- request changes,
- defer.

---

# 13. Data Requirements

## Billing data

AWS:

- Cost and Usage Reports / Cost Explorer data
- service
- account
- region
- usage type
- operation
- tags
- date
- amount
- currency

Azure:

- Cost Management data
- subscription
- resource group
- resource
- meter
- service
- region
- date
- amount
- currency

## Resource data

Common fields:

- provider
- account/subscription
- resource ID
- resource type
- service
- region
- environment
- application
- owner
- tags
- status
- creation time
- configuration
- utilization metrics

## Metrics

Where available:

- CPU
- memory
- network
- disk I/O
- request count
- latency
- database connections
- storage utilization

---

# 14. Canonical Data Model

Provider data is normalized into:

### CloudAccount

- id
- provider
- account_identifier
- name
- environment

### Resource

- id
- provider
- account_id
- resource_id
- resource_type
- service
- region
- tags
- status

### CostRecord

- timestamp
- provider
- account_id
- resource_id
- service
- cost
- currency
- usage_quantity
- usage_unit

### MetricRecord

- timestamp
- resource_id
- metric_name
- metric_value
- unit

### Recommendation

- id
- resource_id
- type
- title
- evidence
- current_cost
- estimated_cost
- estimated_savings
- confidence
- risk
- status
- created_at

### Approval

- id
- recommendation_id
- approver
- decision
- timestamp
- reason

### Execution

- id
- recommendation_id
- action
- status
- started_at
- completed_at
- result
- rollback_reference

---

# 15. MVP Scope

The MVP should focus on **AWS + Azure read-only optimization intelligence**.

### MVP features

1. Cloud account connection
2. Billing ingestion
3. Resource inventory ingestion
4. Metrics ingestion
5. Normalized data layer
6. Cost dashboard
7. Cost anomaly detection
8. Idle resource detection
9. Compute rightsizing
10. Storage waste detection
11. Savings calculation
12. AI investigation
13. Recommendation cards
14. Risk classification
15. Approval workflow
16. Audit logging
17. Read-only cloud integration

Do not begin with autonomous execution.

---

# 16. Recommended Tech Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- TanStack Query

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- Redis

### Data

- PostgreSQL for application data
- Parquet for analytical snapshots
- DuckDB for local/analytical workloads
- Object storage for raw billing files

### AI

Provider-agnostic LLM interface:

- Azure OpenAI
- OpenAI-compatible APIs
- Gemini/other providers later

Use structured tool calls and strict JSON schemas.

### Cloud SDKs

AWS:

- boto3

Azure:

- Azure SDKs
- Azure Resource Graph
- Azure Cost Management APIs

### Observability

- OpenTelemetry
- structured logs
- Prometheus/Grafana later

### Infrastructure

- Docker
- Docker Compose for local development
- Terraform later
- GitHub Actions

---

# 17. API Requirements

Example endpoints:

```text
POST /api/v1/cloud/accounts
GET  /api/v1/cloud/accounts
POST /api/v1/cloud/accounts/{id}/sync

GET  /api/v1/costs/summary
GET  /api/v1/costs/trends
GET  /api/v1/costs/anomalies

GET  /api/v1/resources
GET  /api/v1/resources/{id}

GET  /api/v1/recommendations
GET  /api/v1/recommendations/{id}

POST /api/v1/recommendations/{id}/approve
POST /api/v1/recommendations/{id}/reject

POST /api/v1/chat
GET  /api/v1/chat/runs/{id}

GET  /api/v1/audit
```

---

# 18. Security Requirements

- Read-only cloud roles by default.
- Separate execution credentials.
- Short-lived credentials where supported.
- No cloud secrets in source code.
- Secrets stored in environment/secret manager.
- Encrypt sensitive data at rest.
- TLS in transit.
- Tenant isolation.
- RBAC.
- Audit every privileged operation.
- Never send unnecessary cloud identifiers or secrets to the LLM.
- Tool allowlists.
- Explicit action schemas.
- Approval required for mutation.
- Idempotency keys for execution.
- Execution timeout and rollback strategy.

---

# 19. LLM Guardrails

The LLM must never:

- invent resource data,
- invent pricing,
- invent utilization,
- execute arbitrary cloud CLI commands,
- bypass approval,
- alter policy,
- claim an action succeeded without tool confirmation.

The LLM receives structured data/tools and returns structured outputs.

---

# 20. Success Metrics

### Product

- percentage of recommendations with evidence,
- recommendation acceptance rate,
- realized savings,
- false-positive rate,
- time-to-explanation.

### AI

- grounded answer rate,
- tool-call correctness,
- structured-output validity,
- hallucination rate,
- recommendation reproducibility.

### Engineering

- ingestion success rate,
- API latency,
- execution failure rate,
- audit completeness.

---

# 21. Development Roadmap

## Phase 0 — Foundation

- monorepo
- Docker
- FastAPI
- React
- PostgreSQL
- migrations
- authentication skeleton
- CI

## Phase 1 — Cloud ingestion

- AWS connection
- Azure connection
- billing ingestion
- resource inventory
- normalized schema

## Phase 2 — FinOps engine

- cost aggregation
- anomaly detection
- idle detection
- rightsizing rules
- savings calculator

## Phase 3 — AI

- tool layer
- orchestrator
- cost analyst
- resource analyst
- recommendation explanation
- conversational UI

## Phase 4 — Governance

- risk engine
- policy engine
- approvals
- audit

## Phase 5 — Execution

- dry-run
- low-risk action execution
- verification
- rollback support

---

# 22. Definition of Done for MVP

The MVP is complete when a developer can:

1. connect a test AWS account,
2. connect a test Azure subscription,
3. ingest cost data,
4. ingest resource inventory,
5. view normalized cost data,
6. ask why costs changed,
7. receive evidence-backed explanations,
8. identify idle/oversized resources,
9. see deterministic savings estimates,
10. review risk,
11. approve/reject recommendations,
12. see every decision in the audit log,
13. run the entire stack locally with Docker Compose.

---

# 23. Vibe-Coding Rules

The project should be developed in small vertical slices.

For every feature:

1. define the contract,
2. define data model,
3. implement backend,
4. add tests,
5. implement frontend,
6. connect API,
7. add observability,
8. update documentation.

Do not ask the coding agent to “build the whole app” in one prompt.

Use tasks such as:

> Implement the CostRecord SQLAlchemy model, migration, Pydantic schemas, repository, service, and unit tests. Do not modify unrelated files.

Then:

> Implement GET /api/v1/costs/summary using the existing CostRecord repository. Add integration tests.

Then:

> Build the cost summary dashboard against the existing API. Do not change backend contracts.

This keeps AI-generated changes reviewable.

---

# 24. First Coding Milestone

Start with:

```text
Repository
├── apps/
│   ├── api/
│   └── web/
├── services/
│   ├── ingestion/
│   ├── finops/
│   ├── ai/
│   ├── policy/
│   └── execution/
├── packages/
│   ├── schemas/
│   └── cloud-adapters/
├── infra/
├── tests/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

First deliverable:

**Local development environment + PostgreSQL + FastAPI health endpoint + React shell + database migration + CI.**

Only after this is stable should cloud integrations begin.
