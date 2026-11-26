// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The sounds of a clip as parts a generator reshapes one by one (the Python engine/generators/parts.py): where each starts,
//! how long its place is and how long it is heard. A generator that delivers a tune, or plays a part as a musician would,
//! changes how long a note is heard inside its place and how loud it is, and leaves where it starts alone.

use crate::sound::{NoteSound, Sound};
use llamatron_math::Rational;
use llamatron_model::schema::generated::midi::{MAX_VELOCITY, MIN_VELOCITY};

#[derive(Clone, Debug)]
pub struct Part {
    pub start: Rational,
    pub place: Rational,
    pub heard: Rational,
    pub sound: Sound,
    pub strikes: i64,
}

impl Part {
    fn of(start: Rational, sound: &Sound) -> Part {
        let place = sound.place();
        let sound = match sound {
            Sound::Held { sound, .. } => sound.as_ref().clone(),
            other => other.clone(),
        };
        let heard = sound.length().unwrap_or(place);
        Part {
            start,
            place,
            heard,
            sound,
            strikes: 1,
        }
    }

    /// Whether the sound is a note or a chord, which a generator reshapes; a rest and a phrase are left as they are.
    pub fn is_note(&self) -> bool {
        matches!(self.sound, Sound::Note(_) | Sound::Chord { .. })
    }

    pub fn notes(&self) -> Vec<NoteSound> {
        crate::positions::notes_of(&self.sound)
    }

    /// The highest pitch that sounds.
    pub fn pitch(&self) -> i64 {
        self.notes().iter().map(|note| note.midi).max().unwrap_or(-1)
    }

    /// How loud the sound is, the loudest of a chord's notes, or None for one with no loudness of its own.
    pub fn loudness(&self) -> Option<i64> {
        self.notes().iter().filter_map(|note| note.velocity).max()
    }

    /// The lowest pitch that sounds, or None for a sound with no pitch.
    pub fn lowest(&self) -> Option<i64> {
        self.notes().iter().map(|note| note.midi).min()
    }

    /// Make the sound a rest as long as its place.
    pub fn silence(&mut self) {
        self.sound = Sound::Rest(self.place);
        self.heard = self.place;
        self.strikes = 1;
    }

    /// Move every note of the sound some half steps, or leave it where any note would pass out of the MIDI range.
    pub fn moved_by(&mut self, half_steps: i64) {
        let moved: Option<Vec<NoteSound>> = self.notes().iter().map(|note| note.half_step(half_steps)).collect();
        match (&self.sound, moved) {
            (Sound::Chord { .. }, Some(notes)) => self.sound = Sound::chord(notes),
            (Sound::Note(_), Some(notes)) => self.sound = Sound::Note(notes[0]),
            _ => {}
        }
    }

    /// Make the sound louder or softer by steps of velocity, held to what MIDI allows.
    pub fn louder_by(&mut self, steps: i64) {
        self.sound = match &self.sound {
            Sound::Chord { notes, .. } => Sound::chord(notes.iter().map(|note| louder(note, steps)).collect()),
            Sound::Note(note) => Sound::Note(louder(note, steps)),
            other => other.clone(),
        };
    }

    /// The sounds that take this one's place: itself as heard, held where it outlasts its place and followed by a rest where
    /// it stops short.
    pub fn sounds(&self) -> Vec<Sound> {
        if !self.is_note() {
            if matches!(self.sound, Sound::Rest(_) | Sound::Phrase { .. }) {
                return vec![self.sound.with_length(Some(self.place))];
            }
            if self.heard == self.place {
                return vec![self.sound.clone()];
            }
            return vec![Sound::held(self.sound.clone(), self.place)];
        }
        if self.strikes > 1 {
            let struck = lasting(&self.sound, self.heard / Rational::whole(self.strikes as i128));
            let mut sounds = vec![struck; self.strikes as usize];
            if self.heard < self.place {
                sounds.push(Sound::Rest(self.place - self.heard));
            }
            return sounds;
        }
        let played = lasting(&self.sound, self.heard);
        if self.heard == self.place {
            return vec![played];
        }
        if self.heard > self.place {
            return vec![Sound::held(played, self.place)];
        }
        vec![played, Sound::Rest(self.place - self.heard)]
    }
}

/// Each sound of a clip as a part, with the time it starts at from the clip's start.
pub fn parts_of(sounds: &[Sound]) -> Vec<Part> {
    let mut parts = Vec::new();
    let mut now = Rational::ZERO;
    for sound in sounds {
        parts.push(Part::of(now, sound));
        now = now + sound.place();
    }
    parts
}

/// A note or chord heard for a time, every note of a chord that long.
pub fn lasting(sound: &Sound, heard: Rational) -> Sound {
    match sound {
        Sound::Chord { notes, .. } => Sound::chord(notes.iter().map(|note| NoteSound { length: Some(heard), ..*note }).collect()),
        other => other.with_length(Some(heard)),
    }
}

/// A note louder or softer by steps of velocity, within what MIDI allows; a note with no loudness yet as it is.
pub fn louder(note: &NoteSound, steps: i64) -> NoteSound {
    match note.velocity {
        None => *note,
        Some(velocity) => NoteSound {
            velocity: Some((velocity + steps).clamp(MIN_VELOCITY, MAX_VELOCITY)),
            ..*note
        },
    }
}
