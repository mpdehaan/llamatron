// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Amp, the last part of a voice before its instrument's effects: Env 1 always opens it, and its type sets how. Clean
//! is a perfect VCA, today's amp, its Character rounding off and gently saturating the loudest moments as warmer VCAs do,
//! from none at zero. Transistor is the discrete VCA of the classic monosynths: it warms and squashes the
//! loudest notes and leaks a little when shut, part of their drone. OTA is the chip VCA of the polysynths and modulars,
//! opening exponentially and saturating rounder. Each one's Response sets how Env 1 opens it, from linear to exponential.
//! (The low-pass gate, the fourth type, is gate.rs's GatePart standing in the Amp's place.)

use crate::protocol::values::{number, word};
use crate::registry::{self, Named};
use llamatron_names::spec;

use crate::dsp::saturation::soft_limit;

/// The kinds of Amp, each a circuit.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum AmpKind {
    Clean,
    Transistor,
    Ota,
}

/// An Amp as a patch compiles it.
#[derive(Clone, Copy, Debug)]
pub struct AmpPart {
    pub kind: AmpKind,
    /// How Env 1 opens it, 0 linear to 1 exponential.
    response: f64,
    /// How hard the loudest notes saturate, 0 to 1.
    drive: f64,
    /// What leaks through when it is shut, 0 to 1 of BLEED_MOST.
    bleed: f64,
    /// A Clean amp's warmth, 0 perfectly clean to 1 a gentle saturation of its loudest moments.
    character: f64,
}

/// How steep the exponential response is: the curve exp(k x) - 1 over exp(k) - 1.
const EXPONENTIAL_STEEPNESS: f64 = 5.0;
/// How much harder full Drive pushes the saturation, and the most a shut Transistor amp leaks, -40 dB.
const MOST_DRIVE: f64 = 4.0;
const BLEED_MOST: f64 = 0.01;
/// Each saturating circuit's push at no Drive: enough that the loudest notes warm, none that a quiet one changes.
const TRANSISTOR_PUSH: f64 = 1.2;
const OTA_PUSH: f64 = 1.0;

impl Default for AmpPart {
    fn default() -> Self {
        AmpPart {
            kind: AmpKind::Clean,
            response: 0.0,
            drive: 0.0,
            bleed: 0.0,
            character: 0.0,
        }
    }
}

/// The Amp's type when its spec names none.
const CLEAN: &str = spec::CLEAN;

/// Every Amp type a spec may name, and what it is.
pub static TYPES: &[Named<AmpKind>] = &[
    Named {
        name: CLEAN,
        value: AmpKind::Clean,
    },
    Named {
        name: spec::TRANSISTOR,
        value: AmpKind::Transistor,
    },
    Named {
        name: spec::OTA_VCA,
        value: AmpKind::Ota,
    },
    // The low-pass gate in the Amp's slot is the voice's amp itself (filters/gate.rs); the Amp's own circuit stays
    // clean beside it.
    Named {
        name: crate::filters::gate::LOW_PASS_GATE,
        value: AmpKind::Clean,
    },
];

/// An Amp from its spec: its type, Response, Drive and Bleed as fractions; Clean for none or one it does not know.
pub fn compiled(spec: &rmpv::Value) -> AmpPart {
    let kind = registry::named(TYPES, word(spec, spec::TYPE, CLEAN)).unwrap_or(AmpKind::Clean);
    AmpPart {
        kind,
        response: number(spec, spec::RESPONSE, 0.0).clamp(0.0, 1.0),
        drive: number(spec, spec::DRIVE, 0.0).clamp(0.0, 1.0),
        bleed: number(spec, spec::BLEED, 0.0).clamp(0.0, 1.0),
        character: number(spec, spec::CHARACTER, 0.0).clamp(0.0, 1.0),
    }
}

impl AmpPart {
    /// The gain Env 1's level gives, along the Response's curve from linear to exponential.
    #[inline]
    fn gain(&self, opening: f64) -> f64 {
        if self.response == 0.0 {
            return opening;
        }
        let exponential = ((EXPONENTIAL_STEEPNESS * opening.max(0.0)).exp() - 1.0) / (EXPONENTIAL_STEEPNESS.exp() - 1.0);
        opening * (1.0 - self.response) + exponential * self.response
    }

