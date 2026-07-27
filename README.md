# MuleSoft Agent Fabric Demos

A collection of end-to-end multi-agent orchestration demos built on **MuleSoft Agent Fabric (MAF)**, demonstrating real-world agentic workflows using open standards—A2A (Agent-to-Agent) and MCP (Model Context Protocol)—across AWS, Salesforce, and MuleSoft services.

This repository serves as a reference architecture for enterprise teams exploring multi-agent orchestration. Each demo is self-contained with its own setup guide and can be adapted to your own Anypoint organization and cloud environment.

## Demos

| Demo | Description | Agents Involved |
|------|-------------|-----------------|
| [Business Travel Booking Agent](Business%20Travel%20Booking%20Agent/README.md) | Slack-triggered end-to-end travel booking including flight search, calendar availability checks, approval workflows, booking, and expense submission. | AWS Bedrock, Salesforce Agentforce, MuleSoft MCP |

## Prerequisites

- MuleSoft Anypoint Platform account (CloudHub 2.0 or Runtime Fabric)
- AWS account with Lambda and Amazon Bedrock enabled
- Salesforce organization with Agentforce configured
- Slack app with a bot token and Events API enabled

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for information on reporting bugs, suggesting features, and submitting pull requests.

All contributions must be accompanied by a signed [Salesforce Contributor License Agreement (CLA)](https://cla.salesforce.com/).

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.