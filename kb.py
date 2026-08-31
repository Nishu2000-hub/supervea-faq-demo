"""
Supervea FAQ knowledge base.

Deliberately compact. "Tokens saved" scales linearly with prompt size, so a
bloated system prompt inflates the headline number for free. Keep this tight
and let the savings figure stand on real traffic instead.

Sourced from: SDK CLI Quick Start, Private Beta Developer User Guide,
and the v1.2.0 Integration Pathways section.
"""

KNOWLEDGE_BASE = """\
SUPERVEA — PRODUCT REFERENCE

What it is
Supervea is an AI optimization and observability gateway. It sits between your
application and your existing AI provider. Traffic routed through it gets
intelligent caching, request deduplication, lower latency on repeats, and
metrics on cost and cache behaviour. Your provider contracts and response
shapes are preserved. Two integration styles exist and can be used together:
intent-based (natural language to structured, governed workflows) and the AI
optimization gateway (an OpenAI-compatible caching proxy).

Installation
Python SDK requires Python 3.8+ and has no dependencies beyond the standard
library (urllib). Node SDK requires Node 18+, uses native fetch, and works with
both ES Modules and CommonJS.
  Private beta: pip install ./sdk/python/dist/supervea-1.0.0-py3-none-any.whl
                npm install ./sdk/node/supervea-1.0.1.tgz
  Post-launch:  pip install supervea  /  npm install supervea
  Editable:     pip install -e ./sdk/python

Configuration
Set SUPERVEA_BASE_URL to your gateway. Hosted is https://api.supervea.com;
self-hosted is your own gateway URL. The SDK also recognises SUPERVEA_ENDPOINT,
SUPERVEA_URL, base_url and endpoint, but SUPERVEA_BASE_URL is recommended. Set
it before creating the Client. Some Phase 1 self-hosted pilots additionally
need SUPERVEA_PILOT_ACCESS_KEY and SUPERVEA_ORG_ID.

Creating a client
  from supervea import Client
  client = Client(api_key="sv_free_your_generated_key")
Organization ID is derived automatically from your API key on hosted
deployments, so you never pass org_id manually. Reuse a single Client instance
across your application rather than constructing one per request. In Node,
PilotClient is a backwards-compatible alias for Client.

route() versus submit()
route() classifies and parses a natural-language prompt, returning the matched
use case and parameters without executing anything — use it for advisory,
dry-run, validation, or inspecting missing parameters. submit() classifies,
runs governance checks, and triggers execution of the mapped workflow. Use
submit() only when the request should actually perform an action.

OpenAI-compatible proxy
Any client speaking the OpenAI chat/completions protocol can point at the
gateway with no application logic changes.
  POST https://api.supervea.com/api/v1/proxy/chat/completions
  Headers: Content-Type: application/json
           Authorization: Bearer <your-provider-key>
           X-Supervea-Key: <your-supervea-key>
Other proxy endpoints: GET /api/v1/proxy for service info and summary metrics,
GET /api/v1/proxy/stats for full telemetry, GET /api/v1/proxy/models for the
model catalogue.

Observability headers
Every proxied response carries:
  x-supervea-cache: HIT or MISS
  x-supervea-tokens-saved: number
  x-supervea-latency-ms: number
  x-supervea-adapter: active
Response bodies from the ask() helper include a cached boolean, tokens_saved,
usage, and model.

Gateway metrics
Both SDKs expose a gateway namespace: client.gateway.stats(),
client.gateway.models(), client.gateway.health(). Typical stats fields are
total_requests, cache_hits, cache_misses, cache_hit_rate_pct, tokens_saved,
estimated_cost_saved_usd, and providers_routed.

Bring your own key, and sandbox testing
On a cache miss the gateway forwards the request using the provider key you
supply, so you keep control of your OpenAI, Gemini or Anthropic keys. For local
testing without spending provider quota, use the built-in mock key
"mock-openai-key-for-pilot-testing", which returns a deterministic sandbox
response so you can validate cache behaviour and latency without charges.

Free tier limits
2,500 executions per rolling 30-day window, 30 requests per minute, and 300
requests per hour. Contact team@supervea.com for higher limits or dedicated
environments.

API keys
Keys look like sv_free_.... Generate one at signup; manage it under API Keys in
the Command Center. You can toggle visibility, copy, or regenerate. Regenerating
revokes the previous key immediately, so update SUPERVEA_KEY or
SUPERVEA_API_KEY everywhere before continuing. Store keys in environment
variables or a secrets manager, never hard-coded.

Error codes
401 Unauthorized — invalid, rotated, or expired key or session. Copy the current
key from the Command Center and update your environment variables.
402 Payment Required — license expired or quota exceeded, typically the 2,500
execution free-tier limit. Upgrade in the dashboard.
422 Unprocessable Entity — missing or invalid parameters; check the payload and
that intent is a non-empty string.
500 Internal Server Error — gateway or downstream workflow error; check
execution logs in the Command Center.

Troubleshooting
Cache always MISS: confirm traffic actually routes through the Supervea
endpoint, that prompts are identical or semantically similar, and inspect the
x-supervea-cache header.
DNS or getaddrinfo errors: the base URL is misconfigured. Set SUPERVEA_BASE_URL
before creating the Client.
Metrics not appearing: ensure initial license validation completed so the org
binding exists, and that requests are reaching the gateway.
Browser "process is not defined": browser bundlers need a process polyfill;
apply the Vite config and client shim.
Unexpected routing: use route() to inspect classification before submit().

Multiple environments and multi-tenancy
Corporate Pilot setups can use a separate API key per environment, point each at
its own gateway via SUPERVEA_BASE_URL, and monitor each independently. Every
request is scoped by org_id derived from the key; workflows, logs and metrics
are separated per organization and cross-tenant access is not permitted.

Support
Email team@supervea.com or see https://www.supervea.com. Include your
Organization ID, the approximate timestamp, and any request IDs or dashboard
screenshots so the team can correlate with backend traces.
"""


# Traffic simulator pools. The mix is displayed on screen during the run —
# hit rate is meaningless without the distribution that produced it.

REPEATED = [
    "What are the limits of the Supervea free tier?",
    "How do I install the Supervea Python SDK?",
    "How do I point my OpenAI client at the Supervea gateway?",
    "What does a 402 error mean?",
]

PARAPHRASED = [
    "How many requests per minute does the free plan allow?",
    "What's the command to add the Python SDK to my project?",
    "Can I use my existing OpenAI SDK with Supervea?",
    "Why am I getting a payment required response?",
]

NOVEL = [
    "What is the difference between route() and submit()?",
    "Do I have to pass org_id on every call?",
    "Which Node.js version does the SDK require?",
    "How do I regenerate my API key?",
    "What happens if the gateway is unreachable?",
    "How is multi-tenancy enforced?",
    "Where can I see my cache hit rate?",
    "What is the mock key used for?",
    "Which environment variable sets the gateway URL?",
    "How do I contact Supervea support?",
    "What does the x-supervea-cache header tell me?",
    "Can I run separate dev and staging environments?",
]