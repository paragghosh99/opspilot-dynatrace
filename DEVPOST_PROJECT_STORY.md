# OpsPilot Devpost Project Story

Copy the content below into Devpost's **About the project** field.

---

## Inspiration

Production incidents are stressful because the first few minutes are usually spent gathering context: what broke, which service is affected, whether the issue is real, and what action is safe to take. As a team, we wanted to build something that felt closer to a real SRE teammate than a chatbot: an agent that watches observability signals, diagnoses incidents, takes a limited and auditable action, and learns from previous outcomes.

That became OpsPilot: an autonomous incident-response agent built around Dynatrace MCP, Google Agent Builder, Gemini on Vertex AI, and a self-learning runbook.

## What it does

OpsPilot monitors Dynatrace for active Davis problems and responds automatically.

When Dynatrace detects an incident, OpsPilot:

1. Polls the Dynatrace MCP server for active problems.
2. Fetches affected entities, event details, and DQL-backed context.
3. Uses a Google Conversational Agent to ground the incident in SRE language.
4. Sends the full context to Gemini 2.5 Pro on Vertex AI.
5. Produces a structured diagnosis with root cause, explanation, confidence, and recommended action.
6. Executes a safe remediation path, such as publishing a Pub/Sub incident alert.
7. Persists the incident, action, and diagnosis to Cloud Storage.
8. Updates a learned runbook and MTTR dashboard.

The dashboard shows live Dynatrace problems, incident history, MTTR trends, and learned response patterns.

## How we built it

We built the backend as a FastAPI service deployed on Cloud Run. Cloud Scheduler calls the `/poll` endpoint every two minutes, which starts the autonomous incident-response workflow.

Dynatrace MCP is the observability layer. OpsPilot uses it to query Davis problems, fetch problem details, and run DQL queries for incident context. Google Conversational Agent provides grounding before diagnosis, and Gemini 2.5 Pro on Vertex AI produces the final structured root-cause analysis.

For actions and persistence, we used Pub/Sub for incident alerts and Cloud Storage for incident history, processed problem IDs, and learned runbook data. The frontend is a React dashboard that makes the workflow visible: live incidents, diagnoses, MTTR, and runbook learning.

We also added two levels of testing: a safe production test suite for low-cost endpoint checks, and an opt-in live pipeline test for validating the full Dynatrace to MCP to Agent Builder to Gemini to persistence flow.

## Challenges we ran into

The hardest part was making the project behave like a real production agent instead of a scripted demo.

One of the first issues we hit was that our initial MCP assumptions did not match the live Dynatrace environment. We originally treated tool names like ordinary Python-style identifiers, but the actual MCP server exposed hyphenated tool names.

For example, this failed in production:

```python
await _call_mcp_tool("execute_dql", {"query": query})
```

The live MCP server returned an error like:

```text
Invalid params: Unknown tool name 'execute_dql'
```

The fix was to use the actual Dynatrace MCP tool name and request shape:

```python
await _call_mcp_tool(
    "execute-dql",
    {
        "dqlQueryString": query,
        "includeTypes": False,
    },
)
```

We ran into a similar issue while trying to pull Davis context. Our first implementation called a tool name that did not exist in the live MCP server:

```text
Invalid params: Unknown tool name 'get_davis_context'
```

Instead of creating a separate fake Davis-context path, we changed the production call to use the verified `get-problem-by-id` tool and treated that response as Davis problem context:

```python
rows = await _call_mcp_tool(
    "get-problem-by-id",
    {
        "problemId": problem_id,
        "history": "2d",
        "includeTypes": False,
    },
)
```

Another challenge was parsing MCP responses. The live Dynatrace MCP response was not just a plain list of dictionaries. It returned structured records nested under `structuredContent`, so the parser had to support both demo fixtures and real MCP payloads.

```python
structured = result.get("structuredContent", {})
records = structured.get("records")

if isinstance(records, list):
    return [row for row in records if isinstance(row, dict)]
```

