# CloudFinOps AI — System Architecture

## 1. Architecture Summary

CloudFinOps AI is a modular, event-driven FinOps platform with five major planes:

```text
┌──────────────────────────────────────────────────────────────────┐
│                         EXPERIENCE PLANE                          │
│ React Web App │ FinOps Chat │ Dashboards │ Approvals │ Reports  │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTPS / SSE
┌──────────────────────────────▼───────────────────────────────────┐
│                          API / APP PLANE                          │
│ FastAPI │ Auth │ RBAC │ Recommendation API │ Chat API │ Audit   │
└───────────────┬──────────────────────┬───────────────────────────┘
                │                      │
        ┌───────▼────────┐     ┌───────▼────────────────┐
        │  FinOps Engine │     │      AI Agent Plane     │
        │ Rules/Math     │◄────│ Orchestrator + Agents  │
        │ Forecasting    │     │ Tool Gateway            │
        └───────┬────────┘     └──────────┬─────────────┘
                │                         │
┌───────────────▼─────────────────────────▼────────────────────────┐
│                        DATA / DOMAIN PLANE                         │
│ PostgreSQL │ DuckDB │ Parquet │ Redis │ Raw Object Storage       │
└───────────────────────────────┬───────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────┐
│                        CLOUD CONNECTOR PLANE                       │
│ AWS Adapter │ Azure Adapter │ Billing │ Inventory │ Metrics      │
└──────────────────────┬───────────────────────┬────────────────────┘
                       │                       │
                  ┌────▼────┐             ┌────▼────┐
                  │   AWS   │             │  Azure  │
                  └─────────┘             └─────────┘
```

---

# 2. Architectural Principles

## 2.1 Separate reasoning from execution

The AI layer may reason about actions.

It must not directly receive unrestricted cloud credentials.

All cloud operations pass through:

```text
Agent
  ↓
Tool Gateway
  ↓
Schema Validation
  ↓
Policy Engine
  ↓
Approval
  ↓
Execution Adapter
  ↓
Cloud API
```

## 2.2 Separate facts from interpretation

Facts:

- cost,
- usage,
- utilization,
- resource state,
- price,
- timestamps.

Interpretation:

- “this appears oversized,”
- “this is probably waste,”
- “this architecture may be cheaper.”

The first category must originate from deterministic systems.

---

# 3. Repository Architecture

Recommended monorepo:

```text
cloudfinops-ai/
│
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── dependencies.py
│   │   │   ├── api/
│   │   │   ├── services/
│   │   │   ├── repositories/
│   │   │   └── models/
│   │   └── tests/
│   │
│   └── web/
│       ├── src/
│       │   ├── components/
│       │   ├── features/
│       │   ├── pages/
│       │   ├── api/
│       │   ├── hooks/
│       │   └── types/
│       └── tests/
│
├── packages/
│   ├── schemas/
│   ├── cloud-adapters/
│   ├── finops-rules/
│   └── ai-tools/
│
├── services/
│   ├── ingestion/
│   ├── forecasting/
│   └── workers/
│
├── infra/
│   ├── docker/
│   ├── terraform/
│   └── policies/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/
├── scripts/
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

---

# 4. Service Boundaries

## API Service

Responsible for:

- HTTP APIs,
- authentication,
- authorization,
- request validation,
- chat sessions,
- recommendation access,
- approval APIs.

It should not contain long-running cloud ingestion jobs.

## Ingestion Workers

Responsible for:

- billing synchronization,
- inventory synchronization,
- metric synchronization,
- normalization,
- retries.

Use background workers rather than blocking FastAPI requests.

## FinOps Engine

Responsible for deterministic:

- cost calculations,
- anomaly detection,
- rightsizing rules,
- waste detection,
- savings calculations,
- risk signals.

## AI Service

Responsible for:

- LLM calls,
- agent orchestration,
- tool selection,
- structured responses,
- conversation state.

## Execution Service

Responsible for:

- approved mutations,
- dry runs,
- cloud API calls,
- verification,
- rollback references,
- execution audit.

Keep this service isolated from general AI code.

---

# 5. Data Architecture

## Raw Layer

Store provider responses/files unchanged where practical.

```text
raw/
  aws/
    billing/
    inventory/
    metrics/
  azure/
    billing/
    inventory/
    metrics/
