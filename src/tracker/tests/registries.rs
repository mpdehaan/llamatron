// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The tracker's choices and the backend's registries agree both ways: every type, effect, shape, source and
//! destination the Instrument page offers is written into a sound's spec as a name its registry holds, so that nothing
//! the page offers falls through to something else, and every registered name is one the page can write, so that
//! nothing registered is unreachable. Each list is walked, never typed out here.

use llamatron_backend::effects;
use llamatron_backend::envelopes;
use llamatron_backend::filters;
use llamatron_backend::instrument::amp;
use llamatron_backend::modulation::{lfos, matrix};
use llamatron_backend::oscillators;
use llamatron_model::file::data::{load, Data};
use llamatron_model::objects::setlist::Instrument;
use llamatron_model::schema::generated::file_format::{EFFECTS, LFO_PLUS_SHAPES, LFO_SHAPES, MATRIX_DESTINATIONS, MATRIX_SOURCES};
use llamatron_tracker::generated::sounds::PART_TYPES;
use llamatron_tracker::instrument_sound::Sound;
use llamatron_tracker::sound_spec::synth_spec;
use std::collections::BTreeSet;

/// Where the drums sound from, which a spec needs and these tests do not.
const DRUMS_FROM: i64 = 36;
/// A choice that leaves a slot empty, written as its own name.
const NOTHING: &str = "none";

/// The spec the tracker writes for a sound written as a set file writes one.
fn spec_of(sound: &str) -> Data {
    let text = format!("{{ name: tried, kind: built_in, role: normal, sound: {sound} }}");
    let data = load(&text).expect("the scenario's sound is YAML");
    let instrument = Instrument::from_data(&data).expect("the scenario's instrument is valid");
    synth_spec(&Sound::of(&instrument), DRUMS_FROM)
}

/// A spec's part's type, as the backend reads it.
fn written_type(spec: &Data, part: &str) -> String {
    let found = if let Some(slot) = part.strip_prefix("env") {
        let place: usize = slot.parse::<usize>().expect("an envelope slot's number") - 1;
        spec.get("envelopes")
            .and_then(Data::as_list)
            .and_then(|envelopes| envelopes.get(place))
            .and_then(|envelope| envelope.get("type"))
            .cloned()
    } else {
        spec.get(part).and_then(|written| written.get("type")).cloned()
    };
    found.and_then(|name| name.as_str().map(str::to_string)).unwrap_or_else(|| NOTHING.to_string())
}

/// The names a backend registry holds for a part of a voice.
fn registered(part: &str) -> BTreeSet<&'static str> {
    match part {
        "oscillators" => oscillators::REGISTRY.iter().map(|entry| entry.name).collect(),
        "filter" => filters::REGISTRY.iter().map(|entry| entry.name).collect(),
        "amp" => amp::TYPES.iter().map(|choice| choice.name).collect(),
        envelope if envelope.starts_with("env") => envelopes::REGISTRY.iter().map(|entry| entry.name).collect(),
        other => panic!("the part {other} has no registry these tests know of"),
    }
}

/// The sound of a part set to a type, written as a set file writes one.
fn sound_with(part: &str, kind: &str) -> String {
    if let Some(slot) = part.strip_prefix("env") {
        let place: usize = slot.parse::<usize>().expect("an envelope slot's number") - 1;
        let slots: Vec<String> = (0..3)
            .map(|number| {
                if number == place {
                    format!("{{ type: {kind} }}")
                } else {
                    "{ type: adsr }".to_string()
                }
            })
            .collect();
        return format!("{{ engine: basic, envelopes: [{}] }}", slots.join(", "));
    }
    format!("{{ engine: basic, {part}: {{ type: {kind} }} }}")
}

/// Which registry a part's types are held in: the three envelope slots share one.
fn registry_of(part: &str) -> &str {
    if part.starts_with("env") {
        "envelopes"
    } else {
        part
    }
}

/// Every type the page offers for each part is written as a type that part's registry holds, and every registered
/// type is written for some choice the page offers in a part that registry serves.
#[test]
fn every_part_type_offered_is_registered_and_every_registered_type_is_offered() {
    let mut written: std::collections::BTreeMap<&str, BTreeSet<String>> = std::collections::BTreeMap::new();
    for (part, kinds, _) in PART_TYPES {
        let registry = registered(part);
        for kind in kinds.iter() {
            let name = written_type(&spec_of(&sound_with(part, kind)), part);
            assert!(
                registry.contains(name.as_str()),
                "{part} offers {kind}, written as {name}, which no registry holds"
            );
            written.entry(registry_of(part)).or_default().insert(name);
        }
    }
    for (part, _, _) in PART_TYPES {
        let written = &written[registry_of(part)];
        for name in registered(part) {
            assert!(written.contains(name), "{part}'s registry holds {name}, which the page never writes");
        }
    }
}

/// Every effect the file names is registered, and every registered effect is one the file names.
#[test]
fn every_effect_offered_is_registered_and_every_registered_effect_is_offered() {
    let offered: BTreeSet<&str> = EFFECTS.iter().copied().filter(|name| *name != NOTHING).collect();
    let registered: BTreeSet<&str> = effects::REGISTRY.iter().map(|entry| entry.name).collect();
    assert_eq!(offered, registered);
    for name in &offered {
        let spec = spec_of(&format!("{{ engine: basic, effects: [{{ effect: {name} }}] }}"));
        let written = spec
            .get("effects")
            .and_then(Data::as_list)
            .and_then(|blocks| blocks.first())
            .and_then(|block| block.get("effect"))
            .and_then(Data::as_str);
        assert_eq!(written, Some(*name), "the effect {name} is written as itself");
    }
}

/// Every LFO shape the file names is registered, and every registered shape is one the file names.
#[test]
fn every_lfo_shape_offered_is_registered_and_every_registered_shape_is_offered() {
    let offered: BTreeSet<&str> = LFO_SHAPES.iter().chain(LFO_PLUS_SHAPES.iter()).copied().collect();
    let registered: BTreeSet<&str> = lfos::SHAPES.iter().map(|choice| choice.name).collect();
    assert_eq!(offered, registered);
}

/// Every Mod Matrix source and destination the file names is registered, and every registered one is one the file
/// names.
#[test]
fn every_matrix_source_and_destination_offered_is_registered_and_every_registered_one_is_offered() {
    let sources: BTreeSet<&str> = MATRIX_SOURCES.iter().copied().filter(|name| *name != NOTHING).collect();
    let registered_sources: BTreeSet<&str> = matrix::SOURCES.iter().map(|choice| choice.name).collect();
    assert_eq!(sources, registered_sources);
    let destinations: BTreeSet<&str> = MATRIX_DESTINATIONS.iter().copied().filter(|name| *name != NOTHING).collect();
    let registered_destinations: BTreeSet<&str> = matrix::DESTINATIONS
        .iter()
        .map(|choice| choice.name)
        .chain(matrix::RATE_DESTINATIONS.iter().copied())
        .collect();
    assert_eq!(destinations, registered_destinations);
}
