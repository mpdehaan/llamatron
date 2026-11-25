// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The cut written as a song's data (the Python importers/writing.py): the song named after the file, a track after each
//! voice, a pattern after the first track that plays it and numbered, a scale for each key named after its root and kind
//! unless the set has one so named, a scene after the bars it plays, and each track through an instrument named after its
//! General MIDI sound, played through FluidSynth.

use crate::cutting::{Cut, CutPattern, CutScene};
use crate::keys::MusicalKey;
use crate::steps::{ControlSteps, Step, StepDegree};
use crate::voices::Voice;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::naming::{copy_name, new_name, unique_name};
use llamatron_model::objects::setlist::{Item, Setlist};
use llamatron_model::schema::generated::file_format::Section;
use llamatron_strings::texts::labels;

const NOTE_ROWS: [&str; 11] = [
    "degree",
    "accidental",
    "octave",
    "chord",
    "tension",
    "inversion",
    "double",
    "omit",
    "bass",
    "gate",
    "velocity",
];
const SWITCH_ROWS: [&str; 3] = ["tie", "glide", "bass_octave"];
const CC_ROWS: [&str; 4] = ["cc1", "cc2", "cc3", "cc4"];
const DEFAULT_VELOCITY: i64 = 127;
const MIN_TEMPO_PERCENT: i128 = 10;
const MAX_TEMPO_PERCENT: i128 = 400;
const MICROSECONDS_PER_MINUTE: i128 = 60_000_000;
const FLUIDSYNTH_DEVICE: &str = "*FluidSynth";

/// Things a song needs, each with its name.
type Named = Vec<(String, Data)>;

/// A song an import makes, ready to add to a set: its name, its data, and the patterns, scales and instruments it needs.
pub struct ImportedSong {
    pub name: String,
    pub song: Data,
    pub patterns: Vec<(String, Data)>,
    pub scales: Vec<(String, Data)>,
    pub instruments: Vec<(String, Data)>,
}

fn text(value: &str) -> Data {
    Data::text(value)
}

fn map(pairs: Vec<(&str, Data)>) -> Data {
    Data::Map(pairs.into_iter().map(|(key, value)| (text(key), value)).collect())
}

/// An exact length as a file holds it: a whole number, or text like 3/16.
pub fn fraction_text(value: Rational) -> Data {
    if value.is_whole() {
        return Data::Whole(value.numerator());
    }
    Data::text(&format!("{}/{}", value.numerator(), value.denominator()))
}

fn optional(value: Option<&str>) -> Data {
    value.map(text).unwrap_or(Data::Null)
}

/// A pattern's data: its steps, its step size where it isn't the set's, whether it is a drum's, and each row holding a value.
fn pattern_data(pattern: &CutPattern, set_step_size: Rational) -> Data {
    let (drum, step_size, steps, controls) = pattern;
    let count = steps.len();
    let mut rows: Vec<(&str, Vec<Data>)> = NOTE_ROWS.iter().map(|row| (*row, vec![Data::Null; count])).collect();
    rows.extend(SWITCH_ROWS.iter().map(|row| (*row, vec![Data::Bool(false); count])));
    let mut put = |row: &str, place: usize, value: Data| {
        if let Some((_, values)) = rows.iter_mut().find(|(found, _)| *found == row) {
            values[place] = value;
        }
    };
    for (place, step) in steps.iter().enumerate() {
        match step {
            Some(Step::Tied) => put("tie", place, Data::Bool(true)),
            Some(Step::Note(step)) => {
                let degree = match &step.degree {
                    StepDegree::Number(number) => Data::Whole(*number as i128),
                    StepDegree::Letter(letter) => text(letter),
                };
                put("degree", place, degree);
                put("accidental", place, optional(step.accidental));
                put("octave", place, Data::Whole(step.octave as i128));
                put("chord", place, optional(step.chord));
                put(
                    "tension",
                    place,
                    step.tension.map(|tension| Data::List(vec![text(tension)])).unwrap_or(Data::Null),
                );
                put(
                    "inversion",
                    place,
                    if step.inversion == 0 {
                        Data::Null
                    } else {
                        Data::Whole(step.inversion as i128)
                    },
                );
                put("double", place, optional(step.doubling));
                put("omit", place, optional(step.omission));
                put("bass", place, optional(step.bass));
                put("gate", place, step.gate.map(fraction_text).unwrap_or(Data::Null));
                put(
                    "velocity",
                    place,
                    if step.velocity == DEFAULT_VELOCITY {
                        Data::Null
                    } else {
                        Data::Whole(step.velocity as i128)
                    },
                );
                put("glide", place, Data::Bool(step.glide));
                put("bass_octave", place, Data::Bool(step.bass_octave));
            }
            None => {}
        }
    }
    let mut data = vec![(text("steps"), Data::Whole(count as i128))];
    if *step_size != set_step_size {
        data.push((text("step_size"), fraction_text(*step_size)));
    }
    if *drum {
        data.push((text("drum"), Data::Bool(true)));
    }
    for (row, values) in rows {
        let holds = if SWITCH_ROWS.contains(&row) {
            values.contains(&Data::Bool(true))
        } else {
            values.iter().any(|value| !value.is_null())
        };
        if holds {
            data.push((text(row), Data::List(values)));
        }
    }
    data.extend(control_rows(controls));
    Data::Map(data)
}

