// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Auto chord: the Chords generator's mode that turns each single note of a clip into a chord, so that an instrument needs
//! no chords of its own to play them (the Python engine/generators/chords/auto_chord.py and engine/parts/chords_on_notes.py).
//!
//! From scale builds the triad the note's place in the clip's scale builds, major, minor, diminished or augmented as the
//! scale says, and leaves a note outside the scale a single note, a passing note staying a passing note. Major, Minor,
//! Augmented, Diminished and Power build that chord on the note whatever the scale. The note is the chord's root, or, with
//! Note on top, the chord's top, its other notes an octave down, so that a melody keeps its line. A sound already a chord of
//! more than one note is left as it is, and rests, rhythm, velocity and gates stay as written.

use crate::clip::Clip;
use crate::error::Rendered;
use crate::sound::{triad_above, NoteSound, Sound};
use llamatron_model::values::scale::Scale;
use llamatron_names::file_format;
use llamatron_names::words;

/// The chords Auto chord builds, as the file names them.
pub const FROM_SCALE: &str = words::FROM_SCALE;
const MAJOR: &str = file_format::Quality::MAJOR;
const MINOR: &str = file_format::NamedProgression::MINOR;
const AUGMENTED: &str = file_format::Quality::AUGMENTED;
const DIMINISHED: &str = file_format::Quality::DIMINISHED;
const POWER: &str = words::POWER;
/// The half steps above the root of each fixed chord: its third and fifth, a power chord's fifth and octave.
const FIXED_CHORDS: [(&str, [i64; 2]); 5] = [(MAJOR, [4, 7]), (MINOR, [3, 7]), (AUGMENTED, [4, 8]), (DIMINISHED, [3, 6]), (POWER, [7, 12])];
const HALF_STEPS_PER_OCTAVE: i64 = 12;

/// Auto chord: the chord it builds, and whether the note ends the chord rather than starting it.
pub struct AutoChord {
    pub chord: String,
    pub on_top: bool,
}

impl AutoChord {
    /// The clip with each single note made its chord.
    pub fn generate(&self, clip: &Clip) -> Rendered<Clip> {
        let scale = clip.scale.as_ref();
        let sounds = clip
            .resolved_sounds()?
            .iter()
            .map(|sound| self.chorded(sound, scale))
            .collect::<Rendered<Vec<Sound>>>()?;
        Ok(Clip { sounds, ..clip.clone() })
    }

    /// A sound with each single note in it made a chord: a held sound's and each part of a phrase's too.
    fn chorded(&self, sound: &Sound, scale: Option<&Scale>) -> Rendered<Sound> {
        Ok(match sound {
            Sound::Held { length, sound } => Sound::Held {
                length: *length,
                sound: Box::new(self.chorded(sound, scale)?),
            },
            Sound::Phrase { length, parts } => Sound::Phrase {
                length: *length,
                parts: parts.iter().map(|part| self.chorded(part, scale)).collect::<Rendered<_>>()?,
            },
            Sound::Degree { .. } if scale.is_some() => self.chorded(&super::chords::settled(sound, scale)?, scale)?,
            Sound::Chord { notes, .. } if notes.len() == 1 => self.built(&notes[0], scale),
            Sound::Note(note) => self.built(note, scale),
            other => other.clone(),
        })
    }

    /// A single note's chord, or the note itself where From scale finds it outside the scale, or there is no scale.
    fn built(&self, note: &NoteSound, scale: Option<&Scale>) -> Sound {
        let fixed = FIXED_CHORDS.iter().find(|(name, _)| *name == self.chord).map(|(_, above)| above.to_vec());
        let above = match fixed {
            Some(above) => above,
            None => match scale.and_then(|scale| triad_above(note, scale)) {
                Some(above) => above,
                None => return Sound::Note(*note),
            },
        };
        chord_on(note, &above, self.on_top)
    }
}

/// A chord of a note and the notes some half steps above it, or, on top, the same chord ending on the note: each other note
/// an octave lower, so that a melody keeps its line. A note that would fall outside MIDI's range is left out.
fn chord_on(note: &NoteSound, above: &[i64], on_top: bool) -> Sound {
    let mut steps: Vec<i64> = std::iter::once(0).chain(above.iter().copied()).collect();
    if on_top {
        steps = above
            .iter()
            .map(|half_steps| half_steps - HALF_STEPS_PER_OCTAVE)
            .chain(std::iter::once(0))
            .collect();
        steps.sort();
        steps.dedup();
    }
    Sound::chord(steps.iter().filter_map(|half_steps| note.half_step(*half_steps)).collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use llamatron_model::values::scale::ScaleType;

    fn c4() -> NoteSound {
        match Sound::named_note("C", 4, None, None, false) {
            Ok(note) => note,
            Err(problem) => panic!("{}", problem.0),
        }
    }

    fn midis(sound: &Sound) -> Vec<i64> {
        match sound {
            Sound::Chord { notes, .. } => notes.iter().map(|note| note.midi).collect(),
            Sound::Note(note) => vec![note.midi],
            _ => Vec::new(),
        }
    }

    /// From scale builds the note's triad in the scale; Major builds a major triad whatever the scale; Note on top ends the
    /// chord on the note, the others an octave down; a note outside the scale stays a single note.
    #[test]
    fn auto_chord_builds_the_chord_asked_for() {
        let root = llamatron_model::values::note::Note::new("C", 4, None, None, false).expect("C");
        let c_major = Scale::new(root, ScaleType::named(file_format::Quality::MAJOR).expect(file_format::Quality::MAJOR));
        let from_scale = AutoChord {
            chord: FROM_SCALE.to_string(),
            on_top: false,
        };
        let c = c4();
        assert_eq!(midis(&from_scale.built(&c, Some(&c_major))), [c.midi, c.midi + 4, c.midi + 7]);
        let on_top = AutoChord {
            chord: MAJOR.to_string(),
            on_top: true,
        };
        assert_eq!(midis(&on_top.built(&c, None)), [c.midi - 8, c.midi - 5, c.midi]);
        let sharp = c.half_step(1).expect("C sharp");
        assert_eq!(midis(&from_scale.built(&sharp, Some(&c_major))), [sharp.midi]);
    }
}
