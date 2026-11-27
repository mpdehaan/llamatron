// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What playing a set reads of its objects: each setting as the program uses it, its default filled in where the file leaves
//! it out, and each length read from its text (the getters of the Python model/objects/).

use crate::file::data::Data;
use crate::objects::named::NamedScale;
use crate::objects::pattern::Pattern;
use crate::objects::setlist::{Instrument, Item, Setlist};
use crate::objects::song::{ClipSlot, Scene, Song, Track};
use crate::schema::checking::{time_signature, written_length};
use crate::schema::generated::defaults;
use crate::schema::generated::file_format::{
    ClipSlotSetting, InstrumentKind, InstrumentSetting, PatternSetting, SceneSetting, Section, SetlistSetting, SongSetting, TrackSetting, FLUIDSYNTH_DEVICE,
};
use crate::schema::generated::limits::{MAX_PAN, MAX_STEP_SIZE, MIN_STEPS};
use crate::values::note::Note;
use crate::values::scale::{Scale, ScaleType};
use crate::values::time_signature::TimeSignature;
use crate::ValueError;
use llamatron_math::Rational;

fn whole(value: Option<&Data>) -> Option<i64> {
    value.and_then(Data::as_whole).map(|value| value as i64)
}

fn text(value: Option<&Data>) -> Option<String> {
    value.filter(|value| !value.is_null()).map(Data::python_str)
}

/// Whether a value is what Python takes as true.
fn truthy(value: Option<&Data>) -> bool {
    match value {
        None | Some(Data::Null) | Some(Data::Bool(false)) => false,
        Some(Data::Whole(number)) => *number != 0,
        Some(Data::Text(text)) => !text.is_empty(),
        Some(Data::List(items)) => !items.is_empty(),
        Some(Data::Map(pairs)) => !pairs.is_empty(),
        _ => true,
    }
}

impl Setlist {
    pub fn song_names(&self) -> Vec<&str> {
        self.items(Section::SONGS).iter().map(|(name, _)| name.as_str()).collect()
    }

    pub fn get_song(&self, name: &str) -> Option<&Song> {
        match self.get_item(Section::SONGS, name)? {
            Item::Song(song) => Some(song),
            _ => None,
        }
    }

    /// The pattern of a name, or an instrument's preview pattern by its key, None until one is made.
    pub fn get_pattern(&self, name: &str) -> Option<&Pattern> {
        if let Some(instrument) = crate::objects::instrument_previews::preview_instrument(name) {
            return self.get_instrument(instrument)?.get_preview();
        }
        match self.get_item(Section::PATTERNS, name)? {
            Item::Pattern(pattern) => Some(pattern),
            _ => None,
        }
    }

    /// The scale of a name, or the hidden chromatic scale on C a tonal preview pattern plays under, by its key.
    pub fn get_named_scale(&self, name: &str) -> Option<&NamedScale> {
        if name == crate::objects::instrument_previews::PREVIEW_SCALE_KEY {
            return Some(crate::objects::instrument_previews::preview_scale());
        }
        match self.get_item(Section::SCALES, name)? {
            Item::Scale(scale) => Some(scale),
            _ => None,
        }
    }

    pub fn get_instrument(&self, name: &str) -> Option<&Instrument> {
        match self.get_item(Section::INSTRUMENTS, name)? {
            Item::Instrument(instrument) => Some(instrument),
            _ => None,
        }
    }

    pub fn get_step_size(&self) -> Rational {
        let written = self
            .get_written(SetlistSetting::STEP_SIZE)
            .cloned()
            .unwrap_or(Data::text(defaults::DEFAULT_STEP_SIZE));
        written_length(&written, Rational::whole(MAX_STEP_SIZE as i128)).unwrap_or(Rational::new(1, 16))
    }

    /// How long each step of a pattern is: its own step size, or else the set's.
    pub fn get_pattern_step_size(&self, pattern: &Pattern) -> Rational {
        pattern.get_step_size().unwrap_or_else(|| self.get_step_size())
    }

    /// How long one pass through a pattern lasts: its steps times its step size, whatever the steps hold.
    pub fn get_pattern_length(&self, pattern: &Pattern) -> Rational {
        Rational::whole(pattern.get_steps()) * self.get_pattern_step_size(pattern)
    }

