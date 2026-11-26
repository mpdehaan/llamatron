// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The migrations (the Python model/file/migrations/): each moves a set file's data from the layout before one breaking
//! change to the layout after it, run in order for a file saved before each, so that the reader only ever sees the layout
//! written now. Live's octave numbers (before 1.0.30), one song at the top (before 1.0.39), the long text under description
//! (before 1.0.155), and everything named kept by name rather than in lists (before 1.0.591). One more is told by its
//! shape alone, whatever version saved the file: the acid bass engine's oscillator Slide time, from before its slide became
//! the shared Glide time; an LFO's rate in tenths of a hertz, from before its Speed and Rate percent; and that engine's
//! name, fishline, from before it was named Oh3. And the vactrol's and the low-pass gate's layout (before 1.1.3): the
//! vactrol's Cell, Lit by and Strike became its Response, Trigger and Trigger time, and a low-pass gate on the Filter tab,
//! which was then the note's amp lit by Env 1, moves to the Amp tab, lit by Env 1 as before.

use crate::file::data::Data;
use crate::objects::naming;

const VERSION: &str = "version";
const NAME: &str = "name";

/// What reading a file moved: whether any migration ran, each name a migration changed as (kind, old, new), and the name a
/// one-song file's song takes.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Conversion {
    pub moved: bool,
    pub renames: Vec<(String, String, String)>,
    pub one_song_name: Option<String>,
}

/// A version's three numbers, or None for text that is not one.
pub fn version_numbers(text: &str) -> Option<(u64, u64, u64)> {
    let parts: Vec<&str> = text.split('.').collect();
    if parts.len() != 3 || !parts.iter().all(|part| !part.is_empty() && part.chars().all(|digit| digit.is_ascii_digit())) {
        return None;
    }
    Some((parts[0].parse().ok()?, parts[1].parse().ok()?, parts[2].parse().ok()?))
}

fn saved_version(data: &Data) -> Option<(u64, u64, u64)> {
    data.get(VERSION).and_then(Data::as_str).and_then(version_numbers)
}

/// One breaking change of the layout: the version that first wrote the new layout, how to tell the old layout by its shape
/// when a file records no version, and the change itself.
struct Migration {
    since: &'static str,
    is_before: fn(&Data) -> bool,
    change: fn(Data, &mut Conversion) -> Data,
}

/// The data moved to the layout written now, with what moving it did.
pub fn migrated(data: Data, one_song_name: Option<String>) -> (Data, Conversion) {
    let mut conversion = Conversion {
        one_song_name,
        ..Conversion::default()
    };
    let migrations = [
        Migration {
            since: "1.0.30",
            is_before: |_| false,
            change: live_octaves,
        },
        Migration {
            since: "1.0.39",
            is_before: one_song_is_before,
            change: one_song,
        },
        Migration {
            since: "1.0.155",
            is_before: |_| false,
            change: description_as_notes,
        },
        Migration {
            since: "1.0.591",
            is_before: lists_is_before,
            change: lists,
        },
    ];
    let mut data = data;
    for Migration { since, is_before, change } in migrations {
        if !matches!(data, Data::Map(_)) {
            continue;
        }
        let due = match saved_version(&data) {
            Some(saved) => version_numbers(since).is_some_and(|since| saved < since),
            None => is_before(&data),
        };
        if due {
            conversion.moved = true;
            data = change(data, &mut conversion);
        }
    }
    if matches!(data, Data::Map(_)) && has_acid_slide_time(&data) {
        conversion.moved = true;
        data = acid_slide_as_glide(data);
    }
    if matches!(data, Data::Map(_)) && has_lfo_tenths(&data) {
        conversion.moved = true;
        data = each_sound(data, lfo_speeds);
    }
    // Told by its version and its shape together, since a file from before 1.1.3 may already have been moved.
    let older_than_gates = saved_version(&data).is_none_or(|saved| version_numbers(GATE_LAYOUT_SINCE).is_some_and(|since| saved < since));
    if matches!(data, Data::Map(_)) && older_than_gates && gate_layout_is_before(&data) {
        conversion.moved = true;
        data = each_sound(data, gate_layout);
    }
    if matches!(data, Data::Map(_)) && has_engine(&data, OLD_ACID_ENGINE) {
        conversion.moved = true;
        data = each_sound(data, acid_engine_renamed);
    }
    (data, conversion)
}

const LFOS: &str = "lfos";
/// The older LFO rate, in tenths of a hertz, and what replaced it.
const OLD_RATE: &str = "rate";
const SPEED: &str = "speed";
const RATE_PERCENT: &str = "rate_percent";
const TENTHS: f64 = 10.0;