```

Use object storage in production.

## Normalized Layer

PostgreSQL stores operational entities.

Core tables:

```text
cloud_accounts
resources
resource_relationships
cost_records
usage_records
metric_records
price_records
budgets
anomalies
recommendations
recommendation_evidence
approvals
executions
audit_events
chat_sessions
agent_runs
tool_calls
```

## Analytical Layer

Parquet + DuckDB can be used for:

- large billing datasets,
- exploratory analysis,
- historical comparisons,
- offline evaluation.

PostgreSQL remains the primary application database.

---

# 6. Cloud Adapter Interface

Define a common interface rather than spreading boto3/Azure SDK calls across the application.

Conceptual interface:

```python
class CloudProviderAdapter(Protocol):

    def get_accounts(self): ...

    def get_resources(self, account_id): ...

    def get_costs(self, start, end, account_id): ...

    def get_metrics(self, resource_ids, start, end): ...

    def get_prices(self, resource_type, region): ...

    def validate_connection(self): ...

    def execute_action(self, action): ...
```

Provider implementations:

```text
AWSAdapter
AzureAdapter
```

Later:

```text
GCPAdapter
```

---

# 7. AWS Integration

Use least-privilege IAM roles.

Read-only MVP permissions should cover only required:

- Cost Explorer / billing data,
- EC2,
- EBS,
- RDS,
- S3,
- CloudWatch,
- Elastic IP,
- relevant tagging APIs.

Do not request administrator access.

For execution, use a separate role.

---

# 8. Azure Integration

Use:

- Azure Resource Graph,
- Cost Management,
- Azure Monitor,
- resource management APIs.

Separate read-only and execution permissions.

---

# 9. Data Ingestion Pipeline

```text
Scheduler
   ↓
Connector
   ↓
Provider API
   ↓
Raw Response
   ↓
Validation
   ↓
Normalization
   ↓
Deduplication
   ↓
PostgreSQL / Object Storage
   ↓
FinOps Rules
   ↓
Recommendations
```

Every ingestion job should have:

- job ID,
- provider,
- account/subscription,
- start/end,
- status,
- records fetched,
- records inserted,
- error,
- duration.

Use idempotent ingestion.

---

# 10. Cost Analysis Pipeline

```text
Cost Records
     ↓
Daily Aggregation
     ↓
Service/Account/Resource Dimensions
     ↓
Historical Baseline
     ↓
Anomaly Detection
     ↓
Root-Cause Analysis
     ↓
Recommendation Engine
```

Anomaly detection should initially use simple deterministic/statistical methods:

- moving average,
- rolling standard deviation,
- percentage change,
- seasonal baseline.

Avoid making an LLM responsible for anomaly mathematics.

---

# 11. Rightsizing Engine

Example:

```text
Resource
   ↓
30-day utilization
   ↓
CPU / memory / network
   ↓
Current instance family
   ↓
Candidate families
   ↓
Price lookup
   ↓
Constraint checks
   ↓
Savings calculation
   ↓
Recommendation
```

Candidate selection should consider:

- region,
- architecture,
- CPU,
- memory,
- network,
- workload constraints,
- operating system,
- current utilization,
- production/non-production.

---

# 12. Recommendation Engine

Use a deterministic recommendation pipeline:

```text
Resource facts
     ↓
Rule evaluation
     ↓
Candidate optimization
     ↓
Savings calculation
     ↓
Risk calculation
     ↓
Evidence generation
     ↓
Recommendation record
```

Example rule:

```text
IF
  resource.status = running
  AND average_cpu_30d < 15%
  AND environment != production
  AND sufficient_metric_coverage = true

THEN
  create rightsizing candidate
```

The exact thresholds must be configuration, not hard-coded into prompts.

---

# 13. AI Architecture

The AI system uses a supervisor pattern.

```text
                    User
                     │
                     ▼
             ┌──────────────┐
             │ Orchestrator │
             └──────┬───────┘
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
 Cost Analyst   Resource     Architecture
               Analyst        Analyst
       │            │            │
       └────────────┼────────────┘
                    ▼
              Forecast Agent
                    │
                    ▼
            Optimization Agent
                    │
                    ▼
              Policy Engine
                    │
                    ▼
             Recommendation