Agent Builder integration also required adjustment. We had a real Google Conversational Agent, but our first grounding path treated the ID like a search engine configuration. That caused a production error similar to:

```text
google.api_core.exceptions.InvalidArgument: 400 Request contains an invalid argument
```

The fix was to detect when the configured resource was a Conversational Agent and call Dialogflow detectIntent instead:

```python
session = f"{agent_path}/sessions/{session_id}"
url = f"https://{location}-dialogflow.googleapis.com/v3/{session}:detectIntent"
```

Idempotency was another important challenge. Since Cloud Scheduler calls `/poll` every two minutes, the agent needed to avoid processing the same active incident repeatedly. We solved that by storing processed Dynatrace problem IDs in Cloud Storage:

```python
def save_processed_ids(processed_ids: set[str]) -> None:
    _state_blob().upload_from_string(
        json.dumps(sorted(processed_ids), indent=2),
        content_type="application/json",
    )
```

This prevented duplicate Gemini calls and duplicate remediation actions for the same Dynatrace problem.

## Accomplishments that we're proud of

We are proud that OpsPilot is not just a chatbot. It is an autonomous workflow that starts from a real Dynatrace incident, reasons through Google Cloud AI services, performs a safe action, and persists the result for future learning.

In our live test, OpsPilot processed a real Dynatrace synthetic monitor problem, grounded it with a Google Conversational Agent, diagnosed it with Gemini, published a Pub/Sub alert, saved the incident to Cloud Storage, and updated the learned runbook and MTTR dashboard.

We are also proud of the safety pieces: idempotency, Secret Manager, billing-conscious tests, and audit-friendly incident records. Those details made the project feel much closer to a real incident-response tool.

## What we learned

We learned that observability context is only useful to an AI agent if it is structured well. Raw alert text is not enough. Once OpsPilot pulled Davis problem data, affected entities, event details, and DQL context through Dynatrace MCP, Gemini's diagnosis became much more specific and operationally useful.

We also learned that live integrations reveal issues that local fixtures will not. Our demo-mode tests passed early, but production exposed real differences in MCP tool names, response formats, and Agent Builder APIs. That pushed us to add tests for the actual structured MCP response shape:

```python
def test_parse_mcp_structured_records():
    payload = {
        "result": {
            "structuredContent": {
                "records": [
                    {
                        "display_id": "P-123",
                        "event.status": "ACTIVE",
                        "event.description": "Synthetic checkout failure",
                    }
                ]
            }
        }
    }

    assert _parse_mcp_content(payload)[0]["display_id"] == "P-123"
```

We learned that safe automation matters more than aggressive automation. For the live synthetic outage, OpsPilot classified the issue as a configuration/script problem in the monitor and chose to publish an alert instead of taking a risky infrastructure action.

The final diagnosis looked like this:

```json
{
  "root_cause": "config_error",
  "recommended_action": "publish_alert",
  "confidence": 0.9
}
```

That felt like the right behavior for an incident-response agent: act quickly, but stay within a safe operational boundary.

The self-learning runbook also became more useful than we expected. After processing real Dynatrace incidents, OpsPilot updated the runbook with root-cause categories, successful actions, success rates, and MTTR:

```json
{
  "config_error": {
    "incident_count": 2,
    "recommended_action": "publish_alert",
    "success_rate": 100.0,
    "avg_mttr_minutes": 14.0
  }
}
```

Finally, we learned that production readiness for AI agents is mostly about the quiet engineering details: retries, idempotency, clean logs, secrets, deployment stability, and making sure expensive inference calls are not repeated unnecessarily.

## What's next for OpsPilot

Next, we would expand the remediation engine with more production-safe action adapters, such as creating tickets, notifying on-call channels, or applying pre-approved Cloud Run scaling changes.

We would also add human approval gates for higher-risk actions, richer runbook feedback from operators, and more incident categories beyond synthetic monitor and availability failures.

Longer term, OpsPilot could become a closed-loop SRE assistant that learns which actions actually reduce MTTR for each service, while still keeping humans in control of high-impact changes.