    /// One sample through the Amp: the filtered signal, opened by Env 1's level (with velocity), and the Mod Matrix's
    /// Amp move as a factor.
    #[inline]
    pub fn process(&self, signal: f64, opening: f64, moved: f64) -> f64 {
        let gained = signal * self.gain(opening) * moved;
        match self.kind {
            AmpKind::Clean if self.character == 0.0 => gained,
            AmpKind::Clean => {
                // Warmth: the soft-limited signal faded in by Character, pushed a little harder as it rises, so that quiet
                // moments pass untouched and loud ones round off.
                let push = 1.0 + self.character;
                gained * (1.0 - self.character) + soft_limit(gained * push) / push * self.character
            }
            AmpKind::Transistor => {
                let push = TRANSISTOR_PUSH + self.drive * MOST_DRIVE;
                soft_limit(gained * push) / push + signal * self.bleed * BLEED_MOST
            }
            AmpKind::Ota => {
                let push = OTA_PUSH + self.drive * MOST_DRIVE;
                // An OTA's saturation is rounder than a transistor pair's: a gentler curve, its knee softened.
                let x = gained * push;
                x / (1.0 + x.abs()).sqrt() / push
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn amp(kind: &str, response: f64, drive: f64, bleed: f64) -> AmpPart {
        compiled(&rmpv::Value::Map(vec![
            (spec::TYPE.into(), kind.into()),
            (spec::RESPONSE.into(), response.into()),
            (spec::DRIVE.into(), drive.into()),
            (spec::BLEED.into(), bleed.into()),
        ]))
    }

    /// A Clean amp's Character rounds off a loud note and leaves a quiet one nearly as it was.
    #[test]
    fn a_clean_amps_character_rounds_off_loud_notes() {
        let warm = compiled(&rmpv::Value::Map(vec![
            (spec::TYPE.into(), spec::CLEAN.into()),
            (spec::CHARACTER.into(), 1.0.into()),
        ]));
        let (quiet, loud, open) = (0.05, 1.0, 1.0);
        let (near_unity, squashed) = (0.05, 0.9);
        assert!((warm.process(quiet, open, 1.0) / quiet - 1.0).abs() < near_unity);
        assert!(warm.process(loud, open, 1.0) < loud * squashed);
    }

    /// Clean at a linear Response is the signal times its opening; an exponential Response opens it later.
    #[test]
    fn a_clean_amp_is_the_signal_times_its_opening() {
        let (signal, half) = (0.8, 0.5);
        assert_eq!(amp(spec::CLEAN, 0.0, 0.0, 0.0).process(signal, half, 1.0), signal * half);
        assert!(amp(spec::CLEAN, 1.0, 0.0, 0.0).process(signal, half, 1.0) < signal * half);
    }

    /// A Transistor amp squashes a loud note harder than a quiet one and leaks a little when shut; an OTA saturates too.
    #[test]
    fn a_transistor_amp_warms_loud_notes_and_bleeds_when_shut() {
        let (drive, full_bleed) = (0.5, 1.0);
        let transistor = amp(spec::TRANSISTOR, 0.0, drive, full_bleed);
        let (quiet, loud, open, shut) = (0.05, 1.0, 1.0, 0.0);
        let quiet_gain = transistor.process(quiet, open, 1.0) / quiet;
        let loud_gain = transistor.process(loud, open, 1.0) / loud;
        let squashed = 0.9;
        assert!(loud_gain < quiet_gain * squashed, "{loud_gain} against {quiet_gain}");
        assert!(transistor.process(loud, shut, 1.0) > 0.0, "it leaks when shut");
        let ota = amp(spec::OTA_VCA, 0.0, drive, 0.0);
        assert!(ota.process(loud, open, 1.0) / loud < ota.process(quiet, open, 1.0) / quiet);
    }
}
