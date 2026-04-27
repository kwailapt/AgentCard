//! # pacr-types
//!
//! Pillar: ALL. PACR field: ALL.
//!
//! **PACR (Physically Annotated Causal Record) — the wire-format protocol for
//! Reality Transition Events.**
//!
//! Each record captures exactly one causal step: an intervention `do(a)` on a
//! substrate state `s`, the resulting state `s'`, thermodynamic cost Λ, the
//! resource triple Ω, the cognitive split Γ, and an opaque payload P that
//! carries substrate-level semantics (including `InterventionKind` tag when
//! present). The 6-tuple is the minimum sufficient statistic for any
//! verifiable, replayable, rights-aware causal claim about the physical world.
//!
//! ```text
//! R = (ι,  Π,              Λ,            Ω,               Γ,               P)
//!      id  predecessors    landauer_cost  resources         cognitive_split   payload
//!                                                                              └── InterventionKind (optional, Phase 15B)
//! ```
//!
//! | Field | Module     | Physical axiom                                    |
//! |-------|------------|---------------------------------------------------|
//! | ι     | record     | Logical a priori (referential necessity)           |
//! | Π     | record     | Special relativity → causal partial order (Pearl DAG) |
//! | Λ     | landauer   | Landauer's principle (Second Law)                 |
//! | Ω     | ets        | Conservation laws + Margolus–Levitin              |
//! | Γ     | complexity | Computational mechanics (arXiv:2601.03220) / Free-energy principle |
//! | P     | record     | Completeness axiom — carries `InterventionKind` magic-header payload |
//!
//! ## Rules
//! - Schema is **append-only**: existing field semantics NEVER change.
//! - This crate has **zero dependencies** beyond serde, smallvec, bytes, thiserror.
//! - `#![forbid(unsafe_code)]` is unconditional: no exceptions.
//! - `InterventionKind` is encoded in P behind a 4-byte `b"PACR"` magic header;
//!   legacy payloads without the header decode as `InterventionKind::Observe`.

#![forbid(unsafe_code)]
#![deny(clippy::all, clippy::pedantic)]
#![allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::similar_names,
    clippy::doc_markdown,
    clippy::must_use_candidate,
    clippy::needless_pass_by_value,
    clippy::missing_panics_doc,
    clippy::missing_errors_doc,
    clippy::return_self_not_must_use,
    clippy::unreadable_literal
)]

pub mod complexity;
pub mod estimate;
pub mod ets;
pub mod landauer;
pub mod record;

// ── Top-level re-exports (the public API of this crate) ──────────────────────

pub use complexity::CognitiveSplit;
pub use estimate::{Estimate, EstimateError};
pub use ets::{PhysicsViolation, ResourceTriple};
pub use landauer::{landauer_floor_joules, LandauerCost, H_BAR, K_B, LANDAUER_JOULES_300K};
pub use record::{
    BuildError, CausalId, InterventionDecodeError, InterventionKind, PacrBuilder, PacrRecord,
    Payload, PredecessorSet, TaggedPayload, ValidationIssue, PACR_MAGIC,
};
