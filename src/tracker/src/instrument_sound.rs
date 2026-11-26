// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An instrument's built-in sound as the instrument page reads it (the Python model/objects/built_in_sound.py and the
//! instrument's sound getters): each setting its own, or its engine's preset's, or its part's type's default.

use crate::generated::sounds::{Preset, ENGINE_PRESETS, LFO_DEFAULTS, SOUND_DEFAULTS, TYPE_DEFAULTS};
use llamatron_model::file::data::Data;
use llamatron_model::objects::lfo_speed;
use llamatron_model::objects::setlist::Instrument;
use llamatron_model::schema::generated::file_format::InstrumentSetting;
/// An LFO slot's settings that its Type decides, and the Type that offers them.
const LFOS: &str = "lfos";
pub const LFO_TYPE: &str = "type";
pub const LFO_PLUS: &str = "lfo_plus";
const LFO_SHAPE: &str = "shape";
const LFO_SPEED: &str = "speed";
pub const LFO_FADE_IN: &str = "fade_in";
const SMOOTH_RANDOM: &str = "smooth_random";
const SAMPLE_AND_HOLD: &str = "sample_and_hold";

/// The envelopes' parts, in the order a sound's list of envelopes holds them.
pub const ENVELOPE_PARTS: [&str; 3] = ["env1", "env2", "env3"];
const TYPE: &str = "type";
const ENGINE: &str = "engine";

impl Preset {
    pub fn to_data(self) -> Data {
        match self {
            Preset::Null => Data::Null,
            Preset::Flag(flag) => Data::Bool(flag),
            Preset::Whole(number) => Data::Whole(number as i128),
            Preset::Text(text) => Data::Text(text.to_string()),
            Preset::List(items) => Data::List(items.iter().map(|item| item.to_data()).collect()),
            Preset::Map(pairs) => Data::Map(pairs.iter().map(|(name, item)| (Data::text(name), item.to_data())).collect()),
        }
    }

    fn get(self, name: &str) -> Option<Preset> {
        match self {
            Preset::Map(pairs) => pairs.iter().find(|(found, _)| *found == name).map(|(_, item)| *item),
            _ => None,
        }
    }
}

fn found(table: &[(&str, Preset)], name: &str) -> Option<Preset> {
    table.iter().find(|(found, _)| *found == name).map(|(_, item)| *item)
}

/// An instrument's sound as it holds it.
pub struct Sound {
    written: Option<Data>,
}

impl Sound {
    pub fn of(instrument: &Instrument) -> Sound {
        Sound {
            written: instrument.get_written(InstrumentSetting::SOUND).filter(|sound| !sound.is_null()).cloned(),
        }
    }

    fn own(&self, name: &str) -> Option<Data> {
        self.written.as_ref().and_then(|sound| sound.get(name)).cloned()
    }

    fn engine_preset(&self) -> Option<Preset> {
        let engine = self.value(ENGINE);
        found(ENGINE_PRESETS, engine.as_str().unwrap_or(""))
    }

    /// One of the sound's own settings: its own, the default, or its engine's preset's.
    pub fn value(&self, name: &str) -> Data {
        if let Some(own) = self.own(name) {
            return own;
        }
        if let Some(default) = SOUND_DEFAULTS.get(name) {
            return default.to_data();
        }
        self.engine_preset().and_then(|preset| preset.get(name)).map_or(Data::Null, Preset::to_data)
    }

    fn preset_part(&self, part: &str) -> Data {
        self.engine_preset()
            .and_then(|preset| preset.get(part))
            .map_or(Data::Map(Vec::new()), Preset::to_data)
    }

    /// A part as the sound holds it: its own, or its engine's preset's.
    pub fn part(&self, part: &str) -> Data {
        if let Some(place) = ENVELOPE_PARTS.iter().position(|each| *each == part) {
            if let Some(envelope) = self
                .own("envelopes")
                .as_ref()
                .and_then(Data::as_list)
                .and_then(|envelopes| envelopes.get(place))
            {
                return envelope.clone();
            }
        } else if let Some(own) = self.own(part) {
            return own;
        }
        self.preset_part(part)
    }

    pub fn part_type(&self, part: &str) -> String {
        self.part(part).get(TYPE).and_then(Data::as_str).unwrap_or("").to_string()
    }

    /// One of a part's settings: its own, its preset's where the type is the preset's, or its type's default.
    pub fn part_value(&self, part: &str, name: &str) -> Data {
        let stored = self.part(part);
        if let Some(value) = stored.get(name) {
            return value.clone();
        }
        let kind = stored.get(TYPE).and_then(Data::as_str).unwrap_or("").to_string();
        let preset = self.preset_part(part);
        if preset.get(TYPE).and_then(Data::as_str) == Some(kind.as_str()) {
            if let Some(value) = preset.get(name) {
                return value.clone();
            }
        }
        found(TYPE_DEFAULTS, &kind)
            .and_then(|defaults| defaults.get(name))
            .map_or(Data::Null, Preset::to_data)
    }

    /// One setting of an item of one of the sound's lists, the LFOs, the effects or the matrix, by its number from 1.
    pub fn item(&self, list: &str, number: usize, name: &str, defaults: Preset) -> Data {
        let items = self.value(list);
        let item = items
            .as_list()
            .and_then(|items| items.get(number - 1))
            .cloned()
            .unwrap_or(Data::Map(Vec::new()));
        item.get(name)
            .cloned()
            .unwrap_or_else(|| defaults.get(name).map_or(Data::Null, Preset::to_data))
    }

