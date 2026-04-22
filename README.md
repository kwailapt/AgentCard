# AgentCard

> **AgentCard is to A2A what HTTP headers are to the web.**
> **AgentCard 之於 AI2AI，如同 HTTP 標頭之於 Web。**

A standardized, machine-parseable declaration of agent identity and capability.
Pure data schema. Zero execution logic. Works with any framework.

標準化、機器可解析的 Agent 身份與能力聲明。
純數據規格，無執行邏輯，適用於任何框架。

**Schema version / 規格版本:** 1.0 · **License / 授權:** Apache 2.0 + CC-BY 4.0 (spec)

---

## What is AgentCard? / 什麼是 AgentCard？

When HTTP was designed, headers solved a critical bootstrapping problem: how does a server
know what format a client accepts before any negotiation happens?

HTTP 設計時，標頭解決了一個關鍵的啟動問題：在任何協商發生之前，伺服器如何知道客戶端接受什麼格式？

AgentCard solves the same problem for agent-to-agent (A2A) communication:
AgentCard 為 Agent 對 Agent（A2A）通訊解決了同樣的問題：

| HTTP Header | AgentCard field |
|---|---|
| `Content-Type` | `capabilities[].id` |
| `Accept` | `capabilities[].input_schema` / `output_schema` |
| `Authorization` | `endpoint.auth` |
| `Server` / `User-Agent` | `name` + `version` |
| Cache headers | `metadata.pacr:*` (derived from ledger / 帳本衍生，非自報) |

An AgentCard is a **pure data document** — no network calls, no execution logic.
Any framework can parse it. It travels as the Payload (P) inside a PACR record.

AgentCard 是**純數據文件**——無網路調用，無執行邏輯。
任何框架均可解析。以 PACR 記錄的 Payload（P）字段傳輸。

---

## Quick Start / 快速開始

### Minimal valid AgentCard / 最小合法 AgentCard

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

### Generate an `agent_id` / 生成 `agent_id`

