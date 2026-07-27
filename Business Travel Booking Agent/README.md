# MuleSoft Agent Fabric — Business Travel Booking Agent

An end-to-end multi-agent orchestration demo built on **MuleSoft Agent Fabric (MAF)**. A single Slack message triggers a full business travel booking workflow—flight search, calendar conflict detection, approval, booking, expense submission, and calendar blocking—all coordinated by an LLM-powered orchestrator across AWS, Salesforce, and MuleSoft services.

This project serves as a reference architecture for enterprise teams exploring multi-agent orchestration using open standards—A2A and MCP. It demonstrates how MuleSoft Agent Fabric connects heterogeneous agents (AWS Bedrock, Salesforce Agentforce, MuleSoft MCP servers) without vendor lock-in, giving the community a reusable blueprint for building agentic workflows on any cloud.

---

## Architecture Overview

```
Slack Message
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│               MuleSoft Agent Fabric (MAF)                       │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │          Business Travel Orchestrator (gpt-5)            │  │
│   │                  agent-network.yaml                      │  │
│   └────────┬──────────────┬──────────────┬───────────────────┘  │
│            │              │              │                       │
│     A2A Protocol    A2A Protocol    MCP (Streamable HTTP)        │
│            │              │              │                       │
└────────────┼──────────────┼──────────────┼───────────────────────┘
             │              │              │
    ┌────────▼──────┐ ┌─────▼──────┐ ┌────▼──────────────────┐
    │  AWS Lambda   │ │ Agentforce │ │  MuleSoft MCP Servers │
    │ Travel Search │ │  Calendar  │ │  ┌─────────────────┐  │
    │  (Bedrock)    │ │   Agent    │ │  │ concur-mcp      │  │
    └───────────────┘ └────────────┘ │  │ slack-mcp       │  │
                                     │  └─────────────────┘  │
                                     └────────────────────────┘
```

