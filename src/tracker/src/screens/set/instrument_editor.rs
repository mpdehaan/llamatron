// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An instrument's page (the Python screens/set/instrument_editor.py, pages/instrument.py, sound_tabs.py, part_fields.py,
//! lfo_blocks.py and effect_blocks.py): its name, how loud it plays, its role, kind and engine, then its MIDI tab and its
//! built-in sound's tabs, and its buttons.

use crate::app::App;
use crate::forms::nodes::{Edit, Field, Kind as FieldKind};
use crate::forms::tab_box::{Beside, Tab, TabBox, TabColumn};
use crate::generated::sounds::{
    SettingKind, ENGINES_OF_ROLE, LFO_DEFAULTS, PART_TYPES, SETTING_KINDS, SID_ATTACK_MS, SLOT_DEFAULTS, TYPE_SETTINGS, TYPE_SETTING_KINDS,
};
use crate::instrument_sound::{Sound, ENVELOPE_PARTS};
use crate::keybindings::{InstrumentEditor as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::field_page::{Form, Node};
use crate::settings::named_in;
use crate::sound_spec::DELAY_DIVISIONS;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::lfo_speed;
use llamatron_model::objects::setlist::{Instrument, Item};
use llamatron_model::schema::generated::defaults::DEFAULT_PAN;
use llamatron_model::schema::generated::file_format::{
    InstrumentSetting, Section, BIPOLAR_SOURCES, CURVES, EFFECTS, FILTER_SHARINGS, FLUIDSYNTH_DEVICE, LFO_PLUS_SHAPES, LFO_RESTARTS, LFO_SHAPES, LFO_TYPES,
    MATRIX_DESTINATIONS, MATRIX_POLARITIES, MATRIX_SOURCES, OSCILLATOR_WAVEFORMS,
};
use llamatron_model::schema::generated::limits::{
    EFFECT_BLOCKS, KNOB_COUNT, LFO_COUNT, MATRIX_SLOTS, MAX_BITS, MAX_DETUNE_CENTS, MAX_GLIDE_MS, MAX_GM_SOUND, MAX_INSTRUMENT_LATENCY, MAX_KEYSWITCH_LEAD,
    MAX_KNOB, MAX_MATRIX_AMOUNT, MAX_PAN, MAX_SID_RATE, MAX_TAP_FEEDBACK, MAX_TAP_LOW_CUT, MAX_TAP_MS, MAX_TAP_TONE, MAX_VOICES, MAX_VOLUME_PERCENT, MIN_BITS,
    MIN_GM_SOUND, MIN_INSTRUMENT_LATENCY, MIN_KEYSWITCH_LEAD, MIN_PAN, MIN_TAP_LOW_CUT, MIN_TAP_TONE, MOST_BAX_DECIBELS,
};
use llamatron_strings::{labels, legends, marks, messages, named};

const NAME: usize = 0;
const GM_CELLS: usize = 12;
const BLOCK_CELLS: usize = 8;
/// A Mod Matrix route's Polarity that moves its destination from nothing to its amount.
const UNIPOLAR: &str = "unipolar";
/// The longest an LFO+ takes to fade in, in milliseconds.
const LONGEST_FADE_IN_MS: i64 = 10_000;
const MAX_PERCENT: i64 = 100;
const DEFAULT_VELOCITY: i64 = 127;
const DEFAULT_ACCENT: i64 = 0;
const UNCHANGED: i64 = 100;
const TENTHS: i64 = 10;
const CRUSH_RATES: [i64; 11] = [0, 32000, 22050, 16000, 11025, 8000, 6000, 4000, 3000, 2000, 1000];
const MIDI: &str = "midi";
const BUILT_IN: &str = "built_in";
/// The engines the Engine tab offers, in order: off, an outside MIDI device, FluidSynth, the built-in synths.
const OFF: &str = "off";
const FLUIDSYNTH: &str = "fluidsynth";
const LLAMASYNTH: &str = "llamasynth";
const ENGINES: &[&str] = &[OFF, MIDI, FLUIDSYNTH, LLAMASYNTH];
/// The instrument's two roles.
const NORMAL: &str = "normal";
const PERCUSSION: &str = "percussion";
const NONE_EFFECT: &str = "none";
const BITCRUSH: &str = "bitcrush";
const BAX: &str = "bax";
const MULTITAP: &str = "multitap";
/// The cells of a MultiTap tap's level gauge, narrow to share its row with the tap's time.
const TAP_LEVEL_CELLS: usize = 3;
/// How wide a tap's time is shown, its widest choice's width, a division such as 1/16t or a time such as 4000 ms, so that
/// the taps' levels line up.
const DIVISION_WIDTH: usize = 5;
const TAP_MS_WIDTH: usize = 7;
const ARPEGGIO: &str = "arpeggio";
/// A Mod Matrix source that is a MIDI CC is `cc` and its number; the picker's entry that asks for one; the CC it asks
/// with first, the filter's cutoff by custom, and the highest CC.
const CONTROL_PREFIX: &str = "cc";
const MIDI_CC_CHOICE: &str = "midi_cc";
const DEFAULT_CC: i64 = 74;
const HIGHEST_CC: i64 = 127;

/// The CC number a Mod Matrix source names, such as 74 for `cc74`, or None for any other source.
fn control_number(source: &str) -> Option<i64> {
    source
        .strip_prefix(CONTROL_PREFIX)?
        .parse::<i64>()
        .ok()
        .filter(|number| (0..=HIGHEST_CC).contains(number))
}
/// Asheville: its oscillators' settings, column by column; its panel's own; its Model's Continuous, which shows a Shape
/// in each oscillator's Wave's place; and the endings that tell the two apart.
/// Basic's oscillators: one, a plain wave; the engines of several oscillators are the ones built for it.
const BASIC_OSCILLATORS: usize = 1;
/// Fine tuning's reach either way, in tenths of a cent: ten cents.
const MOST_FINE_TENTHS: i64 = 100;
const ASHEVILLE: &str = "asheville";
const ASHEVILLE_OSCILLATORS: [[&str; 10]; 3] = [
    [
        "osc1_speed",
        "osc1_rate",
        "osc1_range",
        "osc1_wave",
        "osc1_shape",
        "osc1_tune",
        "osc1_fine",
        "osc1_mix",
        "osc1_sub",
        "osc1_on",
    ],
    [
        "osc2_speed",
        "osc2_rate",
        "osc2_range",
        "osc2_wave",
        "osc2_shape",
        "osc2_tune",
        "osc2_fine",
        "osc2_mix",
        "osc2_sub",
        "osc2_on",
    ],
    [
        "osc3_speed",
        "osc3_rate",
        "osc3_range",
        "osc3_wave",
        "osc3_shape",
        "osc3_tune",
        "osc3_fine",
        "osc3_mix",
        "osc3_sub",
        "osc3_on",
    ],
];
/// An oscillator's Speed that plays the note at its Range; at any other it runs at its Rate, as an LFO.
const AUDIO_SPEED: &str = "audio";
const RATE_SUFFIX: &str = "_rate";
const RANGE_SUFFIX: &str = "_range";
const ASHEVILLE_PANEL: [&str; 8] = ["model", "character", "noise_level", "ring", "tune_snap", "drift", "feedback_on", "feedback"];
const CONTINUOUS: &str = "continuous";
const ASHEVILLE_SOURCES: [&str; 3] = ["osc1", "osc2", "osc3"];
/// An engine of one oscillator's output as a source, which Asheville names by each oscillator instead.
const ONE_OSCILLATOR_SOURCE: &str = "osc";
/// The sources a route may read but never scale another by.
const SOURCES_ONLY: [&str; 1] = ["random"];
const WAVE_SUFFIX: &str = "_wave";
const SHAPE_SUFFIX: &str = "_shape";
const CIRCUIT: &str = "circuit";
const MODDED: &str = "modded";

pub struct InstrumentEditor {
    pub name: String,
}

/// The settings of MultiTap's four taps, by tap: whether it sounds, its time as a division of the beat, its time in
/// milliseconds, its level.
const TAP_SETTINGS: [(&str, &str, &str, &str); 4] = [
    ("tap1_on", "tap1_division", "tap1_ms", "tap1_level"),
    ("tap2_on", "tap2_division", "tap2_ms", "tap2_level"),
    ("tap3_on", "tap3_division", "tap3_ms", "tap3_level"),
    ("tap4_on", "tap4_division", "tap4_ms", "tap4_level"),
];
/// The taps MultiTap may feed back from, and how it reaches a changed time.
const FEEDBACK_FROM_TAPS: [&str; 4] = ["1", "2", "3", "4"];
const TIME_CHANGES: [&str; 2] = ["fade", "glide"];
/// MultiTap's modes: a clean digital delay, or a bucket-brigade device's darker echoes on one clock.
const DELAY_MODES: [&str; 2] = ["digital", "analog"];
const ANALOG: &str = "analog";
/// The analog device's own settings, each a gauge of percent, with its label.
const ANALOG_SETTINGS: [(&str, &str); 5] = [
    ("darkness", labels::MSG_EFFECT_DARKNESS_LABEL),
    ("noise", labels::MSG_EFFECT_NOISE_LABEL),
    ("drive", labels::MSG_EFFECT_DRIVE_LABEL),
    ("wow", labels::MSG_EFFECT_WOW_LABEL),
    ("flutter", labels::MSG_EFFECT_FLUTTER_LABEL),
];

/// Where MultiTap starts when its Mode becomes Analog: a warm dotted echo, the second tap off, fed back from the third,
/// darker and thinner than the digital delay.
fn analog_starting_point() -> Vec<(&'static str, Data)> {
    vec![
        ("mode", Data::text(ANALOG)),
        ("tap1_division", Data::text("1/8d")),
        ("tap1_level", Data::Whole(80)),
        ("tap2_division", Data::text("1/4")),
        ("tap2_level", Data::Whole(0)),
        ("tap2_on", Data::Bool(false)),
        ("tap3_division", Data::text("1/4d")),
        ("tap3_level", Data::Whole(55)),
        ("tap4_division", Data::text("1/2")),
        ("tap4_level", Data::Whole(35)),
        ("feedback_from", Data::text("3")),
        ("feedback", Data::Whole(40)),
        ("tone", Data::Whole(3500)),
        ("low_cut", Data::Whole(120)),
    ]
}

/// Whether a switch that is on unless set off is on.
fn flag_or_on(value: &Data) -> bool {
    !matches!(value, Data::Bool(false))
}

/// Whether the instrument slides into glided steps: on unless set off.
fn glides_on(sound: &Sound) -> bool {
    !matches!(sound.value("glides"), Data::Bool(false))
}

fn whole(value: &Data) -> i64 {
    value.as_whole().map_or(0, |whole| whole as i64)
}

fn text(value: &Data) -> String {
    value.as_str().unwrap_or("").to_string()
}

fn flag(value: &Data) -> bool {
    matches!(value, Data::Bool(true))
}

/// A gauge's text: a bar of cells as full as the number is between its ends, then the number in its unit.
fn gauge_text(number: i64, lowest: i64, highest: i64, cells: usize, unit: &str, logarithmic: bool, divisor: i64) -> String {
    let share = if logarithmic {
        ((number - lowest) as f64).ln_1p() / ((highest - lowest) as f64).ln_1p()
    } else {
        (number - lowest) as f64 / (highest - lowest) as f64
    };
    let gauge = gauge_bar(share, cells);
    let value = if divisor != 1 {
        named(unit, &[("number", (number as f64 / divisor as f64).into())])
    } else {
        named(unit, &[("number", number.into())])
    };
    named(marks::MSG_SOUND_GAUGE, &[("gauge", gauge.as_str().into()), ("value", value.as_str().into())])
}

/// Hertz as a rate is read: tenths below ten, whole hertz below a thousand, then kilohertz.
fn hertz_shown(hertz: f64) -> String {
    let (tens, thousand) = (10.0, 1000.0);
    if hertz < tens {
        named(marks::MSG_TENTHS_HERTZ_SHOWN, &[("number", hertz.into())])
    } else if hertz < thousand {
        named(marks::MSG_HERTZ_SHOWN, &[("number", (hertz.round() as i64).into())])
    } else {
        named(marks::MSG_KILOHERTZ_SHOWN, &[("number", (hertz / thousand).into())])
    }
}

/// A gauge's bar, as many of its cells full as a share from 0 to 1 of the way along.
fn gauge_bar(share: f64, cells: usize) -> String {
    let filled = ((share * cells as f64).round_ties_even() as usize).min(cells);
    format!(
        "{}{}",
        marks::MSG_SOUND_GAUGE_FULL.repeat(filled),
        marks::MSG_SOUND_GAUGE_EMPTY.repeat(cells - filled)
    )
}

/// A gauge field of a whole number with ends, its bar filled from the lowest and its value shown as given.
fn bounded_gauge(id: usize, label: &str, number: i64, range: (i64, i64), value_shown: &str) -> Field {
    let (lowest, highest) = range;
    let share = (number - lowest) as f64 / (highest - lowest).max(1) as f64;
    let bar = gauge_bar(share, GM_CELLS);
    let shown = named(marks::MSG_SOUND_GAUGE, &[("gauge", bar.as_str().into()), ("value", value_shown.into())]);
    Field::number(id, label, Some(number), Some(lowest), Some(highest), lowest, Some(shown))
}

/// A gauge field of a whole number; how says whether it grows logarithmically and what the number is divided by to be shown.
fn gauge(id: usize, label: &str, number: i64, range: (i64, i64), cells: usize, unit: &str, how: (bool, i64)) -> Field {
    let (lowest, highest) = range;
    let (logarithmic, divisor) = how;
    let shown = gauge_text(number, lowest, highest, cells, unit, logarithmic, divisor);
    Field::number(id, label, Some(number), Some(lowest), Some(highest), lowest, Some(shown))
}

fn with_names(mut field: Field, names: Vec<String>) -> Field {
    if let FieldKind::Choice { names: held, .. } = &mut field.kind {
        *held = Some(names);
    }
    field
}

/// A choice among values, each shown by its name.
/// The part whose types are filters, and how a choice that is no name, such as (none), begins.
const FILTER_PART: &str = "filter";
const NOT_A_NAME: char = '(';

/// A part's types, each with its name, in the order its picker lists them: the filter's and the envelopes' by name, as a
/// picker's choices are, an entry that is no name, such as (none), first; another part's in its own order.
fn listed_types(part: &str) -> Vec<(&'static str, String)> {
    let (_, kinds, names) = PART_TYPES.iter().find(|(found, ..)| *found == part).copied().unwrap_or(("", &[], &[]));
    let mut types: Vec<(&'static str, String)> = kinds.iter().copied().zip(names.iter().map(|name| name.to_string())).collect();
    if part == FILTER_PART || ENVELOPE_PARTS.contains(&part) {
        types.sort_by_key(|(_, name)| (!name.starts_with(NOT_A_NAME), name.to_lowercase()));
    }
    types
}

fn chosen(id: usize, label: &str, choices: &[&str], names: &[String], current: &str) -> Field {
    let place = choices.iter().position(|choice| *choice == current).unwrap_or(0);
    let shown = names.get(place).cloned().unwrap_or_default();
    with_names(
        Field::choice(id, label, choices.iter().map(|choice| choice.to_string()).collect(), current, Some(shown)),
        names.to_vec(),
    )
}

fn names_in(table: &[(&str, &str)], choices: &[&str]) -> Vec<String> {
    choices.iter().map(|choice| named_in(table, choice)).collect()
}

/// What a field of the page writes.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Write {
    /// One of the instrument's own settings, the engine that plays it, whether it is percussion, its General MIDI sound.
    Setting(&'static str),
    EngineOf,
    Percussion,
    GmSound,
    /// One of its sound's own settings, a part's type or setting, an oscillator's setting, a drum knob, or a setting of an
    /// item of one of its sound's lists by its number from 1.
    Sound(&'static str),
    PartType(&'static str),
    Part(&'static str, &'static str),
    Oscillator(usize, &'static str),
    Knob(usize),
    Item(&'static str, usize, &'static str),
}

/// How far [ and ] step a gauge, by the number it is below each bound, and past the last.
type Strides = (&'static [(i64, i64)], i64);
const STEPS_OF_ONE: Strides = (&[], 1);
const TIME_STRIDES: Strides = (&[(20, 1), (100, 5), (500, 10), (2000, 50)], 100);
/// How far a frequency in hertz steps, coarser as it rises, so that a cutoff crosses its range in a few presses.
const HERTZ_STRIDES: Strides = (&[(100, 5), (500, 10), (1000, 25), (2000, 50), (5000, 100), (10000, 250)], 500);

/// The envelope wired to the filter, the switch that unhooks it, and an envelope that is off.
const FILTER_ENVELOPE: &str = "env2";
const DISCONNECT_FILTER: &str = "disconnect_filter";
const NO_ENVELOPE: &str = "none";

/// Ids for the fields, counting on, with what each that writes writes, and how far a gauge steps.
#[derive(Default)]
struct Ids {
    last: usize,
    writes: Vec<(usize, Write, Strides)>,
}

impl Ids {
    fn next(&mut self) -> usize {
        self.last += 1;
        self.last
    }

    fn at(&mut self, write: Write) -> usize {
        self.at_gauge(write, STEPS_OF_ONE)
    }

    fn at_gauge(&mut self, write: Write, strides: Strides) -> usize {
        let id = self.next();
        self.writes.push((id, write, strides));
        id
    }
}

/// How far a gauge steps from a number.
fn stride(strides: Strides, number: i64) -> i64 {
    let (bounds, longest) = strides;
    if bounds.is_empty() {
        return longest;
    }
    bounds.iter().find(|(below, _)| number < *below).map_or(longest, |(_, stride)| *stride)
}

impl InstrumentEditor {
    /// The GM sound field's ENTER, which picks a sound from General MIDI's families, or none, and its answer.
    fn choose_gm_sound(&self, app: &mut App, edit: Edit) {
        let Some(instrument) = self.instrument(app) else { return };
        let current = instrument
            .get_written(InstrumentSetting::GM_SOUND)
            .and_then(Data::as_whole)
            .map_or(0, |whole| whole as usize);
        let sound = match edit {
            Edit::Enter => {
                let top = vec![(marks::MSG_NONE_SHOWN.to_string(), 0)];
                app.asking = Some(Edit::AskSound {
                    title: messages::MSG_GM_SOUND_TITLE.to_string(),
                    top,
                    groups: sound_families(),
                    current,
                });
                return;
            }
            Edit::Choice(chosen) => chosen.parse::<i128>().ok().filter(|sound| *sound > 0).map(Data::Whole),
            _ => return,
        };
        let name = self.name.clone();
        app.document.change_set(|setlist| {
            if let Some(Item::Instrument(instrument)) = setlist.get_item_mut(Section::INSTRUMENTS, &name) {
                instrument.set_written(InstrumentSetting::GM_SOUND, sound);
            }
        });
    }

    /// The SID's Arpeggio: ENTER types its semitones apart by spaces, refused on the status line unless whole numbers in
    /// range and few enough, and Bksp clears it back to none.
    fn edit_arpeggio(&self, app: &mut App, sound: &Sound, part: &'static str, edit: Edit) {
        use llamatron_model::schema::generated::limits::{MAX_ARPEGGIO_STEPS, MAX_INTERVAL};
        let steps: Vec<i64> = match edit {
            Edit::Enter => {
                let typed: Vec<String> = sound
                    .part_value(part, ARPEGGIO)
                    .as_list()
                    .map_or(Vec::new(), |steps| steps.iter().map(|step| whole(step).to_string()).collect());
                app.asking = Some(Edit::AskText {
                    title: named(messages::MSG_ARPEGGIO_PROMPT, &[("most", MAX_ARPEGGIO_STEPS.into())]),
                    value: typed.join(marks::MSG_ARPEGGIO_SEPARATOR),
                });
                return;
            }
            Edit::Clear => Vec::new(),
            Edit::Text(text) => {
                let parsed: Option<Vec<i64>> = text.split_whitespace().map(|word| word.parse::<i64>().ok()).collect();
                let valid = parsed.filter(|steps| steps.len() as i64 <= MAX_ARPEGGIO_STEPS && steps.iter().all(|step| step.abs() <= MAX_INTERVAL));
                let Some(steps) = valid else {
                    let words = [
                        ("most", MAX_ARPEGGIO_STEPS.into()),
                        ("highest", MAX_INTERVAL.into()),
                        ("value", text.as_str().into()),
                    ];
                    app.refuse(&named(llamatron_strings::errors::ERR_BAD_ARPEGGIO, &words));
                    return;
                };
                steps
            }
            _ => return,
        };
        let value = Data::List(steps.into_iter().map(|step| Data::Whole(step as i128)).collect());
        let changed = sound.with_part_value(part, ARPEGGIO, value);
        let name = self.name.clone();
        app.document.change_set(|setlist| {
            if let Some(Item::Instrument(instrument)) = setlist.get_item_mut(Section::INSTRUMENTS, &name) {
                instrument.set_written(InstrumentSetting::SOUND, Some(changed));
            }
        });
    }

    /// Play the instrument by another engine: its Kind, and its Device where the engine is FluidSynth or an outside MIDI
    /// device, as one step to undo; what the other engines' fields hold is kept.
    fn choose_engine(&self, app: &mut App, device: Option<String>, engine: &str) {
        let kind = match engine {
            OFF => Some(Data::text(OFF)),
            LLAMASYNTH => Some(Data::text(BUILT_IN)),
            _ => None,
        };
        let device = match engine {
            FLUIDSYNTH => Some(Data::text(FLUIDSYNTH_DEVICE)),
            MIDI if device.as_deref() == Some(FLUIDSYNTH_DEVICE) => None,
            _ => device.map(|device| Data::text(&device)),
        };
        let name = self.name.clone();
        app.document.change_set(|setlist| {
            if let Some(Item::Instrument(instrument)) = setlist.get_item_mut(Section::INSTRUMENTS, &name) {
                instrument.set_written(InstrumentSetting::KIND, kind);
                instrument.set_written(InstrumentSetting::DEVICE, device);
            }
        });
    }

    /// Make the instrument percussion or not: refused while any track plays it, since the track's drums or notes depend
    /// on it; otherwise asked first, starting on NO, since its built-in synth settings give way to the new role's first
    /// engine.
    fn change_percussion(&self, app: &mut App, sound: &Sound, on: bool) {
        let uses = crate::uses::tracks_naming(app.document.get_setlist(), Section::INSTRUMENTS, &self.name);
        if let Some((song, track)) = uses.first() {
            let words = [
                ("name", self.name.as_str().into()),
                ("track", track.as_str().into()),
                ("song", song.as_str().into()),
            ];
            app.refuse(&named(llamatron_strings::errors::ERR_PERCUSSION_IN_USE, &words));
            return;
        }
        let role = if on { PERCUSSION } else { NORMAL };
        let first_engine = ENGINES_OF_ROLE
            .iter()
            .find(|(found, _)| *found == role)
            .and_then(|(_, engines)| engines.first())
            .copied()
            .unwrap_or("");
        let replaced = sound.with_engine(first_engine);
        let name = self.name.clone();
        let title = named(messages::MSG_CHANGE_PERCUSSION_TITLE, &[("name", self.name.as_str().into())]);
        let lines = vec![messages::MSG_PERCUSSION_REPLACES_SYNTH.to_string()];
        let dialog =
            crate::screens::dialogs::ConfirmDialog::new(&title, lines, true, true).then(Box::new(move |app: &mut App, _: &crate::screens::dialogs::Answer| {
                app.document.change_set(|setlist| {
                    if let Some(Item::Instrument(instrument)) = setlist.get_item_mut(Section::INSTRUMENTS, &name) {
                        instrument.set_written(InstrumentSetting::ROLE, Some(Data::text(role)));
                        instrument.set_written(InstrumentSetting::SOUND, Some(replaced.clone()));
                    }
                });
            }));
        app.show_page(Box::new(dialog));
    }

    /// The Device field's ENTER, which picks a port of this computer, or no device, and its answer.
    fn choose_device(&self, app: &mut App, edit: Edit) {
        let Some(instrument) = self.instrument(app) else { return };
        let device = instrument.get_written(InstrumentSetting::DEVICE).and_then(Data::as_str).map(str::to_string);
        let value = match edit {
            Edit::Enter => {
                // The ports this computer has now, and the instrument's own device among them even when it has gone, so
                // that it can be seen and kept.
                let mut ports = crate::realtime::backend::device_port_names();
                if let Some(device) = device.as_ref().filter(|device| *device != FLUIDSYNTH_DEVICE && !ports.contains(device)) {
                    ports.push(device.clone());
                }
                // FluidSynth is an engine of its own on the Engine tab, so it is no device to choose here.
                ports.retain(|port| port != FLUIDSYNTH_DEVICE);
                let devices = crate::settings::sorted_names(&ports);
                crate::screens::arrange::arrange_tabs::ask_name_or_above(
                    app,
                    messages::MSG_DEVICE_TITLE,
                    marks::MSG_NO_DEVICE_SHOWN,
                    devices,
                    device.as_deref(),
                );
                return;
            }
            Edit::Choice(chosen) => crate::screens::arrange::arrange_tabs::chosen_name(&chosen),
            Edit::Clear => None,
            _ => return,
        };
        let name = self.name.clone();
        app.document.change_set(|setlist| {
            if let Some(Item::Instrument(instrument)) = setlist.get_item_mut(Section::INSTRUMENTS, &name) {
                instrument.set_written(InstrumentSetting::DEVICE, value);
            }
        });
    }

    /// The page's fields, and what each that writes writes.
    /// Open the Keyswitch Map, whose ten slots go into the instrument together on OK, as one undo step; a slot with nothing
    /// in it is written as none, and a map with nothing in any slot leaves the setting out of the file.
    fn open_keyswitch_map(&self, app: &mut App) {
        let keyswitches = crate::keyswitches::keyswitches_of(app, Some(&self.name));
        let title = llamatron_strings::named(
            llamatron_strings::messages::MSG_KEYSWITCH_MAP_TITLE,
            &[("instrument", self.name.as_str().into())],
        );
        let name = self.name.clone();
        let then = Box::new(move |app: &mut App, slots: Vec<crate::keyswitches::Keyswitch>| {
            let written: Vec<Data> = slots
                .iter()
                .map(|slot| {
                    let mut pairs = Vec::new();
                    if let Some(named) = &slot.name {
                        pairs.push((Data::text("name"), Data::text(named)));
                    }
                    if let Some(note) = slot.note {
                        pairs.push((Data::text("note"), Data::Whole(note as i128)));
                    }
                    if pairs.is_empty() {
                        Data::Null
                    } else {
                        Data::Map(pairs)
                    }
                })
                .collect();
            let value = written.iter().any(|slot| !slot.is_null()).then_some(Data::List(written));
            app.document.change_set(|setlist| {
                if let Some(llamatron_model::objects::setlist::Item::Instrument(held)) =
                    setlist.get_item_mut(llamatron_model::schema::generated::file_format::Section::INSTRUMENTS, &name)
                {
                    held.set_written("keyswitches", value);
                }
            });
        });
        app.show_page(Box::new(crate::screens::keyswitch_map_dialog::KeyswitchMapDialog::new(
            &title,
            keyswitches,
            then,
        )));
    }

    fn built(&self, app: &App) -> (Vec<Node>, Ids) {
        let Some(instrument) = self.instrument(app) else {
            return (Vec::new(), Ids::default());
        };
        let sound = Sound::of(instrument);
        let mut ids = Ids::default();
        let velocity = instrument.get_default_velocity();
        let accent = instrument.get_accent();
        let percent = instrument
            .get_written(InstrumentSetting::VELOCITY)
            .and_then(Data::as_whole)
            .map(|whole| whole as i64);
        let percent_shown = |percent: i64| named(marks::MSG_PERCENT_SHOWN, &[("percent", percent.into())]);
        let accent_shown = |accent: i64| named(marks::MSG_ACCENT_SHOWN, &[("accent", accent.into())]);
        let in_effect = velocity.unwrap_or(DEFAULT_VELOCITY);
        let nodes = vec![
            Field::name(NAME, &self.name),
            Field::number(
                ids.at(Write::Setting(InstrumentSetting::DEFAULT_VELOCITY)),
                labels::MSG_DEFAULT_VELOCITY_LABEL,
                Some(in_effect),
                Some(1),
                Some(127),
                DEFAULT_VELOCITY,
                None,
            )
            .with_clear(&DEFAULT_VELOCITY.to_string()),
            Field::number(
                ids.at(Write::Setting(InstrumentSetting::ACCENT)),
                labels::MSG_ACCENT_LABEL,
                Some(accent),
                Some(0),
                Some(127),
                DEFAULT_ACCENT,
                Some(accent_shown(accent)),
            )
            .with_clear(&accent_shown(DEFAULT_ACCENT)),
            Field::number(
                ids.at(Write::Setting(InstrumentSetting::VELOCITY)),
                labels::MSG_VELOCITY_PERCENT_LABEL,
                percent,
                Some(0),
                Some(200),
                UNCHANGED,
                Some(percent_shown(percent.unwrap_or(UNCHANGED))),
            )
            .with_clear(&percent_shown(UNCHANGED)),
        ];
        let mut nodes: Vec<Node> = nodes.into_iter().map(|field| Node::Field(Box::new(field))).collect();
        // The synth's own tabs follow the Engine tab only where LlamaSynth plays the instrument.
        let mut tabs = vec![self.engine_tab(app, instrument, &sound, &mut ids)];
        if Self::engine_of(instrument) == LLAMASYNTH {
            let ready = false;
            tabs.extend([
                Self::oscillators_tab(&sound, ready, &mut ids),
                Self::envelopes_tab(&sound, ready, &mut ids),
                Self::lfos_tab(&sound, ready, &mut ids),
                Self::filter_tab(&sound, ready, &mut ids),
                Self::amp_tab(&sound, ready, &mut ids),
                Self::effects_tab(&sound, ready, &mut ids),
                Self::matrix_tab(&sound, ready, &mut ids),
            ]);
        }
        nodes.push(Node::TabBox(TabBox {
            label: labels::MSG_TABS_LABEL.to_string(),
            tabs,
        }));
        let buttons = [
            Field::button(ids.next(), labels::MSG_PREVIEW_PATTERN_LABEL, "", legends::What::EDIT),
            Field::button(ids.next(), labels::MSG_KEYSWITCH_MAP_LABEL, Keys::KEYSWITCH_MAP.name, Keys::KEYSWITCH_MAP.what),
            self.listen_button(app, ids.next()),
        ];
        nodes.extend(buttons.into_iter().map(|field| Node::Field(Box::new(field))));
        (nodes, ids)
    }

    /// The Listen button, which does what L does: it starts listening to the instrument, or stops it while it plays, both
    /// names taking the room of the longer so that the button never changes its width.
    fn listen_button(&self, app: &App, id: usize) -> Field {
        let width = labels::MSG_LISTEN_LABEL.chars().count().max(labels::MSG_STOP_LISTENING_LABEL.chars().count());
        if self.is_listening(app) {
            return Field::button(
                id,
                &format!("{:^width$}", labels::MSG_STOP_LISTENING_LABEL),
                legends::KeyName::L,
                legends::MSG_STOP_LISTENING_WHAT,
            );
        }
        Field::button(
            id,
            &format!("{:^width$}", labels::MSG_LISTEN_LABEL),
            legends::KeyName::L,
            legends::MSG_LISTEN_WHAT,
        )
    }

    /// Whether the instrument's preview pattern is being listened to.
    fn is_listening(&self, app: &App) -> bool {
        app.preview.playing_instrument() == Some(self.name.as_str())
    }

    /// L and the Listen button: listen to the instrument's preview pattern through it, or stop while it plays.
    fn listen_or_stop(&self, app: &mut App) {
        if self.is_listening(app) {
            crate::screens::listening::stop_listening_to_pattern(app);
            return;
        }
        crate::screens::listening::listen_to_instrument(app, &self.name);
    }

    /// The Preview pattern button: open the pattern editor on the instrument's preview pattern, made first if it has none,
    /// with this page's crumbs before it, so that ESC comes back here.
    fn open_preview(&self, app: &mut App) {
        let Some(instrument) = self.instrument(app) else { return };
        if instrument.get_preview().is_none() {
            let sound = Sound::of(instrument);
            let drum = self.role(app, instrument, &sound) == "percussion";
            let name = self.name.clone();
            app.document.change_set(|setlist| {
                if let Some(Item::Instrument(instrument)) = setlist.get_item_mut(Section::INSTRUMENTS, &name) {
                    instrument.make_preview(drum);
                }
            });
        }
        let key = llamatron_model::objects::instrument_previews::preview_key(&self.name);
        let crumbs = Form::crumbs(self, app);
        app.show_page(crate::screens::pattern::open_preview_pattern(&key, crumbs));
    }

    fn instrument<'a>(&self, app: &'a App) -> Option<&'a Instrument> {
        match app.document.get_setlist().get_item(Section::INSTRUMENTS, &self.name) {
            Some(Item::Instrument(instrument)) => Some(instrument),
            _ => None,
        }
    }

    fn kind(instrument: &Instrument) -> String {
        instrument
            .get_written(InstrumentSetting::KIND)
            .and_then(Data::as_str)
            .unwrap_or(MIDI)
            .to_string()
    }

    /// Whether the instrument is normal or percussion: as written, or as its tracks play it, or by its drum machine.
    fn role(&self, app: &App, instrument: &Instrument, sound: &Sound) -> String {
        if let Some(role) = instrument.get_written(InstrumentSetting::ROLE).and_then(Data::as_str) {
            return role.to_string();
        }
        let song = app.document.song();
        let tracks: Vec<bool> = song
            .tracks()
            .iter()
            .filter(|(_, track)| track.get_instrument_name().as_deref() == Some(self.name.as_str()))
            .map(|(_, track)| track.is_drum())
            .collect();
        if let Some(drum) = tracks.first() {
            return if *drum { PERCUSSION } else { NORMAL }.to_string();
        }
        if Self::kind(instrument) == BUILT_IN && sound.part_type("oscillators") == "drum" {
            return PERCUSSION.to_string();
        }
        NORMAL.to_string()
    }

    /// The engine that plays an instrument, from its Kind and Device: off, an outside MIDI device, FluidSynth, or the
    /// built-in synths.
    fn engine_of(instrument: &Instrument) -> &'static str {
        let device = instrument.get_written(InstrumentSetting::DEVICE).and_then(Data::as_str);
        match Self::kind(instrument).as_str() {
            OFF => OFF,
            BUILT_IN => LLAMASYNTH,
            _ if device == Some(FLUIDSYNTH_DEVICE) => FLUIDSYNTH,
            _ => MIDI,
        }
    }

    /// The Engine tab: the Engine and Percussion, then what the engine chosen plays by: a device's port and channel, a
    /// General MIDI sound and pan, or the built-in synths' Voice settings.
    fn engine_tab(&self, app: &App, instrument: &Instrument, sound: &Sound, ids: &mut Ids) -> Tab {
        let engine = Self::engine_of(instrument);
        let percussion = self.role(app, instrument, sound) == PERCUSSION;
        let top = vec![
            chosen(
                ids.at(Write::EngineOf),
                labels::MSG_ENGINE_LABEL,
                ENGINES,
                &names_in(labels::MSG_ENGINE_KIND_NAMES, ENGINES),
                engine,
            ),
            Field::toggle(ids.at(Write::Percussion), labels::MSG_PERCUSSION_LABEL, percussion),
        ];
        let sending = self.sending_fields(instrument, percussion, ids);
        let kept: &[&str] = match engine {
            MIDI => &[
                labels::MSG_DEVICE_LABEL,
                labels::MSG_CHANNEL_LABEL,
                labels::MSG_KEYSWITCH_LEAD_LABEL,
                labels::MSG_LATENCY_LABEL,
            ],
            FLUIDSYNTH if percussion => &[labels::MSG_PAN_LABEL, labels::MSG_CHANNEL_LABEL],
            FLUIDSYNTH => &[labels::MSG_GM_SOUND_LABEL, labels::MSG_PAN_LABEL, labels::MSG_CHANNEL_LABEL],
            _ => &[],
        };
        let mut fields: Vec<Field> = Vec::new();
        for label in kept {
            fields.extend(sending.iter().filter(|field| field.label == *label).cloned());
        }
        if engine == LLAMASYNTH {
            fields = Self::voice_fields(sound, ids);
        }
        let mut tab = Tab::new(labels::MSG_ENGINE_TAB, vec![TabColumn::new(None, fields)]);
        tab.top = top;
        tab
    }

    /// Every field of how an instrument is sent to a device or FluidSynth, which the Engine tab shows those of its
    /// engine from: its Device, Channel, General MIDI sound, Pan, keyswitch lead and latency.
    fn sending_fields(&self, instrument: &Instrument, percussion: bool, ids: &mut Ids) -> Vec<Field> {
        let device = instrument.get_written(InstrumentSetting::DEVICE).and_then(Data::as_str);
        let channel = if device == Some(FLUIDSYNTH_DEVICE) {
            // Every track through FluidSynth gets a channel of its own, a percussion instrument's tracks the drums' 10.
            let shown = if percussion {
                marks::MSG_DRUM_CHANNEL_SHOWN
            } else {
                marks::MSG_AUTO_CHANNEL_SHOWN
            };
            Field::custom(ids.next(), labels::MSG_CHANNEL_LABEL, shown)
        } else {
            let channel = instrument
                .get_written(InstrumentSetting::CHANNEL)
                .and_then(Data::as_whole)
                .map_or(1, |whole| whole as i64);
            Field::number(
                ids.at(Write::Setting(InstrumentSetting::CHANNEL)),
                labels::MSG_CHANNEL_LABEL,
                Some(channel),
                Some(1),
                Some(16),
                1,
                None,
            )
            .titled(&named(messages::MSG_CHANNEL_PROMPT, &[("lowest", 1.into()), ("highest", 16.into())]))
        };
        let sound = instrument
            .get_written(InstrumentSetting::GM_SOUND)
            .and_then(Data::as_whole)
            .map(|whole| whole as i64);
        let sound_shown = sound.map_or(marks::MSG_NONE_SHOWN.to_string(), |sound| {
            let name = labels::MSG_GM_SOUNDS.get((sound - MIN_GM_SOUND) as usize).copied().unwrap_or("");
            named(labels::MSG_GM_SOUND_SHOWN, &[("number", sound.into()), ("name", name.into())])
        });
        let lead = instrument
            .get_written(InstrumentSetting::KEYSWITCH_LEAD)
            .and_then(Data::as_whole)
            .map_or(0, |whole| whole as i64);
        let latency = instrument
            .get_written(InstrumentSetting::LATENCY)
            .and_then(Data::as_whole)
            .map_or(0, |whole| whole as i64);
        let milliseconds = |number: i64| named(marks::MSG_KEYSWITCH_LEAD_SHOWN, &[("milliseconds", number.into())]);
        let mut fields = vec![
            Field::custom(
                ids.at(Write::Setting(InstrumentSetting::DEVICE)),
                labels::MSG_DEVICE_LABEL,
                device.unwrap_or(marks::MSG_NO_DEVICE_SHOWN),
            )
            .with_enter(legends::What::CHOOSE)
            .with_clear(marks::MSG_NONE_SHOWN),
            channel,
            Field::custom(ids.at(Write::GmSound), labels::MSG_GM_SOUND_LABEL, &sound_shown)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(marks::MSG_NONE_SHOWN),
            Self::pan_field(instrument, ids),
            Field::number(
                ids.at(Write::Setting(InstrumentSetting::KEYSWITCH_LEAD)),
                labels::MSG_KEYSWITCH_LEAD_LABEL,
                Some(lead),
                Some(MIN_KEYSWITCH_LEAD),
                Some(MAX_KEYSWITCH_LEAD),
                0,
                Some(milliseconds(lead)),
            )
            .titled(&named(
                messages::MSG_KEYSWITCH_LEAD_PROMPT,
                &[("lowest", MIN_KEYSWITCH_LEAD.into()), ("highest", MAX_KEYSWITCH_LEAD.into())],
            )),
            Field::number(
                ids.at(Write::Setting(InstrumentSetting::LATENCY)),
                labels::MSG_LATENCY_LABEL,
                Some(latency),
                Some(MIN_INSTRUMENT_LATENCY),
                Some(MAX_INSTRUMENT_LATENCY),
                0,
                Some(milliseconds(latency)),
            )
            .titled(&named(
                messages::MSG_LATENCY_PROMPT,
                &[("lowest", MIN_INSTRUMENT_LATENCY.into()), ("highest", MAX_INSTRUMENT_LATENCY.into())],
            )),
        ];
        // Only FluidSynth is sent the pan, since a device's own pan is its player's to set.
        if device != Some(FLUIDSYNTH_DEVICE) {
            fields.retain(|field| field.label != labels::MSG_PAN_LABEL);
        }
        fields
    }

    /// A FluidSynth instrument's Pan, a gauge from hard left at 0% to hard right at 100%, the middle at 50% unless set.
    fn pan_field(instrument: &Instrument, ids: &mut Ids) -> Field {
        let pan = instrument.get_pan();
        let unit = if pan == DEFAULT_PAN {
            marks::MSG_PAN_CENTER_SHOWN
        } else {
            marks::MSG_SOUND_PERCENT_SHOWN
        };
        let center = named(marks::MSG_PAN_CENTER_SHOWN, &[("number", DEFAULT_PAN.into())]);
        gauge(
            ids.at(Write::Setting(InstrumentSetting::PAN)),
            labels::MSG_PAN_LABEL,
            pan,
            (MIN_PAN, MAX_PAN),
            GM_CELLS,
            unit,
            (false, 1),
        )
        .with_clear(&center)
    }

    fn type_field(sound: &Sound, part: &'static str, ids: &mut Ids) -> Field {
        let label = part_label(part, labels::MSG_PART_TYPE_LABEL);
        let types = listed_types(part);
        let kinds: Vec<&str> = types.iter().map(|(kind, _)| *kind).collect();
        let names: Vec<String> = types.into_iter().map(|(_, name)| name).collect();
        chosen(ids.at(Write::PartType(part)), &label, &kinds, &names, &sound.part_type(part)).with_shown_label(labels::MSG_PART_TYPE_LABEL)
    }

    fn setting_fields(sound: &Sound, part: &'static str, ids: &mut Ids) -> Vec<Field> {
        let kind = sound.part_type(part);
        let settings: &[&str] = TYPE_SETTINGS.iter().find(|(found, _)| *found == kind).map_or(&[], |(_, settings)| settings);
        // A modded setting shows only with the part's Circuit set to Modded.
        let modded = sound.part_value(part, CIRCUIT).as_str() == Some(MODDED);
        settings
            .iter()
            .filter(|name| modded || !crate::generated::sounds::MODDED_SETTINGS.contains(&(kind.as_str(), **name)))
            .filter(|name| Self::acts_with(sound, part, name))
            .map(|name| Self::setting_field(sound, part, &kind, name, ids))
            .collect()
    }

    /// Whether a setting acts with the part's other settings as they stand: a vactrol's or a gate's Trigger time only
    /// with its Trigger lighting it by a flash, and a gate's Ping time only with a Ping in its Signal.
    fn acts_with(sound: &Sound, part: &str, name: &str) -> bool {
        let chosen = |setting: &str| sound.part_value(part, setting).as_str().map(str::to_string);
        match name {
            "trigger_time" => chosen("trigger").as_deref() == Some("trigger"),
            "ping_time" => chosen("signal").as_deref() != Some("oscillator"),
            _ => true,
        }
    }

    fn setting_field(sound: &Sound, part: &'static str, kind: &str, name: &'static str, ids: &mut Ids) -> Field {
        let value = sound.part_value(part, name);
        let shown_label = named_in(labels::MSG_PART_SETTING_NAMES, name);
        let label = part_label(part, &shown_label);
        if name == ARPEGGIO {
            let steps: Vec<String> = value
                .as_list()
                .map_or(Vec::new(), |steps| steps.iter().map(|step| whole(step).to_string()).collect());
            let shown = if steps.is_empty() {
                marks::MSG_ARPEGGIO_NONE_SHOWN.to_string()
            } else {
                steps.join(marks::MSG_ARPEGGIO_SEPARATOR)
            };
            return Field::custom(ids.at(Write::Part(part, ARPEGGIO)), labels::MSG_ARPEGGIO_LABEL, &shown)
                .with_enter(legends::What::EDIT)
                .with_clear(marks::MSG_ARPEGGIO_NONE_SHOWN);
        }
        let how = TYPE_SETTING_KINDS
            .iter()
            .find(|(found, setting, _)| *found == kind && *setting == name)
            .map(|(.., how)| *how)
            .or_else(|| SETTING_KINDS.iter().find(|(found, _)| *found == name).map(|(_, how)| *how))
            .unwrap_or(SettingKind::Toggle);
        let strides = match how {
            SettingKind::Gauge { what: "milliseconds", .. } => Some(TIME_STRIDES),
            SettingKind::Gauge { what: "hertz", .. } => Some(HERTZ_STRIDES),
            _ => None,
        };
        let id = ids.at_gauge(Write::Part(part, name), strides.unwrap_or(STEPS_OF_ONE));
        let field = match how {
            SettingKind::Choice { choices, names } => {
                let names: Vec<String> = names.iter().map(|name| name.to_string()).collect();
                chosen(id, &label, choices, &names, &text(&value))
            }
            SettingKind::Toggle => Field::toggle(id, &label, flag(&value)),
            SettingKind::Number { lowest, highest, unit, zero } => {
                // A number with ends is a horizontal gauge, stepped and typed (UX.md, "Settings pages").
                let number = whole(&value);
                let value_shown = match zero {
                    Some(zero) if number == 0 => zero.to_string(),
                    _ => named(unit, &[("number", number.into())]),
                };
                bounded_gauge(id, &label, number, (lowest, highest), &value_shown)
            }
            SettingKind::SidTime { times, .. } => {
                let rate = whole(&value);
                let milliseconds = SID_ATTACK_MS.get(rate as usize).copied().unwrap_or(0) * times;
                let shown = named(marks::MSG_SID_RATE_SHOWN, &[("number", rate.into()), ("milliseconds", milliseconds.into())]);
                Field::number(id, &label, Some(rate), Some(0), Some(MAX_SID_RATE), 0, Some(shown))
            }
            SettingKind::Gauge { lowest, highest, what } => {
                let number = whole(&value);
                match what {
                    "milliseconds" => gauge(id, &label, number, (lowest, highest), GM_CELLS, marks::MSG_MILLISECONDS_SHOWN, (true, 1)),
                    "tenths" => gauge(
                        id,
                        &label,
                        number,
                        (lowest, highest),
                        GM_CELLS,
                        marks::MSG_TENTH_MILLISECONDS_SHOWN,
                        (true, TENTHS),
                    ),
                    "tenth_cents" => gauge(id, &label, number, (lowest, highest), GM_CELLS, marks::MSG_TENTH_CENTS_SHOWN, (false, TENTHS)),
                    "hertz" => gauge(id, &label, number, (lowest, highest), GM_CELLS, marks::MSG_HERTZ_SHOWN, (true, 1)),
                    _ => gauge(id, &label, number, (lowest, highest), GM_CELLS, marks::MSG_SOUND_PERCENT_SHOWN, (false, 1)),
                }
            }
        };
        field.with_shown_label(&shown_label)
    }

    fn voice_fields(sound: &Sound, ids: &mut Ids) -> Vec<Field> {
        let sharing = text(&sound.value("filter_sharing"));
        let mut fields = vec![
            Field::number(
                ids.at(Write::Sound("voices")),
                labels::MSG_VOICES_LABEL,
                Some(whole(&sound.value("voices"))),
                Some(1),
                Some(MAX_VOICES),
                1,
                None,
            ),
            Field::toggle(ids.at(Write::Sound("glides")), labels::MSG_GLIDE_LABEL, glides_on(sound)),
            gauge(
                ids.at_gauge(Write::Sound("glide"), TIME_STRIDES),
                labels::MSG_GLIDE_TIME_LABEL,
                whole(&sound.value("glide")),
                (0, MAX_GLIDE_MS),
                GM_CELLS,
                marks::MSG_MILLISECONDS_SHOWN,
                (true, 1),
            ),
            chosen(
                ids.at(Write::Sound("filter_sharing")),
                labels::MSG_FILTER_SHARING_LABEL,
                FILTER_SHARINGS,
                &names_in(labels::MSG_FILTER_SHARING_NAMES, FILTER_SHARINGS),
                &sharing,
            ),
        ];
        // A note's own filter or a shared one differ only while two notes sound at once, which one voice never does.
        if whole(&sound.value("voices")) <= 1 {
            fields.retain(|field| field.label != labels::MSG_FILTER_SHARING_LABEL);
        }
        fields
    }

    fn oscillators_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let top = vec![Self::type_field(sound, "oscillators", ids)];
        let mut columns = Vec::new();
        let kind = sound.part_type("oscillators");
        if kind == "basic" {
            for number in 1..=BASIC_OSCILLATORS {
                let heading = named(labels::MSG_OSCILLATOR_LABEL, &[("number", number.into())]);
                let waveform = text(&sound.oscillator(number, "waveform"));
                let detune = whole(&sound.oscillator(number, "detune"));
                let fields = vec![
                    chosen(
                        ids.at(Write::Oscillator(number, "waveform")),
                        &heading,
                        OSCILLATOR_WAVEFORMS,
                        &names_in(labels::MSG_WAVEFORM_NAMES, OSCILLATOR_WAVEFORMS),
                        &waveform,
                    )
                    .with_shown_label(labels::MSG_WAVE_LABEL),
                    bounded_gauge(
                        ids.at(Write::Oscillator(number, "detune")),
                        &named(labels::MSG_OSCILLATOR_DETUNE_LABEL, &[("number", number.into())]),
                        detune,
                        (-MAX_DETUNE_CENTS, MAX_DETUNE_CENTS),
                        &named(marks::MSG_CENTS_SHOWN, &[("number", detune.into())]),
                    )
                    .with_shown_label(labels::MSG_DETUNE_LABEL),
                    gauge(
                        ids.at(Write::Oscillator(number, "fine")),
                        &named(labels::MSG_OSCILLATOR_FINE_LABEL, &[("number", number.into())]),
                        whole(&sound.oscillator(number, "fine")),
                        (-MOST_FINE_TENTHS, MOST_FINE_TENTHS),
                        GM_CELLS,
                        marks::MSG_TENTH_CENTS_SHOWN,
                        (false, TENTHS),
                    )
                    .with_shown_label(labels::MSG_FINE_LABEL),
                    gauge(
                        ids.at(Write::Oscillator(number, "level")),
                        &named(labels::MSG_OSCILLATOR_LEVEL_LABEL, &[("number", number.into())]),
                        whole(&sound.oscillator(number, "level")),
                        (0, MAX_PERCENT),
                        GM_CELLS,
                        marks::MSG_SOUND_PERCENT_SHOWN,
                        (false, 1),
                    )
                    .with_shown_label(labels::MSG_LEVEL_LABEL),
                ];
                columns.push(TabColumn::new(Some(&heading), fields));
            }
        }
        if kind == ASHEVILLE {
            columns.extend(Self::asheville_columns(sound, ids));
            let mut tab = Tab::new(labels::MSG_OSCILLATORS_TAB, columns);
            tab.top = top;
            tab.not_ready = not_ready;
            return tab;
        }
        let mut own = Self::setting_fields(sound, "oscillators", ids);
        if kind == "drum" {
            let knobs = sound.part_value("oscillators", "knobs");
            for place in 0..KNOB_COUNT as usize {
                let number = knobs.as_list().and_then(|knobs| knobs.get(place)).map_or(0, whole);
                own.push(gauge(
                    ids.at(Write::Knob(place)),
                    labels::MSG_KNOB_LABELS[place],
                    number,
                    (0, MAX_KNOB),
                    GM_CELLS,
                    marks::MSG_NUMBER_SHOWN,
                    (false, 1),
                ));
            }
        }
        // A type of no settings of its own, such as Basic, whose one oscillator has its column, shows no empty column.
        if !own.is_empty() {
            columns.push(TabColumn::new(Some(&named_in(labels::MSG_PART_HEADINGS, "oscillators")), own));
        }
        let mut tab = Tab::new(labels::MSG_OSCILLATORS_TAB, columns);
        tab.top = top;
        tab.not_ready = not_ready;
        tab
    }

    /// Asheville's columns, after its panel: a column for each oscillator, its Range, its Wave (or, on the Continuous
    /// model, its Shape), Tune, Mix, Sub and On, then the panel's own settings.
    fn asheville_columns(sound: &Sound, ids: &mut Ids) -> Vec<TabColumn> {
        let mut columns = Vec::new();
        for (number, names) in ASHEVILLE_OSCILLATORS.iter().enumerate() {
            let heading = named(labels::MSG_OSCILLATOR_LABEL, &[("number", (number + 1).into())]);
            let speed = text(&sound.part_value("oscillators", names[0]));
            let fields = names
                .iter()
                .filter(|name| Self::asheville_shows(sound, &speed, name))
                .map(|name| {
                    let column_label = named_in(labels::MSG_ASHEVILLE_COLUMN_LABELS, name.rsplit_once('_').map_or(*name, |(_, own)| own));
                    let field = if name.ends_with(RATE_SUFFIX) {
                        Self::oscillator_rate_field(sound, &speed, name, ids)
                    } else {
                        Self::setting_field(sound, "oscillators", ASHEVILLE, name, ids)
                    };
                    field.with_shown_label(&column_label)
                })
                .collect();
            columns.push(TabColumn::new(Some(&heading), fields));
        }
        let own = ASHEVILLE_PANEL
            .iter()
            .map(|name| Self::setting_field(sound, "oscillators", ASHEVILLE, name, ids))
            .collect();
        // The panel's own settings stand after the oscillators, in the one row the box scrolls along.
        columns.push(TabColumn::new(Some(&named_in(labels::MSG_PART_HEADINGS, "oscillators")), own));
        columns
    }

    /// Whether an Asheville oscillator's setting shows: its Wave on the Classic model and its Shape on Continuous, its
    /// Range at the Audio speed and its Rate at an LFO's.
    fn asheville_shows(sound: &Sound, speed: &str, name: &str) -> bool {
        let continuous = sound.part_value("oscillators", "model").as_str() == Some(CONTINUOUS);
        let audio = speed == AUDIO_SPEED;
        let model_hides = if continuous { WAVE_SUFFIX } else { SHAPE_SUFFIX };
        let speed_hides = if audio { RATE_SUFFIX } else { RANGE_SUFFIX };
        !name.ends_with(model_hides) && !name.ends_with(speed_hides)
    }

    /// An Asheville oscillator's Rate at an LFO's speed: a gauge of its percent, shown with the hertz it gives there.
    fn oscillator_rate_field(sound: &Sound, speed: &str, name: &'static str, ids: &mut Ids) -> Field {
        let percent = whole(&sound.part_value("oscillators", name));
        let hertz = hertz_shown(lfo_speed::hertz(speed, percent as f64));
        let value = named(marks::MSG_LFO_RATE_SHOWN, &[("percent", percent.into()), ("hertz", hertz.as_str().into())]);
        let label = part_label("oscillators", &named_in(labels::MSG_PART_SETTING_NAMES, name));
        let most = lfo_speed::MOST_PERCENT as i64;
        bounded_gauge(ids.at(Write::Part("oscillators", name)), &label, percent, (0, most), &value)
    }

    fn envelopes_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let columns = ENVELOPE_PARTS
            .iter()
            .map(|part| {
                let mut fields = vec![Self::type_field(sound, part, ids)];
                fields.extend(Self::setting_fields(sound, part, ids));
                // Env 2's switch stands at the foot of its column, so that its settings sit level with the others'.
                if *part == FILTER_ENVELOPE && sound.part_type(part) != NO_ENVELOPE {
                    fields.push(Field::toggle(
                        ids.at(Write::Sound(DISCONNECT_FILTER)),
                        labels::MSG_DISCONNECT_FILTER_LABEL,
                        flag(&sound.value(DISCONNECT_FILTER)),
                    ));
                }
                TabColumn::new(Some(&named_in(labels::MSG_PART_HEADINGS, part)), fields)
            })
            .collect();
        let mut tab = Tab::new(labels::MSG_ENVELOPES_TAB, columns);
        tab.not_ready = not_ready;
        tab
    }

    /// An LFO's Rate: a ratio to the note where it follows the key, or else a percentage across its Speed's span, shown
    /// with the hertz it gives, such as 74% (5.0 Hz).
    fn lfo_rate_field(ids: &mut Ids, number: usize, speed: &str, keyed: bool, percent: &Data, ratio: &str) -> Field {
        let numbered = |label: &str| named(label, &[("number", number.into())]);
        let shown_label = named_in(labels::MSG_LFO_SHOWN_LABELS, labels::MSG_LFO_RATE_LABEL);
        if keyed {
            return chosen(
                ids.at(Write::Item("lfos", number, "ratio")),
                &numbered(labels::MSG_LFO_RATIO_LABEL),
                lfo_speed::RATIOS,
                &lfo_speed::RATIOS.iter().map(|ratio| ratio.to_string()).collect::<Vec<_>>(),
                ratio,
            )
            .with_shown_label(&shown_label);
        }
        let percent = whole(percent);
        let hertz = hertz_shown(lfo_speed::hertz(speed, percent as f64));
        let value = named(marks::MSG_LFO_RATE_SHOWN, &[("percent", percent.into()), ("hertz", hertz.as_str().into())]);
        let most = lfo_speed::MOST_PERCENT as i64;
        let bar = gauge_bar(percent as f64 / most as f64, BLOCK_CELLS);
        let shown = named(marks::MSG_SOUND_GAUGE, &[("gauge", bar.as_str().into()), ("value", value.as_str().into())]);
        Field::number(
            ids.at(Write::Item("lfos", number, "rate_percent")),
            &numbered(labels::MSG_LFO_RATE_LABEL),
            Some(percent),
            Some(0),
            Some(most),
            0,
            Some(shown),
        )
        .with_shown_label(&shown_label)
    }

    /// An LFO+'s Fade in: a gauge of how long its depth takes to rise after a note, 0 to 10 s, "off" at 0.
    fn fade_in_field(ids: &mut Ids, number: usize, milliseconds: i64) -> Field {
        let label = named(labels::MSG_LFO_FADE_IN_LABEL, &[("number", number.into())]);
        let id = ids.at(Write::Item("lfos", number, "fade_in"));
        if milliseconds == 0 {
            let bar = gauge_bar(0.0, BLOCK_CELLS);
            let shown = named(
                marks::MSG_SOUND_GAUGE,
                &[("gauge", bar.as_str().into()), ("value", marks::MSG_FADE_IN_OFF.into())],
            );
            return Field::number(id, &label, Some(0), Some(0), Some(LONGEST_FADE_IN_MS), 0, Some(shown));
        }
        gauge(
            id,
            &label,
            milliseconds,
            (0, LONGEST_FADE_IN_MS),
            BLOCK_CELLS,
            marks::MSG_MILLISECONDS_SHOWN,
            (true, 1),
        )
    }

    fn lfos_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let lfo = |number: usize, name: &str| sound.item("lfos", number, name, LFO_DEFAULTS);
        let shown_label = |label: &str| named_in(labels::MSG_LFO_SHOWN_LABELS, label);
        let mut columns = Vec::new();
        for number in 1..=LFO_COUNT as usize {
            let numbered = |label: &str| named(label, &[("number", number.into())]);
            // An LFO+ offers Smooth random, the Tempo speed and Fade in beside what an LFO does.
            let is_plus = sound.is_lfo_plus(number);
            let (shapes, speeds) = if is_plus {
                (LFO_PLUS_SHAPES, lfo_speed::PLUS_SPEED_NAMES)
            } else {
                (LFO_SHAPES, lfo_speed::SPEED_NAMES)
            };
            let shape = text(&sound.lfo_setting(number, "shape"));
            let speed = text(&sound.lfo_setting(number, "speed"));
            let keyed = speed == lfo_speed::AUDIO_SPEED && flag(&lfo(number, "key"));
            let rate = if speed == lfo_speed::TEMPO_SPEED {
                chosen(
                    ids.at(Write::Item("lfos", number, "division")),
                    &numbered(labels::MSG_LFO_DIVISION_LABEL),
                    lfo_speed::DIVISIONS,
                    &names_in(labels::MSG_LFO_DIVISION_NAMES, lfo_speed::DIVISIONS),
                    &text(&lfo(number, "division")),
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_DIVISION_LABEL))
            } else {
                Self::lfo_rate_field(ids, number, &speed, keyed, &lfo(number, "rate_percent"), &text(&lfo(number, "ratio")))
            };
            let mut fields = vec![
                chosen(
                    ids.at(Write::Item("lfos", number, "type")),
                    &numbered(labels::MSG_LFO_TYPE_LABEL),
                    LFO_TYPES,
                    &names_in(labels::MSG_LFO_TYPE_NAMES, LFO_TYPES),
                    &text(&lfo(number, "type")),
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_TYPE_LABEL)),
                chosen(
                    ids.at(Write::Item("lfos", number, "shape")),
                    &numbered(labels::MSG_LFO_SHAPE_LABEL),
                    shapes,
                    &names_in(labels::MSG_LFO_SHAPE_NAMES, shapes),
                    &shape,
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_SHAPE_LABEL)),
                chosen(
                    ids.at(Write::Item("lfos", number, "speed")),
                    &numbered(labels::MSG_LFO_SPEED_LABEL),
                    speeds,
                    &names_in(labels::MSG_LFO_SPEED_NAMES, speeds),
                    &speed,
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_SPEED_LABEL)),
                rate,
            ];
            if speed == lfo_speed::AUDIO_SPEED {
                fields.push(
                    Field::toggle(ids.at(Write::Item("lfos", number, "key")), &numbered(labels::MSG_LFO_KEY_LABEL), keyed)
                        .with_shown_label(&shown_label(labels::MSG_LFO_KEY_LABEL)),
                );
            }
            if is_plus {
                fields.push(Self::fade_in_field(ids, number, whole(&lfo(number, "fade_in"))).with_shown_label(&shown_label(labels::MSG_LFO_FADE_IN_LABEL)));
            }
            fields.extend([chosen(
                ids.at(Write::Item("lfos", number, "restart")),
                &numbered(labels::MSG_LFO_RESTART_LABEL),
                LFO_RESTARTS,
                &names_in(labels::MSG_LFO_RESTART_NAMES, LFO_RESTARTS),
                &text(&lfo(number, "restart")),
            )
            .with_shown_label(&shown_label(labels::MSG_LFO_RESTART_LABEL))]);
            // The switch stands last, under the settings it turns on; each LFO starts on.
            fields.push(
                Field::toggle(
                    ids.at(Write::Item("lfos", number, "on")),
                    &numbered(labels::MSG_LFO_ON_LABEL),
                    flag(&lfo(number, "on")),
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_ON_LABEL)),
            );
            let mut column = TabColumn::new(Some(&numbered(labels::MSG_LFO_LABEL)), fields);
            column.boxed = true;
            columns.push(column);
        }
        let mut tab = Tab::new(labels::MSG_LFOS_TAB, columns);
        tab.not_ready = not_ready;
        tab
    }

    fn filter_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let top = vec![Self::type_field(sound, "filter", ids)];
        let mut tab = Tab::new(labels::MSG_FILTER_TAB, vec![TabColumn::new(None, Self::setting_fields(sound, "filter", ids))]);
        tab.top = top;
        tab.not_ready = not_ready;
        tab
    }

    /// The instrument's Volume, a gauge dimming everything it plays, after its effects.
    fn volume_field(sound: &Sound, ids: &mut Ids) -> Field {
        gauge(
            ids.at(Write::Sound("volume")),
            labels::MSG_VOLUME_LABEL,
            whole(&sound.value("volume")),
            (0, MAX_VOLUME_PERCENT),
            GM_CELLS,
            marks::MSG_SOUND_PERCENT_SHOWN,
            (false, 1),
        )
    }

    /// The Amp tab: its type, then the instrument's Volume, then the Amp's own settings.
    fn amp_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let top = vec![Self::type_field(sound, "amp", ids)];
        let mut fields = vec![Self::volume_field(sound, ids)];
        fields.extend(Self::setting_fields(sound, "amp", ids));
        let mut tab = Tab::new(labels::MSG_AMP_TAB, vec![TabColumn::new(None, fields)]);
        tab.top = top;
        tab.not_ready = not_ready;
        tab
    }

    /// One of Bax's shelves: a gauge of decibels from a cut of 15 to a lift of 15, halfway at 0 dB, which Bksp brings back,
    /// as wide as the FX blocks' other gauges so that two blocks fit side by side.
    fn shelf_field(id: usize, label: &str, decibels: i64) -> Field {
        let shown = |decibels: i64| {
            let template = if decibels > 0 { marks::MSG_LIFT_DB_SHOWN } else { marks::MSG_DB_SHOWN };
            named(template, &[("number", decibels.into())])
        };
        let share = (decibels + MOST_BAX_DECIBELS) as f64 / (2 * MOST_BAX_DECIBELS) as f64;
        let bar = gauge_bar(share, BLOCK_CELLS);
        let value = named(
            marks::MSG_SOUND_GAUGE,
            &[("gauge", bar.as_str().into()), ("value", shown(decibels).as_str().into())],
        );
        Field::number(id, label, Some(decibels), Some(-MOST_BAX_DECIBELS), Some(MOST_BAX_DECIBELS), 0, Some(value)).with_clear(&shown(0))
    }

    /// A MultiTap's fields after its effect: Sync, a row for each tap of its time and level, then Feedback and Tone.
    fn multitap_fields(sound: &Sound, number: usize, ids: &mut Ids) -> Vec<Field> {
        let effect = |name: &str| sound.effect_setting(number, name);
        let numbered = |label: &str| named(label, &[("number", number.into())]);
        let shown_label = |label: &str| named_in(labels::MSG_EFFECT_SHOWN_LABELS, label);
        let synced = flag_or_on(&effect("sync"));
        let analog = text(&effect("mode")) == ANALOG;
        let mut fields = vec![
            chosen(
                ids.at(Write::Item("effects", number, "mode")),
                &numbered(labels::MSG_EFFECT_MODE_LABEL),
                &DELAY_MODES,
                &names_in(labels::MSG_DELAY_MODE_NAMES, &DELAY_MODES),
                &text(&effect("mode")),
            )
            .with_shown_label(&shown_label(labels::MSG_EFFECT_MODE_LABEL)),
            Field::toggle(ids.at(Write::Item("effects", number, "sync")), &numbered(labels::MSG_EFFECT_SYNC_LABEL), synced)
                .with_shown_label(&shown_label(labels::MSG_EFFECT_SYNC_LABEL)),
        ];
        // The analog device's one clock always glides, so it has no choice of how a time changes.
        if !analog {
            fields.push(
                chosen(
                    ids.at(Write::Item("effects", number, "time_change")),
                    &numbered(labels::MSG_EFFECT_TIME_CHANGE_LABEL),
                    &TIME_CHANGES,
                    &names_in(labels::MSG_TIME_CHANGE_NAMES, &TIME_CHANGES),
                    &text(&effect("time_change")),
                )
                .with_shown_label(&shown_label(labels::MSG_EFFECT_TIME_CHANGE_LABEL)),
            );
        }
        for (tap, names) in TAP_SETTINGS.iter().enumerate() {
            let tapped = |label: &str| named(label, &[("number", number.into()), ("tap", (tap + 1).into())]);
            let (on, division, ms, level) = *names;
            let switch = Field::toggle(
                ids.at(Write::Item("effects", number, on)),
                &tapped(labels::MSG_EFFECT_TAP_ON_LABEL),
                flag_or_on(&effect(on)),
            );
            let time = if synced {
                let divisions: Vec<&str> = DELAY_DIVISIONS.iter().map(|(name, _)| *name).collect();
                chosen(
                    ids.at(Write::Item("effects", number, division)),
                    &tapped(labels::MSG_EFFECT_TAP_TIME_LABEL),
                    &divisions,
                    &names_in(labels::MSG_DELAY_DIVISION_NAMES, &divisions),
                    &text(&effect(division)),
                )
            } else {
                let milliseconds = whole(&effect(ms));
                let shown = named(marks::MSG_MILLISECONDS_SHOWN, &[("number", milliseconds.into())]);
                Field::number(
                    ids.at_gauge(Write::Item("effects", number, ms), TIME_STRIDES),
                    &tapped(labels::MSG_EFFECT_TAP_TIME_LABEL),
                    Some(milliseconds),
                    Some(1),
                    Some(MAX_TAP_MS),
                    1,
                    Some(shown),
                )
            };
            let percent = whole(&effect(level));
            let bar = gauge_bar(percent as f64 / MAX_PERCENT as f64, TAP_LEVEL_CELLS);
            let value = named(marks::MSG_SOUND_PERCENT_SHOWN, &[("number", percent.into())]);
            let shown = named(marks::MSG_NARROW_GAUGE, &[("gauge", bar.as_str().into()), ("value", value.as_str().into())]);
            let loudness = Field::number(
                ids.at(Write::Item("effects", number, level)),
                &tapped(labels::MSG_EFFECT_TAP_LEVEL_LABEL),
                Some(percent),
                Some(0),
                Some(MAX_PERCENT),
                0,
                Some(shown),
            );
            let time = time.padded_to(if synced { DIVISION_WIDTH } else { TAP_MS_WIDTH });
            let row_label = named(labels::MSG_TAP_SHOWN_LABEL, &[("tap", (tap + 1).into())]);
            fields.push(
                Field::cells(ids.next(), &tapped(labels::MSG_EFFECT_TAP_LABEL), vec![switch, time, loudness])
                    .stepped()
                    .with_shown_label(&row_label),
            );
        }
        fields.push(
            chosen(
                ids.at(Write::Item("effects", number, "feedback_from")),
                &numbered(labels::MSG_EFFECT_FEEDBACK_FROM_LABEL),
                &FEEDBACK_FROM_TAPS,
                &names_in(labels::MSG_FEEDBACK_FROM_NAMES, &FEEDBACK_FROM_TAPS),
                &text(&effect("feedback_from")),
            )
            .with_shown_label(&shown_label(labels::MSG_EFFECT_FEEDBACK_FROM_LABEL)),
        );
        fields.push(
            gauge(
                ids.at(Write::Item("effects", number, "feedback")),
                &numbered(labels::MSG_EFFECT_FEEDBACK_LABEL),
                whole(&effect("feedback")),
                (0, MAX_TAP_FEEDBACK),
                BLOCK_CELLS,
                marks::MSG_SOUND_PERCENT_SHOWN,
                (false, 1),
            )
            .with_shown_label(&shown_label(labels::MSG_EFFECT_FEEDBACK_LABEL)),
        );
        fields.push(
            gauge(
                ids.at_gauge(Write::Item("effects", number, "tone"), HERTZ_STRIDES),
                &numbered(labels::MSG_EFFECT_TONE_LABEL),
                whole(&effect("tone")),
                (MIN_TAP_TONE, MAX_TAP_TONE),
                BLOCK_CELLS,
                marks::MSG_HERTZ_SHOWN,
                (true, 1),
            )
            .with_shown_label(&shown_label(labels::MSG_EFFECT_TONE_LABEL)),
        );
        fields.push(
            gauge(
                ids.at_gauge(Write::Item("effects", number, "low_cut"), HERTZ_STRIDES),
                &numbered(labels::MSG_EFFECT_LOW_CUT_LABEL),
                whole(&effect("low_cut")),
                (MIN_TAP_LOW_CUT, MAX_TAP_LOW_CUT),
                BLOCK_CELLS,
                marks::MSG_HERTZ_SHOWN,
                (true, 1),
            )
            .with_shown_label(&shown_label(labels::MSG_EFFECT_LOW_CUT_LABEL)),
        );
        if analog {
            for (name, label) in ANALOG_SETTINGS {
                fields.push(
                    gauge(
                        ids.at(Write::Item("effects", number, name)),
                        &numbered(label),
                        whole(&effect(name)),
                        (0, MAX_PERCENT),
                        BLOCK_CELLS,
                        marks::MSG_SOUND_PERCENT_SHOWN,
                        (false, 1),
                    )
                    .with_shown_label(&shown_label(label)),
                );
            }
        }
        fields
    }

    fn effects_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let effect = |number: usize, name: &str| sound.effect_setting(number, name);
        let shown_label = |label: &str| named_in(labels::MSG_EFFECT_SHOWN_LABELS, label);
        let mut columns = Vec::new();
        for number in 1..=EFFECT_BLOCKS as usize {
            let numbered = |label: &str| named(label, &[("number", number.into())]);
            let chosen_effect = text(&effect(number, "effect"));
            let mut fields = vec![chosen(
                ids.at(Write::Item("effects", number, "effect")),
                &numbered(labels::MSG_EFFECT_BLOCK_LABEL),
                EFFECTS,
                &names_in(labels::MSG_EFFECT_NAMES, EFFECTS),
                &chosen_effect,
            )];
            if chosen_effect != NONE_EFFECT {
                if chosen_effect == MULTITAP {
                    fields.extend(Self::multitap_fields(sound, number, ids));
                } else if chosen_effect == BAX {
                    for (name, label) in [("bass", labels::MSG_EFFECT_BASS_LABEL), ("treble", labels::MSG_EFFECT_TREBLE_LABEL)] {
                        fields.push(
                            Self::shelf_field(ids.at(Write::Item("effects", number, name)), &numbered(label), whole(&effect(number, name)))
                                .with_shown_label(&shown_label(label)),
                        );
                    }
                } else if chosen_effect == BITCRUSH {
                    let bits = whole(&effect(number, "bits"));
                    fields.push(
                        Field::number(
                            ids.at(Write::Item("effects", number, "bits")),
                            &numbered(labels::MSG_EFFECT_BITS_LABEL),
                            Some(bits),
                            Some(MIN_BITS),
                            Some(MAX_BITS),
                            MIN_BITS,
                            None,
                        )
                        .with_shown_label(&shown_label(labels::MSG_EFFECT_BITS_LABEL)),
                    );
                    fields.push(
                        Field::toggle(
                            ids.at(Write::Item("effects", number, "dither")),
                            &numbered(labels::MSG_EFFECT_DITHER_LABEL),
                            flag(&effect(number, "dither")),
                        )
                        .with_shown_label(&shown_label(labels::MSG_EFFECT_DITHER_LABEL)),
                    );
                    let rate = whole(&effect(number, "rate"));
                    let rates: Vec<String> = CRUSH_RATES.iter().map(|rate| rate.to_string()).collect();
                    let rate_names: Vec<String> = CRUSH_RATES.iter().map(|rate| rate_shown(*rate)).collect();
                    let rate_choices: Vec<&str> = rates.iter().map(String::as_str).collect();
                    fields.push(
                        chosen(
                            ids.at(Write::Item("effects", number, "rate")),
                            &numbered(labels::MSG_EFFECT_RATE_LABEL),
                            &rate_choices,
                            &rate_names,
                            &rate.to_string(),
                        )
                        .with_shown_label(&shown_label(labels::MSG_EFFECT_RATE_LABEL)),
                    );
                } else {
                    let curve = text(&effect(number, "curve"));
                    let curve = if CURVES.contains(&curve.as_str()) { curve } else { CURVES[0].to_string() };
                    fields.push(
                        chosen(
                            ids.at(Write::Item("effects", number, "curve")),
                            &numbered(labels::MSG_EFFECT_CURVE_LABEL),
                            CURVES,
                            &names_in(labels::MSG_CURVE_NAMES, CURVES),
                            &curve,
                        )
                        .with_shown_label(&shown_label(labels::MSG_EFFECT_CURVE_LABEL)),
                    );
                    fields.push(
                        gauge(
                            ids.at(Write::Item("effects", number, "amount")),
                            &numbered(labels::MSG_EFFECT_AMOUNT_LABEL),
                            whole(&effect(number, "amount")),
                            (0, MAX_PERCENT),
                            BLOCK_CELLS,
                            marks::MSG_SOUND_PERCENT_SHOWN,
                            (false, 1),
                        )
                        .with_shown_label(&shown_label(labels::MSG_EFFECT_AMOUNT_LABEL)),
                    );
                }
                fields.push(
                    gauge(
                        ids.at(Write::Item("effects", number, "mix")),
                        &numbered(labels::MSG_EFFECT_MIX_LABEL),
                        whole(&effect(number, "mix")),
                        (0, MAX_PERCENT),
                        BLOCK_CELLS,
                        marks::MSG_SOUND_PERCENT_SHOWN,
                        (false, 1),
                    )
                    .with_shown_label(&shown_label(labels::MSG_EFFECT_MIX_LABEL)),
                );
            }
            let mut column = TabColumn::new(None, fields);
            column.boxed = true;
            columns.push(column);
        }
        let mut tab = Tab::new(labels::MSG_FX_TAB, columns);
        tab.not_ready = not_ready;
        tab
    }

    /// A Mod Matrix slot's Source or Via: the usual sources, then MIDI CC, whose number is set in the CC field beside it.
    /// An engine of one oscillator offers it as Osc 1, and Asheville each of its three by number; Per Note S&H, held for the
    /// whole note, is a source and never a Via.
    fn source_field(id: usize, label: &str, current: &str, asheville: bool, via: bool) -> Field {
        let sources: Vec<&str> = MATRIX_SOURCES
            .iter()
            .copied()
            .filter(|source| {
                if asheville {
                    *source != ONE_OSCILLATOR_SOURCE
                } else {
                    !ASHEVILLE_SOURCES.contains(source)
                }
            })
            .filter(|source| !via || !SOURCES_ONLY.contains(source))
            .collect();
        let mut choices: Vec<&str> = sources.clone();
        let mut names = names_in(labels::MSG_MATRIX_SOURCE_NAMES, &sources);
        choices.push(if control_number(current).is_some() { current } else { MIDI_CC_CHOICE });
        names.push(labels::MSG_MIDI_CC_CHOICE.to_string());
        chosen(id, label, &choices, &names, current)
    }

    /// The CC field beside a slot's Source or Via: the CC's number, typed or stepped from 0 to 127, where it reads a MIDI
    /// CC, or a dash where it reads anything else.
    fn control_beside(of: usize, id: usize, label: &str, current: &str) -> Beside {
        let field = control_number(current).map(|number| {
            let mut field = Field::number(id, label, Some(number), Some(0), Some(HIGHEST_CC), DEFAULT_CC, None);
            field.title = Some(messages::MSG_MIDI_CC_TITLE.to_string());
            field
        });
        Beside {
            of,
            label: labels::MSG_SLOT_CC_SHOWN_LABEL.to_string(),
            field,
        }
    }

    /// A Mod Matrix amount as the range it moves its destination over: from minus it to plus it for a Bipolar route of a
    /// source that swings both ways, else from nothing to it.
    fn amount_range(amount: i64, source: &str, polarity: &str) -> String {
        let both_ways = polarity != UNIPOLAR && BIPOLAR_SOURCES.contains(&source);
        let low = if both_ways { -amount } else { 0 };
        named(marks::MSG_PERCENT_RANGE_SHOWN, &[("low", low.into()), ("high", amount.into())])
    }

    fn matrix_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let slot = |number: usize, name: &str| sound.item("matrix", number, name, SLOT_DEFAULTS);
        let shown_label = |label: &str| named_in(labels::MSG_SLOT_SHOWN_LABELS, label);
        let asheville = sound.part_type("oscillators") == ASHEVILLE;
        let mut columns = Vec::new();
        for number in 1..=MATRIX_SLOTS as usize {
            let numbered = |label: &str| named(label, &[("number", number.into())]);
            let amount = whole(&slot(number, "amount"));
            let fields = vec![
                Self::source_field(
                    ids.at(Write::Item("matrix", number, "source")),
                    &numbered(labels::MSG_SLOT_SOURCE_LABEL),
                    &text(&slot(number, "source")),
                    asheville,
                    false,
                )
                .with_shown_label(&shown_label(labels::MSG_SLOT_SOURCE_LABEL)),
                Self::source_field(
                    ids.at(Write::Item("matrix", number, "via")),
                    &numbered(labels::MSG_SLOT_VIA_LABEL),
                    &text(&slot(number, "via")),
                    asheville,
                    true,
                )
                .with_shown_label(&shown_label(labels::MSG_SLOT_VIA_LABEL)),
                chosen(
                    ids.at(Write::Item("matrix", number, "destination")),
                    &numbered(labels::MSG_SLOT_DESTINATION_LABEL),
                    MATRIX_DESTINATIONS,
                    &names_in(labels::MSG_MATRIX_DESTINATION_NAMES, MATRIX_DESTINATIONS),
                    &text(&slot(number, "destination")),
                )
                .with_shown_label(&shown_label(labels::MSG_SLOT_DESTINATION_LABEL)),
                chosen(
                    ids.at(Write::Item("matrix", number, "polarity")),
                    &numbered(labels::MSG_SLOT_POLARITY_LABEL),
                    MATRIX_POLARITIES,
                    &names_in(labels::MSG_POLARITY_NAMES, MATRIX_POLARITIES),
                    &text(&slot(number, "polarity")),
                )
                .with_shown_label(&shown_label(labels::MSG_SLOT_POLARITY_LABEL)),
                bounded_gauge(
                    ids.at(Write::Item("matrix", number, "amount")),
                    &numbered(labels::MSG_SLOT_AMOUNT_LABEL),
                    amount,
                    (-MAX_MATRIX_AMOUNT, MAX_MATRIX_AMOUNT),
                    &Self::amount_range(amount, &text(&slot(number, "source")), &text(&slot(number, "polarity"))),
                )
                .with_shown_label(&shown_label(labels::MSG_SLOT_AMOUNT_LABEL)),
            ];
            let (source_place, via_place) = (0, 1);
            let mut column = TabColumn::new(Some(&numbered(labels::MSG_SLOT_HEADING)), fields);
            column.beside = vec![
                Self::control_beside(
                    source_place,
                    ids.at(Write::Item("matrix", number, "source_cc")),
                    &numbered(labels::MSG_SLOT_SOURCE_CC_LABEL),
                    &text(&slot(number, "source")),
                ),
                Self::control_beside(
                    via_place,
                    ids.at(Write::Item("matrix", number, "via_cc")),
                    &numbered(labels::MSG_SLOT_VIA_CC_LABEL),
                    &text(&slot(number, "via")),
                ),
            ];
            column.boxed = true;
            columns.push(column);
        }
        let mut tab = Tab::new(labels::MSG_MATRIX_TAB, columns);
        tab.not_ready = not_ready;
        tab
    }
}