/// The acid bass engine's name before it was Oh3, and its name now.
const OLD_ACID_ENGINE: &str = "fishline";
const ACID_ENGINE: &str = "oh3";
const ENGINE: &str = "engine";

/// Whether any instrument's sound names an engine.
fn has_engine(data: &Data, engine: &str) -> bool {
    let Some(instruments) = data.get(INSTRUMENTS).and_then(Data::as_list) else {
        return false;
    };
    instruments
        .iter()
        .filter_map(|instrument| instrument.get(SOUND)?.get(ENGINE)?.as_str())
        .any(|named| named == engine)
}

/// A sound on the acid bass engine by its old name, fishline, given its name now, oh3.
fn acid_engine_renamed(sound: Data) -> Data {
    let pairs = pairs_of(&sound)
        .into_iter()
        .map(|(key, value)| {
            if key_is(&key, ENGINE) && value.as_str() == Some(OLD_ACID_ENGINE) {
                (key, Data::text(ACID_ENGINE))
            } else {
                (key, value)
            }
        })
        .collect();
    map(pairs)
}

/// The version that first wrote the vactrol's Response and Trigger and the Amp tab's low-pass gate.
const GATE_LAYOUT_SINCE: &str = "1.1.3";
const ENVELOPES: &str = "envelopes";
const FILTER: &str = "filter";
const AMP: &str = "amp";
const VACTROL: &str = "vactrol";
const LOW_PASS_GATE: &str = "low_pass_gate";
const AMP_GATE: &str = "low_pass_gate_amp";
const NONE: &str = "none";
/// The vactrol's older settings and what each became.
const CELL: &str = "cell";
const LIGHT: &str = "light";
const STRIKE_WIDTH: &str = "strike_width";
const RESPONSE: &str = "response";
const TRIGGER: &str = "trigger";
const TRIGGER_TIME: &str = "trigger_time";
/// The older gate's Input and Ping width, and what each became.
const INPUT: &str = "input";
const PING_WIDTH: &str = "ping_width";
const SIGNAL: &str = "signal";
const PING_TIME: &str = "ping_time";
/// Each older Cell, by name, and the Response that plays it, the cell's place on the gauge.
const CELL_RESPONSES: [(&str, i128); 4] = [("fast", 0), ("classic", 33), ("slow", 67), ("lazy", 100)];
const SLOW_RESPONSE: i128 = 67;
/// What lit the older gate, Env 1, and what struck an older vactrol, now called Trigger.
const ENV1: &str = "env1";
const OLD_STRIKE: &str = "strike";
/// The Response of the fastest cell, which follows Env 1 most nearly as the older gate did, unsmoothed.
const FASTEST_RESPONSE: i128 = 0;

/// Whether a file from before 1.1.3 holds the older layout: a vactrol with a Cell, Lit by or Strike, or a low-pass gate
/// on the Filter tab, where the older layout put every gate.
fn gate_layout_is_before(data: &Data) -> bool {
    let Some(instruments) = data.get(INSTRUMENTS).and_then(Data::as_list) else {
        return false;
    };
    instruments.iter().filter_map(|instrument| instrument.get(SOUND)).any(|sound| {
        let old_vactrol = sound
            .get(ENVELOPES)
            .and_then(Data::as_list)
            .into_iter()
            .flatten()
            .any(|envelope| envelope.get(CELL).is_some() || envelope.get(LIGHT).is_some() || envelope.get(STRIKE_WIDTH).is_some());
        let filter_gate = sound.get(FILTER).and_then(|filter| filter.get(TYPE)).and_then(Data::as_str) == Some(LOW_PASS_GATE);
        old_vactrol || filter_gate
    })
}

/// A sound in the layout of 1.1.3: its vactrol envelopes renamed, and a Filter tab low-pass gate moved to the Amp tab.
fn gate_layout(sound: Data) -> Data {
    let filter_gate = sound
        .get(FILTER)
        .filter(|filter| filter.get(TYPE).and_then(Data::as_str) == Some(LOW_PASS_GATE))
        .cloned();
    let mut pairs: Vec<(Data, Data)> = pairs_of(&sound)
        .into_iter()
        .filter(|(key, _)| !(filter_gate.is_some() && key_is(key, AMP)))
        .map(|(key, value)| {
            if key_is(&key, ENVELOPES) {
                let envelopes = value.as_list().map(<[_]>::to_vec).unwrap_or_default();
                return (key, Data::List(envelopes.iter().map(vactrol_renamed).collect()));
            }
            if key_is(&key, FILTER) && filter_gate.is_some() {
                return (key, map(vec![(Data::text(TYPE), Data::text(NONE))]));
            }
            (key, value)
        })
        .collect();
    if let Some(gate) = filter_gate {
        pairs.push((Data::text(AMP), gate_as_amp(&gate)));
    }
    map(pairs)
}