    pub fn get_default_octave(&self) -> i64 {
        whole(self.get_written(SetlistSetting::DEFAULT_OCTAVE)).unwrap_or(defaults::DEFAULT_OCTAVE)
    }

    pub fn get_default_drum_octave(&self) -> i64 {
        whole(self.get_written(SetlistSetting::DEFAULT_DRUM_OCTAVE)).unwrap_or(defaults::DEFAULT_DRUM_OCTAVE)
    }
}

impl NamedScale {
    pub fn get_scale_type(&self) -> Option<ScaleType> {
        ScaleType::named(&self.get_kind().python_str().trim().to_uppercase().replace(' ', "_"))
    }

    /// The scale with its root in an octave.
    pub fn scale_at(&self, octave: i64) -> Result<Scale, ValueError> {
        let root = Note::new(&self.get_root().python_str(), octave, None, None, false)?;
        let kind = self
            .get_scale_type()
            .ok_or_else(|| ValueError(format!("no scale type called {}", self.get_kind().python_str())))?;
        Ok(Scale::new(root, kind))
    }
}

impl Pattern {
    pub fn get_step_size(&self) -> Option<Rational> {
        let written = self.get_written(PatternSetting::STEP_SIZE)?;
        written_length(written, Rational::whole(MAX_STEP_SIZE as i128)).ok()
    }

    pub fn get_time_signature(&self) -> Option<TimeSignature> {
        time_signature(self.get_written(PatternSetting::TIME_SIGNATURE)?).ok()
    }

    pub fn get_direction(&self) -> Option<String> {
        text(self.get_written(PatternSetting::DIRECTION))
    }

    /// The octave of the pattern's first step with one, or None.
    pub fn get_first_octave(&self) -> Option<i64> {
        self.row(crate::schema::generated::file_format::Row::OCTAVE)?
            .iter()
            .find_map(|octave| octave.as_whole())
            .map(|octave| octave as i64)
    }

    pub fn has_enough_steps(&self) -> bool {
        self.get_steps() >= MIN_STEPS as i128
    }
}

impl Song {
    pub fn get_tempo(&self) -> Data {
        self.get_written(SongSetting::TEMPO)
            .cloned()
            .unwrap_or(Data::Whole(defaults::DEFAULT_TEMPO as i128))
    }

    pub fn get_time_signature(&self) -> TimeSignature {
        let written = self
            .get_written(SongSetting::TIME_SIGNATURE)
            .cloned()
            .unwrap_or(Data::text(defaults::DEFAULT_TIME_SIGNATURE));
        time_signature(&written).unwrap_or_else(|_| TimeSignature::new(4, 4).expect("4/4 is a time signature"))
    }

    pub fn get_scale_name(&self) -> Option<String> {
        text(self.get_written(SongSetting::SCALE))
    }

    pub fn get_track(&self, name: &str) -> Option<&Track> {
        self.tracks().iter().find(|(found, _)| found == name).map(|(_, track)| track)
    }

    pub fn get_track_names(&self) -> Vec<&str> {
        self.tracks().iter().map(|(name, _)| name.as_str()).collect()
    }
}

impl Scene {
    pub fn get_repeat(&self) -> i64 {
        whole(self.get_written(SceneSetting::REPEAT)).unwrap_or(defaults::DEFAULT_REPEAT)
    }

    pub fn get_scale_name(&self) -> Option<String> {
        text(self.get_written(SceneSetting::SCALE))
    }

    pub fn get_name(&self) -> Option<String> {
        text(self.get_written(SceneSetting::NAME))
    }

    pub fn get_clip_slot(&self, track: &str) -> Option<&ClipSlot> {
        self.clip_slots().iter().find(|(found, _)| found == track).map(|(_, clip)| clip)
    }

    pub fn get_track_names(&self) -> Vec<&str> {
        self.clip_slots().iter().map(|(name, _)| name.as_str()).collect()
    }

    pub fn every_clip_loops(&self) -> bool {
        !self.clip_slots().is_empty() && self.clip_slots().iter().all(|(_, clip)| clip.loops())
    }
}

