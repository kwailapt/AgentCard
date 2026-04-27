# pacr-types

Reference implementation of the **PACR 6-tuple** (Physically Annotated Causal Record)
as defined in [draft-aevum-causal-intervention-record-00](https://datatracker.ietf.org/doc/draft-aevum-causal-intervention-record/).

## What is PACR?

PACR is a wire-format protocol for representing one verifiable causal-intervention event
between autonomous agents. A PACR record is the six-tuple:

```
R = (ι, Π, Λ, Ω, Γ, P)
```

| Symbol | Name                | Description                                              |
|--------|---------------------|----------------------------------------------------------|
| ι      | Causal Identity     | 128-bit unique identifier (ULID / UUIDv7)                |
| Π      | Predecessor Set     | Causal predecessors (partial order, not timestamps)      |
| Λ      | Landauer Cost       | Theoretical energy floor in joules (bits × k_B × T × ln2) |
| Ω      | Resource Triple     | Actually measured (energy, time, space)                   |
| Γ      | Cognitive Split     | Statistical complexity S_T + entropy rate H_T            |
| P      | Payload             | Opaque bytes with optional Pearl-hierarchy intervention tag |

## Intervention Kinds (Pearl's do-calculus hierarchy)

| Byte | Kind           | Pearl Rung |
|------|----------------|------------|
| 0x00 | Observe        | 1          |
| 0x01 | DoPhysical     | 2          |
| 0x02 | DoDigital      | 2          |
| 0x03 | DoChemical     | 2          |
| 0x04 | DoGenetic      | 2          |
| 0x05 | Counterfactual | 3          |

## Usage

```rust
use pacr_types::{PacrBuilder, Estimate, CausalId};

let record = PacrBuilder::new()
    .id(CausalId::generate())
    .predecessors(vec![])
    .landauer_cost(Estimate::exact(2.854e-21))
    .resource_triple(energy, time, space)
    .cognitive_split(s_t, h_t, info_gain)
    .payload(bytes::Bytes::new())
    .build()
    .expect("valid PACR record");

let violations = record.validate();
assert!(violations.is_empty());
```

## Safety

This crate carries `#![forbid(unsafe_code)]` unconditionally.
It is the cryptographic-grade trust root of the PACR ecosystem.

## Related

- [AgentCard](https://github.com/kwailapt/AgentCard) — declares what an agent *is*
- [PACR draft](https://datatracker.ietf.org/doc/draft-aevum-causal-intervention-record/) — records what an agent *did*

## License

Apache-2.0