/// A vactrol envelope with its Cell as a Response, Lit by as Trigger and Strike as Trigger time; any other as it was.
fn vactrol_renamed(envelope: &Data) -> Data {
    if envelope.get(TYPE).and_then(Data::as_str) != Some(VACTROL) {
        return envelope.clone();
    }
    let pairs = pairs_of(envelope)
        .into_iter()
        .map(|(key, value)| {
            if key_is(&key, CELL) {
                let named = value.as_str().unwrap_or_default();
                let response = CELL_RESPONSES
                    .iter()
                    .find(|(cell, _)| *cell == named)
                    .map_or(SLOW_RESPONSE, |(_, response)| *response);
                return (Data::text(RESPONSE), Data::Whole(response));
            }
            if key_is(&key, LIGHT) {
                let trigger = if value.as_str() == Some(OLD_STRIKE) {
                    TRIGGER
                } else {
                    value.as_str().unwrap_or(TRIGGER)
                };
                return (Data::text(TRIGGER), Data::text(trigger));
            }
            if key_is(&key, STRIKE_WIDTH) {
                return (Data::text(TRIGGER_TIME), value);
            }
            (key, value)
        })
        .collect();
    map(pairs)
}

/// An older Filter tab low-pass gate as the Amp tab's: the same settings, Input as Signal and Ping width as Ping time, lit
/// by Env 1 through the fastest cell, as it was lit by Env 1 before.
fn gate_as_amp(gate: &Data) -> Data {
    let mut pairs: Vec<(Data, Data)> = pairs_of(gate)
        .into_iter()
        .map(|(key, value)| {
            if key_is(&key, TYPE) {
                (key, Data::text(AMP_GATE))
            } else if key_is(&key, INPUT) {
                (Data::text(SIGNAL), value)
            } else if key_is(&key, PING_WIDTH) {
                (Data::text(PING_TIME), value)
            } else {
                (key, value)
            }
        })
        .collect();
    pairs.push((Data::text(TRIGGER), Data::text(ENV1)));
    pairs.push((Data::text(RESPONSE), Data::Whole(FASTEST_RESPONSE)));
    map(pairs)
}

/// Whether any LFO still holds its rate in tenths of a hertz.
fn has_lfo_tenths(data: &Data) -> bool {
    let Some(instruments) = data.get(INSTRUMENTS).and_then(Data::as_list) else {
        return false;
    };
    instruments
        .iter()
        .filter_map(|instrument| instrument.get(SOUND)?.get(LFOS)?.as_list())
        .flatten()
        .any(|lfo| lfo.get(OLD_RATE).is_some())
}

/// Every instrument's sound changed by a change of sounds, the rest of the file as it was.
fn each_sound(data: Data, change: fn(Data) -> Data) -> Data {
    let pairs = pairs_of(&data)
        .into_iter()
        .map(|(key, value)| {
            if !key_is(&key, INSTRUMENTS) {
                return (key, value);
            }
            let instruments = value.as_list().map(<[_]>::to_vec).unwrap_or_default();
            let changed = instruments
                .into_iter()
                .map(|instrument| {
                    let pairs = pairs_of(&instrument)
                        .into_iter()
                        .map(|(key, value)| if key_is(&key, SOUND) { (key, change(value)) } else { (key, value) })
                        .collect();
                    map(pairs)
                })
                .collect();
            (key, Data::List(changed))
        })
        .collect();
    map(pairs)
}

/// A sound's LFOs each given the Speed and Rate percent nearest its rate in tenths of a hertz, so that it sounds as it did.
fn lfo_speeds(sound: Data) -> Data {
    let pairs = pairs_of(&sound)
        .into_iter()
        .map(|(key, value)| {
            if !key_is(&key, LFOS) {
                return (key, value);
            }
            let lfos = value.as_list().map(<[_]>::to_vec).unwrap_or_default();
            (key, Data::List(lfos.into_iter().map(lfo_speed).collect()))
        })
        .collect();
    map(pairs)
}

