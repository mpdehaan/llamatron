// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What the tracker's tests share: a built-in sound and its instrument built as data, never written as text, and the
//! spec the tracker writes for it.

// Each test file uses what it needs of these.
#![allow(dead_code)]

use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Instrument;
use llamatron_names::file_format::{FileLayout, InstrumentKind, InstrumentRole, InstrumentSetting};
use llamatron_names::scenario;
use llamatron_tracker::instrument_sound::Sound;
use llamatron_tracker::sound_spec::synth_spec;

/// Where the drums sound from, which a spec needs and these tests do not.
pub const DRUMS_FROM: i64 = 36;

/// A map of settings, built as data.
pub fn settings(pairs: &[(&str, Data)]) -> Data {
    Data::Map(pairs.iter().map(|(key, value)| (Data::text(key), value.clone())).collect())
}

/// A list of settings maps, built as data.
pub fn list(items: Vec<Data>) -> Data {
    Data::List(items)
}

/// A built-in instrument, made up for a test, playing a sound.
pub fn built_in(sound: Data) -> Instrument {
    let instrument = settings(&[
        (FileLayout::NAME, Data::text(scenario::TRIED)),
        (InstrumentSetting::KIND, Data::text(InstrumentKind::BUILT_IN)),
        (InstrumentSetting::ROLE, Data::text(InstrumentRole::NORMAL)),
        (InstrumentSetting::SOUND, sound),
    ]);
    Instrument::from_data(&instrument).expect("the scenario's instrument is valid")
}

/// The spec the tracker writes for a built-in instrument playing a sound.
pub fn spec_of(sound: Data) -> Data {
    synth_spec(&Sound::of(&built_in(sound)), DRUMS_FROM)
}
