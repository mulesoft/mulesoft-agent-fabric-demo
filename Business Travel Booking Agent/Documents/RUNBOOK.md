# AgentFabric Travel Booking Demo — Runbook

*Build and Adapt Multi-Agent Use Cases*

---

## Table of Contents

- [Quick Start](#quick-start)
- [Audience](#audience)
- [1. Introduction](#1-introduction)
- [2. Understand the Reference Use Case](#2-understand-the-reference-use-case)
- [3. Prerequisites](#3-prerequisites)
  - [3.1 Anypoint Platform Permissions](#31-anypoint-platform-permissions)
  - [3.2 LLM Provider Credentials](#32-llm-provider-credentials)
- [4. Omni Gateways (One-Time Per Environment)](#4-omni-gateways-one-time-per-environment)
- [5. Configure Agent Fabric](#5-configure-agent-fabric)
  - [5.1 exchange.json](#51-exchangejson)
  - [5.2 agent-network.yaml](#52-agent-networkyaml)
- [6. Deploy the Agent Network](#6-deploy-the-agent-network)
- [7. Test the Deployment](#7-test-the-deployment)
- [8. Agents & Tools Setup](#8-agents--tools-setup)
  - [8.1 Amazon Bedrock Agent](#81-amazon-bedrock-agent)
  - [8.2 Azure OpenAI LLM](#82-azure-openai-llm)
  - [8.3 Salesforce Agentforce Calendar Agent](#83-salesforce-agentforce-calendar-agent)
  - [8.4 MuleSoft — Concur MCP](#84-mulesoft--concur-mcp)
  - [8.5 MuleSoft — Slack MCP](#85-mulesoft--slack-mcp)
  - [8.6 Agent Scanners (Optional)](#86-agent-scanners-optional)
  - [8.7 MCP Bridge (Alternative to Custom MCP App)](#87-mcp-bridge-alternative-to-custom-mcp-app)
- [9. Additional Documents ](#9-additional-documents)
  - [Runbook pdf file](#runbook-pdf-file)
  - [Demo Video in youtube](#demo-video-in-youtube)

---

## Quick Start

High-level steps to build the end-to-end Agent Fabric Travel Booking Demo:

- [ ] Configure prerequisites
- [ ] Configure AWS Bedrock Agent
- [ ] Configure Agentforce
- [ ] Deploy MCP Servers
- [ ] Configure Agent Network
- [ ] Deploy Omni Gateways
- [ ] Publish Agent Network
- [ ] Deploy Agent Network
- [ ] Test the workflow

---

## Audience

This runbook is intended for:

- MuleSoft developers exploring Agent Fabric
- Integration engineers building multi-agent workflows
- Architects evaluating A2A and MCP integration patterns

**Recommended familiarity:** Basic MuleSoft, APIs, YAML, LLM concepts (helpful but not required)

---

## 1. Introduction

This guide describes how to configure, deploy, and run the Agent Fabric demo. The demo showcases a multi-agent orchestration workflow for business travel booking, where a single natural language request triggers an automated 8-step process across multiple systems.

The guide focuses on Agent Fabric — specifically the `agent-network.yaml` and `exchange.json` files that define and configure the agent network. External components (the travel search agent, calendar agent, MCP tool servers) are described for context. Teams can substitute their own equivalents.

---

## 2. Understand the Reference Use Case

**Example:** A business traveler asks to travel from Chicago to Atlanta for a date range.

Agent Fabric receives the request, coordinates supporting agents and tools, presents options, waits for confirmation, books the selected option, blocks the calendar, submits an expense, and sends final confirmation.

### Architecture

### 8-Step Workflow

| Step | Action | Component |
|---|---|---|
| 1 | User sends travel request in Slack | Slack MCP (inbound) |
| 2 | AgentFabric parses intent and plans calls | Azure OpenAI LLM |
| 3 | Search flights + hotels | AWS Bedrock A2A Agent |
| 4 | Check calendar for conflicts | Agentforce Calendar Agent |
| 5 | Post options to Slack, wait for approval | Slack MCP |
| 6 | User confirms — book flight + hotel | Concur MCP |
| 7 | Block travel dates on calendar | Agentforce Calendar Agent |
| 8 | Submit expense + send final Slack confirmation | Concur MCP + Slack MCP |

---

## 3. Prerequisites

### Accounts Required

| Platform | Purpose |
|---|---|
| AWS | Lambda + Bedrock Agent + API Gateway (travel search) |
| Azure | Azure OpenAI LLM (orchestrator brain) |
| Salesforce Developer | Agentforce calendar agent + flows |
| MuleSoft Anypoint | Agent Fabric broker + Concur MCP + Slack MCP |

### 3.1 Anypoint Platform Permissions

The following roles are required on your Anypoint user account:

- **Runtime Manager** — deploy apps
- **API Manager** — view/apply policies
- **Exchange Contributor** — publish agent network asset
- **ACB Mule Developer Generative AI User** — required for Agent Fabric features in ACB

Assign roles in: **Anypoint Platform → Access Management → Users → your user → Roles**

#### CloudHub 2.0 Private Space

Agent Fabric deploys to a CloudHub 2.0 Private Space. If one does not exist:

1. Go to **Runtime Manager → Private Spaces → Create Private Space**
2. After creation, associate it with your business group and target environment:
   **Private Space → Settings → Environments → Add**

#### Anypoint Code Builder Desktop

Download from the MuleSoft downloads page and install. ACB Desktop is required — the cloud IDE does not support the Agent Fabric deploy commands.

### 3.2 LLM Provider Credentials

You need an API key and endpoint for your chosen LLM. This demo uses **Azure OpenAI gpt-5**.

Required details:
- API key
- Endpoint URL: `https://<your-resource>.openai.azure.com/openai/v1/`
- Deployment name (e.g. `gpt-5`)

---

## 4. Omni Gateways (One-Time Per Environment)

Agent Fabric auto-deploys 2 Omni Gateways into your Private Space. They handle all A2A and MCP protocol enforcement, authentication, and telemetry. Without them, Agent Fabric deployment fails.

> This step is done **once per Anypoint environment**. Skip if gateways are already provisioned.

**Step 1** — Open Anypoint Code Builder Desktop.

**Step 2** — Open the command palette (`Cmd+Shift+P` on Mac, `Ctrl+Shift+P` on Windows).

**Step 3** — Run the setup command:
```
MuleSoft: Set Up Agent Network Gateways
```

**Step 4** — Select targets:
- Your CloudHub 2.0 Private Space
- Your target environment (e.g. Sandbox, Production)

This deploys two Omni Gateways. The process takes approximately 5 minutes.

> Once deployed, gateway size can be changed to Small or Large based on your requirements.

**Step 5** — Go to **Runtime Manager → CloudHub 2.0** and confirm both gateways are in **Running** status. You should see:
- `<your-prefix>-agent-network-ingress-gw` — Running
- `<your-prefix>-agent-network-egress-gw` — Running

---

## 5. Configure Agent Fabric

**Step 1** — Create an Agent Network in ACB. Two files are auto-created: `exchange.json` and `agent-network.yaml`.

### 5.1 exchange.json

This file defines:
- Exchange publishing metadata (org, asset ID, version)
- All variables and secrets referenced as `${}` in `agent-network.yaml`

#### Key Rules

- `"secret": true` — Agent Fabric encrypts this value in Exchange and injects it securely at runtime. **Never put secrets directly in agent-network.yaml.**
- `organizationId` and `groupId` are your Anypoint business group ID.
- `version` must be incremented on every deployment — Exchange rejects duplicate versions.

### 5.2 agent-network.yaml

This is the core file. It defines the entire agent network — the broker, sub-agents, MCP tools, LLM, and all connections.


#### Brokers: The Orchestrating Agent

The broker receives user requests, runs the LLM, and dispatches to agents and tools. The `card` block is the A2A agent card that external clients use to discover this broker.

**Key rules:**
- `url` uses `${ingressgw.url}` — the Omni Gateway URL from Step 4. Agent Fabric appends the broker name as the path.
- `skills.examples` helps the LLM route incoming requests correctly. Add real example phrases a user would type.

#### Spec: LLM + Instructions + Wiring


#### Workflow Steps (System Prompt)

Include these steps in the `instructions` block:

1. Parse the user request into structured fields: `origin`, `destination`, `travel_date`, `check_out`, `city_code`. Call `aws-bedrock-travel-search` with only these structured fields. Store the full `flights` and `hotels` arrays — needed in step 5.
2. Call `agentforce-calendar-agent` to check calendar availability. Pass: `travelerId`, `travelStartDate`, `travelEndDate`. Expected response: `CLEARED` or `CONFLICTS_FOUND`.
3. If `CLEARED`: call `slack-messenger-mcp sendTravelRequest` to notify the channel with flight and hotel options. If `CONFLICTS_FOUND`: notify via Slack and ask for alternative dates — stop.
4. Wait for user confirmation.
5. Upon approval, call `concur-mcp book-flight` with this exact flat JSON (all 13 fields):
6. Call `agentforce-calendar-agent` to block calendar dates. Failure here is non-fatal — continue and note it in the final message.
7. Call `concur-mcp submit-expense` with same fields + `booking_reference` from step 5.
8. Call `slack-messenger-mcp` with a booking summary including all statuses.

#### Agents — A2A

**Key rules:**
- Any system that exposes an A2A-compliant `/.well-known/agent.json` endpoint and accepts JSON-RPC messages can be an agent here.
- The actual URL goes in the `connections` section — this section is the type declaration only.

#### mcpServers — MCP Tool Servers

**Key rules:**
- `transport.kind: streamableHttp` — always use this. SSE transport is deprecated.
- `path: /mcp` — the standard path for any Mule app using mule-mcp-connector.
- Any MCP-compliant server works here — Mule, Node.js, Python, or any other runtime.

#### llmProviders — LLM Backend

#### connections — URLs and Credentials

**Key rules:**
- `kind` must match the section: `agent` for A2A, `mcp` for MCP servers, `llm` for LLM providers.
- Convention: connection name = `<agent-or-server-name>-connection`.
- All `${}` values are resolved from `exchange.json` at deploy time — never hardcode credentials here.
- Set `timeout` on the LLM connection to at least `120000` ms for complex multi-step workflows.

---

## 6. Deploy the Agent Network

**Step 1** — Open the project in ACB Desktop (the folder containing `agent-network.yaml` and `exchange.json`).

**Step 2** — Verify all variables in `exchange.json`. Confirm every `${}` reference in the YAML has a corresponding entry in `exchange.json`. Missing variables cause a silent deploy failure.

**Step 3** — Publish to Exchange. Bump the version — Exchange rejects deploys with a duplicate version. Increment the patch number each time.

**Step 4** — Deploy via ACB Desktop using the deploy command, or use the Anypoint CLI:

```bash
anypoint-cli fabric deploy --environment <env-name>
```

ACB publishes the asset to Exchange and deploys it to CloudHub 2.0. The broker appears in Runtime Manager as your `assetId`.

**Step 5** — Verify in Runtime Manager → CloudHub 2.0:
- Both Omni Gateways are **Running**
- Under **Egress Gateway**: your agents, MCPs, and LLMs are deployed
- Under **Ingress Gateway**: your broker (orchestrator) is deployed

---

## 7. Test the Deployment

Send the test request to your broker endpoint:

```bash
curl --location 'https://<your-ingress-gw>.<region>.cloudhub.io/travel-orchestrator/' \
--header 'Content-Type: application/json' \
--data '{
  "jsonrpc": "2.0",
  "method": "message/send",
  "id": "test-001",
  "params": {
    "message": {
      "kind": "message",
      "messageId": "550e8400-e29b-41d4-a716-446655440001",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Book a business trip from New York EWR to Atlanta, July 10 to July 12 2026. Traveler ID is <your-salesforce-user-id>"
        }
      ]
    }
  }
}'
```

---

## 8. Agents & Tools Setup

### 8.1 Amazon Bedrock Agent

#### AWS Lambda — `Bedrock-GetFlights-Hotels-Agent`

Python Lambda that searches real flights via RapidAPI Google Flights and returns hotel options from a pre-seeded dataset. Handles three invocation types: Bedrock action group, A2A JSON-RPC from Agent Fabric, and direct REST for testing.

**Steps:**

1. AWS Console → Lambda → **Create Function** → Author from scratch
2. Runtime: **Python 3.12**, name: `Bedrock-GetFlights-Hotels-Agent`
3. Write your function code (see `AWS/Lambda/lambda_travel_planner.py`)
4. Set environment variables:
   - `RAPIDAPI_HOST` = `google-flights2.p.rapidapi.com`
   - `RAPIDAPI_KEY` = `<your-rapidapi-key>`
   - `AGENT_URL` = set after API Gateway is created in the next step
5. Set **Timeout to 60 seconds** — the default 3s causes failures on slow API calls. Set internal RapidAPI timeout to 5s with mock fallback.
6. Test and deploy the function.

> **Important:** All handler functions (`handle_bedrock_agent_call`, `handle_a2a_message`) must be at top-level scope — not nested inside other functions. Nesting makes them unreachable from `lambda_handler`.

#### Amazon Bedrock Agent — `travel-planner-agent`

Bedrock provides the AI reasoning layer on top of the Lambda. It interprets travel requests, calls the Lambda via an action group, and returns structured results. Agent Fabric calls this Bedrock Agent via the A2A protocol.

**Steps:**

1. AWS Console → Amazon Bedrock → Agents → **Create Agent**
2. Name: `travel-planner-agent`, Model: **Claude 3.5 Haiku**
   > Do not use Claude 3.5 Sonnet v1 — stricter access controls cause IAM denials.
3. Instructions: search flights and hotels, show policy compliance, never book directly
4. Create Action Group `TravelSearchGroup`:
   - Type: Lambda function → select `Bedrock-GetFlights-Hotels-Agent`
   - Provide OpenAPI schema as a **single minified line** — embedded newlines cause schema rejection
5. In the Agent Card skills array, add `"tags": []` to every skill — Agent Fabric A2A discovery fails without this field
6. Add Lambda resource policy allowing `bedrock.amazonaws.com` to invoke the function
7. **Prepare** the agent, test, then **Deploy**

#### Amazon API Gateway — `travel-planner-api`

HTTP API that exposes the Lambda as a public HTTPS endpoint. Provides the stable URL Agent Fabric uses for A2A calls, and exposes the agent card at `/.well-known/agent.json`.

**Steps:**

1. AWS Console → API Gateway → **Create API → HTTP API** (not REST API)
2. Add integration: Lambda → `Bedrock-GetFlights-Hotels-Agent`
3. Configure two routes:
   - `GET /.well-known/agent.json` → Lambda
   - `POST /` → Lambda
4. Deploy to stage `$default`
5. Copy the invoke URL → set as Lambda env var `AGENT_URL`

---

### 8.2 Azure OpenAI LLM

Azure OpenAI resource hosting a GPT-5 deployment. Used as the LLM brain for the Agent Fabric orchestrator broker.

**Steps:**

1. Azure Portal → Create Resource → **Azure OpenAI**
   - Region: **East US** (required — GPT-5 availability varies by region)
2. Open in AI Foundry → Deployments → New → Deploy Model → `gpt-5`
   - Copy API Key and Endpoint URL
3. Add CloudHub outbound IPs to the Azure firewall — without this, all Agent Fabric calls are blocked:
   - Azure Portal → your resource → **Networking → Add IPs**
   - Add all CloudHub 2.0 outbound IPs for your region

---

### 8.3 Salesforce Agentforce Calendar Agent

**Account setup:**

1. Sign up at `https://www.salesforce.com/products/free-trial/developer/` → create Developer Edition org
2. Enable:
   - Einstein: **Setup → Einstein Setup → Enable**
   - Data Cloud: **Setup → Data Cloud Setup → Get Started**
   - Agentforce: **Setup → Agentforce → Enable**

#### Permission Set — Agent_Event_Access

Create this **before** building the agent:

1. Setup → Permission Sets → **New**
2. Name: `Agent_Event_Access`
3. Object Settings → Tasks → enable **Read, Create, Edit**
4. Assign to both Einstein Agent User accounts in the org

#### Flow 1 — Check Calendar Conflicts

Queries the traveler's Salesforce calendar for events that overlap the travel dates. Returns `CLEARED` or `CONFLICTS_FOUND`.

1. Setup → Flows → **New Flow → Autolaunched Flow**
2. Input variables (mark **Available for Input**):
   - `travelStartDate` (DateTime), `travelEndDate` (DateTime), `travelerId` (Text)
3. Output variables (mark **Available for Output**):
   - `hasConflict` (Boolean), `conflictSummary` (Text), `out_ConflictStatus` (Text)
4. Get Records from **Event** where `OwnerId = travelerId AND StartDateTime <= travelEndDate AND EndDateTime >= travelStartDate`
5. Decision: if records found → `hasConflict = true`, set conflict summary. Else → `hasConflict = false`, `No conflicts found`
6. Flow Settings: set run mode to **System — Without Sharing**
7. Save, test, and activate

#### Flow 2 — Block Travel Dates

Creates a **Task** record on the traveler's calendar to block the booked travel dates.

> **Why Task, not Event?** Einstein Agent User context cannot insert Event records — hits `CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY`. Tasks appear in Salesforce activity/calendar views and avoid this restriction.

1. Setup → Flows → **New Flow → Autolaunched Flow**
2. Input variables: `var_Destination`, `var_StartDate`, `var_EndDate`, `var_FlightDetails`, `var_travelerId`
3. Formula: `fDueDate = DATEVALUE(var_EndDate)` — converts text date to Task `ActivityDate`
4. Create Records — **Task**:
   - `Subject` = `"OOO: Business Trip to " + var_Destination`
   - `ActivityDate` = `fDueDate`
   - `OwnerId` = `var_travelerId`
   - `Status` = `In Progress`
   - `Description` = `var_FlightDetails`
5. Output variable `var_EventId` (Text, Available for Output) = Task Id from Create Records
6. Save, test, and activate

#### Create the Agentforce Agent

1. Setup → Agentforce → **New Agent**
2. Name: `Calendar_Agent`, Topic: `Manage Travel Calendar`
3. Instructions: only manage calendar activities, do not book flights, always check conflicts before blocking
4. Add actions for both flows above
5. Test and **Activate**

---

### 8.4 MuleSoft — Concur MCP

The Concur integration uses a 3-layer API-led architecture:

| Layer | App | Responsibility |
|---|---|---|
| System API | `mock-concur-sys-api` | Mock Concur backend — raw booking and expense data |
| Process API | `concur-prc-api` | Business logic, validation, field mapping |
| Experience / MCP | `booking-expense-mcp` | Exposes `book-flight` and `submit-expense` as MCP tools |

Deploy each app independently to CloudHub 2.0:

---

### 8.5 MuleSoft — Slack MCP

Mule app exposing one MCP tool: `sendTravelRequest` — posts formatted travel options or booking summaries to a Slack channel (step 3 for approval, step 8 for final confirmation). Also listens for inbound Slack events and routes travel requests to the MAF broker.

**Slack App setup:**

1. Go to `api.slack.com/apps` → **Create New App**
2. Add Bot Token Scopes: `chat:write`, `channels:read`
3. Add bot events: `message.channels`, `message.groups`
4. Install app to workspace — copy **Bot User OAuth Token** (`xoxb-...`)
5. Invite bot to demo channel: `/invite @your-bot-name`
   > This is the most commonly missed step — the bot won't receive messages without it.
6. Copy **Channel ID** from channel settings
7. Reinstall the app after any scope or event changes

**Maintaining conversation context:** The Slack MCP uses Object Store keyed by Slack channel ID to persist `contextId` + `taskId` for 1 hour. Type `reset` in Slack to clear the session.

---

### 8.6 Agent Scanners (Optional)

Agent Scanners are a MuleSoft Exchange feature that discovers, imports, and catalogs external agents from third-party platforms directly into Anypoint Exchange. Once cataloged, these agents can be referenced directly in `agent-network.yaml` without manual URL entry in `exchange.json`.

**Supported platforms:** Amazon Bedrock, Amazon Bedrock AgentCore Runtime, Anthropic Claude, Google Vertex AI, Microsoft Azure Copilot, Snowflake Cortex AI, LangChain LangSmith, Databricks, GoDaddy ANS, Microsoft Foundry

**Steps:**

1. Go to **Anypoint Exchange → left nav → Agent Scanners**
2. Click **Add Scanner**
3. Select your platform (e.g. Amazon Bedrock or Salesforce Agentforce)
4. Provide the required credentials (AWS credentials, Salesforce OAuth, etc.)
5. Run the scan — Exchange discovers all agents available on that platform
6. Select the agents to import — published as assets in Exchange
7. Reference them directly in `agent-network.yaml` by name

Full documentation: `https://docs.mulesoft.com/exchange/agent-scanners`

---

### 8.7 MCP Bridge (Alternative to Custom MCP App)

If you already have a deployed API in Anypoint Exchange, MuleSoft's **MCP Bridge** can convert it into an MCP server without writing any Mule code — configuration only.

| Category | MCP App (custom) | MCP Bridge (alternative) |
|---|---|---|
| When to use | Custom logic, flat-field mapping, multi-system composition | Existing API already in Exchange; no transformation needed |
| Effort | Build and deploy a Mule application | Configuration only; no code required |
| Flexibility | Full flexibility with DataWeave, error handling, validation | Limited to operations the existing API already exposes |
| Governance | Manual policy application | Automatically inherits existing API governance policies |

**How to use MCP Bridge:**

1. Go to **Anypoint Exchange** → find your existing API asset
2. Select **Expose as MCP Server**
3. Choose which API operations to expose as MCP tools
4. Apply governance policies from your existing portfolio
5. The MCP server becomes discoverable by Agent Fabric immediately — no deployment needed

Full documentation: `https://docs.mulesoft.com/general/agent-fabric-overview#mcp-bridge`

> **Recommendation:** Use MCP Bridge when your backend is already an API in Exchange and no payload transformation is needed. Use a custom Mule MCP app when you need flat-field mapping, multi-step validation, or to compose multiple backend systems into a single tool — as required for Concur in this demo.

---

## 9. Additional Documents

### Runbook pdf file

### Demo Video in youtube