fn lfo_speed(lfo: Data) -> Data {
    let Some(tenths) = lfo.get(OLD_RATE).and_then(Data::as_whole).map(|tenths| tenths as f64) else {
        return lfo;
    };
    let (speed, percent) = crate::objects::lfo_speed::speed_of(tenths / TENTHS);
    let mut pairs: Vec<(Data, Data)> = pairs_of(&lfo).into_iter().filter(|(key, _)| !key_is(key, OLD_RATE)).collect();
    pairs.push((Data::text(SPEED), Data::text(speed)));
    pairs.push((Data::text(RATE_PERCENT), Data::Whole(percent as i128)));
    map(pairs)
}

const INSTRUMENTS: &str = "instruments";
const SOUND: &str = "sound";
const OSCILLATORS: &str = "oscillators";
const TYPE: &str = "type";
const ACID: &str = "acid";
const CIRCUIT: &str = "circuit";
const MODDED: &str = "modded";
const SLIDE_TIME: &str = "slide_time";
const GLIDE: &str = "glide";

/// Each built-in instrument's sound with an acid oscillator, by its place among the instruments.
fn acid_oscillators(data: &Data) -> Vec<&Data> {
    let Some(instruments) = data.get(INSTRUMENTS).and_then(Data::as_list) else {
        return Vec::new();
    };
    instruments
        .iter()
        .filter_map(|instrument| instrument.get(SOUND)?.get(OSCILLATORS))
        .filter(|oscillators| oscillators.get(TYPE).and_then(Data::as_str) == Some(ACID))
        .collect()
}

/// Whether an acid oscillator still holds its own Slide time or Circuit, from before the acid bass's slide was its Glide time.
fn has_acid_slide_time(data: &Data) -> bool {
    acid_oscillators(data)
        .iter()
        .any(|oscillators| oscillators.get(SLIDE_TIME).is_some() || oscillators.get(CIRCUIT).is_some())
}

/// The acid bass's oscillator Slide time moved to the sound's Glide time where its Circuit was Modded, Stock's fixed slide
/// being Glide time's default, and the oscillator's Slide time and Circuit taken away.
fn acid_slide_as_glide(data: Data) -> Data {
    let pairs = pairs_of(&data)
        .into_iter()
        .map(|(key, value)| {
            if !key_is(&key, INSTRUMENTS) {
                return (key, value);
            }
            let instruments = value.as_list().map(<[_]>::to_vec).unwrap_or_default();
            (key, Data::List(instruments.into_iter().map(instrument_glide).collect()))
        })
        .collect();
    map(pairs)
}

fn instrument_glide(instrument: Data) -> Data {
    let Some(sound) = instrument.get(SOUND) else { return instrument };
    let Some(oscillators) = sound.get(OSCILLATORS) else { return instrument };
    if oscillators.get(TYPE).and_then(Data::as_str) != Some(ACID) {
        return instrument;
    }
    let modded = oscillators.get(CIRCUIT).and_then(Data::as_str) == Some(MODDED);
    let slide = oscillators.get(SLIDE_TIME).cloned().filter(|_| modded);
    let kept: Vec<(Data, Data)> = pairs_of(oscillators)
        .into_iter()
        .filter(|(key, _)| !key_is(key, SLIDE_TIME) && !key_is(key, CIRCUIT))
        .collect();
    let mut sound_pairs: Vec<(Data, Data)> = pairs_of(sound)
        .into_iter()
        .map(|(key, value)| if key_is(&key, OSCILLATORS) { (key, map(kept.clone())) } else { (key, value) })
        .collect();
    if let Some(slide) = slide {
        sound_pairs.retain(|(key, _)| !key_is(key, GLIDE));
        sound_pairs.push((Data::text(GLIDE), slide));
    }
    let pairs = pairs_of(&instrument)
        .into_iter()
        .map(|(key, value)| if key_is(&key, SOUND) { (key, map(sound_pairs.clone())) } else { (key, value) })
        .collect();
    map(pairs)
}

fn map(pairs: Vec<(Data, Data)>) -> Data {
    Data::Map(pairs)
}

fn pairs_of(data: &Data) -> Vec<(Data, Data)> {
    data.as_map().map(<[_]>::to_vec).unwrap_or_default()
}

fn key_is(key: &Data, name: &str) -> bool {
    key.as_str() == Some(name)
}

