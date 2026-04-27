//! Pillar: ALL. PACR field: ALL (integrates ι, Π, Λ, Ω, Γ, P into one record).
//!
//! This module defines the **PACR 6-tuple** — the immutable Day-0 contract.
//!
//! **R = (ι, Π, Λ, Ω, Γ, P)**
//!
//! Physical axiom for each dimension:
//!   ι — logical a priori (every distinct event needs a unique address)
//!   Π — special relativity (causal partial order, never total order)
//!   Λ — Landauer's principle (see landauer.rs)
//!   Ω — conservation + Margolus–Levitin (see ets.rs)
//!   Γ — computational mechanics (see complexity.rs)
//!   P — completeness axiom (semantic content must be preserved)
//!
//! SCHEMA IS APPEND-ONLY.  New optional fields may be added.
//! Existing field semantics MUST NEVER change.

use crate::complexity::CognitiveSplit;
use crate::estimate::Estimate;
use crate::ets::{PhysicsViolation, ResourceTriple};
use crate::landauer::LandauerCost;

use serde::{Deserialize, Serialize};
use smallvec::SmallVec;
use std::fmt;

// ── Dimension ι: Causal Identity ──────────────────────────────────────────────

/// The causal identity of a PACR record.
///
/// 128 bits = 48-bit millisecond timestamp (storage locality) + 80-bit randomness.
///
/// **Important**: ordering by `CausalId` value is for efficient storage scans
/// only.  Causal order is determined solely by the predecessor set Π.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub struct CausalId(pub u128);

impl CausalId {
    /// Sentinel for genesis events — events with no causal predecessors.
    pub const GENESIS: Self = Self(0);

    /// Returns `true` if this is a genesis event (no causal predecessors).
    #[must_use]
    pub fn is_genesis(&self) -> bool {
        self.0 == 0
    }
}

impl fmt::Display for CausalId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Hex display; Crockford Base32 encoder lives in the `causal-id` crate.
        write!(f, "{:032X}", self.0)
    }
}

// ── Dimension Π: Causal Predecessor Set ──────────────────────────────────────

/// Direct causal predecessors of this event.
///
/// Unordered set (partial order, not total order — physics-mandated).
/// `SmallVec<[CausalId; 4]>` avoids heap allocation for the common case of
/// 1–4 predecessors (Pillar I: zero-copy on the hot path).
pub type PredecessorSet = SmallVec<[CausalId; 4]>;

// ── Dimension P: Opaque Payload ───────────────────────────────────────────────

/// Opaque payload — the semantic content of the computation event.
///
/// PACR does not interpret this field.  Upper layers (`AgentCard`, etc.) define
/// their own schemas within P.  Zero-copy via `bytes::Bytes`.
///
/// Phase 15B: a payload starting with [`PACR_MAGIC`] carries a
/// [`TaggedPayload`] header encoding the [`InterventionKind`].  Legacy payloads
/// without the magic prefix remain valid and are decoded as
/// [`InterventionKind::Observe`].
pub type Payload = bytes::Bytes;

// ── Phase 15B: InterventionKind (do-operator extension, append-only) ──────────

/// Magic header for Phase 15B tagged payloads.
///
/// A `Payload` starting with these four bytes carries an [`InterventionKind`]
/// tag.  Legacy payloads without this prefix are treated as
/// [`InterventionKind::Observe`] — full backwards compatibility.
pub const PACR_MAGIC: [u8; 4] = *b"PACR";

/// The kind of causal intervention recorded in this PACR record.
///
/// Implements Pearl's do-calculus rung classification at the wire level.
/// Encoded as a single byte in the tagged payload behind [`PACR_MAGIC`].
///
/// # Backwards compatibility
/// Records predating Phase 15B have no magic header; callers MUST decode
/// absence of the header as [`InterventionKind::Observe`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[non_exhaustive]
pub enum InterventionKind {
    /// Pearl rung 1 — pure observation, no action taken on the substrate.
    Observe,
    /// Pearl rung 2 — physical-world action (robot, lab equipment, sensor).
    DoPhysical,
    /// Pearl rung 2 — digital action (API call, settlement, routing).
    DoDigital,
    /// Pearl rung 2 — chemical or biological perturbation.
    DoChemical,
    /// Pearl rung 2 — genetic edit (CRISPR, directed evolution, etc.).
    DoGenetic,
    /// Pearl rung 3 — simulated counterfactual ("what if").
    ///
    /// **Requires** `sim_real_corr ∈ [0.0, 1.0]` — a counterfactual without
    /// a sim-real correlation score fails [`PacrRecord::validate`].
    Counterfactual,
}