```

The orchestrator controls investigation flow.

---

# 14. Agent Tools

Tools should be narrow and typed.

Examples:

```text
get_cost_summary
get_cost_breakdown
get_cost_trend
get_anomalies
get_resource
get_resource_metrics
get_resource_cost
find_idle_resources
find_rightsizing_candidates
calculate_savings
forecast_spend
get_architecture_context
create_recommendation
check_policy
request_approval
```

Avoid generic tools such as:

```text
run_any_aws_command
run_any_azure_command
execute_shell
```

---

# 15. Tool Gateway

The Tool Gateway is a security boundary.

```text
LLM
 ↓
Tool request
 ↓
Pydantic schema
 ↓
Authentication
 ↓
Authorization
 ↓
Input validation
 ↓
Policy
 ↓
Tool execution
 ↓
Structured result
```

Tool calls must be logged.

---

# 16. LLM Context Strategy

Do not dump the entire cloud account into the prompt.

Use retrieval:

```text
User Question
   ↓
Intent
   ↓
Relevant tools
   ↓
Minimal structured data
   ↓
LLM
```

For example, “Why did compute cost increase?” should retrieve only:

- relevant date range,
- compute service costs,
- changed resources,
- utilization,
- pricing changes,
- account/region context.

---

# 17. Structured LLM Output

Use a schema similar to:

```json
{
  "answer": "string",
  "findings": [],
  "evidence": [],
  "recommendations": [],
  "confidence": 0.0,
  "requires_human_review": true
}
```

Validate every response.

If validation fails:

1. retry with constrained output,
2. otherwise return a safe error.

---

# 18. Policy Engine

Policies should be code/configuration, not natural-language instructions alone.

Example:

```yaml
production:
  allow_auto_execution: false

database:
  require_approval: true

network:
  require_security_review: true

delete_resource:
  require_approval: true

max_monthly_savings_claim:
  require_evidence: true
```

Policy engine result:

```json
{
  "allowed": false,
  "risk": "HIGH",
  "reasons": [
    "Production resource",
    "Database resource",
    "Explicit approval required"
  ]
}
```

---

# 19. Execution Architecture

Execution is deliberately isolated:

```text
Approved Recommendation
          ↓
Execution Service
          ↓
Policy Re-check
          ↓
Precondition Check
          ↓
Dry Run
          ↓
Cloud API
          ↓
Verification
          ↓
Success / Failure
          ↓
Audit Event
```

The policy must be evaluated again immediately before execution because resource state may have changed.

---

# 20. Idempotency

Every execution request receives an idempotency key.

Example:

```text
execution:{recommendation_id}:{action_hash}
```

If the same request is submitted twice, it must not blindly perform the mutation twice.

---

# 21. Rollback

Every executable action should define:

```text
action
preconditions
rollback_action
verification
timeout
```

Some cloud actions are not naturally reversible.

For irreversible actions:

- require stronger approval,
- display warning,
- require explicit confirmation,
- record exact resource state before execution.

---

# 22. Forecasting Architecture

Initial forecasting:

- historical daily spend,
- rolling average,
- trend,
- seasonality where enough history exists.

Later:

- Prophet-style models,
- gradient boosting,
- time-series models.

Architecture:

```text
Historical Costs
      ↓
Feature Engineering
      ↓
Forecast Model
      ↓
Prediction
      ↓
Confidence Interval
      ↓
LLM Explanation
```

The LLM should explain the forecast, not generate the numeric forecast.

---

# 23. Observability

Use structured logs with:

```text
request_id
tenant_id
user_id
agent_run_id
tool_call_id
provider
account_id
recommendation_id
execution_id
duration_ms
status
```

Metrics:

- API latency,
- ingestion latency,
- ingestion failures,
- agent latency,
- token usage,
- tool failures,
- recommendation generation count,
- execution success rate.

---

# 24. Security Architecture

```text
User
 ↓
Authentication
 ↓
RBAC
 ↓
API
 ↓
Service authorization
 ↓
Tool Gateway
 ↓
Policy Engine
 ↓
Cloud role
```

Never:

```text
User → LLM → AWS Administrator
```

Secrets:

- local: `.env`
- production: cloud secret manager.

Never commit:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AZURE_CLIENT_SECRET
OPENAI_API_KEY
```

---

# 25. Multi-Tenancy

Design tenant isolation from the beginning.

Every major domain record should contain:

```text
tenant_id
```

Authorization should verify:

```text
current_user.tenant_id == resource.tenant_id
```

Do not rely solely on frontend filtering.

---

# 26. Database Relationships

Simplified:

```text
Tenant
 ├── CloudAccount
 │     ├── Resource
 │     │     ├── MetricRecord
 │     │     └── CostRecord
 │     └── CostRecord
 │
 ├── Recommendation
 │     ├── Evidence
 │     ├── Approval
 │     └── Execution
 │
 └── AuditEvent
```

---

# 27. API Layer

Recommended structure:

```text
/api/v1
  /auth
  /cloud
  /costs
  /resources
  /recommendations
  /forecasts
  /chat
  /approvals
  /executions
  /audit
```

Use:

- versioned APIs,
- Pydantic request/response models,
- consistent errors,
- pagination,
- filtering,
- sorting.

---

# 28. Frontend Architecture

Pages:

```text
/login
/dashboard
/costs
/resources
/recommendations
/recommendations/:id
/forecast
/chat
/approvals
/audit
/settings/cloud-accounts
```

Core dashboard widgets:

- Spend KPI
- Spend trend
- Cost by service
- Cost by account
- Anomalies
- Potential savings
- Recommendation feed
- Forecast
- Recent approvals

---

# 29. Recommendation Detail UI

A recommendation must show:

```text
Problem
↓
Evidence
↓
Current State
↓
Proposed State
↓
Estimated Savings
↓
Risk
↓
Confidence
↓
Potential Impact
↓
Implementation Plan
↓
Approval
```

Example:

```text
EC2 m5.4xlarge

Current monthly cost: $580
Average CPU: 12%
Observed period: 30 days

Suggested candidate: m5.2xlarge

Estimated cost: $290/month
Estimated savings: $290/month

Risk: MEDIUM
Confidence: HIGH

Reason:
30-day CPU utilization remained below threshold
with sufficient metric coverage.

[Approve] [Reject] [Defer]
```

---

# 30. Event Model

Use domain events for important transitions.

Examples:

```text
cloud.account.connected
billing.sync.completed
resource.discovered
cost.anomaly.detected
recommendation.created
recommendation.approved
recommendation.rejected
execution.started
execution.completed
execution.failed
```

This enables future event-driven workers without tightly coupling services.

---

# 31. Async Processing

Long-running tasks should be asynchronous:

- cloud sync,
- large billing imports,
- forecasting,
- recommendation generation,
- execution.

Initial implementation can use:

- FastAPI,
- Redis,
- Celery/RQ/Arq-style worker architecture.

Do not block HTTP requests for multi-minute jobs.

---

# 32. Local Development

Use Docker Compose:

```text
api
web
postgres
redis
worker
```

Optional:

```text
adminer
mailhog
```

Development command target:

```bash
docker compose up --build
```

The developer should be able to start the entire stack with one command.

---

# 33. Environment Variables

Example:

```text
APP_ENV=development
DATABASE_URL=
REDIS_URL=

LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=

AWS_REGION=
AWS_ROLE_ARN=

AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_SUBSCRIPTION_ID=

AI_TLS_VERIFY=true
```

Never hard-code credentials.

---

# 34. Testing Architecture

## Unit tests

Test:

- FinOps rules,
- savings calculations,
- risk calculations,
- policy decisions,
- data normalization.

## Integration tests

Test:

- PostgreSQL,
- cloud adapters with mocked APIs,
- ingestion,
- recommendation persistence,
- approval flow.

## Contract tests

Validate:

- API schemas,
- cloud adapter interface,
- LLM structured output.

## E2E

Test:

```text
connect cloud
→ sync data
→ detect recommendation
→ inspect recommendation
→ approve
→ execute mocked action
→ audit
```

---

# 35. AI Evaluation

Maintain a benchmark dataset of FinOps questions.

Examples:

```text
Why did compute cost increase?
Which resources are idle?
What are the top savings opportunities?
Why is storage cost increasing?
```

Evaluate:

- factual grounding,
- correct tool selection,
- calculation consistency,
- citation/evidence completeness,
- schema validity,
- refusal of unsafe actions.

Store evaluation cases in:

```text
tests/evals/
```

---

# 36. Failure Handling

Cloud APIs can fail.

LLM APIs can fail.

Workers can fail.

The system must return useful states:

```text
SYNC_FAILED
DATA_PARTIAL
ANALYSIS_UNAVAILABLE
APPROVAL_REQUIRED
EXECUTION_BLOCKED
EXECUTION_FAILED
```

Never present partial data as complete.