/// Octaves numbered as Live labels them, two lower than from C0, moved up.
fn live_octaves(data: Data, _: &mut Conversion) -> Data {
    const OFFSET: i128 = 2;
    let mut moved = data;
    for name in ["default_octave", "default_drum_octave"] {
        if let Some(Data::Whole(octave)) = moved.get(name).cloned() {
            moved.set(name, Data::Whole(octave + OFFSET));
        }
    }
    if let Some(Data::Map(patterns)) = moved.get("patterns").cloned() {
        let shifted = patterns
            .into_iter()
            .map(|(name, mut pattern)| {
                if let Some(Data::List(octaves)) = pattern.get("octave").cloned() {
                    let raised = octaves
                        .into_iter()
                        .map(|octave| {
                            if let Data::Whole(whole) = octave {
                                Data::Whole(whole + OFFSET)
                            } else {
                                octave
                            }
                        })
                        .collect();
                    pattern.set("octave", Data::List(raised));
                }
                (name, pattern)
            })
            .collect();
        moved.set("patterns", map(shifted));
    }
    moved
}

const ONE_SONG_KEYS: [&str; 9] = [
    "tempo",
    "time_signature",
    "entry_size",
    "scale",
    "seed",
    "groove",
    "registers",
    "tracks",
    "scenes",
];

fn one_song_is_before(data: &Data) -> bool {
    data.get("songs").is_none() && ONE_SONG_KEYS.iter().any(|key| data.get(key).is_some())
}

/// One song at the top of the file becomes the file's one song, named after the file.
fn one_song(data: Data, conversion: &mut Conversion) -> Data {
    if data.get("songs").is_some() {
        return data;
    }
    let name = conversion.one_song_name.clone().unwrap_or_else(|| "song".to_string());
    let pairs = pairs_of(&data);
    let mut moved: Vec<(Data, Data)> = pairs
        .iter()
        .filter(|(key, _)| !ONE_SONG_KEYS.iter().any(|one| key_is(key, one)))
        .cloned()
        .collect();
    let song: Vec<(Data, Data)> = ONE_SONG_KEYS
        .iter()
        .filter_map(|key| data.get(key).map(|value| (Data::text(key), value.clone())))
        .collect();
    moved.push((Data::text("songs"), map(vec![(Data::Text(name), map(song))])));
    map(moved)
}

/// The long text under description moves to notes.
fn description_as_notes(data: Data, _: &mut Conversion) -> Data {
    if data.get("description").is_none() {
        return data;
    }
    let mut moved = data;
    let notes = moved.remove("description").unwrap_or(Data::Null);
    moved.set("notes", notes);
    moved
}

const LISTED_SECTIONS: [&str; 4] = ["scales", "patterns", "grooves", "instruments"];
const SECTIONS_OF_KINDS: [(&str, &str); 19] = [
    ("arp", "arps"),
    ("auto_ratchet", "auto_ratchets"),
    ("drift", "drifts"),
    ("progression", "progressions"),
    ("voice_leading", "voice_leadings"),
    ("strum", "strums"),
    ("euclid", "euclids"),
    ("density", "densities"),
    ("swell", "swells"),
    ("articulate", "articulates"),
    ("glide", "glides"),
    ("shorten", "shortens"),
    ("rush", "rushes"),
    ("drag", "drags"),
    ("hocket", "hockets"),
    ("guitarify", "guitarifies"),
    ("follow_chords", "follow_chords"),
    ("phrasing", "phrasings"),
    ("musician", "musicians"),
];

fn kind_of_section(section: &str) -> Option<&'static str> {
    SECTIONS_OF_KINDS.iter().find(|(_, found)| *found == section).map(|(kind, _)| *kind)
}

fn lists_is_before(data: &Data) -> bool {
    let keyed = LISTED_SECTIONS
        .iter()
        .chain(["songs"].iter())
        .any(|section| matches!(data.get(section), Some(Data::Map(_))));
    keyed
        || SECTIONS_OF_KINDS
            .iter()
            .map(|(_, section)| *section)
            .chain(["chains"])
            .any(|section| data.get(section).is_some())
}

/// A mapping of things by name as a list, each item its settings with its name first; anything else left for the reader.
fn as_items(mapping: &Data, key: &str) -> Data {
    let Some(pairs) = mapping.as_map() else { return mapping.clone() };
    if !pairs.iter().all(|(_, settings)| matches!(settings, Data::Map(_))) {
        return mapping.clone();
    }
    Data::List(
        pairs
            .iter()
            .map(|(name, settings)| {
                let mut item = vec![(Data::text(key), name.clone())];
                item.extend(pairs_of(settings));
                map(item)
            })
            .collect(),
    )
}

fn with_key_replaced(settings: &Data, old: &str, new: &str, value: Data) -> Data {
    map(pairs_of(settings)
        .into_iter()
        .map(|(key, held)| if key_is(&key, old) { (Data::text(new), value.clone()) } else { (key, held) })
        .collect())
}