fn part_label(part: &str, setting: &str) -> String {
    named(
        labels::MSG_PART_SETTING_LABEL,
        &[("part", named_in(labels::MSG_PART_NAMES, part).as_str().into()), ("setting", setting.into())],
    )
}

fn rate_shown(rate: i64) -> String {
    if rate == 0 {
        marks::MSG_RATE_OFF_SHOWN.to_string()
    } else {
        named(marks::MSG_HERTZ_SHOWN, &[("number", rate.into())])
    }
}

impl Form for InstrumentEditor {
    /// ENTER on the Name field and F2 ask for a new name, refusing an empty one or one already taken.
    fn rename(&self, app: &mut App) -> Option<()> {
        crate::screens::rename::ask_rename(app, Section::INSTRUMENTS, &self.name, messages::MSG_RENAME_INSTRUMENT_PROMPT);
        Some(())
    }
    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        let section = llamatron_model::schema::generated::file_format::Section::INSTRUMENTS;
        crate::page::follow_name(&mut self.name, section, renames);
    }

    fn still_exists(&self, app: &App) -> bool {
        crate::page::named_exists(app, llamatron_model::schema::generated::file_format::Section::INSTRUMENTS, &self.name)
    }

    fn name(&self) -> &'static str {
        "InstrumentEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::INSTRUMENTS.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
        ]
    }

    fn caption(&self, _app: &App) -> Option<String> {
        let what = named_in(labels::MSG_CAPTION_WORDS, Section::INSTRUMENTS).to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.name.as_str().into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::INSTRUMENTS)
    }

    fn form(&self, app: &App) -> Vec<Node> {
        self.built(app).0
    }

    fn page_keys(&self, app: &App, _row: Option<&Field>) -> Vec<KeyItem> {
        let listening = if self.is_listening(app) { &Keys::STOP_LISTENING } else { &Keys::LISTEN };
        vec![KeyItem::of(&Keys::CLASS, &Keys::KEYSWITCH_MAP), KeyItem::of(&Keys::CLASS, listening)]
    }

    fn press_own(&mut self, app: &mut App, item: &KeyItem, _key: &str, _row: Option<&Field>) {
        if item.is(&Keys::KEYSWITCH_MAP) {
            self.open_keyswitch_map(app);
        } else if item.is(&Keys::LISTEN) || item.is(&Keys::STOP_LISTENING) {
            self.listen_or_stop(app);
        }
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        let Some(instrument) = self.instrument(app) else { return };
        let label_of = |nodes: &[Node]| {
            nodes.iter().find_map(|node| match node {
                Node::Field(field) if field.id == id && field.is_button() => Some(field.label.trim().to_string()),
                _ => None,
            })
        };
        if matches!(edit, Edit::Enter) {
            let label = label_of(&self.built(app).0);
            match label.as_deref() {
                Some(labels::MSG_KEYSWITCH_MAP_LABEL) => return self.open_keyswitch_map(app),
                Some(labels::MSG_PREVIEW_PATTERN_LABEL) => return self.open_preview(app),
                Some(labels::MSG_LISTEN_LABEL) | Some(labels::MSG_STOP_LISTENING_LABEL) => return self.listen_or_stop(app),
                _ => {}
            }
        }
        let sound = Sound::of(instrument);
        let (nodes, ids) = self.built(app);
        let Some((_, write, strides)) = ids.writes.iter().find(|(found, ..)| *found == id).copied() else {
            return;
        };
        let field = nodes.iter().find_map(|node| match node {
            Node::Field(field) => field.find(id).cloned(),
            Node::TabBox(tab_box) => tab_box
                .tabs
                .iter()
                .find_map(|tab| tab.every_field().into_iter().find_map(|field| field.find(id).cloned())),
        });
        // A gauge steps by a stride that grows with it, where [ and ] step a number.
        let edit = match (edit, field.as_ref().map(|field| &field.kind)) {
            (
                Edit::Number(number),
                Some(FieldKind::Number {
                    number: Some(current),
                    lowest,
                    highest,
                    ..
                }),
            ) if strides != STEPS_OF_ONE => {
                let step = stride(strides, *current) * (number - current).signum();
                Edit::Number(crate::forms::nodes::within(current + step, *lowest, *highest))
            }
            (edit, _) => edit,
        };
        if write == Write::GmSound && matches!(edit, Edit::Enter | Edit::Choice(_)) {
            self.choose_gm_sound(app, edit);
            return;
        }
        if write == Write::Setting(InstrumentSetting::DEVICE) {
            self.choose_device(app, edit);
            return;
        }
        if let Write::Part(part, ARPEGGIO) = write {
            self.edit_arpeggio(app, &sound, part, edit);
            return;
        }
        // MIDI CC in a slot's Source or Via reads the CC its CC field beside names, 74 at first, stored as `cc74`.
        let controlled = match (write, &edit) {
            (Write::Item("matrix", number, name @ ("source" | "via")), Edit::Choice(chosen)) if chosen == MIDI_CC_CHOICE => Some((number, name, DEFAULT_CC)),
            (Write::Item("matrix", number, "source_cc"), Edit::Number(control)) => Some((number, "source", *control)),
            (Write::Item("matrix", number, "via_cc"), Edit::Number(control)) => Some((number, "via", *control)),
            (Write::Item("matrix", number, "source_cc"), Edit::Clear) => Some((number, "source", DEFAULT_CC)),
            (Write::Item("matrix", number, "via_cc"), Edit::Clear) => Some((number, "via", DEFAULT_CC)),
            _ => None,
        };
        if let Some((number, name, control)) = controlled {
            let value = Data::text(&format!("{CONTROL_PREFIX}{}", control.clamp(0, HIGHEST_CC)));
            let name_of = self.name.clone();
            let changed = sound.with_item("matrix", number, name, value);
            app.document.change_set(|setlist| {
                if let Some(Item::Instrument(instrument)) = setlist.get_item_mut(Section::INSTRUMENTS, &name_of) {
                    instrument.set_written(InstrumentSetting::SOUND, Some(changed));
                }
            });
            return;
        }
        let value = match edit {
            Edit::Number(number) => Some(Data::Whole(number as i128)),
            Edit::Toggle(on) => Some(Data::Bool(on)),
            Edit::Choice(chosen) => Some(Data::text(&chosen)),
            Edit::Clear => None,
            Edit::Adjust(offset) if write == Write::GmSound => {
                let sound = instrument
                    .get_written(InstrumentSetting::GM_SOUND)
                    .and_then(Data::as_whole)
                    .map_or(0, |whole| whole as i64)
                    + offset;
                (sound > 0).then_some(Data::Whole(sound.min(MAX_GM_SOUND) as i128))
            }
            _ => return,
        };
        let name = self.name.clone();
        let set = |app: &mut App, setting: &str, value: Option<Data>| {
            app.document.change_set(|setlist| {
                if let Some(Item::Instrument(instrument)) = setlist.get_item_mut(Section::INSTRUMENTS, &name) {
                    instrument.set_written(setting, value);
                }
            });
        };
        let sound_value = |value: Option<Data>| value.unwrap_or(Data::Null);
        match write {
            Write::Setting(setting) if setting == InstrumentSetting::KEYSWITCH_LEAD => set(app, setting, value.filter(|value| value.as_whole() != Some(0))),
            Write::Setting(setting) => set(app, setting, value),
            Write::EngineOf => {
                let engine = value.as_ref().and_then(Data::as_str).unwrap_or(MIDI).to_string();
                let device = instrument.get_written(InstrumentSetting::DEVICE).and_then(Data::as_str).map(str::to_string);
                self.choose_engine(app, device, &engine);
            }
            Write::Percussion => {
                let on = value.as_ref().is_some_and(|value| *value == Data::Bool(true));
                self.change_percussion(app, &sound, on);
            }
            Write::GmSound => set(app, InstrumentSetting::GM_SOUND, value),
            Write::Sound(name) => set(app, InstrumentSetting::SOUND, Some(sound.with_value(name, sound_value(value)))),
            Write::PartType(part) => {
                let kind = value.as_ref().and_then(Data::as_str).unwrap_or("").to_string();
                set(app, InstrumentSetting::SOUND, Some(sound.with_part_type(part, &kind)));
            }
            Write::Part(part, name) => set(app, InstrumentSetting::SOUND, Some(sound.with_part_value(part, name, sound_value(value)))),
            Write::Oscillator(number, name) => set(app, InstrumentSetting::SOUND, Some(sound.with_oscillator(number, name, sound_value(value)))),
            Write::Knob(place) => set(app, InstrumentSetting::SOUND, Some(sound.with_knob(place, sound_value(value)))),
            Write::Item("effects", number, "mode") if value.as_ref().and_then(Data::as_str) == Some(ANALOG) => {
                set(
                    app,
                    InstrumentSetting::SOUND,
                    Some(sound.with_item_values("effects", number, &analog_starting_point())),
                );
            }
            Write::Item(list, number, name) => {
                // An effect's rate is a number of hertz, chosen as its text.
                let value = match (name, value) {
                    ("rate", Some(Data::Text(text))) if list == "effects" => text.parse::<i128>().ok().map(Data::Whole),
                    (_, value) => value,
                };
                set(app, InstrumentSetting::SOUND, Some(sound.with_item(list, number, name, sound_value(value))));
            }
        }
    }
}