impl ClipSlot {
    pub fn get_pattern_names(&self) -> Vec<String> {
        self.get_written(ClipSlotSetting::PATTERNS)
            .and_then(Data::as_list)
            .unwrap_or(&[])
            .iter()
            .map(Data::python_str)
            .collect()
    }

    pub fn get_pattern_name(&self) -> String {
        self.get_pattern_names().into_iter().next().unwrap_or_default()
    }

    /// The clip's own name, else its one pattern's, else its first pattern's with a count of the others.
    pub fn get_display_name(&self) -> String {
        if let Some(name) = text(self.get_written(ClipSlotSetting::NAME)).filter(|name| !name.is_empty()) {
            return name;
        }
        let names = self.get_pattern_names();
        if names.len() == 1 {
            return names[0].clone();
        }
        llamatron_strings::named(
            llamatron_strings::marks::MSG_CLIP_PATTERNS_COUNTED,
            &[("name", names[0].as_str().into()), ("more", ((names.len() - 1) as i64).into())],
        )
    }

    pub fn loops(&self) -> bool {
        truthy(self.get_written(ClipSlotSetting::LOOP))
    }

    pub fn get_repeat(&self) -> i64 {
        whole(self.get_written(ClipSlotSetting::REPEAT)).unwrap_or(defaults::DEFAULT_REPEAT)
    }

    pub fn get_direction(&self) -> Option<String> {
        text(self.get_written(ClipSlotSetting::DIRECTION))
    }

    pub fn get_scale_name(&self) -> Option<String> {
        text(self.get_written(ClipSlotSetting::SCALE))
    }

    pub fn get_pattern_order(&self) -> Option<String> {
        text(self.get_written(ClipSlotSetting::PATTERN_ORDER)).filter(|order| !order.is_empty())
    }
}

impl Track {
    pub fn get_transpose(&self) -> i64 {
        if self.is_drum() {
            return defaults::DEFAULT_TRANSPOSE;
        }
        whole(self.get_written(TrackSetting::TRANSPOSE)).unwrap_or(defaults::DEFAULT_TRANSPOSE)
    }

    pub fn get_default_velocity(&self) -> Option<i64> {
        whole(self.get_written(TrackSetting::DEFAULT_VELOCITY))
    }

    pub fn get_accent(&self) -> i64 {
        whole(self.get_written(TrackSetting::ACCENT)).unwrap_or(defaults::DEFAULT_TRACK_ACCENT)
    }

    pub fn get_instrument_name(&self) -> Option<String> {
        text(self.get_written(TrackSetting::INSTRUMENT))
    }
}

impl Instrument {
    pub fn get_default_velocity(&self) -> Option<i64> {
        whole(self.get_written(InstrumentSetting::DEFAULT_VELOCITY))
    }

    pub fn get_accent(&self) -> i64 {
        whole(self.get_written(InstrumentSetting::ACCENT)).unwrap_or(defaults::DEFAULT_INSTRUMENT_ACCENT)
    }

    /// Where the instrument stands in the stereo field, from 0, hard left, to 100, hard right, 50 unless its Pan says.
    pub fn get_pan(&self) -> i64 {
        whole(self.get_written(InstrumentSetting::PAN)).unwrap_or(defaults::DEFAULT_PAN)
    }

    /// The value of the pan CC, 10, that places the instrument where its Pan says, 0 to 127 with 64 the middle; None where
    /// its Pan was never set, so that nothing is sent and the player's own middle stands.
    pub fn pan_control(&self) -> Option<i64> {
        whole(self.get_written(InstrumentSetting::PAN)).map(pan_control_of)
    }

    /// The MIDI note of each of its keyswitch slots, by slot from 0, None for a slot with no note.
    pub fn keyswitch_notes(&self) -> Vec<Option<i64>> {
        let Some(slots) = self.get_written(InstrumentSetting::KEYSWITCHES).and_then(Data::as_list) else {
            return Vec::new();
        };
        slots.iter().map(|slot| whole(slot.get(KEYSWITCH_NOTE))).collect()
    }