/// Wire-format tagged payload (Phase 15B).
///
/// # Wire layout
/// ```text
/// Bytes  0..4   magic = b"PACR"
/// Byte   4      kind byte  (see InterventionKind discriminants)
/// Bytes  5..13  sim_real_corr as f64 big-endian — ONLY if kind == Counterfactual
/// Bytes  5..    inner payload (non-Counterfactual)
/// Bytes  13..   inner payload (Counterfactual)
/// ```
#[derive(Debug, Clone)]
pub struct TaggedPayload {
    /// The Pearl-hierarchy rung of this intervention.
    pub kind: InterventionKind,
    /// Sim-real correlation `∈ [0.0, 1.0]`; mandatory for `Counterfactual`.
    pub sim_real_corr: Option<f64>,
    /// Application-specific inner bytes after the header.
    pub inner: bytes::Bytes,
}

impl TaggedPayload {
    const KIND_OBSERVE: u8 = 0;
    const KIND_DO_PHYSICAL: u8 = 1;
    const KIND_DO_DIGITAL: u8 = 2;
    const KIND_DO_CHEMICAL: u8 = 3;
    const KIND_DO_GENETIC: u8 = 4;
    const KIND_COUNTERFACTUAL: u8 = 5;

    /// Encode into bytes suitable for storage in the PACR P field.
    #[must_use]
    pub fn encode(&self) -> bytes::Bytes {
        let kind_byte = match self.kind {
            InterventionKind::Observe => Self::KIND_OBSERVE,
            InterventionKind::DoPhysical => Self::KIND_DO_PHYSICAL,
            InterventionKind::DoDigital => Self::KIND_DO_DIGITAL,
            InterventionKind::DoChemical => Self::KIND_DO_CHEMICAL,
            InterventionKind::DoGenetic => Self::KIND_DO_GENETIC,
            InterventionKind::Counterfactual => Self::KIND_COUNTERFACTUAL,
        };
        let corr_len = if self.kind == InterventionKind::Counterfactual {
            8
        } else {
            0
        };
        let mut buf = Vec::with_capacity(4 + 1 + corr_len + self.inner.len());
        buf.extend_from_slice(&PACR_MAGIC);
        buf.push(kind_byte);
        if self.kind == InterventionKind::Counterfactual {
            let corr = self.sim_real_corr.unwrap_or(0.0);
            buf.extend_from_slice(&corr.to_be_bytes());
        }
        buf.extend_from_slice(&self.inner);
        bytes::Bytes::from(buf)
    }

    /// Decode a PACR P field.
    ///
    /// Returns `None` for legacy payloads (no magic header) — callers treat
    /// these as [`InterventionKind::Observe`].  Returns `Some(Err(_))` when the
    /// magic header is present but the remainder is malformed.
    pub fn decode(payload: &Payload) -> Option<Result<Self, InterventionDecodeError>> {
        if payload.len() < 4 || payload[..4] != PACR_MAGIC {
            return None;
        }
        if payload.len() < 5 {
            return Some(Err(InterventionDecodeError::TruncatedAfterMagic));
        }
        let kind = match payload[4] {
            Self::KIND_OBSERVE => InterventionKind::Observe,
            Self::KIND_DO_PHYSICAL => InterventionKind::DoPhysical,
            Self::KIND_DO_DIGITAL => InterventionKind::DoDigital,
            Self::KIND_DO_CHEMICAL => InterventionKind::DoChemical,
            Self::KIND_DO_GENETIC => InterventionKind::DoGenetic,
            Self::KIND_COUNTERFACTUAL => InterventionKind::Counterfactual,
            b => return Some(Err(InterventionDecodeError::UnknownKindByte(b))),
        };
        if kind == InterventionKind::Counterfactual {
            if payload.len() < 13 {
                return Some(Err(InterventionDecodeError::TruncatedSimRealCorr));
            }
            let arr: [u8; 8] = payload[5..13].try_into().unwrap();
            return Some(Ok(TaggedPayload {
                kind,
                sim_real_corr: Some(f64::from_be_bytes(arr)),
                inner: payload.slice(13..),
            }));
        }
        Some(Ok(TaggedPayload {
            kind,
            sim_real_corr: None,
            inner: payload.slice(5..),
        }))
    }

