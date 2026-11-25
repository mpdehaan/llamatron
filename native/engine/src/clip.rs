// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! One cell of the grid a song renders into (the Python engine/clips/clip.py): the sounds it plays in order, the scale its
//! degrees take, and whether it loops. A clip of no length of its own ends after its last position.

use crate::error::{RenderError, Rendered};
use crate::generators::timing::NudgePlan;
use crate::groove::Groove;
use crate::positions::{fit_to_length, piece_of};
use crate::sound::{NoteSound, Sound};
use crate::timing::StrumPlan;
use llamatron_math::Rational;
use llamatron_model::values::scale::Scale;
use llamatron_model::values::time_signature::TimeSignature;

/// A CC value a clip sends: when, its number (a lane until the clip is finished, then the track's CC number), its value, and
/// whether it slides to the next value for the same number rather than holding.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Control {
    pub time: Rational,
    pub number: i64,
    pub value: i64,
    pub slide: bool,
}

impl Control {
    pub fn moved_by(&self, offset: Rational) -> Control {
        Control {
            time: self.time + offset,
            ..*self
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Clip {
    pub name: Option<String>,
    pub sounds: Vec<Sound>,
    pub scale: Option<Scale>,
    pub length: Option<Rational>,
    pub note_length: Option<Rational>,
    pub looping: bool,
    pub time_signature: Option<TimeSignature>,
    /// The groove the clip plays with, which the Realizer gives it once it is finished, so that no generator sees it.
    pub groove: Option<Groove>,
    /// The CC values the clip sends, in time order.
    pub controls: Vec<Control>,
    /// How the clip's notes are rushed and dragged, which the Realizer gives it once it is finished, or None.
    pub nudge: Option<NudgePlan>,
    /// How the clip strums its chords at the very end, which the Realizer gives it once it is finished, or None.
    pub strum: Option<StrumPlan>,
}

impl Clip {
    /// A clip of sounds in a scale, of no length of its own.
    pub fn of(sounds: Vec<Sound>, scale: Option<Scale>) -> Clip {
        Clip {
            name: None,
            sounds,
            scale,
            length: None,
            note_length: None,
            looping: true,
            time_signature: None,
            groove: None,
            controls: Vec::new(),
            nudge: None,
            strum: None,
        }
    }

    /// The clip with CC values, put in time order, those at one time kept in the order given.
    pub fn with_controls(mut self, mut controls: Vec<Control>) -> Clip {
        controls.sort_by_key(|control| control.time);
        self.controls = controls;
        self
    }

    pub fn has_positions(&self) -> bool {
        !self.sounds.is_empty()
    }

    /// The sounds with every missing length filled in from the note length, which a rendered clip's already are.
    pub fn resolved_sounds(&self) -> Rendered<Vec<Sound>> {
        self.sounds.iter().map(|sound| self.filled(sound)).collect()
    }

    fn filled(&self, sound: &Sound) -> Rendered<Sound> {
        Ok(match sound {
            Sound::Phrase { length, parts } => Sound::Phrase {
                length: *length,
                parts: parts.iter().map(|part| self.filled(part)).collect::<Rendered<_>>()?,
            },
            Sound::Held { length, sound } => Sound::Held {
                length: *length,
                sound: Box::new(self.filled(sound)?),
            },
            other if other.length().is_some() => other.clone(),
            Sound::Chord { notes, .. } => Sound::chord(notes.iter().map(|note| self.filled_note(note)).collect::<Rendered<_>>()?),
            other => other.with_length(Some(self.missing_length()?)),
        })
    }

    fn filled_note(&self, note: &NoteSound) -> Rendered<NoteSound> {
        if note.length.is_some() {
            return Ok(*note);
        }
        Ok(NoteSound {
            length: Some(self.missing_length()?),
            ..*note
        })
    }

    fn missing_length(&self) -> Rendered<Rational> {
        self.note_length
            .ok_or_else(|| RenderError::Refused("a position has no length and the clip no note length".to_string()))
    }

    /// The resolved sounds, filling the clip's own length where it has one.
    pub fn played_sounds(&self) -> Rendered<Vec<Sound>> {
        let sounds = self.resolved_sounds()?;
        Ok(match self.length {
            None => sounds,
            Some(length) => fit_to_length(&sounds, length),
        })
    }

    /// How long the clip lasts.
    pub fn total_length(&self) -> Rendered<Rational> {
        if let Some(length) = self.length {
            return Ok(length);
        }
        let mut total = Rational::ZERO;
        for sound in self.resolved_sounds()? {
            total = total + sound.place();
        }
        Ok(total)
    }

    /// The part of the clip from start to end: a note crossing either edge is cut, and anything past the clip's end is
    /// silence, so that the section lasts exactly end less start.
    pub fn section(&self, start: Rational, end: Rational) -> Rendered<Clip> {
        if start < Rational::ZERO || end <= start {
            return Err(RenderError::Refused(format!(
                "a section must start at 0 or later and end after it starts, got {start} to {end}"
            )));
        }
        let mut sounds = Vec::new();
        let mut sound_start = Rational::ZERO;
        for sound in self.played_sounds()? {
            if sound_start >= end {
                break;
            }
            let sound_end = sound_start + sound.place();
            if start <= sound_start && sound_end <= end {
                sounds.push(sound);
            } else {
                let piece_start = start.max(sound_start);
                let piece_end = end.min(sound_end);
                if piece_start < piece_end {
                    sounds.push(piece_of(&sound, piece_start - sound_start, piece_end - piece_start));
                }
            }
            sound_start = sound_end;
        }
        if sound_start < end {
            sounds.push(Sound::Rest(end - sound_start.max(start)));
        }
        Ok(Clip {
            name: self.name.clone(),
            sounds,
            scale: self.scale,
            length: None,
            note_length: self.note_length,
            looping: true,
            time_signature: None,
            groove: None,
            nudge: None,
            strum: None,
            controls: self
                .controls
                .iter()
                .filter(|control| start <= control.time && control.time < end)
                .map(|control| control.moved_by(Rational::ZERO - start))
                .collect(),
        })
    }

    /// A clip that plays this one some times in a row.
    pub fn repeated(&self, times: i128) -> Rendered<Clip> {
        let length = self.total_length()?;
        let played = self.played_sounds()?;
        let mut sounds = Vec::new();
        let mut controls = Vec::new();
        for place in 0..times {
            sounds.extend(played.iter().cloned());
            controls.extend(self.controls.iter().map(|control| control.moved_by(length * Rational::whole(place))));
        }
        Ok(Clip {
            sounds,
            controls,
            length: None,
            ..self.clone()
        })
    }

    /// A clip that plays this one over and over, cut to last a length, as a morph's target is to its pass.
    pub fn looped_to(&self, length: Rational) -> Rendered<Clip> {
        let own = self.total_length()?;
        let clip = if own > Rational::ZERO {
            self.repeated((length / own).ceil())?
        } else {
            self.clone()
        };
        clip.section(Rational::ZERO, length)
    }
}
