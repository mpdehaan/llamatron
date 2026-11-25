// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The musicians of a band (the Python engine/generators/musician/): each plays a track's part as a player of that
//! instrument would in the song, by the kind of section its scene is, round the tune another track carries and along the
//! chords another plays, with the player's own touch. Every note is one the clip wrote, moved to the chord, left out, held,
//! shortened, struck again or made louder or softer; nothing is drawn by chance but a loose player's loudness.

use crate::chord_source::ChordSource;
use crate::clip::Clip;
use crate::error::Rendered;
use crate::generators::chords::follow;
use crate::generators::parts::{parts_of, Part};
use crate::sound::{scale_sound, Sound};
use crate::tune_source::TuneSource;
use llamatron_math::{PythonRandom, Rational, Seed};
use llamatron_model::file::data::Data;

const SPARSE: &str = "sparse";
const LIGHT: &str = "light";
const BUSY: &str = "busy";
const VERY_BUSY: &str = "very busy";
const AS_WRITTEN: &str = "as written";
const NO_GIVING_WAY: &str = "none";
const GIVES_WAY_SOME: &str = "some";
const GIVES_WAY_OFTEN: &str = "often";
const IN_THE_GAPS: &str = "plays in the gaps";
const HELD_NOTES: &str = "held";
const SHORT_NOTES: &str = "short";

/// An instrument's player: the pitches it can play, None for a drum, and how it gives way and plays its notes when its
/// settings leave that out.
struct Instrument {
    range: Option<(i64, i64)>,
    gives_way: &'static str,
    notes: &'static str,
}

fn instrument(name: &str) -> Instrument {
    let (range, gives_way, notes) = match name {
        "bassist" => (Some((28, 55)), NO_GIVING_WAY, AS_WRITTEN),
        "drummer" | "percussionist" => (None, NO_GIVING_WAY, AS_WRITTEN),
        "backing piano" => (Some((36, 96)), GIVES_WAY_SOME, AS_WRITTEN),
        "backing organ" => (Some((36, 84)), GIVES_WAY_SOME, HELD_NOTES),
        "backing synth" => (Some((36, 96)), GIVES_WAY_SOME, HELD_NOTES),
        "lead guitarist" => (Some((52, 88)), IN_THE_GAPS, AS_WRITTEN),
        "lead organ" => (Some((48, 91)), IN_THE_GAPS, HELD_NOTES),
        "lead piano" | "lead synth" => (Some((48, 100)), IN_THE_GAPS, AS_WRITTEN),
        "answering player" => (Some((48, 88)), IN_THE_GAPS, AS_WRITTEN),
        "backup singers" => (Some((48, 79)), GIVES_WAY_SOME, HELD_NOTES),
        "horn section" => (Some((46, 82)), GIVES_WAY_SOME, SHORT_NOTES),
        "string section" => (Some((36, 96)), GIVES_WAY_SOME, HELD_NOTES),
        _ => (Some((40, 76)), GIVES_WAY_SOME, AS_WRITTEN),
    };
    Instrument { range, gives_way, notes }
}

/// What a musician hears round its clip: the kind of section the scene is, the chords of the track it reads them from, and
/// when the tune sounds on another track.
pub struct Surroundings {
    pub section: Option<String>,
    pub chords: Option<ChordSource>,
    pub tune: Option<TuneSource>,
}

/// One stage of how a musician plays a part: what it does to the parts that are notes as it reaches them.
type Stage = fn(&Musician, &mut [Part], &[usize]);

pub struct Musician {
    instrument: Instrument,
    bar: Rational,
    beat: Rational,
    surroundings: Surroundings,
    activity: String,
    loudness: i64,
    looseness: i64,
    gives_way: String,
    accents: String,
    notes: String,
    range: String,
    plays: bool,
    form: String,
    seed: Option<i128>,
}

/// The instrument and the tracks a Musician's settings name, for the Realizer to find what it hears.
pub fn plays_pitches(settings: &Data) -> bool {
    instrument(&settings.get("instrument").map(Data::python_str).unwrap_or_default())
        .range
        .is_some()
}