fn control_rows(controls: &ControlSteps) -> Vec<(Data, Data)> {
    let mut rows = Vec::new();
    if controls.is_empty() {
        return rows;
    }
    for (lane, row) in CC_ROWS.iter().enumerate() {
        let values: Vec<Data> = controls
            .iter()
            .map(|step| {
                step.as_ref()
                    .and_then(|step| step.values.get(lane).copied().flatten())
                    .map(|value| Data::Whole(value as i128))
                    .unwrap_or(Data::Null)
            })
            .collect();
        if values.iter().any(|value| !value.is_null()) {
            rows.push((text(row), Data::List(values)));
        }
    }
    let slides: Vec<Data> = controls.iter().map(|step| Data::Bool(step.as_ref().is_some_and(|step| step.slide))).collect();
    if slides.contains(&Data::Bool(true)) {
        rows.push((text("slide"), Data::List(slides)));
    }
    rows
}

fn tempo_percent_of(microseconds: i64, song_microseconds: i64) -> Data {
    let percent = Rational::new(song_microseconds as i128 * 100, microseconds as i128);
    fraction_text(percent.max(Rational::whole(MIN_TEMPO_PERCENT)).min(Rational::whole(MAX_TEMPO_PERCENT)))
}

/// A tempo in microseconds a quarter note as a song's tempo: a whole number of beats a minute where one gives the very same
/// microseconds, else exact.
pub fn tempo_of(microseconds: i64) -> Data {
    let exact = Rational::new(MICROSECONDS_PER_MINUTE, microseconds as i128);
    let whole = exact.round();
    if whole != 0 && (60.0 * 1e6 / whole as f64 * 4.0 / 4.0).round_ties_even() as i64 == microseconds {
        return Data::Whole(whole);
    }
    fraction_text(exact)
}

/// A word a name is made from, as the program makes one: lowercase, underscores for spaces.
fn suggested_word(text: &str) -> String {
    text.trim().to_lowercase().replace(' ', "_")
}

fn instrument_name(voice: &Voice) -> String {
    match voice.sound {
        None => "drums".to_string(),
        Some(sound) => suggested_word(&labels::MSG_GM_SOUNDS[(sound - 1) as usize].replace(['(', ')'], "")),
    }
}

fn default_scale_name(key: &MusicalKey) -> String {
    format!("{}_{}", key.root, suggested_word(&key.kind.replace('_', " ")))
}