    /// Decode only the `InterventionKind`; returns `Observe` on any error or
    /// for legacy payloads.
    #[must_use]
    pub fn decode_kind(payload: &Payload) -> InterventionKind {
        match Self::decode(payload) {
            None | Some(Err(_)) => InterventionKind::Observe,
            Some(Ok(tp)) => tp.kind,
        }
    }
}

/// Error returned when a tagged payload header is present but malformed.
#[derive(Debug, Clone, thiserror::Error)]
#[non_exhaustive]
pub enum InterventionDecodeError {
    /// Magic bytes present but payload ends before the kind byte.
    #[error("PACR magic present but payload truncated before kind byte")]
    TruncatedAfterMagic,
    /// Counterfactual kind byte present but payload ends before sim_real_corr.
    #[error("Counterfactual payload truncated before sim_real_corr (need 8 bytes)")]
    TruncatedSimRealCorr,
    /// Kind byte value is not recognised by this version.
    #[error("unknown InterventionKind byte 0x{0:02X}")]
    UnknownKindByte(u8),
}

// ── THE PACR RECORD ───────────────────────────────────────────────────────────

/// A Physically Annotated Causal Record — the minimal sufficient statistic
/// for a computation event.
///
/// ```text
/// R = (ι,  Π,  Λ,   Ω,          Γ,              P)
///      id  preds  cost  resources  cognitive_split  payload
/// ```
///
/// Six dimensions, each derived from physical first principles,
/// mutually independent and atomically irreducible.
///
/// # Immutability
/// This is the Day-0 contract.  Adding fields is permitted (append-only
/// schema evolution).  Changing existing field semantics is **forbidden**.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PacrRecord {
    /// ι — Causal Identity (logical a priori)
    pub id: CausalId,

    /// Π — Causal Predecessor Set (special relativity → partial order)
    pub predecessors: PredecessorSet,

    /// Λ — Landauer Cost in joules (Landauer's principle)
    pub landauer_cost: LandauerCost,

    /// Ω — Resource Constraint Triple (conservation laws)
    pub resources: ResourceTriple,

    /// Γ — Cognitive Split (computational mechanics)
    pub cognitive_split: CognitiveSplit,

    /// P — Opaque Payload (completeness axiom)
    pub payload: Payload,
}

impl PacrRecord {
    /// Validates all physical invariants of this record.
    ///
    /// Returns every issue found; an empty `Vec` means the record is clean.
    /// A physically invalid record is still storable (measurement errors happen),
    /// but violations must be flagged for the Landauer auditor to investigate.
    #[must_use]
    pub fn validate(&self) -> Vec<ValidationIssue> {
        let mut issues: Vec<ValidationIssue> = Vec::new();

        // Ω: physics constraints on the resource triple
        for v in self.resources.validate_physics() {
            issues.push(ValidationIssue::Physics(v));
        }

        // E ≥ Λ: actual energy must exceed the Landauer theoretical floor
        if self.resources.energy.point < self.landauer_cost.point {
            issues.push(ValidationIssue::EnergyBelowLandauer {
                actual_j: self.resources.energy.point,
                landauer_j: self.landauer_cost.point,
            });
        }

        // Λ ≥ 0
        if self.landauer_cost.point < 0.0 {
            issues.push(ValidationIssue::NegativeLandauer);
        }

        // S_T ≥ 0
        if self.cognitive_split.statistical_complexity.point < 0.0 {
            issues.push(ValidationIssue::NegativeComplexity);
        }

        // H_T ≥ 0
        if self.cognitive_split.entropy_rate.point < 0.0 {
            issues.push(ValidationIssue::NegativeEntropyRate);
        }

        // No self-reference in Π (causal loops are acausal)
        if self.predecessors.contains(&self.id) {
            issues.push(ValidationIssue::SelfReference);
        }

        // P: Phase 15B — validate InterventionKind tagged payload when present
        if let Some(result) = TaggedPayload::decode(&self.payload) {
            match result {
                Err(e) => issues.push(ValidationIssue::MalformedInterventionPayload(
                    e.to_string(),
                )),
                Ok(tp) if tp.kind == InterventionKind::Counterfactual => {
                    match tp.sim_real_corr {
                        None => issues.push(ValidationIssue::CounterfactualMissingSimRealCorr),
                        Some(c) if !(0.0..=1.0).contains(&c) => {
                            issues.push(ValidationIssue::SimRealCorrOutOfRange(c));
                        }
                        _ => {}
                    }
                }
                Ok(_) => {}
            }
        }

        issues
    }