    /// One setting of an LFO, by its number from 1, as its Type plays it: an LFO, not an LFO+, plays a Smooth random shape
    /// as Sample & Hold, a Tempo speed as the default Speed, and no Fade in, so that a slot turned back to LFO sounds as an
    /// LFO does while keeping what its LFO+ was set to.
    pub fn lfo_setting(&self, number: usize, name: &str) -> Data {
        let value = self.item(LFOS, number, name, LFO_DEFAULTS);
        let is_plus = self.item(LFOS, number, LFO_TYPE, LFO_DEFAULTS).as_str() == Some(LFO_PLUS);
        if is_plus {
            return value;
        }
        match (name, value.as_str()) {
            (LFO_SHAPE, Some(SMOOTH_RANDOM)) => Data::text(SAMPLE_AND_HOLD),
            (LFO_SPEED, Some(lfo_speed::TEMPO_SPEED)) => Data::text(lfo_speed::DEFAULT_SPEED),
            (LFO_FADE_IN, _) => Data::Whole(0),
            _ => value,
        }
    }

    /// Whether an LFO, by its number from 1, is an LFO+.
    pub fn is_lfo_plus(&self, number: usize) -> bool {
        self.item(LFOS, number, LFO_TYPE, LFO_DEFAULTS).as_str() == Some(LFO_PLUS)
    }

    /// One setting of an oscillator of a basic engine's, by its number from 1.
    pub fn oscillator(&self, number: usize, name: &str) -> Data {
        let oscillators = self.part_value("oscillators", "oscillators");
        let item = oscillators
            .as_list()
            .and_then(|items| items.get(number - 1))
            .cloned()
            .unwrap_or(Data::Map(Vec::new()));
        item.get(name)
            .cloned()
            .unwrap_or_else(|| crate::generated::sounds::OSCILLATOR_DEFAULTS.get(name).map_or(Data::Null, Preset::to_data))
    }
}

/// Put a value under a name in a mapping, replacing what it held, or adding it last.
fn put(map: &mut Data, name: &str, value: Data) {
    if !matches!(map, Data::Map(_)) {
        *map = Data::Map(Vec::new());
    }
    if let Data::Map(pairs) = map {
        match pairs.iter_mut().find(|(key, _)| key.as_str() == Some(name)) {
            Some((_, held)) => *held = value,
            None => pairs.push((Data::text(name), value)),
        }
    }
}

impl Sound {
    fn written_or_empty(&self) -> Data {
        self.written.clone().unwrap_or(Data::Map(Vec::new()))
    }

    /// The sound with one of its own settings changed.
    pub fn with_value(&self, name: &str, value: Data) -> Data {
        let mut sound = self.written_or_empty();
        put(&mut sound, name, value);
        sound
    }

    /// The sound made from an engine's preset, its volume and LFOs kept.
    pub fn with_engine(&self, engine: &str) -> Data {
        let mut sound = Data::Map(vec![(Data::text(ENGINE), Data::text(engine))]);
        for name in ["volume", "lfos"] {
            if let Some(kept) = self.own(name) {
                put(&mut sound, name, kept);
            }
        }
        sound
    }

    fn with_part(&self, part: &str, value: Data) -> Data {
        let mut sound = self.written_or_empty();
        if ENVELOPE_PARTS.contains(&part) {
            let envelopes: Vec<Data> = ENVELOPE_PARTS
                .iter()
                .map(|each| if *each == part { value.clone() } else { self.part(each) })
                .collect();
            put(&mut sound, "envelopes", Data::List(envelopes));
        } else {
            put(&mut sound, part, value);
        }
        sound
    }

    /// The sound with a part swapped for a type: its engine's preset's part where that is the type, else the type alone.
    pub fn with_part_type(&self, part: &str, kind: &str) -> Data {
        let preset = self.preset_part(part);
        let value = if preset.get(TYPE).and_then(Data::as_str) == Some(kind) {
            preset
        } else {
            Data::Map(vec![(Data::text(TYPE), Data::text(kind))])
        };
        self.with_part(part, value)
    }

    /// The sound with one setting of a part changed.
    pub fn with_part_value(&self, part: &str, name: &str, value: Data) -> Data {
        let mut stored = self.part(part);
        put(&mut stored, name, value);
        self.with_part(part, stored)
    }

    /// The sound with one setting of an oscillator changed, the oscillators before it made, off, where it has none.
    pub fn with_oscillator(&self, number: usize, name: &str, value: Data) -> Data {
        let mut oscillators = self
            .part_value("oscillators", "oscillators")
            .as_list()
            .map(<[Data]>::to_vec)
            .unwrap_or_default();
        while oscillators.len() < number {
            oscillators.push(Data::Map(vec![(Data::text("waveform"), Data::text("off"))]));
        }
        put(&mut oscillators[number - 1], name, value);
        self.with_part_value("oscillators", "oscillators", Data::List(oscillators))
    }

    /// The sound with one setting of an item of one of its lists changed, the items before it made empty.
    pub fn with_item(&self, list: &str, number: usize, name: &str, value: Data) -> Data {
        let mut items = self.value(list).as_list().map(<[Data]>::to_vec).unwrap_or_default();
        while items.len() < number {
            items.push(Data::Map(Vec::new()));
        }
        put(&mut items[number - 1], name, value);
        self.with_value(list, Data::List(items))
    }

    /// The sound with one of the drum machine's knobs changed.
    pub fn with_knob(&self, place: usize, value: Data) -> Data {
        let mut knobs = self.part_value("oscillators", "knobs").as_list().map(<[Data]>::to_vec).unwrap_or_default();
        if place < knobs.len() {
            knobs[place] = value;
        }
        self.with_part_value("oscillators", "knobs", Data::List(knobs))
    }
}