impl Musician {
    pub fn of(settings: &Data, bar: Rational, beat: Rational, surroundings: Surroundings, seed: Option<i128>) -> Musician {
        let written = |name: &str| settings.get(name).filter(|value| !value.is_null());
        let text = |name: &str, default: &str| written(name).map(Data::python_str).unwrap_or(default.to_string());
        let whole = |name: &str| written(name).and_then(Data::as_whole).unwrap_or(0) as i64;
        let player = instrument(&text("instrument", "rhythm guitarist"));
        let own = surroundings
            .section
            .as_ref()
            .and_then(|section| written("by_section").and_then(|by_section| by_section.get(section)).cloned())
            .unwrap_or(Data::Map(Vec::new()));
        let plays = own.get("plays") != Some(&Data::Bool(false));
        let form = own
            .get("played")
            .filter(|form| !form.is_null())
            .map(Data::python_str)
            .unwrap_or("whole".to_string());
        Musician {
            gives_way: text("gives_way", player.gives_way),
            notes: text("notes", player.notes),
            instrument: player,
            bar,
            beat,
            surroundings,
            activity: text("activity", AS_WRITTEN),
            loudness: whole("loudness"),
            looseness: whole("looseness"),
            accents: text("accents", "none"),
            range: text("range", AS_WRITTEN),
            plays,
            form,
            seed,
        }
    }

    pub fn generate(&self, clip: &Clip) -> Rendered<Clip> {
        let finished = |sounds: Vec<Sound>| Clip {
            sounds,
            time_signature: None,
            looping: true,
            groove: None,
            ..clip.clone()
        };
        if !self.plays {
            let mut parts = parts_of(&clip.resolved_sounds()?);
            for part in parts.iter_mut().filter(|part| part.is_note()) {
                part.silence();
            }
            return Ok(finished(parts.iter().flat_map(Part::sounds).collect()));
        }
        let mut clip = clip.clone();
        if let (Some(_), Some(chords)) = (self.instrument.range, &self.surroundings.chords) {
            clip = follow(&clip, Some(chords))?;
        }
        let mut settled = Vec::new();
        for sound in clip.resolved_sounds()? {
            settled.push(match (&sound, clip.scale.as_ref()) {
                (
                    Sound::Degree {
                        length,
                        number,
                        octave,
                        scale_notes,
                        half_steps,
                    },
                    Some(scale),
                ) => Sound::Note(
                    scale_sound(scale, *number, *scale_notes, octave * 12 + half_steps, *length, None, false)
                        .map_err(|problem| crate::error::RenderError::Refused(problem.0))?,
                ),
                _ => sound,
            });
        }
        let mut parts = parts_of(&settled);
        // Each stage plays the parts that are notes as it reaches them, so that a note an earlier stage silenced is a rest to it.
        let stages: [Stage; 7] = [
            Musician::play_form,
            Musician::play_activity,
            Musician::give_way,
            Musician::hold_notes,
            Musician::lean_on,
            Musician::play_in_range,
            Musician::play_loud,
        ];
        for stage in stages {
            let notes: Vec<usize> = (0..parts.len()).filter(|place| parts[*place].is_note()).collect();
            stage(self, &mut parts, &notes);
        }
        Ok(finished(parts.iter().flat_map(Part::sounds).collect()))
    }

    fn in_bar(&self, part: &Part) -> Rational {
        part.start - Rational::whole((part.start / self.bar).floor()) * self.bar
    }

    fn on_grid(&self, part: &Part, grid: Rational) -> bool {
        (self.in_bar(part) / grid).is_whole()
    }

    /// The part played as a kind of section asks: softer, thinned to the beats, its head alone, muted, or as hits.
    fn play_form(&self, parts: &mut [Part], notes: &[usize]) {
        for place in notes {
            let part = &mut parts[*place];
            match self.form.as_str() {
                "softer" => part.louder_by(-18),
                "thinned" if !self.on_grid(part, self.beat) => part.silence(),
                "head only" if (part.start / self.bar).floor() % 2 != 0 => part.silence(),
                "muted" => {
                    part.heard = part.heard.min(Rational::new(1, 16));
                    part.louder_by(-10);
                }
                "hits" => {
                    if self.on_grid(part, self.bar) {
                        part.heard = part.heard.min(Rational::new(1, 4));
                    } else {
                        part.silence();
                    }
                }
                _ => {}
            }
        }
    }