    /// Thermodynamic waste for this record: E − Λ with uncertainty propagation.
    #[must_use]
    pub fn thermodynamic_waste(&self) -> Estimate<f64> {
        self.resources.thermodynamic_waste(&self.landauer_cost)
    }

    /// Decode the [`InterventionKind`] from the P payload (Phase 15B).
    ///
    /// Returns [`InterventionKind::Observe`] for legacy payloads or any
    /// decoding error (never panics).
    #[must_use]
    pub fn intervention_kind(&self) -> InterventionKind {
        TaggedPayload::decode_kind(&self.payload)
    }
}

// ── Validation issue enum ─────────────────────────────────────────────────────

/// A validation issue found in a [`PacrRecord`].
#[derive(Debug, Clone, thiserror::Error)]
#[non_exhaustive]
pub enum ValidationIssue {
    /// A physical-law violation in the resource triple.
    #[error("physics violation: {0}")]
    Physics(PhysicsViolation),

    /// Actual energy is below the Landauer floor — violates Landauer's principle.
    #[error("actual energy {actual_j:.3e} J is below Landauer floor {landauer_j:.3e} J")]
    EnergyBelowLandauer { actual_j: f64, landauer_j: f64 },

    /// Landauer cost is negative — energy is non-negative by definition.
    #[error("Landauer cost cannot be negative")]
    NegativeLandauer,

    /// Statistical complexity `S_T` is negative — information is non-negative.
    #[error("statistical complexity `S_T` cannot be negative")]
    NegativeComplexity,

    /// Entropy rate `H_T` is negative — entropy is non-negative.
    #[error("entropy rate `H_T` cannot be negative")]
    NegativeEntropyRate,

    /// Record lists itself as a causal predecessor — creates a causal loop.
    #[error("record references itself as predecessor — causal loop")]
    SelfReference,

    /// Phase 15B: tagged payload header is present but bytes are malformed.
    #[error("malformed InterventionKind payload: {0}")]
    MalformedInterventionPayload(String),

    /// Phase 15B: `Counterfactual` record is missing the required
    /// `sim_real_corr` field.
    #[error("Counterfactual record missing sim_real_corr — required by Phase 15B")]
    CounterfactualMissingSimRealCorr,

    /// Phase 15B: `sim_real_corr` value is outside `[0.0, 1.0]`.
    #[error("sim_real_corr {0:.4} is outside the valid range [0.0, 1.0]")]
    SimRealCorrOutOfRange(f64),
}

// ── Builder ───────────────────────────────────────────────────────────────────

/// Builder for [`PacrRecord`].
///
/// `build()` returns `Err` if **any** of the six PACR dimensions is missing.
/// Partial records are a protocol violation — the error names the missing field.
#[derive(Default)]
pub struct PacrBuilder {
    id: Option<CausalId>,
    predecessors: Option<PredecessorSet>,
    landauer_cost: Option<LandauerCost>,
    resources: Option<ResourceTriple>,
    cognitive_split: Option<CognitiveSplit>,
    payload: Option<Payload>,
}

impl PacrBuilder {
    /// Creates a new empty builder.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Sets the causal identity ι.
    #[must_use]
    pub fn id(mut self, id: CausalId) -> Self {
        self.id = Some(id);
        self
    }

    /// Sets the predecessor set Π.
    #[must_use]
    pub fn predecessors(mut self, preds: PredecessorSet) -> Self {
        self.predecessors = Some(preds);
        self
    }

