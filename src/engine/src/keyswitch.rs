// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Keyswitches as a render carries them: the slots a step asks for, and the notes a clip sends for them.
//!
//! A keyswitch is a note a plugin reads as an order to change how it plays. A pattern's step names slots of its track's
//! instrument; playing the pattern gives switched slots, which nothing between the pattern and the clip touches, no
//! generator, scale or transposing; and the clip's track turns each slot into the instrument's note, leaving out a slot the
//! instrument gives no note. The timing moves a keyswitch note with the note it belongs to, by the clip's groove and its
//! rushes and drags, and nothing else.

use llamatron_math::rational::Rational;

/// The slots one step's note is played with: when the note starts and ends as the pattern wrote it, in whole notes from
/// the pass's or the clip's start, and the slots, numbered from 0.
#[derive(Clone, Debug, PartialEq)]
pub struct SwitchedSlots {
    pub start: Rational,
    pub end: Rational,
    pub slots: Vec<i64>,
}

impl SwitchedSlots {
    /// The same slots a time later, for a pass that starts there.
    pub fn moved_by(&self, time: Rational) -> SwitchedSlots {
        SwitchedSlots {
            start: self.start + time,
            end: self.end + time,
            slots: self.slots.clone(),
        }
    }
}

/// One keyswitch note a clip sends: when it starts and ends, in whole notes from the clip's start before any groove, and
/// its MIDI number.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct SwitchNote {
    pub start: Rational,
    pub end: Rational,
    pub midi_number: i64,
}

/// The keyswitch notes switched slots send before a clip's end, in time order: each slot's note, by the instrument's
/// notes for its slots, cut at the end; a slot with no note sends nothing.
pub fn switch_notes(switched: &[SwitchedSlots], notes: &[Option<i64>], end: Rational) -> Vec<SwitchNote> {
    let mut sent = Vec::new();
    for slots in switched.iter().filter(|slots| slots.start < end) {
        for slot in &slots.slots {
            if let Some(Some(midi_number)) = usize::try_from(*slot).ok().and_then(|slot| notes.get(slot)) {
                sent.push(SwitchNote {
                    start: slots.start,
                    end: slots.end.min(end),
                    midi_number: *midi_number,
                });
            }
        }
    }
    sent
}