`agent_id` is a [ULID](https://github.com/ulid/spec) encoded as Crockford Base32 (26 chars).
`agent_id` 是以 Crockford Base32 編碼的 [ULID](https://github.com/ulid/spec)（26 字符）。

```bash
# Python
python3 -c "import uuid; print(str(uuid.uuid4()).replace('-','').upper()[:26])"

# Rust  (Cargo.toml: ulid = "1.0")
# let id = ulid::Ulid::new().to_string();

# Node.js
npm install ulid && node -e "const {ulid} = require('ulid'); console.log(ulid())"
```

---

## Schema Reference / 規格參考

Full JSON Schema: [`schema.json`](./schema.json)

### Top-level fields / 頂層字段

| Field | Req | Type | Description / 說明 |
|---|---|---|---|
| `agent_id` | ✓ | string | ULID Crockford Base32 26-char — globally unique / 全局唯一身份 |
| `name` | ✓ | string | Display name 1–128 chars / 顯示名稱 |
| `version` | ✓ | string | semver 2.0 |
| `capabilities` | ✓ | array | ≥1 capability / 至少一項能力聲明 |
| `endpoint` | ✓ | object | How to reach this agent / 聯繫方式 |
| `pricing` | — | object | Cost model: Joules + optional fiat / 定價：焦耳 + 可選法幣 |
| `metadata` | — | object | `pacr:*` fields derived from ledger / 帳本衍生字段 |

### Capability fields / 能力字段

| Field | Req | Description / 說明 |
|---|---|---|
| `id` | ✓ | Dot-namespaced: `text.generate`, `vision.classify` |
| `description` | ✓ | Human-readable description / 可讀描述 |
| `tags` | — | Semantic tags for routing / 語義標籤 |
| `input_schema` | — | JSON Schema for input; null = unstructured / 輸入格式 |
| `output_schema` | — | JSON Schema for output / 輸出格式 |

### Endpoint fields / 端點字段

| Field | Req | Description / 說明 |
|---|---|---|
| `protocol` | ✓ | `http` · `grpc` · `mcp` · `ws` · `custom` |
| `url` | ✓ | Endpoint URL / 端點地址 |
| `health_check` | — | Optional health-check URL / 健康檢查 |
| `auth` | — | Auth config; null = no auth / 認證配置 |

### Pricing fields / 定價字段

| Field | Description / 說明 |
|---|---|
| `joules_per_request` | **Canonical settlement unit.** Min: 2.854×10⁻²¹ J (Landauer floor at 300 K) / **標準結算單位**，蘭道爾下界 |
| `latency_ms_p50` | p50 latency derived from PACR Ω history / 基於 PACR Ω 歷史的 p50 延遲 |
| `currency` | ISO 4217 or token symbol / 法幣或代幣符號 |
| `fiat_per_request` | Cost in fiat/token (requires `currency`) / 法幣費用 |

### PACR Metadata / PACR 元數據

`pacr:*` fields are **derived from the causal ledger** by the CSO — not self-declared.

`pacr:*` 字段由 CSO（因果結算預言機）從帳本衍生，**非 Agent 自報**。

| Key | Source | Description / 說明 |
|---|---|---|
| `pacr:trust_tier` | CSO ρ + count | `Verified` · `Established` · `Basic` · `Untrusted` · `Banned` |
| `pacr:rho_ema` | CSO | ρ = ΔΦ / Λ (causal return rate EMA / 因果回報率) |
| `pacr:substrate_scope` | Self-declared | Deployment substrate: `"M1-Ultra"`, `"AWS-Graviton"`, etc. |
| `pacr:substrate_gap` | Self-declared | Known validation gaps / 已知驗證缺口 |
| `pacr:ossification_risk` | Computed | `high` · `medium` · `low` — substrate diversity health / 基質多樣性健康度 |

---

## Agent Discovery / Agent 發現

Place your AgentCard at `.well-known/agent.json` on your domain:
將 AgentCard 放置於域名下的 `.well-known/agent.json`：

```
https://your-agent.example.com/.well-known/agent.json
```

Follows [Well-Known URIs RFC 8615](https://www.rfc-editor.org/rfc/rfc8615).
遵循 [Well-Known URIs RFC 8615](https://www.rfc-editor.org/rfc/rfc8615) 慣例。

---

## Validators / 驗證器

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

## Examples / 範例

| File / 文件 | Agent type / 類型 |
|---|---|
| [`examples/llm-agent.json`](./examples/llm-agent.json) | Language model / 語言模型 |
| [`examples/code-review-agent.json`](./examples/code-review-agent.json) | Code review / 代碼審查 |
| [`examples/data-pipeline-agent.json`](./examples/data-pipeline-agent.json) | ETL pipeline / 數據管道 |

---

## Design Invariants / 設計不變量

1. **Pure data / 純數據** — no execution logic, no RPC, no network calls / 無執行邏輯
2. **Zero core dependency / 零核心依賴** — any framework can parse without Aevum Core / 任何框架可直接解析
3. **Append-only schema / 只增規格** — existing field semantics never change / 現有字段語義永不改變
4. **Metadata is derived / 元數據為衍生值** — `pacr:*` from ledger, not self-report / `pacr:*` 來自帳本
5. **Landauer floor / 蘭道爾下界** — `joules_per_request` ≥ 2.854×10⁻²¹ J at 300 K

---

## Contributing / 貢獻

1. Fork → add validator or example → `cargo test` → Pull Request
2. Issues and RFC proposals welcome / 歡迎提交 Issue 和 RFC 提案
3. All contributions are under Apache 2.0 + the patent non-reservation in [NOTICE](./NOTICE) / 所有貢獻採用 Apache 2.0 並受 NOTICE 中專利非保留條款約束

---

## License / 授權

### Code / 代碼 — Apache 2.0

Reference implementation and validators: [Apache 2.0](./LICENSE) with **explicit patent grant** (Section 3).

參考實現與驗證器：[Apache 2.0](./LICENSE)，含**明確專利授權**（第三條）。
見 [NOTICE](./NOTICE)：對 AgentCard 規格及線路格式**不保留任何專利主張**。

### Specification / 規格文件 — CC-BY 4.0

`SPEC-CAUSAL-TOPOLOGY.md`, `schema.json`, `*-SPEC.md` files:
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).

允許引入 RFC、標準文件、第三方協議棧，**僅需署名**，無需另行協議。

### Public Domain Posture / 公域立場

AgentCard aims to be the TCP/IP of AI2AI — owned by no one, usable by everyone.
The maintainers commit (recorded in [NOTICE](./NOTICE) and git history):

AgentCard 旨在成為 AI2AI 的 TCP/IP——無人擁有，人人可用。
維護者承諾（記錄於 [NOTICE](./NOTICE) 及 git 歷史）：

- No proprietary terms or dual-licensing, ever / 永不添加專有條款或雙重授權
- No patent claims on any part of the schema / 不申請任何規格相關專利
- No commercial edition with withheld capabilities / 不創建功能受限的商業版本

Any fork preserving this NOTICE is the authoritative continuation of the project.
任何保留此 NOTICE 的複刻版本均視為本項目的正統延續。