fn name_references(names: &Data) -> Data {
    match names {
        Data::List(items) => Data::List(items.iter().map(|name| map(vec![(Data::text(NAME), name.clone())])).collect()),
        other => other.clone(),
    }
}

/// Everything named becomes an item of a list; every generator and chain becomes one list, each item saying its kind.
fn lists(data: Data, conversion: &mut Conversion) -> Data {
    let mut listed: Vec<(Data, Data)> = Vec::new();
    let mut generators: Vec<Data> = Vec::new();
    let mut taken: Vec<String> = Vec::new();
    let mut renamed: Vec<((String, String), String)> = Vec::new();
    for (key, value) in pairs_of(&data) {
        let section = key.as_str().unwrap_or("");
        if let (Some(kind), Data::Map(items)) = (kind_of_section(section), &value) {
            for (name, settings) in items {
                let old = name.python_str();
                let new = free_name(&old, kind, &mut taken, conversion);
                renamed.push(((kind.to_string(), old), new.clone()));
                let mut item = vec![(Data::text(NAME), Data::Text(new)), (Data::text("kind"), Data::text(kind))];
                if let Data::Map(own) = settings {
                    item.extend(own.iter().cloned());
                }
                generators.push(map(item));
            }
        } else if LISTED_SECTIONS.contains(&section) {
            listed.push((key.clone(), as_items(&value, NAME)));
        } else {
            listed.push((key.clone(), value.clone()));
        }
    }
    let mut renamed_chains: Vec<(String, String)> = Vec::new();
    if let Some(place) = listed.iter().position(|(key, _)| key_is(key, "chains")) {
        let (_, chains) = listed.remove(place);
        for (name, chain) in chains.as_map().unwrap_or(&[]) {
            let old = name.python_str();
            let new = free_name(&old, "chain", &mut taken, conversion);
            renamed_chains.push((old, new.clone()));
            generators.push(chain_item(&new, chain, &renamed));
        }
    }
    if !generators.is_empty() {
        listed.push((Data::text("generators"), Data::List(generators)));
    }
    if let Some(place) = listed.iter().position(|(key, value)| key_is(key, "songs") && matches!(value, Data::Map(_))) {
        let songs = listed[place].1.clone();
        let items = songs
            .as_map()
            .unwrap_or(&[])
            .iter()
            .map(|(name, song)| {
                let mut item = vec![(Data::text(NAME), name.clone())];
                item.extend(pairs_of(&song_listed(song, &renamed_chains)));
                map(item)
            })
            .collect();
        listed[place].1 = Data::List(items);
    }
    map(listed)
}

fn free_name(name: &str, kind: &str, taken: &mut Vec<String>, conversion: &mut Conversion) -> String {
    let new = naming::unique_name(name, taken);
    taken.push(new.clone());
    if new != name {
        conversion.renames.push((kind.to_string(), name.to_string(), new.clone()));
    }
    new
}

fn step_of(step: &Data) -> Option<(String, String)> {
    match step.as_map() {
        Some([(kind, name)]) => Some((kind.python_str(), name.python_str())),
        _ => None,
    }
}

fn chain_item(name: &str, chain: &Data, renamed: &[((String, String), String)]) -> Data {
    let steps = match chain {
        Data::Map(_) => chain.get("steps").cloned().unwrap_or(Data::Null),
        other => other.clone(),
    };
    let steps = match steps {
        Data::List(items) => Data::List(
            items
                .iter()
                .map(|step| match step_of(step) {
                    Some(key) => {
                        let found = renamed.iter().find(|(known, _)| *known == key).map(|(_, new)| new.clone()).unwrap_or(key.1);
                        Data::Text(found)
                    }
                    None => step.clone(),
                })
                .collect(),
        ),
        other => other,
    };
    let mut item = vec![
        (Data::text(NAME), Data::text(name)),
        (Data::text("kind"), Data::text("chain")),
        (Data::text("generators"), name_references(&steps)),
    ];
    if let Data::Map(own) = chain {
        for (key, value) in own {
            if !key_is(key, "steps") {
                match item.iter_mut().find(|(found, _)| found == key) {
                    Some(pair) => pair.1 = value.clone(),
                    None => item.push((key.clone(), value.clone())),
                }
            }
        }
    }
    map(item)
}