    /// How many milliseconds before its note a keyswitch is sent, 0 for at the same moment.
    pub fn keyswitch_lead(&self) -> i64 {
        whole(self.get_written(InstrumentSetting::KEYSWITCH_LEAD)).unwrap_or(defaults::DEFAULT_KEYSWITCH_LEAD)
    }

    /// What it plays through: off, MIDI or a built-in synth, MIDI where its file does not say.
    pub fn get_kind(&self) -> &str {
        self.get_written(InstrumentSetting::KIND).and_then(Data::as_str).unwrap_or(InstrumentKind::MIDI)
    }

    /// The MIDI device it plays through, where it is a MIDI instrument whose device is chosen: one switched off, or built
    /// in, keeps its device for when it is MIDI again, and plays nothing through it.
    pub fn played_device(&self) -> Option<&str> {
        if self.get_kind() != InstrumentKind::MIDI {
            return None;
        }
        self.get_written(InstrumentSetting::DEVICE).and_then(Data::as_str)
    }

    /// Whether it plays through FluidSynth, which would sound a keyswitch as a note, rather than through a MIDI port.
    pub fn uses_fluidsynth(&self) -> bool {
        self.get_written(InstrumentSetting::DEVICE).and_then(Data::as_str) == Some(FLUIDSYNTH_DEVICE)
    }

    /// The value of the pan CC that places the instrument where its Pan stands, set or not, 64 in the middle.
    pub fn pan_control_in_effect(&self) -> i64 {
        pan_control_of(self.get_pan())
    }
}

/// The pan CC's value for a Pan's percent, rounded to the nearest.
fn pan_control_of(percent: i64) -> i64 {
    (percent * HIGHEST_CONTROL_VALUE + PAN_HALF_STEP) / MAX_PAN
}

/// The key of a keyswitch slot's MIDI note in the file.
const KEYSWITCH_NOTE: &str = "note";

/// The highest value a MIDI CC carries, and half of one percent's share of it, rounding a pan to its nearest CC value.
const HIGHEST_CONTROL_VALUE: i64 = 127;
const PAN_HALF_STEP: i64 = MAX_PAN / 2;

impl Song {
    /// What a step with no velocity typed plays at on a track: the track's own, else its instrument's, else the loudest.
    pub fn default_velocity_of(&self, track: &Track, setlist: &Setlist) -> i64 {
        if let Some(own) = track.get_default_velocity() {
            return own;
        }
        self.instrument_of(track, setlist)
            .and_then(Instrument::get_default_velocity)
            .unwrap_or(defaults::DEFAULT_VELOCITY)
    }

    /// What an accented step adds on a track: the track's accent on top of its instrument's.
    pub fn accent_of(&self, track: &Track, setlist: &Setlist) -> i64 {
        let of_instrument = self
            .instrument_of(track, setlist)
            .map(Instrument::get_accent)
            .unwrap_or(defaults::DEFAULT_INSTRUMENT_ACCENT);
        track.get_accent() + of_instrument
    }

    pub fn instrument_of<'a>(&self, track: &Track, setlist: &'a Setlist) -> Option<&'a Instrument> {
        setlist.get_instrument(&track.get_instrument_name()?)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// An instrument read from its YAML.
    fn instrument(text: &str) -> Instrument {
        let data = crate::file::data::load(text).expect("the scenario's instrument is YAML");
        Instrument::from_data(&data).expect("the scenario's instrument is valid")
    }

    /// Pan sends CC 10 only once set, its percent rounded to the nearest of the CC's values, the middle at 64; an
    /// instrument that never set it stands at 50%.
    #[test]
    fn a_pan_sends_the_cc_value_nearest_its_percent() {
        let control = |pan: i64| instrument(&format!("{{ name: piano, device: FluidSynth, pan: {pan} }}")).pan_control();
        let (left, middle, right) = (0, 50, 100);
        assert_eq!(control(left), Some(0));
        assert_eq!(control(middle), Some(64));
        assert_eq!(control(right), Some(127));
        let unset = instrument("{ name: piano, device: FluidSynth }");
        assert_eq!(unset.pan_control(), None);
        assert_eq!(unset.get_pan(), defaults::DEFAULT_PAN);
    }
}