**Protocol used between agents:** [A2A (Agent-to-Agent)](https://a2aprotocol.ai/) for external agents, MCP (Model Context Protocol) for tool servers.

---

## Workflow (8 Steps)

```
1. User sends travel request in Slack
        │
2. AWS Lambda searches flights + hotels (RapidAPI + policy check)
        │
3. Agentforce Calendar Agent checks for conflicts
        │
4. Slack notification sent with options → user approves
        │
5. Concur MCP books flight + hotel
        │
6. Agentforce Calendar Agent blocks travel dates
        │
7. Concur MCP submits expense report
        │
8. Slack final confirmation sent
```

---

## Repo Structure

```
├── business-travel-maf/           # MAF orchestrator (agent-network.yaml + exchange.json)
│
├── Mulesoft/
│   ├── booking-expense-mcp-AGF/       # Concur MCP Server (book-flight, submit-expense tools)
│   ├── slack-mcp/                 # Slack MCP Server (sendTravelRequest + events listener)
│   ├── af-concur-prc-api/         # Concur Process API (business logic + field mapping)
│   ├── af-mock-concur-sys-api/    # Mock Concur System API (local testing — no real Concur needed)
│
├── AWS/
│   └── Lambda/
│       └── lambda_travel_planner.py   # AWS Lambda — flight search (RapidAPI) + hotel inventory
```

> **Note:** The `jkm-` prefix in folder names is a personal namespace from the original author's Anypoint org. When deploying to your own org, rename these to match your naming conventions.

---

## Components

### MAF Orchestrator (`business-travel-maf`)

The brain of the system. Defined in `agent-network.yaml` using MuleSoft Agent Fabric schema.

- **LLM:** Azure OpenAI gpt-5
- **Linked agents (A2A):** `aws-bedrock-travel-search`, `agentforce-calendar-agent`
- **MCP tools:** `concur-mcp`, `slack-messenger-mcp`

### AWS Lambda Travel Search

Searches real flights via RapidAPI (with fallback mock data) and static hotel inventory across 12 cities. Validates results against company travel policy:

| Policy Rule | Limit |
|---|---|
| Max flight price | $1,200 |
| Max hotel per night | $200 |
| Max total trip | $3,000 |
| Advance booking | 3 days minimum |
| Cabin class | Economy |

Supports three invocation modes: Bedrock action group, A2A JSON-RPC, and REST via API Gateway.

### Agentforce Calendar Agent (Salesforce)

Exposed via Agent Scanners. Provides two skills:

- `calendar-check` — returns `CLEARED` or `CONFLICTS_FOUND`
- `calendar-block` — creates a calendar event for the travel dates

### Concur MCP Server (`booking-expense-mcp-AGF`)

Exposes two MCP tools:

- `book-flight` — books flight + hotel in Concur
- `submit-expense` — submits expense report with booking reference

### Slack MCP Server (`jkm-slack-mcp`)

- Listens for Slack events (`/slack/events`) and routes travel-related messages to the MAF orchestrator via A2A
- Exposes `sendTravelRequest` MCP tool for the orchestrator to post messages back to Slack
- Maintains conversation context (`contextId` + `taskId`) per channel using Object Store (1-hour TTL)
- Type `reset` in Slack to clear the session and start a fresh conversation


---

## Prerequisites

| Component | Requirement |
|---|---|
| MuleSoft | Anypoint Platform account, CloudHub 2.0 or RTF |
| Azure | Azure OpenAI deployment (gpt-5) |
| AWS | Lambda + API Gateway + Bedrock enabled |
| Salesforce | Agentforce agent configured |
| Slack | Slack app with bot token + Events API enabled |
| Concur | SAP Concur API credentials (or use mock) |

---

## Configuration

Each MuleSoft project uses a `config.properties` file (not committed). Key properties:

### MAF Orchestrator (`business-travel-maf`)

```properties
ingressgw.url=https://<your-flex-gateway-url>
AzureOpenAI.openaiurl=https://<your-azure-openai-url>
AzureOpenAI.apiKey=<key>
AzureOpenAI.deploymentName=gpt-5
awsBedrock.travelSearchUrl=https://<your-lambda-api-gateway-url>
salesforce.agentUrl=https://<your-agentforce-url>
salesforce.travelerId=<traveler-id>
slack.channelId=<slack-channel-id>
mulesoft.concurURL=https://<your-concur-mcp-url>
slack.messengerUrl=https://<your-slack-mcp-url>
```

### Slack MCP (`jkm-slack-mcp`)

```properties
slack.botToken=xoxb-...
agent.broker.host=<maf-host>
agent.broker.port=443
```

---

## Deployment

Each MuleSoft project is deployed independently to CloudHub 2.0:

```
Via Anypoint Code Builder
```
Or

```bash
# From each Mulesoft project directory
mvn clean deploy -DmuleDeploy \
  -Danypoint.username=<user> \
  -Danypoint.password=<pass> \
  -DenvironmentName=Sandbox
```

---

## Testing

1. Add your Slack bot to the target channel.
2. Send a message:
   ```
   I want to travel from Chicago to New York JFK from Oct 12 to Oct 15 2026
   ```
3. The bot replies with flight and hotel options.
4. Reply `yes` or `approve` to confirm booking.
5. Check Concur and your calendar for the booking.

To reset a session, type `reset` in the Slack channel.

---

## Tech Stack

- **MuleSoft Agent Fabric** — multi-agent orchestration
- **Azure OpenAI gpt-5** — LLM orchestrator
- **AWS Lambda + Bedrock** — travel search agent
- **Salesforce Agentforce** — calendar agent
- **MCP (Model Context Protocol)** — tool servers
- **A2A Protocol** — agent-to-agent communication
- **Slack Events API** — user interface
- **SAP Concur API** — booking & expense
- **Google Calendar API** — optional calendar integration

---

## Demo

> **Note:** Demo video is currently restricted. It will be made public upon OSS approval.
> [Watch Full Demo (Google Drive)](https://drive.google.com/file/d/18oFkFf6Lai-xsuoXK3tNyQDRy4hQr868/view?usp=sharing)

---

## Maintainers

| Name | GitHub |
|---|---|
| Kavya Mounika Tadepalli | [@Personal-jkm](https://github.com/Personal-jkm) |

To become a maintainer or report a security issue, open a GitHub Issue.

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to report bugs, suggest features, and submit pull requests.

All contributions must be accompanied by a signed [Salesforce CLA](https://cla.salesforce.com/).

## License

Apache 2.0 — see [LICENSE](../LICENSE).