    /// Fewer of the part's notes, or its long notes struck again.
    fn play_activity(&self, parts: &mut [Part], notes: &[usize]) {
        for place in notes {
            let part = &mut parts[*place];
            match self.activity.as_str() {
                SPARSE | LIGHT => {
                    let half_bar = self.bar / Rational::whole(2);
                    let grid = if self.activity == SPARSE && (half_bar / self.beat).is_whole() {
                        half_bar
                    } else {
                        self.beat
                    };
                    if part.heard < self.beat && !self.on_grid(part, grid) {
                        part.silence();
                    }
                }
                BUSY | VERY_BUSY => {
                    let longest = if self.activity == BUSY { Rational::new(1, 4) } else { Rational::new(1, 8) };
                    if part.heard >= longest {
                        part.strikes = 2;
                    }
                }
                _ => {}
            }
        }
    }

    /// Room made for the tune while it sounds on another track.
    fn give_way(&self, parts: &mut [Part], notes: &[usize]) {
        let Some(tune) = &self.surroundings.tune else { return };
        if self.gives_way == NO_GIVING_WAY {
            return;
        }
        for place in notes {
            let part = &mut parts[*place];
            if !tune.sounds_at(part.start) {
                continue;
            }
            if self.gives_way == IN_THE_GAPS {
                part.silence();
                continue;
            }
            part.louder_by(if self.gives_way == GIVES_WAY_SOME { -12 } else { -22 });
            if self.gives_way == GIVES_WAY_OFTEN && part.heard < self.beat && !self.on_grid(part, self.beat) {
                part.silence();
            }
        }
    }

    /// Each note held until the next starts, or cut short.
    fn hold_notes(&self, parts: &mut [Part], notes: &[usize]) {
        if self.notes == HELD_NOTES {
            for pair in notes.windows(2) {
                let after = parts[pair[1]].start;
                let part = &mut parts[pair[0]];
                if part.strikes == 1 {
                    part.heard = part.heard.max(after - part.start);
                }
            }
        } else if self.notes == SHORT_NOTES {
            for place in notes {
                let part = &mut parts[*place];
                part.heard = part.heard.min(Rational::new(1, 8) * Rational::whole(part.strikes as i128));
            }
        }
    }

    /// The notes the musician leans on played louder.
    fn lean_on(&self, parts: &mut [Part], notes: &[usize]) {
        if self.accents == "none" {
            return;
        }
        for place in notes {
            let in_bar = self.in_bar(&parts[*place]);
            let on_beat = (in_bar / self.beat).is_whole();
            let leaned = match self.accents.as_str() {
                "downbeat" => in_bar == Rational::ZERO,
                "backbeat" => on_beat && (in_bar / self.beat).floor() % 2 == 1,
                _ => !on_beat,
            };
            if leaned {
                parts[*place].louder_by(12);
            }
        }
    }

    /// The part moved an octave lower or higher, each note then brought by octaves inside what the instrument plays.
    fn play_in_range(&self, parts: &mut [Part], notes: &[usize]) {
        let Some((lowest, highest)) = self.instrument.range else { return };
        let shift = match self.range.as_str() {
            "low" => -12,
            "high" => 12,
            _ => return,
        };
        for place in notes {
            let part = &mut parts[*place];
            part.moved_by(shift);
            while part.lowest().is_some_and(|low| low < lowest) {
                let before = part.lowest();
                part.moved_by(12);
                if part.lowest() == before {
                    break;
                }
            }
            while part.lowest().is_some_and(|low| part.pitch() > highest && low - 12 >= lowest) {
                part.moved_by(-12);
            }
        }
    }

    /// Every note louder or softer by the musician's loudness, a loose one's each a little more by chance from the seed.
    fn play_loud(&self, parts: &mut [Part], notes: &[usize]) {
        let mut dice = match self.seed {
            Some(seed) => PythonRandom::new(Seed::Whole(seed)),
            None => PythonRandom::unseeded(),
        };
        let reach = self.looseness * 4;
        for place in notes {
            let wander = if reach != 0 { dice.randint(-reach as i128, reach as i128) as i64 } else { 0 };
            if self.loudness != 0 || wander != 0 {
                parts[*place].louder_by(self.loudness * 7 + wander);
            }
        }
    }
}
