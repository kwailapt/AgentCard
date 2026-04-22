# AgentCard

> **AgentCard is to A2A what HTTP headers are to the web.**

A standardized, machine-parseable declaration of agent identity and capability.
Pure data schema. Zero execution logic. Works with any framework.

**Schema version:** 1.0 · **License:** Apache 2.0 + CC-BY 4.0 (spec)

---

## What is AgentCard?

When HTTP was designed, headers solved a critical bootstrapping problem: how does a server
know what format a client accepts before any negotiation happens?

AgentCard solves the same problem for agent-to-agent (A2A) communication:

| HTTP Header | AgentCard field |
|---|---|
| `Content-Type` | `capabilities[].id` |
| `Accept` | `capabilities[].input_schema` / `output_schema` |
| `Authorization` | `endpoint.auth` |
| `Server` / `User-Agent` | `name` + `version` |
| Cache headers | `metadata.pacr:*` (derived from ledger) |

An AgentCard is a **pure data document** — no network calls, no execution logic.
Any framework can parse it. It travels as the Payload (P) inside a PACR record.

---

## Quick Start

### Minimal valid AgentCard

```json
{
  "agent_id": "01HZQK3P8EMXR9V7T5N2W4J6C0",
  "name": "My Agent",
  "version": "1.0.0",
  "capabilities": [
    {
      "id": "text.generate",
      "description": "Generate text given a prompt"
    }
  ],
  "endpoint": {
    "protocol": "http",
    "url": "https://agent.example.com/api"
  }
}
```

### Generate an `agent_id`

`agent_id` is a [ULID](https://github.com/ulid/spec) encoded as Crockford Base32 (26 chars).

```bash
# Python
python3 -c "import uuid; print(str(uuid.uuid4()).replace('-','').upper()[:26])"

# Rust  (Cargo.toml: ulid = "1.0")
# let id = ulid::Ulid::new().to_string();

# Node.js
npm install ulid && node -e "const {ulid} = require('ulid'); console.log(ulid())"
```

---

## Schema Reference

Full JSON Schema: [`schema.json`](./schema.json)

### Top-level fields

| Field | Req | Type | Description |
|---|---|---|---|
| `agent_id` | ✓ | string | ULID Crockford Base32 26-char — globally unique |
| `name` | ✓ | string | Display name 1–128 chars |
| `version` | ✓ | string | semver 2.0 |
| `capabilities` | ✓ | array | ≥1 capability |
| `endpoint` | ✓ | object | How to reach this agent |
| `pricing` | — | object | Cost model: Joules + optional fiat |
| `metadata` | — | object | `pacr:*` fields derived from ledger |

### Capability fields

| Field | Req | Description |
|---|---|---|
| `id` | ✓ | Dot-namespaced: `text.generate`, `vision.classify` |
| `description` | ✓ | Human-readable description |
| `tags` | — | Semantic tags for routing |
| `input_schema` | — | JSON Schema for input; null = unstructured |
| `output_schema` | — | JSON Schema for output |

### Endpoint fields

| Field | Req | Description |
|---|---|---|
| `protocol` | ✓ | `http` · `grpc` · `mcp` · `ws` · `custom` |
| `url` | ✓ | Endpoint URL |
| `health_check` | — | Optional health-check URL |
| `auth` | — | Auth config; null = no auth |

### Pricing fields

| Field | Description |
|---|---|
| `joules_per_request` | **Canonical settlement unit.** Min: 2.854×10⁻²¹ J (Landauer floor at 300 K) |
| `latency_ms_p50` | p50 latency derived from PACR Ω history |
| `currency` | ISO 4217 or token symbol |
| `fiat_per_request` | Cost in fiat/token (requires `currency`) |

### PACR Metadata

`pacr:*` fields are **derived from the causal ledger** by the CSO — not self-declared.

| Key | Source | Description |
|---|---|---|
| `pacr:trust_tier` | CSO ρ + count | `Verified` · `Established` · `Basic` · `Untrusted` · `Banned` |
| `pacr:rho_ema` | CSO | ρ = ΔΦ / Λ (causal return rate EMA) |
| `pacr:substrate_scope` | Self-declared | Deployment substrate: `"M1-Ultra"`, `"AWS-Graviton"`, etc. |
| `pacr:substrate_gap` | Self-declared | Known validation gaps |
| `pacr:ossification_risk` | Computed | `high` · `medium` · `low` — substrate diversity health |

---

## Agent Discovery

Place your AgentCard at `.well-known/agent.json` on your domain:

```
https://your-agent.example.com/.well-known/agent.json
```

Follows [Well-Known URIs RFC 8615](https://www.rfc-editor.org/rfc/rfc8615).

---

## Validators

### Rust

```rust
use agentcard_validator::validate;

let json = std::fs::read_to_string("my-agent.json")?;
let errors = validate(&json);
if errors.is_empty() { println!("Valid AgentCard"); }
else { for e in &errors { eprintln!("Error: {e}"); } }
```

### Python

```python
import json, jsonschema
schema = json.load(open("schema.json"))
card   = json.load(open("my-agent.json"))
jsonschema.validate(card, schema)  # raises ValidationError on failure
```

### Node.js

```js
const Ajv = require("ajv/dist/2020");
const ajv = new Ajv();
const valid = ajv.validate(require("./schema.json"), require("./my-agent.json"));
if (!valid) console.error(ajv.errors);
```

---

## Examples

| File | Agent type |
|---|---|
| [`examples/llm-agent.json`](./examples/llm-agent.json) | Language model |
| [`examples/code-review-agent.json`](./examples/code-review-agent.json) | Code review |
| [`examples/data-pipeline-agent.json`](./examples/data-pipeline-agent.json) | ETL pipeline |

---

## Design Invariants

1. **Pure data** — no execution logic, no RPC, no network calls
2. **Zero core dependency** — any framework can parse without Aevum Core
3. **Append-only schema** — existing field semantics never change
4. **Metadata is derived** — `pacr:*` from ledger, not self-report
5. **Landauer floor** — `joules_per_request` ≥ 2.854×10⁻²¹ J at 300 K

---

## Contributing

1. Fork → add validator or example → `cargo test` → Pull Request
2. Issues and RFC proposals welcome
3. All contributions are under Apache 2.0 + the patent non-reservation in [NOTICE](./NOTICE)

---

## License

### Code — Apache 2.0

Reference implementation and validators: [Apache 2.0](./LICENSE.en) with **explicit patent grant** (Section 3).

See [NOTICE](./NOTICE): **no patent claims on the AgentCard schema or wire format**.

### Specification — CC-BY 4.0

`SPEC-CAUSAL-TOPOLOGY.md`, `schema.json`, `*-SPEC.md` files:
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).

Allows incorporation into RFCs, standards documents, third-party protocol stacks — **attribution only**, no separate agreement needed.

### Public Domain Posture

AgentCard aims to be the TCP/IP of AI2AI — owned by no one, usable by everyone.
The maintainers commit (recorded in [NOTICE](./NOTICE) and git history):

- No proprietary terms or dual-licensing, ever
- No patent claims on any part of the schema
- No commercial edition with withheld capabilities

Any fork preserving this NOTICE is the authoritative continuation of the project.