---

# 37. Cost Optimization of the AI System

Because the product itself is a FinOps product, its AI infrastructure must also be cost-aware.

Implement:

- model routing,
- smaller model for classification,
- larger model only for complex reasoning,
- caching,
- compact tool outputs,
- prompt versioning,
- token tracking.

Track:

```text
agent_run
input_tokens
output_tokens
model
estimated_cost
latency
```

---

# 38. Recommended Build Order

## Step 1

Create repository and local infrastructure.

## Step 2

Create database schema.

## Step 3

Create cloud adapter interfaces.

## Step 4

Build mocked AWS/Azure adapters.

## Step 5

Build ingestion pipeline.

## Step 6

Build cost APIs.

## Step 7

Build dashboard.

## Step 8

Build deterministic FinOps rules.

## Step 9

Build recommendation system.

## Step 10

Add LLM tool layer.

## Step 11

Add FinOps agents.

## Step 12

Add chat UI.

## Step 13

Add policy engine.

## Step 14

Add approvals.

## Step 15

Add mocked execution.

## Step 16

Only then connect real execution APIs.

---

# 39. Vibe-Coding Development Protocol

Use this loop:

```text
PLAN
 ↓
SMALL TASK
 ↓
IMPLEMENT
 ↓
TEST
 ↓
RUN
 ↓
INSPECT
 ↓
FIX
 ↓
COMMIT
```

Every AI coding prompt should state:

- exact files allowed to change,
- expected behavior,
- interfaces/contracts,
- tests required,
- files that must not change.

Example:

```text
Implement the CostRecord model.

Allowed files:
- apps/api/app/models/cost.py
- apps/api/tests/test_cost_model.py
- migrations/...

Requirements:
- tenant_id required
- provider required
- resource_id nullable
- cost Decimal, never float
- timestamp timezone-aware

Do not modify API routes or frontend.

Add tests for:
- valid record
- missing tenant
- invalid cost
- timezone handling.
```

---

# 40. Important Engineering Decisions

### Money

Use `Decimal`, not floating-point arithmetic.

### IDs

Use UUIDs internally.

### Time

Store timestamps in UTC.

### Currency

Store:

- amount,
- currency,
- original amount,
- original currency where conversion occurs.

Never silently convert money without recording the conversion basis.

### LLM

Never let the LLM become the source of truth for billing.

### Cloud mutations

Never let an LLM directly invoke arbitrary cloud APIs.

---

# 41. Initial MVP Architecture

For the first deployable version, keep the architecture simpler than the final diagram:

```text
React
  │
  ▼
FastAPI
  ├── Auth/RBAC
  ├── Cost API
  ├── Resource API
  ├── Recommendation API
  └── Chat API
        │
        ├── FinOps Engine
        ├── AI Orchestrator
        └── Tool Gateway
                │
        ┌───────┴────────┐
        ▼                ▼
     AWS Adapter     Azure Adapter
        │                │
        ▼                ▼
       AWS              Azure

PostgreSQL
Redis
Object Storage
Worker
```

Do not prematurely split everything into microservices.

Start modular-monolith + worker.

Split services only when scaling or security boundaries justify it.

---

# 42. First Sprint

### Task 1 — Repository

Create monorepo.

### Task 2 — Docker

Create:

- API
- frontend
- PostgreSQL
- Redis

### Task 3 — FastAPI

Implement:

```text
GET /health
GET /ready
```

### Task 4 — Database

Add:

- Alembic,
- Tenant,
- CloudAccount.

### Task 5 — Frontend

Create:

- app shell,
- sidebar,
- dashboard placeholder,
- API client.

### Task 6 — CI

Run:

```text
lint
typecheck
unit tests
build
```

on every pull request.

### Task 7 — Cloud abstraction

Create:

```text
CloudProviderAdapter
AWSAdapter
AzureAdapter
```

with mocked implementations.

Only after these tasks pass should billing ingestion begin.

---

# 43. Definition of Architectural Success

The architecture succeeds if:

- cloud providers can be added without rewriting the domain layer,
- billing calculations are deterministic,
- AI outputs are grounded in retrieved data,
- recommendations are explainable,
- every action is policy-controlled,
- every mutation is approval-gated,
- every action is auditable,
- the application can run locally,
- the MVP can scale without immediately becoming a microservice maze,
- and developers can safely extend the system using small AI-assisted coding tasks.
