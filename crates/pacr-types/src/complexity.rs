//! Pillar: III. PACR field: Γ (Cognitive Split).
//!
//! Computational mechanics fundamental theorem (arXiv:2601.03220):
//! any data stream admits a unique decomposition into two inseparable projections
//! of the same ε-machine:
//!
//!   `S_T` — statistical complexity (bits)
//!         Minimum causal-state information needed to optimally predict the stream.
//!         Rising `S_T` → the system is discovering learnable structure.
//!
//!   `H_T` — entropy rate (bits per symbol)
//!         Residual unpredictability that cannot be further compressed.
//!         Rising `H_T` → the system is encountering irreducible noise.
//!
//!   `ΔH`  — information gain (bits) — Phase 11-A append.
//!   Entropy reduction when this record was processed: H_T_before − H_T_after.
//!   Positive → record reduced uncertainty (learned structure).
//!   Negative → record increased uncertainty (surprising new regime).
//!   Zero     → neutral observation (no change to causal model).
//!
//!   Physical basis: Landauer symmetry.  Every Λ (bits ERASED, Pillar II)
//!   has a symmetric dual ΔH (bits LEARNED).  Their ratio η = ΔH / λ_bits
//!   is the **information efficiency** - the fundamental KPI for cognitive
//!   value per thermodynamic cost.
//!
//! These quantities are OBSERVER-DEPENDENT (the observer's computational
//! budget `T_budget` determines the ε-machine approximation order) and
//! INSEPARABLE — removing either one from the record permanently loses
//! information that cannot be recovered from the other.

use crate::estimate::Estimate;

// ── Serde default helper ───────────────────────────────────────────────────────

/// Returns `Estimate::exact(0.0)` for backward-compatible `info_gain` deserialization.
/// Records that predate Phase 11-A carry no ΔH measurement; treating them as
/// zero-gain is the conservative (non-inflationary) default.
fn zero_info_gain() -> Estimate<f64> {
    Estimate::exact(0.0)
}

// ── Core type ─────────────────────────────────────────────────────────────────

/// The cognitive split Γ = (`S_T`, `H_T`, `ΔH`): intrinsic information structure
/// of the processed data stream, as computed by the ε-machine approximation.
///
/// PACR field Γ.  Derived from Pillar III (computational mechanics).
///
/// # Append-only schema
///
/// `info_gain` was added in Phase 11-A.  Existing serialised records that lack
/// this field deserialise with `info_gain = Estimate::exact(0.0)` (zero-gain
/// default, semantically neutral).
#[derive(Debug, Clone, Copy, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct CognitiveSplit {
    /// Statistical complexity `S_T` (bits).
    /// Minimum information needed to optimally predict the stream.
    pub statistical_complexity: Estimate<f64>,

    /// Entropy rate `H_T` (bits per symbol).
    /// Residual unpredictability even with the optimal predictor.
    pub entropy_rate: Estimate<f64>,

    /// Information gain `ΔH` (bits) — Phase 11-A.
    ///
    /// Entropy reduction H_T_before − H_T_after from processing this record.
    /// Symmetric complement to `Λ`: Λ counts bits erased, `ΔH` counts bits learned.
    /// Default: `Estimate::exact(0.0)` for pre-Phase-11-A records.
    #[serde(default = "zero_info_gain")]
    pub info_gain: Estimate<f64>,
}

impl CognitiveSplit {
    /// Construct with zero information gain (convenience for callers that do not
    /// yet measure ΔH).  Equivalent to filling `info_gain: Estimate::exact(0.0)`.
    #[must_use]
    pub fn new(statistical_complexity: Estimate<f64>, entropy_rate: Estimate<f64>) -> Self {
        Self {
            statistical_complexity,
            entropy_rate,
            info_gain: Estimate::exact(0.0),
        }
    }

    /// Construct with all three Γ fields (Phase 11-A callers that measure ΔH).
    #[must_use]
    pub fn with_info_gain(
        statistical_complexity: Estimate<f64>,
        entropy_rate: Estimate<f64>,
        info_gain: Estimate<f64>,
    ) -> Self {
        Self {
            statistical_complexity,
            entropy_rate,
            info_gain,
        }
    }

    /// Information efficiency η = ΔH / λ_bits ∈ (−∞, +∞).
    ///
    /// Measures bits of entropy reduced per bit of Landauer cost paid.
    /// - η > 1 : more entropy compressed than thermodynamic floor → efficient
    /// - η ∈ (0,1] : learned something but below theoretical maximum
    /// - η ≤ 0 : neutral or entropy-increasing observation
    ///
    /// Returns `None` when `lambda_bits` ≈ 0 (no cost → ratio undefined).
    #[must_use]
    pub fn info_efficiency(&self, lambda_bits: f64) -> Option<f64> {
        if lambda_bits.abs() < f64::EPSILON {
            return None;
        }
        Some(self.info_gain.point / lambda_bits)
    }