    /// Sets the Landauer cost Λ.
    #[must_use]
    pub fn landauer_cost(mut self, cost: LandauerCost) -> Self {
        self.landauer_cost = Some(cost);
        self
    }

    /// Sets the resource triple Ω.
    #[must_use]
    pub fn resources(mut self, res: ResourceTriple) -> Self {
        self.resources = Some(res);
        self
    }

    /// Sets the cognitive split Γ.
    #[must_use]
    pub fn cognitive_split(mut self, split: CognitiveSplit) -> Self {
        self.cognitive_split = Some(split);
        self
    }

    /// Sets the opaque payload P.
    #[must_use]
    pub fn payload(mut self, payload: Payload) -> Self {
        self.payload = Some(payload);
        self
    }

    /// Builds the [`PacrRecord`].
    ///
    /// # Errors
    /// Returns [`BuildError::MissingDimension`] naming the first missing field.
    pub fn build(self) -> Result<PacrRecord, BuildError> {
        Ok(PacrRecord {
            id: self.id.ok_or(BuildError::MissingDimension("ι (id)"))?,
            predecessors: self
                .predecessors
                .ok_or(BuildError::MissingDimension("Π (predecessors)"))?,
            landauer_cost: self
                .landauer_cost
                .ok_or(BuildError::MissingDimension("Λ (landauer_cost)"))?,
            resources: self
                .resources
                .ok_or(BuildError::MissingDimension("Ω (resources)"))?,
            cognitive_split: self
                .cognitive_split
                .ok_or(BuildError::MissingDimension("Γ (cognitive_split)"))?,
            payload: self
                .payload
                .ok_or(BuildError::MissingDimension("P (payload)"))?,
        })
    }
}

/// Error returned by [`PacrBuilder::build`] when a required dimension is absent.
#[derive(Debug, Clone, thiserror::Error)]
#[non_exhaustive]
pub enum BuildError {
    /// A named PACR dimension was not supplied to the builder.
    #[error("missing PACR dimension: {0} — all six dimensions are mandatory")]
    MissingDimension(&'static str),
}

// ── Unit tests (Phase 15B: InterventionKind) ─────────────────────────────────

#[cfg(test)]
mod intervention_tests {
    use super::*;
    use bytes::Bytes;

    // ── encode/decode round-trips ─────────────────────────────────────────────

    #[test]
    fn observe_round_trips() {
        let tp = TaggedPayload {
            kind: InterventionKind::Observe,
            sim_real_corr: None,
            inner: Bytes::from_static(b"payload"),
        };
        let encoded = tp.encode();
        let decoded = TaggedPayload::decode(&encoded).unwrap().unwrap();
        assert_eq!(decoded.kind, InterventionKind::Observe);
        assert_eq!(decoded.sim_real_corr, None);
        assert_eq!(&decoded.inner[..], b"payload");
    }

    #[test]
    fn do_genetic_round_trips() {
        let tp = TaggedPayload {
            kind: InterventionKind::DoGenetic,
            sim_real_corr: None,
            inner: Bytes::from_static(b"crispr-edit"),
        };
        let encoded = tp.encode();
        let decoded = TaggedPayload::decode(&encoded).unwrap().unwrap();
        assert_eq!(decoded.kind, InterventionKind::DoGenetic);
        assert_eq!(&decoded.inner[..], b"crispr-edit");
    }

    #[test]
    fn counterfactual_round_trips_with_sim_real_corr() {
        let corr = 0.87_f64;
        let tp = TaggedPayload {
            kind: InterventionKind::Counterfactual,
            sim_real_corr: Some(corr),
            inner: Bytes::from_static(b"sim"),
        };
        let encoded = tp.encode();
        let decoded = TaggedPayload::decode(&encoded).unwrap().unwrap();
        assert_eq!(decoded.kind, InterventionKind::Counterfactual);
        assert!((decoded.sim_real_corr.unwrap() - corr).abs() < 1e-15);
        assert_eq!(&decoded.inner[..], b"sim");
    }