fn title(text: &str) -> String {
    text.split(' ')
        .map(|word| {
            let mut characters = word.chars();
            match characters.next() {
                Some(first) => first.to_uppercase().collect::<String>() + &characters.as_str().to_lowercase(),
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn is_default_scale_name(name: &str, key: &MusicalKey) -> bool {
    let legacy = format!("{} {}", key.root, title(&key.kind.replace('_', " ")));
    name.to_lowercase() == default_scale_name(key).to_lowercase() || name.to_lowercase() == legacy.to_lowercase()
}

pub struct SongWriter<'w> {
    pub setlist: &'w Setlist,
    pub voices: &'w [Voice],
    pub cut: &'w Cut,
    pub bars: &'w [Rational],
    pub step_size: Rational,
}

impl SongWriter<'_> {
    pub fn track_names(&self) -> Vec<String> {
        let mut names: Vec<String> = Vec::new();
        for voice in self.voices {
            names.push(unique_name(&voice.name, &names));
        }
        names
    }

    pub fn written(&self, name: &str, time_signature: Option<String>) -> ImportedSong {
        let track_names = self.track_names();
        let (patterns, pattern_names) = self.patterns(&track_names);
        let (scales, scale_names) = self.scales();
        let mut song = vec![("tempo", tempo_of(self.song_microseconds()))];
        if let Some(signature) = time_signature {
            song.push(("time_signature", text(&signature)));
        }
        song.push(("scale", text(&scale_names[0])));
        let tracks = track_names
            .iter()
            .zip(self.voices)
            .map(|(track, voice)| (text(track), self.track_data(voice)))
            .collect();
        song.push(("tracks", Data::Map(tracks)));
        let scenes = self
            .cut
            .scenes
            .iter()
            .enumerate()
            .map(|(place, scene)| self.scene_data(scene, &scale_names[0], &pattern_names, &scale_names[place], &track_names))
            .collect();
        song.push(("scenes", Data::List(scenes)));
        let song_names: Vec<&str> = self.setlist.song_names();
        let song_name = if song_names.iter().any(|found| found.to_lowercase() == name.to_lowercase()) {
            copy_name(name, &song_names)
        } else {
            name.to_string()
        };
        ImportedSong {
            name: song_name,
            song: map(song),
            patterns,
            scales,
            instruments: self.instruments(),
        }
    }

    fn track_data(&self, voice: &Voice) -> Data {
        let mut data = vec![("instrument", text(&instrument_name(voice)))];
        if voice.drum {
            data.push(("drum", Data::Bool(true)));
        }
        if !voice.lanes.is_empty() {
            let mut lanes: Vec<Data> = voice.lanes.iter().map(|number| Data::Whole(*number as i128)).collect();
            lanes.resize(CC_ROWS.len(), Data::Null);
            data.push(("cc", Data::List(lanes)));
        }
        map(data)
    }

    fn instruments(&self) -> Vec<(String, Data)> {
        let mut made: Vec<(String, Data)> = Vec::new();
        for voice in self.voices {
            let name = instrument_name(voice);
            if self.setlist.get_instrument(&name).is_some() {
                continue;
            }
            let mut data = vec![("device", text(FLUIDSYNTH_DEVICE))];
            if let Some(sound) = voice.sound {
                data.push(("gm_sound", Data::Whole(sound as i128)));
            }
            match made.iter_mut().find(|(found, _)| *found == name) {
                Some((_, found)) => *found = map(data),
                None => made.push((name, map(data))),
            }
        }
        made
    }

    fn patterns(&self, track_names: &[String]) -> (Named, Vec<(CutPattern, String)>) {
        let set_step_size = self.setlist.get_step_size();
        let mut taken: Vec<String> = self.setlist.items(Section::PATTERNS).iter().map(|(name, _)| name.clone()).collect();
        let mut first_track: Vec<(CutPattern, String)> = Vec::new();
        for scene in &self.cut.scenes {
            for clip in &scene.clips {
                for pattern in &clip.patterns {
                    if !first_track.iter().any(|(found, _)| found == pattern) {
                        first_track.push((pattern.clone(), track_names[clip.voice].clone()));
                    }
                }
            }
        }
        let mut added = Vec::new();
        let mut names = Vec::new();
        for pattern in &self.cut.patterns {
            let data = pattern_data(pattern, set_step_size);
            let word = first_track
                .iter()
                .find(|(found, _)| found == pattern)
                .map(|(_, track)| track.clone())
                .unwrap_or_default();
            let name = new_name(&word, &taken);
            taken.push(name.clone());
            added.push((name.clone(), data));
            names.push((pattern.clone(), name));
        }
        (added, names)
    }

    fn scales(&self) -> (Vec<(String, Data)>, Vec<String>) {
        let mut taken: Vec<String> = self.setlist.items(Section::SCALES).iter().map(|(name, _)| name.clone()).collect();
        let mut added = Vec::new();
        let mut names: Vec<(MusicalKey, String)> = Vec::new();
        for scene in &self.cut.scenes {
            let key = &scene.key;
            if names.iter().any(|(found, _)| found == key) {
                continue;
            }
            let name = match self.scale_already_named(key) {
                Some(name) => name,
                None => {
                    let name = unique_name(&default_scale_name(key), &taken);
                    taken.push(name.clone());
                    added.push((name.clone(), map(vec![("root", text(&key.root)), ("type", text(&key.kind))])));
                    name
                }
            };
            names.push((key.clone(), name));
        }
        let per_scene = self
            .cut
            .scenes
            .iter()
            .map(|scene| {
                names
                    .iter()
                    .find(|(found, _)| *found == scene.key)
                    .map(|(_, name)| name.clone())
                    .unwrap_or_default()
            })
            .collect();
        (added, per_scene)
    }

    fn scale_already_named(&self, key: &MusicalKey) -> Option<String> {
        for (name, item) in self.setlist.items(Section::SCALES) {
            let Item::Scale(scale) = item else { continue };
            if scale.get_root().python_str() == key.root && scale.get_kind().python_str() == key.kind && is_default_scale_name(name, key) {
                return Some(name.clone());
            }
        }
        None
    }

    fn song_microseconds(&self) -> i64 {
        let tempos: Vec<i64> = self.cut.scenes.iter().map(|scene| scene.tempo).collect();
        let lowest = *tempos.iter().min().unwrap_or(&500_000);
        tempos[0].min(lowest * MAX_TEMPO_PERCENT as i64 / 100)
    }

    fn scene_data(&self, scene: &CutScene, song_scale: &str, pattern_names: &[(CutPattern, String)], scale_name: &str, track_names: &[String]) -> Data {
        let mut data = vec![("name", text(&self.bars_named(scene)))];
        if scene.repeat > 1 {
            data.push(("repeat", Data::Whole(scene.repeat as i128)));
        }
        if scale_name != song_scale {
            data.push(("scale", text(scale_name)));
        }
        let percent = tempo_percent_of(scene.tempo, self.song_microseconds());
        if percent != Data::Whole(100) {
            data.push(("tempo", percent));
        }
        let mut clips: Vec<(Data, Data)> = Vec::new();
        for clip in &scene.clips {
            let names: Vec<String> = clip
                .patterns
                .iter()
                .map(|pattern| {
                    pattern_names
                        .iter()
                        .find(|(found, _)| found == pattern)
                        .map(|(_, name)| name.clone())
                        .unwrap_or_default()
                })
                .collect();
            let mut clip_data = if names.len() > 1 {
                vec![("patterns", Data::List(names.iter().map(|name| text(name)).collect()))]
            } else {
                vec![("pattern", text(&names[0]))]
            };
            if clip.repeats > 1 {
                clip_data.push(("repeat", Data::Whole(clip.repeats as i128)));
            }
            let track = text(&track_names[clip.voice]);
            match clips.iter_mut().find(|(found, _)| *found == track) {
                Some((_, found)) => *found = map(clip_data),
                None => clips.push((track, map(clip_data))),
            }
        }
        data.push(("tracks", Data::Map(clips)));
        map(data)
    }

    fn bars_named(&self, scene: &CutScene) -> String {
        let start = self.step_size * Rational::whole(scene.start as i128);
        let last = self.step_size * Rational::whole((scene.start + (scene.end - scene.start) * scene.repeat - 1) as i128);
        let (first_bar, last_bar) = (self.bar_number(start), self.bar_number(last));
        if first_bar == last_bar {
            format!("bar {first_bar}")
        } else {
            format!("bars {first_bar}-{last_bar}")
        }
    }

    fn bar_number(&self, time: Rational) -> usize {
        self.bars[..self.bars.len() - 1].iter().filter(|line| **line <= time).count()
    }
}