fn song_listed(song: &Data, renamed: &[(String, String)]) -> Data {
    if !matches!(song, Data::Map(_)) {
        return song.clone();
    }
    let mut listed = song.clone();
    if let Some(Data::Map(tracks)) = song.get("tracks") {
        if tracks.iter().all(|(_, track)| matches!(track, Data::Map(_))) {
            let items = tracks
                .iter()
                .map(|(name, track)| {
                    let mut item = vec![(Data::text(NAME), name.clone())];
                    item.extend(pairs_of(&references_listed(track, renamed)));
                    map(item)
                })
                .collect();
            listed.set("tracks", Data::List(items));
        }
    }
    if let Some(Data::List(scenes)) = song.get("scenes") {
        listed.set("scenes", Data::List(scenes.iter().map(|scene| scene_listed(scene, renamed)).collect()));
    }
    listed
}

fn scene_listed(scene: &Data, renamed: &[(String, String)]) -> Data {
    if !matches!(scene, Data::Map(_)) {
        return scene.clone();
    }
    let listed = references_listed(scene, renamed);
    match listed.get("tracks") {
        Some(Data::Map(clips)) if clips.iter().all(|(_, clip)| matches!(clip, Data::Map(_))) => {
            let items = clips
                .iter()
                .map(|(track, clip)| {
                    let mut item = vec![(Data::text("track"), track.clone())];
                    item.extend(pairs_of(&references_listed(clip, renamed)));
                    map(item)
                })
                .collect();
            with_key_replaced(&listed, "tracks", "clips", Data::List(items))
        }
        _ => listed,
    }
}