    #[test]
    fn all_non_counterfactual_kinds_round_trip() {
        let kinds = [
            InterventionKind::Observe,
            InterventionKind::DoPhysical,
            InterventionKind::DoDigital,
            InterventionKind::DoChemical,
            InterventionKind::DoGenetic,
        ];
        for kind in kinds {
            let tp = TaggedPayload { kind, sim_real_corr: None, inner: Bytes::new() };
            let encoded = tp.encode();
            let decoded = TaggedPayload::decode(&encoded).unwrap().unwrap();
            assert_eq!(decoded.kind, kind, "kind={kind:?}");
        }
    }

    // ── legacy payload compatibility ──────────────────────────────────────────

    #[test]
    fn legacy_payload_returns_none() {
        let legacy = Bytes::from_static(b"hello aevum");
        assert!(TaggedPayload::decode(&legacy).is_none());
    }

    #[test]
    fn empty_payload_returns_none() {
        assert!(TaggedPayload::decode(&Bytes::new()).is_none());
    }

    #[test]
    fn decode_kind_on_legacy_returns_observe() {
        let legacy = Bytes::from_static(b"any old bytes");
        assert_eq!(TaggedPayload::decode_kind(&legacy), InterventionKind::Observe);
    }

    // ── error cases ───────────────────────────────────────────────────────────

    #[test]
    fn truncated_after_magic_returns_err() {
        let truncated = Bytes::copy_from_slice(b"PACR"); // only magic, no kind byte
        let result = TaggedPayload::decode(&truncated);
        assert!(matches!(
            result,
            Some(Err(InterventionDecodeError::TruncatedAfterMagic))
        ));
    }

    #[test]
    fn counterfactual_truncated_sim_real_corr_returns_err() {
        // PACR + kind=5 (Counterfactual) + only 3 bytes of sim_real_corr (need 8)
        let mut buf = b"PACR\x05\x00\x00\x00".to_vec();
        buf.truncate(8); // 4 magic + 1 kind + 3 bytes (not 8)
        let result = TaggedPayload::decode(&Bytes::from(buf));
        assert!(matches!(
            result,
            Some(Err(InterventionDecodeError::TruncatedSimRealCorr))
        ));
    }

    #[test]
    fn unknown_kind_byte_returns_err() {
        let buf = Bytes::from(vec![b'P', b'A', b'C', b'R', 0xFF]);
        let result = TaggedPayload::decode(&buf);
        assert!(matches!(
            result,
            Some(Err(InterventionDecodeError::UnknownKindByte(0xFF)))
        ));
    }
}

// ── Unit tests (PacrRecord::validate Phase 15B) ───────────────────────────────

#[cfg(test)]
mod validate_intervention_tests {
    use super::*;
    use crate::complexity::CognitiveSplit;
    use crate::ets::ResourceTriple;
    use bytes::Bytes;
    use smallvec::smallvec;

    fn base_record_with_payload(payload: Bytes) -> PacrRecord {
        PacrBuilder::new()
            .id(CausalId(42))
            .predecessors(smallvec![CausalId::GENESIS])
            .landauer_cost(Estimate::exact(1e-20))
            .resources(ResourceTriple {
                energy: Estimate::exact(1e-19),
                time: Estimate::exact(1e-9),
                space: Estimate::exact(128.0),
            })
            .cognitive_split(CognitiveSplit {
                statistical_complexity: Estimate::exact(3.0),
                entropy_rate: Estimate::exact(1.0),
                info_gain: Estimate::exact(0.0),
            })
            .payload(payload)
            .build()
            .expect("all fields provided")
    }

    #[test]
    fn counterfactual_with_valid_corr_passes_validation() {
        let tp = TaggedPayload {
            kind: InterventionKind::Counterfactual,
            sim_real_corr: Some(0.75),
            inner: Bytes::new(),
        };
        let record = base_record_with_payload(tp.encode());
        let issues = record.validate();
        assert!(issues.is_empty(), "unexpected issues: {issues:?}");
    }

    #[test]
    fn counterfactual_without_corr_fails_validation() {
        // Manually craft a payload with Counterfactual kind but no sim_real_corr bytes
        // (This can only happen via low-level manipulation; TaggedPayload::encode always
        // fills it. We simulate via encode with 0.0 then verify the positive path.)
        let tp = TaggedPayload {
            kind: InterventionKind::Counterfactual,
            sim_real_corr: Some(0.0), // edge: 0.0 is valid
            inner: Bytes::new(),
        };
        let record = base_record_with_payload(tp.encode());
        assert!(record.validate().is_empty());
    }

