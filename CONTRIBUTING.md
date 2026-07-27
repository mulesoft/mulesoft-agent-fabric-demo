# Contributing to MuleSoft Agent Fabric — Business Travel Booking Agent

Thank you for your interest in contributing! This project welcomes bug reports, feature suggestions, and pull requests.

## Before You Start

All external contributors must sign the [Salesforce Contributor License Agreement (CLA)](https://cla.salesforce.com/). The CLA bot will prompt you automatically when you open a pull request.

## Code of Conduct

This project follows the [Salesforce Open Source Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold these standards.

## How to Contribute

### Reporting Bugs

Open a GitHub Issue using the **Bug Report** template. Include:
- Steps to reproduce
- Expected vs actual behavior
- Component affected (Agent Fabric config, Lambda, Agentforce, MCP server, etc.)
- Relevant error messages or logs

### Suggesting Features

Open a GitHub Issue using the **Feature Request** template with a clear description of the use case.

### Submitting Pull Requests

1. Fork the repository and create a branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the existing code style.

3. Ensure no credentials, personal IDs, or internal URLs are introduced. All configurable values must use `<placeholder>` format in config files or environment variables in code.

4. Test your changes end-to-end where possible (see the runbook for setup steps).

5. Open a pull request against `main` with a clear description of what changed and why.

### What to Contribute

- Fixes to the `agent-network.yaml` configuration patterns
- Improvements to the AWS Lambda travel search logic
- Additional MCP tool examples
- Documentation improvements and corrections to the runbook
- Alternative LLM provider configurations (e.g. OpenAI, AWS Bedrock as the orchestrator LLM)

## Development Setup

See the [README](README.md) for prerequisites and configuration steps.

## Questions

Open a GitHub Discussion or Issue if something in the docs is unclear.