    /// Structure-to-noise ratio: `S_T` / `H_T`.
    ///
    /// - **High** → structured, predictable stream (e.g. chess move sequences).
    /// - **Low** → simple but random stream (e.g. fair-coin outputs).
    /// - `None` → `H_T` ≈ 0, stream is fully deterministic; ratio is effectively ∞.
    #[must_use]
    pub fn structure_noise_ratio(&self) -> Option<f64> {
        if self.entropy_rate.point.abs() < f64::EPSILON {
            return None; // deterministic stream; avoid division by near-zero
        }
        Some(self.statistical_complexity.point / self.entropy_rate.point)
    }

    /// Returns `true` when `S_T` > `H_T` (or `H_T` ≈ 0), indicating a stream with
    /// more learnable structure than irreducible randomness.
    #[must_use]
    pub fn is_structured(&self) -> bool {
        self.structure_noise_ratio().is_none_or(|r| r > 1.0)
    }
}

// ── Unit tests ────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::estimate::Estimate;

    #[test]
    fn structured_stream_ratio_gt_one() {
        let g = CognitiveSplit {
            statistical_complexity: Estimate::exact(4.0),
            entropy_rate: Estimate::exact(1.0),
            info_gain: Estimate::exact(0.0),
        };
        let r = g.structure_noise_ratio().unwrap();
        assert!((r - 4.0).abs() < f64::EPSILON);
        assert!(g.is_structured());
    }

    #[test]
    fn noisy_stream_ratio_lt_one() {
        let g = CognitiveSplit {
            statistical_complexity: Estimate::exact(0.5),
            entropy_rate: Estimate::exact(2.0),
            info_gain: Estimate::exact(0.0),
        };
        assert!(!g.is_structured());
    }

    #[test]
    fn deterministic_stream_returns_none_and_is_structured() {
        let g = CognitiveSplit {
            statistical_complexity: Estimate::exact(3.0),
            entropy_rate: Estimate::exact(0.0),
            info_gain: Estimate::exact(0.0),
        };
        assert!(g.structure_noise_ratio().is_none());
        assert!(g.is_structured()); // deterministic → always structured
    }

    #[test]
    fn equal_complexity_and_entropy_ratio_is_one() {
        let g = CognitiveSplit {
            statistical_complexity: Estimate::exact(2.0),
            entropy_rate: Estimate::exact(2.0),
            info_gain: Estimate::exact(0.0),
        };
        let r = g.structure_noise_ratio().unwrap();
        assert!((r - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn info_efficiency_positive_when_learned() {
        let g = CognitiveSplit::with_info_gain(
            Estimate::exact(3.0),
            Estimate::exact(1.0),
            Estimate::exact(2.0), // ΔH = 2 bits
        );
        let eta = g.info_efficiency(4.0).unwrap(); // λ = 4 bits
        assert!((eta - 0.5).abs() < 1e-10, "η = 2/4 = 0.5, got {eta}");
    }

    #[test]
    fn info_efficiency_none_on_zero_lambda() {
        let g = CognitiveSplit::new(Estimate::exact(3.0), Estimate::exact(1.0));
        assert!(g.info_efficiency(0.0).is_none());
    }

    #[test]
    fn new_constructor_sets_zero_info_gain() {
        let g = CognitiveSplit::new(Estimate::exact(1.5), Estimate::exact(0.5));
        assert_eq!(g.info_gain, Estimate::exact(0.0));
    }

    #[test]
    fn serde_roundtrip_with_info_gain() {
        let g = CognitiveSplit::with_info_gain(
            Estimate::exact(2.0),
            Estimate::exact(0.8),
            Estimate::exact(1.2),
        );
        let json = serde_json::to_string(&g).unwrap();
        let g2: CognitiveSplit = serde_json::from_str(&json).unwrap();
        assert_eq!(g, g2);
    }

    #[test]
    fn serde_backward_compat_missing_info_gain() {
        // Records from before Phase 11-A lack the info_gain field.
        // They must deserialise with info_gain = 0.0 (no panic, no error).
        let json = r#"{"statistical_complexity":{"point":1.0,"lower":0.9,"upper":1.1},"entropy_rate":{"point":0.5,"lower":0.4,"upper":0.6}}"#;
        let g: CognitiveSplit = serde_json::from_str(json).unwrap();
        assert_eq!(g.info_gain, Estimate::exact(0.0));
    }
}