/// A clip's, a scene's or a track's settings with the chains it ran written as the generators it runs.
fn references_listed(settings: &Data, renamed: &[(String, String)]) -> Data {
    let mut listed = settings.clone();
    if let (Some(chain), None) = (listed.get("chain").cloned(), listed.get("chains")) {
        listed = with_key_replaced(&listed, "chain", "chains", Data::List(vec![chain]));
    }
    if let Some(names) = listed.get("chains").cloned() {
        let names = match names {
            Data::List(items) => Data::List(
                items
                    .into_iter()
                    .map(|name| {
                        let text = name.python_str();
                        match renamed.iter().find(|(old, _)| *old == text) {
                            Some((_, new)) if matches!(name, Data::Text(_)) => Data::text(new),
                            _ => name,
                        }
                    })
                    .collect(),
            ),
            other => other,
        };
        listed = with_key_replaced(&listed, "chains", "generators", name_references(&names));
    }
    listed
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::file::data::load;

    /// A Modded acid bass's oscillator Slide time becomes its sound's Glide time, a Stock one's is dropped for the
    /// default, and both oscillators lose their Slide time and Circuit, whatever version saved the file.
    #[test]
    fn an_acid_slide_time_becomes_its_glide_time() {
        let file = "version: 1.1.1\ninstruments:\n  - { name: modded, kind: built_in, sound: { engine: fishline, oscillators: { type: acid, circuit: modded, slide_time: 200 } } }\n  - { name: stock, kind: built_in, sound: { engine: fishline, glide: 90, oscillators: { type: acid, circuit: stock, slide_time: 300 } } }\n";
        let (data, conversion) = migrated(load(file).expect("the file reads"), None);
        assert!(conversion.moved);
        let instruments = data.get(INSTRUMENTS).and_then(Data::as_list).expect("instruments");
        let sound = |place: usize| instruments[place].get(SOUND).expect("a sound").clone();
        assert_eq!(sound(0).get(GLIDE).cloned(), Some(Data::Whole(200)));
        assert_eq!(sound(1).get(GLIDE).cloned(), Some(Data::Whole(90)), "a Stock sound keeps its own Glide time");
        for place in 0..2 {
            let oscillators = sound(place).get(OSCILLATORS).expect("oscillators").clone();
            assert!(oscillators.get(SLIDE_TIME).is_none() && oscillators.get(CIRCUIT).is_none());
        }
        let (_, untouched) = migrated(data, None);
        assert!(!untouched.moved, "a file already moved is left alone");
    }

    /// An LFO's rate in tenths of a hertz becomes the Speed and Rate percent giving it again, 5.0 Hz Medium at 74%.
    #[test]
    fn an_lfo_rate_in_tenths_becomes_its_speed_and_percent() {
        let file = "version: 1.1.1\ninstruments:\n  - { name: lead, kind: built_in, sound: { engine: sid, lfos: [{ on: true, rate: 50 }, ~] } }\n";
        let (data, conversion) = migrated(load(file).expect("the file reads"), None);
        assert!(conversion.moved);
        let instruments = data.get(INSTRUMENTS).and_then(Data::as_list).expect("instruments");
        let lfos = instruments[0]
            .get(SOUND)
            .and_then(|sound| sound.get(LFOS))
            .and_then(Data::as_list)
            .expect("lfos")
            .to_vec();
        assert_eq!(lfos[0].get(SPEED).and_then(Data::as_str), Some("medium"));
        assert_eq!(lfos[0].get(RATE_PERCENT).cloned(), Some(Data::Whole(74)));
        assert!(lfos[0].get(OLD_RATE).is_none());
        assert!(lfos[1].is_null(), "an LFO left out stays so");
    }

    /// An older vactrol's Cell, Lit by and Strike become its Response, Trigger and Trigger time, and an older Filter tab
    /// low-pass gate, then the note's amp lit by Env 1, moves to the Amp tab lit by Env 1; a set of 1.1.3 is left alone.
    #[test]
    fn the_vactrol_and_the_gate_move_to_their_new_layout() {
        let older = "version: 1.1.2\ninstruments:\n  - { name: pluck, kind: built_in, sound: { engine: basic, envelopes: [{ type: vactrol, cell: lazy, light: gate, strike_width: 30 }], filter: { type: low_pass_gate, gate_mode: lowpass, input: ping, ping_width: 15 } } }\n";
        let (data, conversion) = migrated(load(older).expect("the file reads"), None);
        assert!(conversion.moved);
        let sound = data.get(INSTRUMENTS).and_then(Data::as_list).expect("instruments")[0]
            .get(SOUND)
            .expect("a sound")
            .clone();
        let text = |part: &Data, key: &str| part.get(key).and_then(Data::as_str).map(str::to_string);
        let whole = |part: &Data, key: &str| part.get(key).and_then(Data::as_whole);
        let vactrol = sound.get(ENVELOPES).and_then(Data::as_list).expect("envelopes")[0].clone();
        let lazy = 100;
        let strike = 30;
        assert_eq!(whole(&vactrol, RESPONSE), Some(lazy));
        assert_eq!(text(&vactrol, TRIGGER).as_deref(), Some("gate"));
        assert_eq!(whole(&vactrol, TRIGGER_TIME), Some(strike));
        assert!(vactrol.get(CELL).is_none() && vactrol.get(LIGHT).is_none());
        let filter = sound.get(FILTER).expect("a filter");
        assert_eq!(text(filter, TYPE).as_deref(), Some(NONE));
        let amp = sound.get(AMP).expect("an amp");
        let ping = 15;
        assert_eq!(text(amp, TYPE).as_deref(), Some(AMP_GATE));
        assert_eq!(text(amp, "gate_mode").as_deref(), Some("lowpass"));
        assert_eq!(text(amp, SIGNAL).as_deref(), Some("ping"));
        assert_eq!(whole(amp, PING_TIME), Some(ping));
        assert_eq!(text(amp, TRIGGER).as_deref(), Some(ENV1));
        let newer =
            "version: 1.1.3\ninstruments:\n  - { name: pluck, kind: built_in, sound: { engine: basic, filter: { type: low_pass_gate, trigger: env2 } } }\n";
        let (data, conversion) = migrated(load(newer).expect("the file reads"), None);
        assert!(!conversion.moved);
        let sound = data.get(INSTRUMENTS).and_then(Data::as_list).expect("instruments")[0]
            .get(SOUND)
            .expect("a sound")
            .clone();
        assert_eq!(text(sound.get(FILTER).expect("a filter"), TYPE).as_deref(), Some(LOW_PASS_GATE));
    }

    /// A sound on the acid bass engine by its old name, fishline, is renamed oh3; other engines are left alone.
    #[test]
    fn the_fishline_engine_is_renamed_oh3() {
        let file = "version: 1.1.1\ninstruments:\n  - { name: acid, kind: built_in, sound: { engine: fishline } }\n  - { name: chip, kind: built_in, sound: { engine: sid } }\n";
        let (data, conversion) = migrated(load(file).expect("the file reads"), None);
        assert!(conversion.moved);
        let instruments = data.get(INSTRUMENTS).and_then(Data::as_list).expect("instruments");
        let engine = |place: usize| {
            instruments[place]
                .get(SOUND)
                .and_then(|sound| sound.get(ENGINE))
                .and_then(Data::as_str)
                .map(str::to_string)
        };
        assert_eq!(engine(0).as_deref(), Some(ACID_ENGINE));
        assert_eq!(engine(1).as_deref(), Some("sid"));
    }
}
