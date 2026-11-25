// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An instrument's page (the Python screens/set/instrument_editor.py, pages/instrument.py, sound_tabs.py, part_fields.py,
//! lfo_blocks.py and effect_blocks.py): its name, how loud it plays, its role, kind and engine, then its MIDI tab and its
//! built-in sound's tabs, and its buttons.

use crate::app::App;
use crate::forms::nodes::{Edit, Field, Kind as FieldKind};
use crate::forms::tab_box::{Tab, TabBox, TabColumn};
use crate::generated::sounds::{
    SettingKind, EFFECT_DEFAULTS, ENGINES_OF_ROLE, LFO_DEFAULTS, PART_TYPES, SETTING_KINDS, SID_ATTACK_MS, SLOT_DEFAULTS, TYPE_SETTINGS, TYPE_SETTING_KINDS,
};
use crate::instrument_sound::{Sound, ENVELOPE_PARTS};
use crate::keybindings::{InstrumentEditor as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::field_page::{Form, Node};
use crate::settings::named_in;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::{Instrument, Item};
use llamatron_model::schema::generated::file_format::{
    InstrumentSetting, Section, CURVES, EFFECTS, FILTER_SHARINGS, INSTRUMENT_KINDS, LFO_SHAPES, MATRIX_DESTINATIONS, MATRIX_SOURCES, OSCILLATOR_WAVEFORMS,
};
use llamatron_model::schema::generated::limits::{
    EFFECT_BLOCKS, KNOB_COUNT, LFO_COUNT, MATRIX_SLOTS, MAX_BITS, MAX_DETUNE_CENTS, MAX_GLIDE_MS, MAX_GM_SOUND, MAX_INSTRUMENT_LATENCY, MAX_KEYSWITCH_LEAD,
    MAX_KNOB, MAX_LFO_RATE, MAX_MATRIX_AMOUNT, MAX_OSCILLATORS, MAX_SID_RATE, MAX_VOICES, MAX_VOLUME_PERCENT, MIN_BITS, MIN_GM_SOUND, MIN_INSTRUMENT_LATENCY,
    MIN_KEYSWITCH_LEAD, MIN_LFO_RATE,
};
use llamatron_strings::{labels, legends, marks, named};

const NAME: usize = 0;
const GM_CELLS: usize = 12;
const BLOCK_CELLS: usize = 8;
const MAX_PERCENT: i64 = 100;
const DEFAULT_VELOCITY: i64 = 127;
const DEFAULT_ACCENT: i64 = 0;
const UNCHANGED: i64 = 100;
const TENTHS: i64 = 10;
const SECOND_ROW_LFO: usize = 3;
const SECOND_ROW_SLOT: usize = 4;
const CRUSH_RATES: [i64; 11] = [0, 32000, 22050, 16000, 11025, 8000, 6000, 4000, 3000, 2000, 1000];
const MIDI: &str = "midi";
const BUILT_IN: &str = "built_in";
const FLUIDSYNTH_DEVICE: &str = "FluidSynth";
const NONE_EFFECT: &str = "none";
const BITCRUSH: &str = "bitcrush";

pub struct InstrumentEditor {
    pub name: String,
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
    let filled = ((share * cells as f64).round_ties_even() as usize).min(cells);
    let gauge = format!(
        "{}{}",
        marks::MSG_SOUND_GAUGE_FULL.repeat(filled),
        marks::MSG_SOUND_GAUGE_EMPTY.repeat(cells - filled)
    );
    let value = if divisor != 1 {
        named(unit, &[("number", (number as f64 / divisor as f64).into())])
    } else {
        named(unit, &[("number", number.into())])
    };
    named(marks::MSG_SOUND_GAUGE, &[("gauge", gauge.as_str().into()), ("value", value.as_str().into())])
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
    /// One of the instrument's own settings, its kind, its engine, its General MIDI sound.
    Setting(&'static str),
    Kind,
    Engine,
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
const RATE_STRIDES: Strides = (&[(20, 1), (50, 2), (100, 5), (300, 10), (600, 25)], 50);

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
    /// The page's fields, and what each that writes writes.
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
        let mut nodes = vec![
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
        nodes.extend(self.above_tabs(app, instrument, &sound, &mut ids));
        let mut nodes: Vec<Node> = nodes.into_iter().map(|field| Node::Field(Box::new(field))).collect();
        let not_ready = Self::kind(instrument) != BUILT_IN;
        let tabs = vec![
            self.midi_tab(instrument, &mut ids),
            Self::oscillators_tab(&sound, not_ready, &mut ids),
            Self::envelopes_tab(&sound, not_ready, &mut ids),
            Self::lfos_tab(&sound, not_ready, &mut ids),
            Self::filter_tab(&sound, not_ready, &mut ids),
            Self::effects_tab(&sound, not_ready, &mut ids),
            Self::matrix_tab(&sound, not_ready, &mut ids),
        ];
        nodes.push(Node::TabBox(TabBox {
            label: labels::MSG_TABS_LABEL.to_string(),
            tabs,
        }));
        let buttons = [
            Field::button(ids.next(), labels::MSG_PREVIEW_PATTERN_LABEL, "", legends::What::EDIT),
            Field::button(ids.next(), labels::MSG_KEYSWITCH_MAP_LABEL, Keys::KEYSWITCH_MAP.name, Keys::KEYSWITCH_MAP.what),
            Field::button(ids.next(), labels::MSG_LISTEN_LABEL, legends::KeyName::L, legends::MSG_LISTEN_WHAT),
        ];
        nodes.extend(buttons.into_iter().map(|field| Node::Field(Box::new(field))));
        (nodes, ids)
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
            return if *drum { "percussion" } else { "normal" }.to_string();
        }
        if Self::kind(instrument) == BUILT_IN && sound.part_type("oscillators") == "drum" {
            return "percussion".to_string();
        }
        "normal".to_string()
    }

    fn above_tabs(&self, app: &App, instrument: &Instrument, sound: &Sound, ids: &mut Ids) -> Vec<Field> {
        let role = self.role(app, instrument, sound);
        let kind = Self::kind(instrument);
        let engines: &[&str] = ENGINES_OF_ROLE.iter().find(|(found, _)| *found == role).map_or(&[], |(_, engines)| engines);
        let written = text(&sound.value("engine"));
        let engine = if engines.contains(&written.as_str()) {
            written
        } else {
            engines.first().map_or(String::new(), |first| first.to_string())
        };
        vec![
            Field::custom(ids.next(), labels::MSG_ROLE_LABEL, &named_in(labels::MSG_ROLE_NAMES, &role)),
            chosen(
                ids.at(Write::Kind),
                labels::MSG_INSTRUMENT_KIND_LABEL,
                INSTRUMENT_KINDS,
                &names_in(labels::MSG_KIND_NAMES, INSTRUMENT_KINDS),
                &kind,
            ),
            chosen(
                ids.at(Write::Engine),
                labels::MSG_ENGINE_LABEL,
                engines,
                &names_in(labels::MSG_ENGINE_NAMES, engines),
                &engine,
            ),
        ]
    }

    fn midi_tab(&self, instrument: &Instrument, ids: &mut Ids) -> Tab {
        let device = instrument.get_written(InstrumentSetting::DEVICE).and_then(Data::as_str);
        let channel = if device == Some(FLUIDSYNTH_DEVICE) {
            Field::custom(ids.next(), labels::MSG_CHANNEL_LABEL, marks::MSG_AUTO_CHANNEL_SHOWN)
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
        let fields = vec![
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
            Field::number(
                ids.at(Write::Setting(InstrumentSetting::KEYSWITCH_LEAD)),
                labels::MSG_KEYSWITCH_LEAD_LABEL,
                Some(lead),
                Some(MIN_KEYSWITCH_LEAD),
                Some(MAX_KEYSWITCH_LEAD),
                0,
                Some(milliseconds(lead)),
            ),
            Field::number(
                ids.at(Write::Setting(InstrumentSetting::LATENCY)),
                labels::MSG_LATENCY_LABEL,
                Some(latency),
                Some(MIN_INSTRUMENT_LATENCY),
                Some(MAX_INSTRUMENT_LATENCY),
                0,
                Some(milliseconds(latency)),
            ),
        ];
        let mut tab = Tab::new(labels::MSG_MIDI_TAB, vec![TabColumn::new(None, fields)]);
        tab.not_ready = Self::kind(instrument) != MIDI;
        tab
    }

    fn type_field(sound: &Sound, part: &'static str, ids: &mut Ids) -> Field {
        let (_, kinds, names) = PART_TYPES.iter().find(|(found, ..)| *found == part).copied().unwrap_or(("", &[], &[]));
        let label = part_label(part, labels::MSG_PART_TYPE_LABEL);
        let names: Vec<String> = names.iter().map(|name| name.to_string()).collect();
        chosen(ids.at(Write::PartType(part)), &label, kinds, &names, &sound.part_type(part)).with_shown_label(labels::MSG_PART_TYPE_LABEL)
    }

    fn setting_fields(sound: &Sound, part: &'static str, ids: &mut Ids) -> Vec<Field> {
        let kind = sound.part_type(part);
        let settings: &[&str] = TYPE_SETTINGS.iter().find(|(found, _)| *found == kind).map_or(&[], |(_, settings)| settings);
        settings.iter().map(|name| Self::setting_field(sound, part, &kind, name, ids)).collect()
    }

    fn setting_field(sound: &Sound, part: &'static str, kind: &str, name: &'static str, ids: &mut Ids) -> Field {
        let value = sound.part_value(part, name);
        let shown_label = named_in(labels::MSG_PART_SETTING_NAMES, name);
        let label = part_label(part, &shown_label);
        if name == "arpeggio" {
            let steps: Vec<String> = value
                .as_list()
                .map_or(Vec::new(), |steps| steps.iter().map(|step| whole(step).to_string()).collect());
            let shown = if steps.is_empty() {
                marks::MSG_ARPEGGIO_NONE_SHOWN.to_string()
            } else {
                steps.join(marks::MSG_ARPEGGIO_SEPARATOR)
            };
            return Field::custom(ids.at(Write::Part(part, "arpeggio")), labels::MSG_ARPEGGIO_LABEL, &shown)
                .with_enter(legends::What::EDIT)
                .with_clear(marks::MSG_ARPEGGIO_NONE_SHOWN);
        }
        let how = TYPE_SETTING_KINDS
            .iter()
            .find(|(found, setting, _)| *found == kind && *setting == name)
            .map(|(.., how)| *how)
            .or_else(|| SETTING_KINDS.iter().find(|(found, _)| *found == name).map(|(_, how)| *how))
            .unwrap_or(SettingKind::Toggle);
        let strides = matches!(how, SettingKind::Gauge { what: "milliseconds", .. }).then_some(TIME_STRIDES);
        let id = ids.at_gauge(Write::Part(part, name), strides.unwrap_or(STEPS_OF_ONE));
        let field = match how {
            SettingKind::Choice { choices, names } => {
                let names: Vec<String> = names.iter().map(|name| name.to_string()).collect();
                chosen(id, &label, choices, &names, &text(&value))
            }
            SettingKind::Toggle => Field::toggle(id, &label, flag(&value)),
            SettingKind::Number { lowest, highest, unit, zero } => {
                let number = whole(&value);
                let shown = match zero {
                    Some(zero) if number == 0 => zero.to_string(),
                    _ => named(unit, &[("number", number.into())]),
                };
                Field::number(id, &label, Some(number), Some(lowest), Some(highest), lowest, Some(shown))
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
                        (false, TENTHS),
                    ),
                    _ => gauge(id, &label, number, (lowest, highest), GM_CELLS, marks::MSG_SOUND_PERCENT_SHOWN, (false, 1)),
                }
            }
        };
        field.with_shown_label(&shown_label)
    }

    fn voice_fields(sound: &Sound, ids: &mut Ids) -> Vec<Field> {
        let sharing = text(&sound.value("filter_sharing"));
        vec![
            gauge(
                ids.at(Write::Sound("volume")),
                labels::MSG_VOLUME_LABEL,
                whole(&sound.value("volume")),
                (0, MAX_VOLUME_PERCENT),
                GM_CELLS,
                marks::MSG_SOUND_PERCENT_SHOWN,
                (false, 1),
            ),
            Field::number(
                ids.at(Write::Sound("voices")),
                labels::MSG_VOICES_LABEL,
                Some(whole(&sound.value("voices"))),
                Some(1),
                Some(MAX_VOICES),
                1,
                None,
            ),
            Field::toggle(ids.at(Write::Sound("legato")), labels::MSG_LEGATO_LABEL, flag(&sound.value("legato"))),
            gauge(
                ids.at_gauge(Write::Sound("glide"), TIME_STRIDES),
                labels::MSG_GLIDE_LABEL,
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
        ]
    }

    fn oscillators_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let top = vec![Self::type_field(sound, "oscillators", ids)];
        let mut columns = vec![TabColumn::new(Some(labels::MSG_VOICE_HEADING), Self::voice_fields(sound, ids))];
        let kind = sound.part_type("oscillators");
        if kind == "basic" {
            for number in 1..=MAX_OSCILLATORS as usize {
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
                    Field::number(
                        ids.at(Write::Oscillator(number, "detune")),
                        &named(labels::MSG_OSCILLATOR_DETUNE_LABEL, &[("number", number.into())]),
                        Some(detune),
                        Some(-MAX_DETUNE_CENTS),
                        Some(MAX_DETUNE_CENTS),
                        0,
                        Some(named(marks::MSG_CENTS_SHOWN, &[("number", detune.into())])),
                    )
                    .with_shown_label(labels::MSG_DETUNE_LABEL),
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
        columns.push(TabColumn::new(Some(&named_in(labels::MSG_PART_HEADINGS, "oscillators")), own));
        let mut tab = Tab::new(labels::MSG_OSCILLATORS_TAB, columns);
        tab.top = top;
        tab.not_ready = not_ready;
        tab
    }

    fn envelopes_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let columns = ENVELOPE_PARTS
            .iter()
            .map(|part| {
                let mut fields = vec![Self::type_field(sound, part, ids)];
                fields.extend(Self::setting_fields(sound, part, ids));
                TabColumn::new(Some(&named_in(labels::MSG_PART_HEADINGS, part)), fields)
            })
            .collect();
        let mut tab = Tab::new(labels::MSG_ENVELOPES_TAB, columns);
        tab.not_ready = not_ready;
        tab
    }

    fn lfos_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let lfo = |number: usize, name: &str| sound.item("lfos", number, name, LFO_DEFAULTS);
        let shown_label = |label: &str| named_in(labels::MSG_LFO_SHOWN_LABELS, label);
        let mut columns = Vec::new();
        for number in 1..=LFO_COUNT as usize {
            let numbered = |label: &str| named(label, &[("number", number.into())]);
            let shape = text(&lfo(number, "shape"));
            let fields = vec![
                Field::toggle(
                    ids.at(Write::Item("lfos", number, "on")),
                    &numbered(labels::MSG_LFO_LABEL),
                    flag(&lfo(number, "on")),
                ),
                chosen(
                    ids.at(Write::Item("lfos", number, "shape")),
                    &numbered(labels::MSG_LFO_SHAPE_LABEL),
                    LFO_SHAPES,
                    &names_in(labels::MSG_LFO_SHAPE_NAMES, LFO_SHAPES),
                    &shape,
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_SHAPE_LABEL)),
                gauge(
                    ids.at_gauge(Write::Item("lfos", number, "rate"), RATE_STRIDES),
                    &numbered(labels::MSG_LFO_RATE_LABEL),
                    whole(&lfo(number, "rate")),
                    (MIN_LFO_RATE, MAX_LFO_RATE),
                    BLOCK_CELLS,
                    marks::MSG_LFO_RATE_SHOWN,
                    (true, TENTHS),
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_RATE_LABEL)),
                Field::toggle(
                    ids.at(Write::Item("lfos", number, "retrigger")),
                    &numbered(labels::MSG_LFO_RETRIGGER_LABEL),
                    flag(&lfo(number, "retrigger")),
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_RETRIGGER_LABEL)),
                Field::toggle(
                    ids.at(Write::Item("lfos", number, "each_scene")),
                    &numbered(labels::MSG_LFO_EACH_SCENE_LABEL),
                    flag(&lfo(number, "each_scene")),
                )
                .with_shown_label(&shown_label(labels::MSG_LFO_EACH_SCENE_LABEL)),
            ];
            let mut column = TabColumn::new(None, fields);
            column.under = number == SECOND_ROW_LFO;
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

    fn effects_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let effect = |number: usize, name: &str| sound.item("effects", number, name, EFFECT_DEFAULTS);
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
                if chosen_effect == BITCRUSH {
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

    fn matrix_tab(sound: &Sound, not_ready: bool, ids: &mut Ids) -> Tab {
        let slot = |number: usize, name: &str| sound.item("matrix", number, name, SLOT_DEFAULTS);
        let shown_label = |label: &str| named_in(labels::MSG_SLOT_SHOWN_LABELS, label);
        let mut columns = Vec::new();
        for number in 1..=MATRIX_SLOTS as usize {
            let numbered = |label: &str| named(label, &[("number", number.into())]);
            let sources = names_in(labels::MSG_MATRIX_SOURCE_NAMES, MATRIX_SOURCES);
            let amount = whole(&slot(number, "amount"));
            let fields = vec![
                chosen(
                    ids.at(Write::Item("matrix", number, "source")),
                    &numbered(labels::MSG_SLOT_SOURCE_LABEL),
                    MATRIX_SOURCES,
                    &sources,
                    &text(&slot(number, "source")),
                )
                .with_shown_label(&shown_label(labels::MSG_SLOT_SOURCE_LABEL)),
                chosen(
                    ids.at(Write::Item("matrix", number, "via")),
                    &numbered(labels::MSG_SLOT_VIA_LABEL),
                    MATRIX_SOURCES,
                    &sources,
                    &text(&slot(number, "via")),
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
                Field::number(
                    ids.at(Write::Item("matrix", number, "amount")),
                    &numbered(labels::MSG_SLOT_AMOUNT_LABEL),
                    Some(amount),
                    Some(-MAX_MATRIX_AMOUNT),
                    Some(MAX_MATRIX_AMOUNT),
                    0,
                    Some(named(marks::MSG_SIGNED_PERCENT_SHOWN, &[("number", amount.into())])),
                )
                .with_shown_label(&shown_label(labels::MSG_SLOT_AMOUNT_LABEL)),
            ];
            let mut column = TabColumn::new(None, fields);
            column.under = number == SECOND_ROW_SLOT;
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

    fn page_keys(&self, _app: &App, _row: Option<&Field>) -> Vec<KeyItem> {
        vec![KeyItem::of(&Keys::CLASS, &Keys::KEYSWITCH_MAP), KeyItem::of(&Keys::CLASS, &Keys::LISTEN)]
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        let Some(instrument) = self.instrument(app) else { return };
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
            Write::Kind => set(app, InstrumentSetting::KIND, value.filter(|value| value.as_str() != Some(MIDI))),
            Write::GmSound => set(app, InstrumentSetting::GM_SOUND, value),
            Write::Engine => {
                let engine = value.as_ref().and_then(Data::as_str).unwrap_or("").to_string();
                set(app, InstrumentSetting::SOUND, Some(sound.with_engine(&engine)));
            }
            Write::Sound(name) => set(app, InstrumentSetting::SOUND, Some(sound.with_value(name, sound_value(value)))),
            Write::PartType(part) => {
                let kind = value.as_ref().and_then(Data::as_str).unwrap_or("").to_string();
                set(app, InstrumentSetting::SOUND, Some(sound.with_part_type(part, &kind)));
            }
            Write::Part(part, name) => set(app, InstrumentSetting::SOUND, Some(sound.with_part_value(part, name, sound_value(value)))),
            Write::Oscillator(number, name) => set(app, InstrumentSetting::SOUND, Some(sound.with_oscillator(number, name, sound_value(value)))),
            Write::Knob(place) => set(app, InstrumentSetting::SOUND, Some(sound.with_knob(place, sound_value(value)))),
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