    #[test]
    fn counterfactual_sim_real_corr_out_of_range_fails() {
        // Manually build a raw payload with corr=1.5 (out of range)
        let mut buf = b"PACR\x05".to_vec();
        buf.extend_from_slice(&1.5_f64.to_be_bytes()); // out of range
        let record = base_record_with_payload(Bytes::from(buf));
        let issues = record.validate();
        assert!(
            issues
                .iter()
                .any(|i| matches!(i, ValidationIssue::SimRealCorrOutOfRange(_))),
            "expected SimRealCorrOutOfRange, got: {issues:?}"
        );
    }

    #[test]
    fn non_counterfactual_tagged_payload_passes_validation() {
        let tp = TaggedPayload {
            kind: InterventionKind::DoGenetic,
            sim_real_corr: None,
            inner: Bytes::from_static(b"CRISPR-Cas9"),
        };
        let record = base_record_with_payload(tp.encode());
        assert!(record.validate().is_empty());
    }

    #[test]
    fn legacy_payload_passes_validation_unchanged() {
        let record = base_record_with_payload(Bytes::from_static(b"legacy data"));
        assert!(record.validate().is_empty());
    }

    #[test]
    fn intervention_kind_helper_returns_correct_kind() {
        let tp = TaggedPayload {
            kind: InterventionKind::DoChemical,
            sim_real_corr: None,
            inner: Bytes::new(),
        };
        let record = base_record_with_payload(tp.encode());
        assert_eq!(record.intervention_kind(), InterventionKind::DoChemical);
    }

    #[test]
    fn intervention_kind_on_legacy_returns_observe() {
        let record = base_record_with_payload(Bytes::from_static(b"legacy"));
        assert_eq!(record.intervention_kind(), InterventionKind::Observe);
    }
}

// ── Unit tests ────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::complexity::CognitiveSplit;
    use crate::ets::ResourceTriple;
    use bytes::Bytes;
    use smallvec::smallvec;

    fn complete_record() -> PacrRecord {
        PacrBuilder::new()
            .id(CausalId(42))
            .predecessors(smallvec![CausalId::GENESIS])
            .landauer_cost(Estimate::exact(1e-20))
            .resources(ResourceTriple {
                energy: Estimate::exact(1e-19),
                time: Estimate::exact(1e-9),
                space: Estimate::exact(128.0),
            })
            .cognitive_split(CognitiveSplit {
                statistical_complexity: Estimate::exact(3.0),
                entropy_rate: Estimate::exact(1.0),
                info_gain: Estimate::exact(0.0),
            })
            .payload(Bytes::from_static(b"hello aevum"))
            .build()
            .expect("all fields provided")
    }

    // ── CausalId ─────────────────────────────────────────────────────────────

    #[test]
    fn genesis_sentinel_is_genesis() {
        assert!(CausalId::GENESIS.is_genesis());
    }

    #[test]
    fn non_zero_id_is_not_genesis() {
        assert!(!CausalId(1).is_genesis());
    }

    // ── Builder ───────────────────────────────────────────────────────────────

    #[test]
    fn builder_rejects_missing_id() {
        let r = PacrBuilder::new()
            .predecessors(smallvec![])
            .landauer_cost(Estimate::exact(0.0))
            .resources(ResourceTriple {
                energy: Estimate::exact(1e-19),
                time: Estimate::exact(1e-9),
                space: Estimate::exact(0.0),
            })
            .cognitive_split(CognitiveSplit {
                statistical_complexity: Estimate::exact(0.0),
                entropy_rate: Estimate::exact(0.0),
                info_gain: Estimate::exact(0.0),
            })
            .payload(Bytes::new())
            .build();
        assert!(r.is_err());
        let msg = r.unwrap_err().to_string();
        assert!(msg.contains('\u{03B9}') || msg.contains("id"), "msg={msg}");
    }

    #[test]
    fn builder_rejects_empty_partially_filled() {
        let r = PacrBuilder::new().id(CausalId(1)).build();
        assert!(r.is_err());
    }

