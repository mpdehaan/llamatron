// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! One cell of the grid a song renders into (the Python engine/clips/clip.py): the sounds it plays in order, the scale its
//! degrees take, and whether it loops. A clip of no length of its own ends after its last position.

use crate::error::{RenderError, Rendered};
use crate::groove::Groove;
use crate::positions::{fit_to_length, piece_of};
use crate::sound::{NoteSound, Sound};
use llamatron_math::Rational;
use llamatron_model::values::scale::Scale;
use llamatron_model::values::time_signature::TimeSignature;

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
        }
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
        })
    }
}