/// General MIDI's families for the sound picker, each its name with its sounds, each labelled by its number and name.
fn sound_families() -> Vec<(String, Vec<(String, usize)>)> {
    use llamatron_model::schema::generated::limits::GM_FAMILY_SIZE;
    labels::MSG_GM_FAMILIES
        .iter()
        .enumerate()
        .map(|(place, family)| {
            let first = place as i64 * GM_FAMILY_SIZE + MIN_GM_SOUND;
            let sounds = (first..first + GM_FAMILY_SIZE)
                .map(|sound| {
                    let name = labels::MSG_GM_SOUNDS.get((sound - MIN_GM_SOUND) as usize).copied().unwrap_or("");
                    (
                        named(labels::MSG_GM_SOUND_SHOWN, &[("number", sound.into()), ("name", name.into())]),
                        sound as usize,
                    )
                })
                .collect();
            (family.to_string(), sounds)
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A built-in instrument on a ladder filter at a cutoff in hertz.
    fn ladder_at(cutoff: i64) -> Instrument {
        let text = format!("{{ name: lead, kind: built_in, role: normal, sound: {{ engine: basic, filter: {{ type: ladder, cutoff: {cutoff} }} }} }}");
        let data = llamatron_model::file::data::load(&text).expect("the scenario's instrument is YAML");
        Instrument::from_data(&data).expect("the scenario's instrument is valid")
    }

    /// The cutoff is a frequency, so its field shows hertz, never a percent.
    #[test]
    fn a_filter_cutoff_shows_in_hertz() {
        let cutoff = 1200;
        let sound = Sound::of(&ladder_at(cutoff));
        let mut ids = Ids { last: 0, writes: Vec::new() };
        let field = InstrumentEditor::setting_field(&sound, "filter", "ladder", "cutoff", &mut ids);
        let hertz = named(marks::MSG_HERTZ_SHOWN, &[("number", cutoff.into())]);
        assert!(field.value().ends_with(&hertz), "{}", field.value());
    }

    /// A slot reading a MIDI CC shows MIDI CC, with its number in the CC field beside; any other source has a dash there.
    #[test]
    fn a_midi_cc_source_shows_its_number_beside() {
        let control = 74;
        let source = format!("{CONTROL_PREFIX}{control}");
        let field = InstrumentEditor::source_field(1, labels::MSG_SLOT_SOURCE_LABEL, &source, false, false);
        assert_eq!(field.value(), labels::MSG_MIDI_CC_CHOICE);
        let beside = InstrumentEditor::control_beside(0, 2, labels::MSG_SLOT_SOURCE_CC_LABEL, &source);
        assert_eq!(beside.field.map(|field| field.value().to_string()), Some(control.to_string()));
        let other = InstrumentEditor::control_beside(0, 2, labels::MSG_SLOT_SOURCE_CC_LABEL, "lfo1");
        assert!(other.field.is_none(), "no CC field beside an LFO");
    }

    /// The Filter field, a note's own or one shared, shows only on an instrument of more than one voice.
    #[test]
    fn the_filter_sharing_shows_only_with_more_than_one_voice() {
        let shows = |voices: i64| {
            let text = format!("{{ name: synth, kind: built_in, role: normal, sound: {{ engine: basic, voices: {voices} }} }}");
            let data = llamatron_model::file::data::load(&text).expect("the scenario's instrument is YAML");
            let instrument = Instrument::from_data(&data).expect("the scenario's instrument is valid");
            let sound = Sound::of(&instrument);
            let mut ids = Ids { last: 0, writes: Vec::new() };
            InstrumentEditor::voice_fields(&sound, &mut ids)
                .iter()
                .any(|field| field.label == labels::MSG_FILTER_SHARING_LABEL)
        };
        let (one, several) = (1, 4);
        assert!(!shows(one));
        assert!(shows(several));
    }

    /// MultiTap shows Sync, a row of time and level for each of its four taps, then Feedback, Tone and its own Mix of 35%;
    /// a falling figure untouched, the taps on 1/8, 1/4, 1/4d and 1/2. With Sync off each tap's time is in milliseconds.
    #[test]
    fn multitap_shows_its_taps_as_rows_of_switch_time_and_level() {
        let fields_of = |effect: &str| {
            let text = format!("{{ name: synth, kind: built_in, role: normal, sound: {{ engine: basic, effects: [{effect}] }} }}");
            let data = llamatron_model::file::data::load(&text).expect("the scenario's instrument is YAML");
            let instrument = Instrument::from_data(&data).expect("the scenario's instrument is valid");
            let mut ids = Ids { last: 0, writes: Vec::new() };
            InstrumentEditor::effects_tab(&Sound::of(&instrument), false, &mut ids).columns[0]
                .fields
                .clone()
        };
        let synced = fields_of("{ effect: multitap }");
        let numbered = |label: &str| named(label, &[("number", 1.into())]);
        let tapped = |label: &str, tap: usize| named(label, &[("number", 1.into()), ("tap", tap.into())]);
        let taps: Vec<&Field> = synced.iter().filter(|field| field.is_cells()).collect();
        assert_eq!(taps.len(), 4);
        let times: Vec<String> = taps.iter().map(|tap| tap.cells[1].value().trim_end().to_string()).collect();
        assert_eq!(times, ["1/8", "1/4", "1/4d", "1/2"]);
        assert!(taps.iter().all(|tap| tap.cells[0].is_toggle() && tap.cells[0].value() == marks::MSG_TOGGLE_ON));
        assert!(taps[0].cells[2]
            .value()
            .ends_with(&named(marks::MSG_SOUND_PERCENT_SHOWN, &[("number", 70.into())])));
        assert_eq!(taps[0].label, tapped(labels::MSG_EFFECT_TAP_LABEL, 1));
        let mix = synced.last().expect("a Mix last");
        assert_eq!(mix.label, numbered(labels::MSG_EFFECT_MIX_LABEL));
        assert!(
            mix.value().ends_with(&named(marks::MSG_SOUND_PERCENT_SHOWN, &[("number", 35.into())])),
            "{}",
            mix.value()
        );
        let free = fields_of("{ effect: multitap, sync: false }");
        let first = free.iter().find(|field| field.is_cells()).expect("a tap row");
        assert_eq!(
            first.cells[1].value().trim_end(),
            named(marks::MSG_MILLISECONDS_SHOWN, &[("number", 250.into())])
        );
        let second_off = fields_of("{ effect: multitap, tap2_on: false }");
        let switches: Vec<bool> = second_off
            .iter()
            .filter(|field| field.is_cells())
            .map(|tap| tap.cells[0].value() == marks::MSG_TOGGLE_ON)
            .collect();
        assert_eq!(switches, [true, false, true, true]);
    }

    /// A set of one song with an instrument of the YAML given, called fish, and a track called bass playing it or not.
    fn engine_app(instrument: &str, played: bool) -> App {
        let track = if played { "{ name: bass, instrument: fish }" } else { "{ name: bass }" };
        let text = format!(
            "scales:\n  - {{ name: C Major, root: C, type: major }}\ninstruments:\n  - {instrument}\nsongs:\n  - name: song\n    scale: C Major\n    tracks: [{track}]\n    scenes: [{{ name: one }}]\n"
        );
        let setlist = llamatron_model::objects::setlist::Setlist::read_text(&text).expect("the scenario's set is valid");
        App::new(crate::document::Document::new(setlist, None))
    }

    /// The tabs of the Instrument page of fish, by their labels, and the Engine tab's fields under its Engine and Percussion.
    fn engine_tabs(app: &App) -> (Vec<String>, Vec<Field>) {
        let editor = InstrumentEditor { name: "fish".to_string() };
        let (nodes, _) = editor.built(app);
        let tabs = nodes
            .iter()
            .find_map(|node| match node {
                Node::TabBox(tab_box) => Some(tab_box.tabs.clone()),
                _ => None,
            })
            .expect("a tab box");
        let labels_shown = tabs.iter().map(|tab| tab.label.clone()).collect();
        (labels_shown, tabs[0].columns[0].fields.clone())
    }

    fn labels_of(fields: &[Field]) -> Vec<&str> {
        fields.iter().map(|field| field.label.as_str()).collect()
    }

    /// The Engine tab shows what the engine chosen plays by, and only LlamaSynth has the synth's tabs after it: a
    /// FluidSynth instrument its GM sound, Pan in the middle and an automatic channel, a percussion one the drums' channel
    /// and no GM sound; an outside device its Device, Channel, keyswitch lead and latency; LlamaSynth its Voice settings.
    #[test]
    fn the_engine_tab_shows_its_engines_own_fields() {
        let fluid = engine_app("{ name: fish, device: \"*FluidSynth\", gm_sound: 1 }", false);
        let (tabs, fields) = engine_tabs(&fluid);
        assert_eq!(tabs, [labels::MSG_ENGINE_TAB]);
        assert_eq!(
            labels_of(&fields),
            [labels::MSG_GM_SOUND_LABEL, labels::MSG_PAN_LABEL, labels::MSG_CHANNEL_LABEL]
        );
        let center = named(marks::MSG_PAN_CENTER_SHOWN, &[("number", DEFAULT_PAN.into())]);
        assert!(fields[1].value().ends_with(&center), "{}", fields[1].value());
        assert_eq!(fields[2].value(), marks::MSG_AUTO_CHANNEL_SHOWN);
        let drums = engine_app("{ name: fish, device: \"*FluidSynth\", role: percussion }", false);
        let (_, fields) = engine_tabs(&drums);
        assert_eq!(labels_of(&fields), [labels::MSG_PAN_LABEL, labels::MSG_CHANNEL_LABEL]);
        assert_eq!(fields[1].value(), marks::MSG_DRUM_CHANNEL_SHOWN);
        let outside = engine_app("{ name: fish, device: \"a synthesizer\", channel: 3 }", false);
        let (_, fields) = engine_tabs(&outside);
        let expected = [
            labels::MSG_DEVICE_LABEL,
            labels::MSG_CHANNEL_LABEL,
            labels::MSG_KEYSWITCH_LEAD_LABEL,
            labels::MSG_LATENCY_LABEL,
        ];
        assert_eq!(labels_of(&fields), expected);
        let synth = engine_app("{ name: fish, kind: built_in, role: normal, sound: { engine: asheville } }", false);
        let (tabs, fields) = engine_tabs(&synth);
        assert_eq!(tabs.first().map(String::as_str), Some(labels::MSG_ENGINE_TAB));
        assert!(tabs.iter().any(|tab| tab == labels::MSG_OSCILLATORS_TAB));
        assert!(labels_of(&fields).contains(&labels::MSG_VOICES_LABEL));
        let off = engine_app("{ name: fish, kind: \"off\" }", false);
        let (tabs, fields) = engine_tabs(&off);
        assert_eq!(tabs, [labels::MSG_ENGINE_TAB]);
        assert!(fields.is_empty());
    }

    /// The id of one of the editor's fields by what it writes.
    fn id_of(app: &App, write: Write) -> usize {
        let editor = InstrumentEditor { name: "fish".to_string() };
        editor
            .built(app)
            .1
            .writes
            .iter()
            .find(|(_, found, _)| *found == write)
            .map(|(id, ..)| *id)
            .expect("the field")
    }

    /// Choosing an engine sets the instrument's Kind and Device: FluidSynth its device, an outside device's port kept,
    /// LlamaSynth the built-in synths, Off nothing played.
    #[test]
    fn choosing_an_engine_sets_kind_and_device() {
        let mut app = engine_app("{ name: fish, device: \"a synthesizer\" }", false);
        let instrument_of = |app: &App| match app.document.get_setlist().get_item(Section::INSTRUMENTS, "fish") {
            Some(Item::Instrument(instrument)) => instrument.clone(),
            _ => panic!("the instrument"),
        };
        let mut editor = InstrumentEditor { name: "fish".to_string() };
        let engine = id_of(&app, Write::EngineOf);
        editor.apply(&mut app, engine, Edit::Choice(FLUIDSYNTH.to_string()));
        assert_eq!(InstrumentEditor::engine_of(&instrument_of(&app)), FLUIDSYNTH);
        editor.apply(&mut app, engine, Edit::Choice(LLAMASYNTH.to_string()));
        assert_eq!(InstrumentEditor::engine_of(&instrument_of(&app)), LLAMASYNTH);
        editor.apply(&mut app, engine, Edit::Choice(OFF.to_string()));
        assert_eq!(InstrumentEditor::engine_of(&instrument_of(&app)), OFF);
        editor.apply(&mut app, engine, Edit::Choice(MIDI.to_string()));
        let held = instrument_of(&app);
        assert_eq!(InstrumentEditor::engine_of(&held), MIDI);
        // Leaving FluidSynth for an outside device leaves no device chosen, rather than FluidSynth's.
        assert_eq!(held.get_written(InstrumentSetting::DEVICE).and_then(Data::as_str), None);
    }

    /// Choosing Analog for MultiTap's Mode sets the analog starting point, a dotted echo with the second tap off fed back
    /// from the third, shows the device's five gauges and hides Time change, which the device's one clock settles.
    #[test]
    fn choosing_analog_starts_multitap_on_its_warm_dotted_echo() {
        let mut app = engine_app(
            "{ name: fish, kind: built_in, role: normal, sound: { engine: asheville, effects: [{ effect: multitap }] } }",
            false,
        );
        let mut editor = InstrumentEditor { name: "fish".to_string() };
        let mode = id_of(&app, Write::Item("effects", 1, "mode"));
        editor.apply(&mut app, mode, Edit::Choice(ANALOG.to_string()));
        let instrument = match app.document.get_setlist().get_item(Section::INSTRUMENTS, "fish") {
            Some(Item::Instrument(instrument)) => instrument.clone(),
            _ => panic!("the instrument"),
        };
        let sound = Sound::of(&instrument);
        for (name, value) in analog_starting_point() {
            assert_eq!(sound.effect_setting(1, name), value, "{name}");
        }
        let mut ids = Ids { last: 0, writes: Vec::new() };
        let fields = InstrumentEditor::effects_tab(&sound, false, &mut ids).columns[0].fields.clone();
        let numbered = |label: &str| named(label, &[("number", 1.into())]);
        let shown = labels_of(&fields);
        for (_, label) in ANALOG_SETTINGS {
            assert!(shown.contains(&numbered(label).as_str()), "{label}");
        }
        assert!(!shown.contains(&numbered(labels::MSG_EFFECT_TIME_CHANGE_LABEL).as_str()));
    }

    /// Percussion changes only while no track plays the instrument, after a question starting on NO: a track playing
    /// it refuses the change and names the track; an unused one, answered YES, turns percussion with MechaDrum's sound.
    #[test]
    fn percussion_changes_only_while_unused_after_asking() {
        use crate::keybindings::ConfirmDialog as ConfirmKeys;
        use crate::keys::first_key;
        let synth = "{ name: fish, kind: built_in, role: normal, sound: { engine: asheville } }";
        let mut played = engine_app(synth, true);
        let mut editor = InstrumentEditor { name: "fish".to_string() };
        let toggle = id_of(&played, Write::Percussion);
        editor.apply(&mut played, toggle, Edit::Toggle(true));
        let refused = named(
            llamatron_strings::errors::ERR_PERCUSSION_IN_USE,
            &[("name", "fish".into()), ("track", "bass".into()), ("song", "song".into())],
        );
        assert_eq!(played.status.text(), refused);
        let unused = engine_app(synth, false);
        let mut tracker = crate::app::Tracker::new(unused.document);
        let mut editor = InstrumentEditor { name: "fish".to_string() };
        editor.apply(&mut tracker.app, toggle, Edit::Toggle(true));
        tracker.settle();
        assert_eq!(tracker.top().name(), "ConfirmDialog");
        tracker.press(first_key(&ConfirmKeys::SELECT));
        tracker.press(first_key(&ConfirmKeys::ANSWER));
        let Some(Item::Instrument(changed)) = tracker.app.document.get_setlist().get_item(Section::INSTRUMENTS, "fish") else {
            panic!("the instrument")
        };
        assert_eq!(changed.get_written(InstrumentSetting::ROLE).and_then(Data::as_str), Some(PERCUSSION));
        assert_eq!(Sound::of(changed).part_type("oscillators"), "drum");
    }

    /// An LFO's Rate shows its percentage with the hertz it gives at its Speed; the Key switch shows only at Very High,
    /// and with Key on the Rate is a ratio to the note.
    #[test]
    fn an_lfo_rate_shows_its_hertz_and_key_shows_only_at_audio_rate() {
        let fields_of = |lfo: &str| {
            let text = format!("{{ name: synth, kind: built_in, role: normal, sound: {{ engine: basic, lfos: [{lfo}] }} }}");
            let data = llamatron_model::file::data::load(&text).expect("the scenario's instrument is YAML");
            let instrument = Instrument::from_data(&data).expect("the scenario's instrument is valid");
            let mut ids = Ids { last: 0, writes: Vec::new() };
            let tab = InstrumentEditor::lfos_tab(&Sound::of(&instrument), false, &mut ids);
            tab.columns[0].fields.clone()
        };
        let labelled = |fields: &[Field], label: &str| fields.iter().find(|field| field.label == named(label, &[("number", 1.into())])).cloned();
        let medium = fields_of("{ on: true, speed: medium, rate_percent: 74 }");
        let rate = labelled(&medium, labels::MSG_LFO_RATE_LABEL).expect("a Rate");
        let shown = named(
            marks::MSG_LFO_RATE_SHOWN,
            &[("percent", 74.into()), ("hertz", hertz_shown(lfo_speed::hertz("medium", 74.0)).as_str().into())],
        );
        assert!(rate.value().ends_with(&shown), "{}", rate.value());
        assert!(labelled(&medium, labels::MSG_LFO_KEY_LABEL).is_none(), "no Key below Very High");
        let keyed = fields_of("{ on: true, speed: very_high, key: true, ratio: \"2:1\" }");
        assert!(labelled(&keyed, labels::MSG_LFO_KEY_LABEL).is_some());
        let ratio = labelled(&keyed, labels::MSG_LFO_RATIO_LABEL).expect("a ratio in the Rate's place");
        assert_eq!(ratio.value(), "2:1");
    }

    /// The filter's types are listed by name with (none) first, and an envelope's by name.
    #[test]
    fn filter_and_envelope_types_are_listed_by_name() {
        for part in [FILTER_PART, ENVELOPE_PARTS[0]] {
            let names: Vec<String> = listed_types(part).into_iter().map(|(_, name)| name).collect();
            let named: Vec<&String> = names.iter().filter(|name| !name.starts_with(NOT_A_NAME)).collect();
            let mut sorted = named.clone();
            sorted.sort_by_key(|name| name.to_lowercase());
            assert_eq!(named, sorted, "{part}");
            if part == FILTER_PART {
                assert!(names[0].starts_with(NOT_A_NAME), "(none) first");
            }
        }
    }

    /// Every field on every tab of the Instrument page, for every engine and every effect the registries hold, shows a
    /// label and a value with every placeholder filled: no `{` is ever drawn.
    #[test]
    fn no_field_shows_an_unfilled_placeholder() {
        let unfilled = '{';
        // Every engine and every effect, walked from their lists, so that one added later is held too.
        let engines = ENGINES_OF_ROLE.iter().flat_map(|(_, engines)| engines.iter().copied());
        for engine in engines {
            for effect in llamatron_backend::effects::REGISTRY.iter().map(|entry| entry.name) {
                let instrument = format!("{{ name: fish, kind: built_in, sound: {{ engine: {engine}, effects: [{{ effect: {effect} }}] }} }}");
                let app = engine_app(&instrument, true);
                let editor = InstrumentEditor { name: "fish".to_string() };
                let (nodes, _) = editor.built(&app);
                let tab_box = nodes
                    .iter()
                    .find_map(|node| match node {
                        Node::TabBox(tab_box) => Some(tab_box),
                        _ => None,
                    })
                    .expect("a tab box");
                for tab in &tab_box.tabs {
                    for field in tab.columns.iter().flat_map(|column| column.fields.iter()) {
                        let drawn = [field.drawn_label(true), field.value().to_string()];
                        for text in drawn {
                            assert!(!text.contains(unfilled), "{engine} with {effect}, {}: {text}", tab.label);
                        }
                    }
                }
            }
        }
    }

    /// Basic's Oscillators tab shows its one oscillator's column and nothing more: no column of settings it has none of.
    #[test]
    fn basics_tab_shows_its_one_oscillator_alone() {
        let app = engine_app("{ name: fish, kind: built_in, sound: { engine: basic } }", true);
        let editor = InstrumentEditor { name: "fish".to_string() };
        let (nodes, _) = editor.built(&app);
        let tab_box = nodes
            .iter()
            .find_map(|node| match node {
                Node::TabBox(tab_box) => Some(tab_box),
                _ => None,
            })
            .expect("a tab box");
        let oscillators = tab_box
            .tabs
            .iter()
            .find(|tab| tab.label == labels::MSG_OSCILLATORS_TAB)
            .expect("the Oscillators tab");
        let headings: Vec<Option<String>> = oscillators.columns.iter().map(|column| column.heading.clone()).collect();
        let first = named(labels::MSG_OSCILLATOR_LABEL, &[("number", 1.into())]);
        assert_eq!(headings, [Some(first)]);
    }

    /// The Mod Matrix offers each oscillator by its number: Osc 1 alone on an engine of one oscillator, Osc 1 to Osc 3 on
    /// Asheville, never the two together; Per Note S&H is a source and never a Via.
    #[test]
    fn the_matrix_names_its_oscillators_and_keeps_per_note_sh_a_source() {
        let names_of = |asheville: bool, via: bool| -> Vec<String> {
            let field = InstrumentEditor::source_field(1, labels::MSG_SLOT_SOURCE_LABEL, "none", asheville, via);
            match field.kind {
                FieldKind::Choice { names, .. } => names.unwrap_or_default(),
                _ => Vec::new(),
            }
        };
        let first = named_in(labels::MSG_MATRIX_SOURCE_NAMES, ONE_OSCILLATOR_SOURCE);
        let per_note = named_in(labels::MSG_MATRIX_SOURCE_NAMES, SOURCES_ONLY[0]);
        let one = names_of(false, false);
        assert_eq!(one.iter().filter(|name| **name == first).count(), 1, "{one:?}");
        let three = names_of(true, false);
        for source in ASHEVILLE_SOURCES {
            assert!(three.contains(&named_in(labels::MSG_MATRIX_SOURCE_NAMES, source)), "{three:?}");
        }
        assert_eq!(three.iter().filter(|name| **name == first).count(), 1, "Osc 1 once on Asheville: {three:?}");
        assert!(one.contains(&per_note) && !names_of(false, true).contains(&per_note));
    }

    /// Each Mod Matrix slot is headed by its number, Slot 1 to the last.
    #[test]
    fn each_matrix_slot_is_headed_by_its_number() {
        let app = engine_app("{ name: fish, kind: built_in, sound: { engine: basic } }", true);
        let editor = InstrumentEditor { name: "fish".to_string() };
        let (nodes, _) = editor.built(&app);
        let tab_box = nodes
            .iter()
            .find_map(|node| match node {
                Node::TabBox(tab_box) => Some(tab_box),
                _ => None,
            })
            .expect("a tab box");
        let matrix = tab_box.tabs.iter().find(|tab| tab.label == labels::MSG_MATRIX_TAB).expect("the Mod Matrix tab");
        let headings: Vec<Option<String>> = matrix.columns.iter().map(|column| column.heading.clone()).collect();
        let wanted: Vec<Option<String>> = (1..=MATRIX_SLOTS as usize)
            .map(|number| Some(named(labels::MSG_SLOT_HEADING, &[("number", number.into())])))
            .collect();
        assert_eq!(headings, wanted);
    }
}