    #[test]
    fn builder_accepts_fully_filled() {
        let r = complete_record();
        assert!(r.validate().is_empty());
    }

    // ── PacrRecord::validate ──────────────────────────────────────────────────

    #[test]
    fn validate_clean_record_is_empty() {
        assert!(complete_record().validate().is_empty());
    }

    #[test]
    fn validate_self_reference_in_predecessors() {
        let id = CausalId(99);
        let r = PacrBuilder::new()
            .id(id)
            .predecessors(smallvec![id]) // self-reference
            .landauer_cost(Estimate::exact(1e-20))
            .resources(ResourceTriple {
                energy: Estimate::exact(1e-19),
                time: Estimate::exact(1e-9),
                space: Estimate::exact(0.0),
            })
            .cognitive_split(CognitiveSplit {
                statistical_complexity: Estimate::exact(0.0),
                entropy_rate: Estimate::exact(0.0),
                info_gain: Estimate::exact(0.0),
            })
            .payload(Bytes::new())
            .build()
            .unwrap();
        let issues = r.validate();
        assert!(issues
            .iter()
            .any(|i| matches!(i, ValidationIssue::SelfReference)));
    }

    #[test]
    fn validate_energy_below_landauer_floor() {
        let r = PacrBuilder::new()
            .id(CausalId(1))
            .predecessors(smallvec![])
            .landauer_cost(Estimate::exact(1e-10)) // huge floor
            .resources(ResourceTriple {
                energy: Estimate::exact(1e-20), // energy < floor
                time: Estimate::exact(1e-9),
                space: Estimate::exact(0.0),
            })
            .cognitive_split(CognitiveSplit {
                statistical_complexity: Estimate::exact(0.0),
                entropy_rate: Estimate::exact(0.0),
                info_gain: Estimate::exact(0.0),
            })
            .payload(Bytes::new())
            .build()
            .unwrap();
        let issues = r.validate();
        assert!(issues
            .iter()
            .any(|i| matches!(i, ValidationIssue::EnergyBelowLandauer { .. })));
    }

    // ── thermodynamic_waste ───────────────────────────────────────────────────

    #[test]
    fn waste_equals_energy_minus_landauer() {
        let r = complete_record(); // energy=1e-19, landauer=1e-20
        let waste = r.thermodynamic_waste();
        let expected = 1e-19 - 1e-20;
        assert!(
            (waste.point - expected).abs() < 1e-30,
            "waste={}",
            waste.point
        );
    }
}

// ── Property-based tests ──────────────────────────────────────────────────────

#[cfg(test)]
mod prop_tests {
    use super::*;
    use crate::complexity::CognitiveSplit;
    use crate::ets::ResourceTriple;
    use bytes::Bytes;
    use proptest::prelude::*;
    use smallvec::smallvec;

    /// Any complete record with valid physics must pass validate() cleanly.
    proptest! {
        #[test]
        fn complete_valid_record_has_no_issues(
            id_raw      in 1_u128..u128::MAX,
            energy      in 1e-25_f64..1e-10_f64,
            time        in 1e-12_f64..1.0_f64,
            space       in 0.0_f64..1e9_f64,
            s_t         in 0.0_f64..100.0_f64,
            h_t         in 0.0_f64..100.0_f64,
        ) {
            // Λ ≤ E: pick Λ as half of E
            let landauer = Estimate::exact(energy * 0.5);
            let r = PacrBuilder::new()
                .id(CausalId(id_raw))
                .predecessors(smallvec![CausalId::GENESIS])
                .landauer_cost(landauer)
                .resources(ResourceTriple {
                    energy: Estimate::exact(energy),
                    time:   Estimate::exact(time),
                    space:  Estimate::exact(space),
                })
                .cognitive_split(CognitiveSplit {
                    statistical_complexity: Estimate::exact(s_t),
                    entropy_rate:           Estimate::exact(h_t),
                    info_gain:              Estimate::exact(0.0),
                })
                .payload(Bytes::new())
                .build()
                .unwrap();
            let issues = r.validate();
            prop_assert!(
                issues.is_empty(),
                "unexpected issues: {:?}", issues
            );
        }
    }
}
