// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A generator's page (the Python screens/shared/plugin_editor.py, pages/generator.py and pages/view_fields.py): its name,
//! whether it is enabled, its mode where it has one, then each column of its plugin's view as fields, and the statements
//! that bypass it.

use crate::app::App;
use crate::forms::nodes::{Edit, Field};
use crate::generated::generator_views::{GeneratorView, SettingView, VIEWS};
use crate::keybindings::{KeyClass, PluginEditor as Keys};
use crate::screens::field_page::{Form, Node};
use crate::settings::{named_in, shown_octave};
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::{GENERATOR_ENABLED, GENERATOR_RESTART, RESTARTS, SHAPE_PARTS, SHAPE_THENS, TIME_CHOICES};
use llamatron_model::schema::generated::limits::{MAX_OCTAVE, MIN_OCTAVE};
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_model::schema::generated::settings::{Described, Plain};
use llamatron_strings::{labels, legends, marks, messages, named};

const NAME: usize = 0;
/// The id of the generator's Enabled toggle, the first field made after its name.
const ENABLED: usize = NAME + 1;
/// How many steps an arpeggiator's offsets start with when its Offsets field first opens them.
const NEW_OFFSET_STEPS: usize = 8;

pub struct PluginEditor {
    pub kind: &'static str,
    pub name: String,
}

/// A plugin's word for what its page edits.
pub fn caption_word(kind: &str) -> &'static str {
    use llamatron_strings::plugin_texts::*;
    match kind {
        "arp" => arp::MSG_CAPTION_WORD,
        "chords" => chords::MSG_CAPTION_WORD,
        "drift" => drift::MSG_CAPTION_WORD,
        "guitarify" => guitarify::MSG_CAPTION_WORD,
        "hocket" => hocket::MSG_CAPTION_WORD,
        "musician" => musician::MSG_CAPTION_WORD,
        "phrasing" => phrasing::MSG_CAPTION_WORD,
        "shapes" => shapes::MSG_CAPTION_WORD,
        _ => timing::MSG_CAPTION_WORD,
    }
}

fn plain_text(value: &Plain) -> String {
    match value {
        Plain::Text(text) => text.to_string(),
        Plain::Whole(whole) => whole.to_string(),
        Plain::Flag(flag) => flag.to_string(),
        _ => String::new(),
    }
}

fn plain_data(value: &Plain) -> Data {
    match value {
        Plain::Text(text) => Data::text(text),
        Plain::Whole(whole) => Data::Whole(*whole as i128),
        Plain::Float(number) => Data::Float(*number),
        Plain::Flag(flag) => Data::Bool(*flag),
        Plain::Null => Data::Null,
        Plain::List(items) => Data::List(items.iter().map(plain_data).collect()),
    }
}

/// The setting an edit of a view writes and the value it writes there, None leaving it out of the file where the value is
/// the one the generator takes unwritten; or None where the edit writes nothing of the view's own.
pub fn view_write(view: &SettingView, edit: &Edit, mode: Option<&str>) -> Option<(&'static str, Option<Data>)> {
    if let SettingView::When { view, .. } = view {
        return view_write(view, edit, mode);
    }
    if *edit == Edit::Clear {
        return setting_name(view).map(|setting| (setting, None));
    }
    let written = match (view, edit) {
        (SettingView::Choice { setting, choices, default, .. }, Edit::Choice(chosen)) => {
            let value = choices
                .iter()
                .find(|choice| plain_text(choice) == *chosen)
                .map_or_else(|| Data::text(chosen), plain_data);
            (*setting, (value != plain_data(default)).then_some(value))
        }
        (SettingView::InheritedChoice { setting, inherited_choice, .. }, Edit::Choice(chosen)) => {
            (*setting, (chosen != inherited_choice).then(|| Data::text(chosen)))
        }
        (SettingView::Track { setting, .. }, Edit::Choice(chosen)) => (*setting, (chosen != marks::MSG_NONE_SHOWN).then(|| Data::text(chosen))),
        (SettingView::Number { setting, default, .. }, Edit::Number(number)) => {
            let unwritten = match default {
                Some(default) => plain_data(default) == Data::Whole(*number as i128),
                None => *number == 0,
            };
            (*setting, (!unwritten).then_some(Data::Whole(*number as i128)))
        }
        (SettingView::Gauge { setting, default, .. }, Edit::Number(number)) => (*setting, (number != default).then_some(Data::Whole(*number as i128))),
        (SettingView::Octave { setting, default, .. }, Edit::Number(number)) => (*setting, (number != default).then_some(Data::Whole(*number as i128))),
        (SettingView::Toggle { setting, default, by_mode, .. }, Edit::Toggle(on)) => {
            let in_mode = by_mode
                .and_then(|by_mode| by_mode.iter().find(|(chosen, _)| Some(plain_text(chosen).as_str()) == mode))
                .map_or(*default, |(_, on)| *on);
            (*setting, (*on != in_mode).then_some(Data::Bool(*on)))
        }
        (SettingView::Time { setting, first, .. }, Edit::Choice(chosen)) => (*setting, (Some(chosen.as_str()) != *first).then(|| Data::text(chosen))),
        (SettingView::Restart, Edit::Choice(chosen)) => (GENERATOR_RESTART, (chosen != RESTARTS[0]).then(|| Data::text(chosen))),
        _ => return None,
    };
    Some(written)
}

/// The lowest and highest number a generator's setting may hold, as its table of settings describes it.
fn setting_limits(kind: &str, setting: &str) -> (i64, i64) {
    let table = llamatron_model::objects::named::plugin_table(kind).unwrap_or(&[]);
    match table.iter().find(|found| found.name == setting).map(|found| found.described) {
        Some(Described::WholeNumber { lowest, highest, .. }) => (lowest.unwrap_or(i64::MIN), highest.unwrap_or(i64::MAX)),
        _ => (i64::MIN, i64::MAX),
    }
}

/// The setting a generator keeps its Bypass When statements under, and the first id their cells take, past every other
/// field's.
const BYPASS_WHEN: &str = "bypass_when";
const STATEMENT_IDS: usize = 10_000;

/// The ends of a voicing's range of octaves, each kept from passing the other.
const LOWEST_OCTAVE: &str = "lowest_octave";
const HIGHEST_OCTAVE: &str = "highest_octave";

/// What a drift's scale or root may be, (none) aside: the set's scales by name, or the roots.
fn drift_choices(app: &App, setting: &str) -> Vec<String> {
    if setting.ends_with("_scale") {
        let names: Vec<String> = app
            .document
            .get_setlist()
            .items(llamatron_model::schema::generated::file_format::Section::SCALES)
            .iter()
            .map(|(name, _)| name.clone())
            .collect();
        return crate::settings::sorted_names(&names);
    }
    llamatron_model::values::generated::note::ROOT_NAMES
        .iter()
        .map(|name| name.to_string())
        .collect()
}

/// The lowest and highest octave a generator's setting may hold, as its table of settings describes it.
fn octave_limits(kind: &str, setting: &str) -> (i64, i64) {
    let table = llamatron_model::objects::named::plugin_table(kind).unwrap_or(&[]);
    match table.iter().find(|found| found.name == setting).map(|found| found.described) {
        Some(Described::WholeNumber { lowest, highest, .. }) => (lowest.unwrap_or(MIN_OCTAVE), highest.unwrap_or(MAX_OCTAVE)),
        _ => (MIN_OCTAVE, MAX_OCTAVE),
    }
}

fn data_text(value: &Data) -> String {
    match value {
        Data::Text(text) => text.clone(),
        Data::Whole(whole) => whole.to_string(),
        Data::Bool(flag) => if *flag { "True" } else { "False" }.to_string(),
        _ => String::new(),
    }
}

/// What a page asks of a generator's settings while its fields are made: its data as written, its table of settings,
/// and whether it is built into a track or a clip, which is off until enabled.
pub struct Made<'a> {
    data: &'a Data,
    table: &'static [llamatron_model::schema::generated::settings::Setting],
    built_in: bool,
    view: &'static GeneratorView,
    app: &'a App,
    next_id: usize,
    /// Each field's id with the view it shows, for an edit to find its setting by.
    views: Vec<(usize, &'static SettingView)>,
}

impl<'a> Made<'a> {
    fn id(&mut self) -> usize {
        self.next_id += 1;
        self.next_id
    }

    fn written(&self, setting: &str) -> Option<&'a Data> {
        self.data.get(setting).filter(|value| !value.is_null())
    }

    /// The fields made from a generator's data, its kind naming its view and its table of settings.
    pub fn of(app: &'a App, kind: &str, data: &'a Data, built_in: bool) -> Made<'a> {
        let view = VIEWS
            .iter()
            .find(|(name, _)| *name == kind)
            .map(|(_, view)| *view)
            .expect("every plugin has a view");
        let table = llamatron_model::objects::named::plugin_table(kind).unwrap_or(&[]);
        Made {
            data,
            table,
            built_in,
            view,
            app,
            next_id: NAME,
            views: Vec::new(),
        }
    }

    /// The fields made from a scene's or a clip's data, which no generator's view describes, for the shapes they hold.
    pub fn over(app: &'a App, data: &'a Data) -> Made<'a> {
        Made {
            data,
            table: &[],
            built_in: false,
            view: VIEWS[0].1,
            app,
            next_id: NAME,
            views: Vec::new(),
        }
    }

    /// A shape's section, its heading taking the next id.
    pub fn shape_section(&mut self, shape: &str) -> Vec<Field> {
        let id = self.id();
        self.shape_fields(id, shape)
    }

    /// The generator's mode, as its view's mode setting chooses it, where its view has one.
    pub fn mode(&self) -> Option<String> {
        self.view.mode.map(|mode| self.chosen(mode))
    }

    /// Each field made so far by its id, with the view it shows.
    pub fn views(&self) -> &[(usize, &'static SettingView)] {
        &self.views
    }

    /// The same, its fields' ids counting on from an id, so that several generators' fields on one page stay apart.
    pub fn counting_from(mut self, id: usize) -> Made<'a> {
        self.next_id = id;
        self
    }

    pub fn is_enabled(&self) -> bool {
        match self.written(GENERATOR_ENABLED) {
            Some(value) => matches!(value, Data::Bool(true)),
            None => !self.built_in,
        }
    }

    /// The generator as a tab of a track's or a clip's page: whether it is on and its mode across the top, then its columns,
    /// each section of its view a column of its own, and its Bypass When button under them.
    pub fn tab(&mut self, label: &str, bypass_count: usize) -> crate::forms::tab_box::Tab {
        use crate::forms::tab_box::{Tab, TabColumn};
        let mut top = vec![self.enabled_field()];
        let view = self.view;
        let mode = view.mode.map(|mode| self.chosen(mode));
        if let Some(mode_view) = view.mode {
            top.extend(self.fields_of(mode_view));
        }
        let mut columns = Vec::new();
        for column in view.columns {
            if !column.modes.is_empty() && !column.modes.iter().any(|each| Some(plain_text(each)) == mode) {
                continue;
            }
            let mut own = Vec::new();
            let mut sections = Vec::new();
            for setting in column.settings {
                if let SettingView::Section { heading, settings } = setting {
                    let mut fields = Vec::new();
                    for inside in settings.iter() {
                        fields.extend(self.fields_of(inside));
                    }
                    fields.retain(|field| !field.is_heading());
                    sections.push(TabColumn::new(Some(heading), fields));
                } else {
                    let mut fields = self.fields_of(setting);
                    fields.retain(|field| !field.is_heading());
                    own.extend(fields);
                }
            }
            if !own.is_empty() {
                let mut first = TabColumn::new(column.heading, own);
                first.under = column.under;
                columns.push(first);
            }
            columns.extend(sections);
        }
        let id = self.id();
        let button = Field::button(
            id,
            &named(labels::MSG_BYPASS_WHEN_BUTTON, &[("count", bypass_count.into())]),
            "",
            legends::What::EDIT,
        );
        let mut under = TabColumn::new(None, vec![button]);
        under.under = true;
        columns.push(under);
        let mut tab = Tab::new(label, columns);
        tab.top = top;
        tab.on = Some(self.is_enabled());
        tab
    }

    fn chosen(&self, setting: &SettingView) -> String {
        let SettingView::Choice { setting, default, .. } = setting else {
            return String::new();
        };
        self.written(setting).map_or_else(|| plain_text(default), data_text)
    }

    fn limits_of(&self, setting: &str) -> (Option<i64>, Option<i64>) {
        match self.table.iter().find(|found| found.name == setting).map(|found| found.described) {
            Some(Described::WholeNumber { lowest, highest, .. }) => (lowest, highest),
            _ => (None, None),
        }
    }

    /// The musician's kind, which plays the instrument named: whether it plays pitches, and how it gives way and holds its notes.
    fn musician_kind(&self) -> (&'static str, bool, &'static str, &'static str) {
        use crate::generated::tables::MUSICIAN_KINDS;
        let instrument = self.written("instrument").map_or("rhythm guitarist".to_string(), data_text);
        *MUSICIAN_KINDS.iter().find(|(name, ..)| *name == instrument).unwrap_or(&MUSICIAN_KINDS[0])
    }

    /// One of the musician's settings, or what the musician does with it left out.
    fn musician_own(&self, setting: &str) -> String {
        if let Some(written) = self.written(setting) {
            return data_text(written);
        }
        let (_, _, gives_way, notes) = self.musician_kind();
        match setting {
            "gives_way" => gives_way.to_string(),
            "notes" => notes.to_string(),
            _ => crate::generated::tables::MUSICIAN_DEFAULTS
                .iter()
                .find(|(name, _)| *name == setting)
                .map_or(String::new(), |(_, value)| plain_text(value)),
        }
    }

    /// Whether a condition a field shows only when holds: the musician plays pitches, or names a tune.
    fn holds(&self, condition: &str) -> bool {
        if condition == crate::generated::tables::PLAYS_PITCHES {
            return self.musician_kind().1;
        }
        self.written("tune_from").is_some()
    }

    /// A drift's rows, a value each, with a cell for each of its two versions.
    fn drift_rows(&mut self) -> Vec<Field> {
        let order = [
            "velocity",
            "probability",
            "degree",
            "degree_random",
            "scale",
            "scale_probability",
            "root",
            "root_probability",
        ];
        let mut rows = Vec::new();
        for value in order {
            let label = named_in(labels::MSG_DRIFT_VALUE_LABELS, value);
            let mut cells = Vec::new();
            for version in ["a", "b"] {
                let setting = format!("{version}_{value}");
                let cell_id = self.id();
                let cell = if value == "scale" || value == "root" {
                    let current = self.written(&setting).map_or(marks::MSG_NONE_SHOWN.to_string(), data_text);
                    Field::custom(cell_id, &label, &current)
                        .with_adjust()
                        .with_enter(legends::What::CHOOSE)
                        .with_clear(legends::What::CLEAR)
                        .writing(&setting)
                } else {
                    let number = self.written(&setting).and_then(Data::as_whole).unwrap_or(0);
                    Field::custom(cell_id, &label, &number.to_string())
                        .with_adjust()
                        .with_enter(legends::What::EDIT)
                        .with_clear(legends::What::CLEAR)
                        .writing(&setting)
                };
                cells.push(cell);
            }
            let row_id = self.id();
            rows.push(Field::cells(row_id, &label, cells).stepped());
        }
        rows
    }

    /// A musician's table of the song's kinds of section: whether it plays in each, and how much of it.
    fn section_table(&mut self, caption: &str, plays: (&str, &str), played: (&str, &str), choices: &[Plain]) -> Vec<Field> {
        use llamatron_model::schema::generated::file_format::{SceneSetting, SECTION_KINDS};
        let song = self.app.document.song();
        let used: Vec<String> = song
            .scenes()
            .iter()
            .filter_map(|scene| scene.get_written(SceneSetting::SECTION).and_then(Data::as_str).map(str::to_string))
            .collect();
        let by_section = self.written("by_section");
        let own = |kind: &str, name: &str| {
            by_section
                .and_then(|sections| sections.get(kind))
                .and_then(|section| section.get(name))
                .filter(|value| !value.is_null())
                .cloned()
        };
        let kinds: Vec<&str> = SECTION_KINDS
            .iter()
            .filter(|kind| used.iter().any(|each| each == *kind) || own(kind, plays.0).is_some() || own(kind, played.0).is_some())
            .copied()
            .collect();
        let plays_width = [
            plays.1.chars().count(),
            marks::MSG_TOGGLE_ON.chars().count(),
            marks::MSG_FIELD_TOGGLE_OFF.chars().count(),
        ]
        .into_iter()
        .max()
        .unwrap_or(0);
        let played_width = choices
            .iter()
            .map(|choice| plain_text(choice).chars().count())
            .chain([played.1.chars().count()])
            .max()
            .unwrap_or(0);
        let widths = vec![plays_width, played_width];
        let mut rows = Vec::new();
        for (place, kind) in kinds.iter().enumerate() {
            let on = own(kind, plays.0).is_none_or(|value| matches!(value, Data::Bool(true)));
            let toggle_id = self.id();
            let mut cells = vec![Field::toggle(toggle_id, plays.1, on)];
            let played_id = self.id();
            if on {
                let current = own(kind, played.0).map_or("whole".to_string(), |value| data_text(&value));
                cells.push(Field::custom(played_id, played.1, &current).with_adjust().with_enter(legends::What::CHOOSE));
            } else {
                cells.push(Field::custom(played_id, played.1, marks::MSG_SITS_OUT_SHOWN));
            }
            let row_id = self.id();
            let caption = (place == 0).then(|| (caption.to_string(), vec![plays.1.to_string(), played.1.to_string()]));
            rows.push(Field::cells(row_id, kind, cells).table_row(widths.clone(), caption));
        }
        rows
    }

    /// A Guitarify's bar as its field shows it: the ready-made bar it is, or custom, with its cells and their length.
    fn bar_shown(&self) -> String {
        use crate::generated::tables::{DEFAULT_BAR, READY_BARS};
        let (_, default_cell, default_strokes, default_accents) = READY_BARS
            .iter()
            .find(|(name, ..)| *name == DEFAULT_BAR)
            .expect("the default bar is ready-made");
        let texts = |value: Option<&Data>| value.and_then(Data::as_list).map(|items| items.iter().map(data_text).collect::<Vec<_>>());
        let bar = texts(self.written("bar")).unwrap_or_else(|| default_strokes.iter().map(|stroke| stroke.to_string()).collect());
        let accents: Vec<bool> = if self.written("bar").is_none() && self.written("accents").is_none() {
            default_accents.to_vec()
        } else {
            let written: Vec<bool> = self
                .written("accents")
                .and_then(Data::as_list)
                .map_or(Vec::new(), |items| items.iter().map(|item| matches!(item, Data::Bool(true))).collect());
            (0..bar.len()).map(|place| written.get(place).copied().unwrap_or(false)).collect()
        };
        let cell = self.written("cell").map_or(default_cell.to_string(), data_text);
        let ready = READY_BARS.iter().find(|(_, ready_cell, strokes, ready_accents)| {
            *ready_cell == cell && strokes.iter().map(|stroke| stroke.to_string()).collect::<Vec<_>>() == bar && ready_accents.to_vec() == accents
        });
        let name = ready.map_or(labels::MSG_OWN_BAR.to_string(), |(name, ..)| named_in(labels::MSG_READY_BAR_NAMES, name));
        named(
            marks::MSG_GUITAR_BAR_SHOWN,
            &[("name", name.as_str().into()), ("count", bar.len().into()), ("cell", cell.as_str().into())],
        )
    }

    /// A shape's section: its heading, then its start and end, each a percentage, how long it takes, and what it does then.
    fn shape_fields(&mut self, id: usize, shape: &str) -> Vec<Field> {
        let (lowest, highest) = match shape {
            "density" => (0, 100),
            "swell" => (0, 200),
            _ => (10, 200),
        };
        let name = named_in(labels::MSG_SHAPE_NAMES, shape);
        let setting = |part: &str| format!("{shape}_{part}");
        let label = |part: &str| named(&named_in(labels::MSG_SHAPE_FIELD_LABELS, part), &[("shape", name.as_str().into())]);
        let part_label = |part: &str| named_in(labels::MSG_SHAPE_PART_LABELS, part);
        let is_set = SHAPE_PARTS.iter().any(|part| self.written(&setting(part)).is_some());
        let mut fields = vec![Field::heading(id, &name, is_set, None, false)];
        for part in ["start", "end"] {
            let written = self.written(&setting(part)).and_then(Data::as_whole).map(|whole| whole as i64);
            let shown = written.map_or(marks::MSG_NONE_SHOWN.to_string(), |percent| {
                named(marks::MSG_SHAPE_PERCENT_SHOWN, &[("percent", percent.into())])
            });
            let field_id = self.id();
            fields.push(
                Field::number(field_id, &label(part), written, Some(lowest), Some(highest), 100, Some(shown))
                    .with_clear(legends::What::CLEAR)
                    .with_shown_label(&part_label(part))
                    .writing(&setting(part)),
            );
        }
        let over_id = self.id();
        let over = self.time_field(over_id, &label("over"), &setting("over"), labels::MSG_WHOLE_SPAN);
        fields.push(over.with_shown_label(&part_label("over")).writing(&setting("over")));
        let then = self.written(&setting("then")).map_or(SHAPE_THENS[0].to_string(), data_text);
        let then_id = self.id();
        fields.push(
            Field::choice(then_id, &label("then"), SHAPE_THENS.iter().map(|each| each.to_string()).collect(), &then, None)
                .with_shown_label(&part_label("then"))
                .writing(&setting("then")),
        );
        fields
    }

    /// A length of time chosen from the plain lengths, the first choice standing for none of its own.
    fn time_field(&mut self, id: usize, label: &str, setting: &str, first: &str) -> Field {
        let mut times: Vec<String> = TIME_CHOICES.iter().filter(|time| **time != first).map(|time| time.to_string()).collect();
        let current = self.written(setting).map_or(first.to_string(), data_text);
        if current != first && !times.contains(&current) {
            times.push(current.clone());
        }
        let mut choices = vec![first.to_string()];
        choices.extend(times);
        let name = |choice: &str| named_in(labels::MSG_TIME_NAMES, choice);
        let names: Vec<String> = choices.iter().map(|choice| name(choice)).collect();
        let mut field = Field::choice(id, label, choices, &current, Some(name(&current))).with_clear(&name(first));
        if let crate::forms::nodes::Kind::Choice { names: held, .. } = &mut field.kind {
            *held = Some(names);
        }
        field
    }

    fn enabled_field(&mut self) -> Field {
        let on = self.is_enabled();
        let id = self.id();
        Field::toggle(id, labels::MSG_ENABLED_LABEL, on)
    }

    fn fields_of(&mut self, setting: &'static SettingView) -> Vec<Field> {
        let id = self.id();
        self.views.push((id, setting));
        match setting {
            SettingView::Choice {
                setting,
                label,
                choices,
                default,
                names,
            } => {
                let current = self.written(setting).map_or_else(|| plain_text(default), data_text);
                let choices: Vec<String> = choices.iter().map(plain_text).collect();
                let shown = names.map(|names| {
                    names
                        .iter()
                        .find(|(choice, _)| plain_text(choice) == current)
                        .map_or(current.clone(), |(_, name)| name.to_string())
                });
                let mut field = Field::choice(id, label, choices.clone(), &current, shown);
                if let (Some(names), crate::forms::nodes::Kind::Choice { names: held, .. }) = (names, &mut field.kind) {
                    *held = Some(
                        choices
                            .iter()
                            .map(|choice| {
                                names
                                    .iter()
                                    .find(|(found, _)| plain_text(found) == *choice)
                                    .map_or(choice.clone(), |(_, name)| name.to_string())
                            })
                            .collect(),
                    );
                }
                vec![field]
            }
            SettingView::Number {
                setting,
                label,
                default,
                shown,
                zero_shown,
            } => {
                let number = self.written(setting).and_then(Data::as_whole).map(|whole| whole as i64);
                let (lowest, highest) = self.limits_of(setting);
                let default = default.as_ref().map(plain_text).and_then(|text| text.parse::<i64>().ok());
                let number_shown = |number: i64| {
                    if number == 0 && zero_shown.is_some() {
                        return zero_shown.map(str::to_string);
                    }
                    shown.map(|template| named(template, &[("number", number.into())]))
                };
                let (value, start, text) = match (number, default) {
                    (None, None) => (None, lowest.unwrap_or(0), Some(marks::MSG_NONE_SHOWN.to_string())),
                    (None, Some(default)) => (Some(default), default, number_shown(default)),
                    (Some(number), _) => (Some(number), lowest.unwrap_or(0), number_shown(number)),
                };
                let cleared = default.map_or(marks::MSG_NONE_SHOWN.to_string(), |default| {
                    number_shown(default).unwrap_or_else(|| default.to_string())
                });
                vec![Field::number(id, label, value, lowest, highest, start, text).with_clear(&cleared)]
            }
            SettingView::Toggle {
                setting,
                label,
                default,
                by_mode,
            } => {
                let mode = self.view.mode.map(|mode| self.chosen(mode));
                let toggle_default = by_mode
                    .and_then(|by_mode| by_mode.iter().find(|(found, _)| Some(plain_text(found)) == mode).map(|(_, on)| *on))
                    .unwrap_or(*default);
                let on = self.written(setting).map_or(toggle_default, |value| matches!(value, Data::Bool(true)));
                vec![Field::toggle(id, label, on)]
            }
            SettingView::Octave { setting, label, default } => {
                let octave = self.written(setting).and_then(Data::as_whole).map_or(*default, |whole| whole as i64);
                let setlist = self.app.document.get_setlist();
                vec![Field::custom(id, label, &shown_octave(setlist, octave).to_string())
                    .with_adjust()
                    .with_enter(legends::What::EDIT)
                    .with_clear(&shown_octave(setlist, *default).to_string())]
            }
            SettingView::Track { setting, label } => {
                let named_track = self.written(setting).map_or(marks::MSG_NONE_SHOWN.to_string(), data_text);
                let mut tracks: Vec<String> = self.app.document.song().get_track_names().into_iter().map(str::to_string).collect();
                if named_track != marks::MSG_NONE_SHOWN && !tracks.contains(&named_track) {
                    tracks.push(named_track.clone());
                }
                let mut choices = vec![marks::MSG_NONE_SHOWN.to_string()];
                choices.extend(crate::settings::sorted_names(&tracks));
                vec![Field::choice(id, label, choices, &named_track, None).with_clear(marks::MSG_NONE_SHOWN)]
            }
            SettingView::Offsets { setting, label } => {
                let shown = self
                    .written(setting)
                    .and_then(Data::as_list)
                    .map_or(marks::MSG_NONE_SHOWN.to_string(), |offsets| {
                        offsets
                            .iter()
                            .map(|offset| offset.as_whole().map_or(marks::MSG_NO_NUMBER_MARK.to_string(), |whole| whole.to_string()))
                            .collect::<Vec<_>>()
                            .join(" ")
                    });
                vec![Field::custom(id, label, &shown)
                    .with_enter(legends::What::EDIT)
                    .with_clear(marks::MSG_NONE_SHOWN)]
            }
            SettingView::Time { setting, label, first } => vec![self.time_field(id, label, setting, first.unwrap_or(marks::MSG_PATTERN_STEP_SHOWN))],
            SettingView::Steps { label, .. } => vec![Field::custom(id, label, marks::MSG_CONFIGURE_STEPS).with_enter(legends::What::EDIT)],
            SettingView::Restart => {
                let current = self.written(GENERATOR_RESTART).map_or(RESTARTS[0].to_string(), data_text);
                let choices: Vec<String> = RESTARTS.iter().map(|choice| choice.to_string()).collect();
                let names: Vec<String> = RESTARTS.iter().map(|choice| named_in(labels::MSG_RESTART_NAMES, choice)).collect();
                let mut field = Field::choice(
                    id,
                    labels::MSG_RESTART_LABEL,
                    choices,
                    &current,
                    Some(named_in(labels::MSG_RESTART_NAMES, &current)),
                );
                if let crate::forms::nodes::Kind::Choice { names: held, .. } = &mut field.kind {
                    *held = Some(names);
                }
                vec![field]
            }
            SettingView::Gauge {
                setting,
                label,
                lowest,
                highest,
                default,
            } => {
                let number = self.written(setting).and_then(Data::as_whole).map_or(*default, |whole| whole as i64);
                let drawn = format!(
                    "{}{}",
                    marks::MSG_WIZARD_GAUGE_FULL.repeat((number - (lowest + 1) + 1).max(0) as usize),
                    marks::MSG_WIZARD_GAUGE_EMPTY.repeat((highest - number).max(0) as usize)
                );
                let shown = named(
                    marks::MSG_WIZARD_PLAYER_GAUGE_SHOWN,
                    &[("gauge", drawn.as_str().into()), ("place", number.into())],
                );
                vec![Field::number(id, label, Some(number), Some(*lowest), Some(*highest), *lowest, Some(shown))]
            }
            SettingView::When { view, when } => {
                if !self.holds(when) {
                    return Vec::new();
                }
                self.fields_of(view)
            }
            SettingView::Progression { label } => {
                let song = self.app.document.song();
                let shape = song
                    .get_scale_name()
                    .map(|scale| crate::patterns::scale_half_steps(self.app.document.get_setlist(), &scale))
                    .filter(|shape| !shape.is_empty())
                    .unwrap_or_else(|| MAJOR_SHAPE.to_vec());
                let chords: Vec<i64> = self
                    .written("chords")
                    .and_then(Data::as_list)
                    .map_or(vec![1], |chords| chords.iter().filter_map(Data::as_whole).map(|whole| whole as i64).collect());
                let accidentals: Vec<Option<String>> = self
                    .written("accidentals")
                    .and_then(Data::as_list)
                    .map_or(Vec::new(), |items| items.iter().map(|item| item.as_str().map(str::to_string)).collect());
                let numerals: Vec<String> = chords
                    .iter()
                    .enumerate()
                    .map(|(place, degree)| roman_numeral(&shape, *degree, accidentals.get(place).cloned().flatten().as_deref()))
                    .collect();
                vec![Field::custom(id, label, &numerals.join(marks::MSG_NUMERALS_SEPARATOR)).with_enter(legends::What::EDIT)]
            }
            SettingView::Shape { shape } => self.shape_fields(id, shape),
            SettingView::DriftValues => self.drift_rows(),
            SettingView::Sections {
                caption,
                plays,
                plays_label,
                played,
                played_label,
                played_choices,
                defaults: _,
            } => self.section_table(caption, (plays, plays_label), (played, played_label), played_choices),
            SettingView::InheritedChoice {
                setting,
                label,
                choices,
                inherited_choice,
                inherited_shown,
                inherited_what,
            } => {
                let value = self.musician_own(setting);
                let (current, shown) = if self.written(setting).is_none() {
                    (inherited_choice.to_string(), named(inherited_shown, &[("value", value.as_str().into())]))
                } else {
                    (value.clone(), value)
                };
                let mut offered = vec![inherited_choice.to_string()];
                offered.extend(choices.iter().map(plain_text));
                vec![Field::choice(id, label, offered, &current, Some(shown)).with_clear(inherited_what)]
            }
            SettingView::GuitarBar { label } => vec![Field::custom(id, label, &self.bar_shown()).with_enter(legends::What::EDIT)],
            SettingView::Section { heading, settings } => {
                let is_set = settings
                    .iter()
                    .any(|inside| setting_name(inside).is_some_and(|name| self.written(name).is_some()));
                let mut fields = vec![Field::heading(id, heading, is_set, None, false)];
                for inside in settings.iter() {
                    fields.extend(self.fields_of(inside));
                }
                fields
            }
        }
    }
}

/// The major scale's half steps, which a song with no scale places degrees by.
const MAJOR_SHAPE: [i64; 7] = [0, 2, 4, 5, 7, 9, 11];
pub const ROMAN_NUMERALS: [&str; 7] = ["I", "II", "III", "IV", "V", "VI", "VII"];

/// A chord's Roman numeral in a scale: upper case major, lower case minor, a mark for diminished or augmented, a sharp or a
/// flat in front, the quality the triad the scale builds on the degree has, or the first degree's where it has an accidental.
fn roman_numeral(shape: &[i64], degree: i64, accidental: Option<&str>) -> String {
    let length = shape.len() as i64;
    let place = if accidental.is_some_and(|accidental| !accidental.is_empty()) {
        0
    } else {
        (degree - 1).rem_euclid(length)
    };
    let root = shape[place as usize];
    let third = (shape[((place + 2) % length) as usize] - root).rem_euclid(12);
    let fifth = (shape[((place + 4) % length) as usize] - root).rem_euclid(12);
    let quality = match (third, fifth) {
        (3, 7) => "minor",
        (3, 6) => "diminished",
        (4, 8) => "augmented",
        _ => "major",
    };
    let mut numeral = ROMAN_NUMERALS[(degree - 1).rem_euclid(7) as usize].to_string();
    if quality == "minor" || quality == "diminished" {
        numeral = numeral.to_lowercase();
    }
    let sign = accidental
        .map_or(String::new(), |accidental| named_in(marks::MSG_ACCIDENTAL_MARKS, accidental))
        .replace(accidental.unwrap_or("\u{0}"), "");
    let sign = if accidental.is_some_and(|accidental| marks::MSG_ACCIDENTAL_MARKS.iter().any(|(found, _)| *found == accidental)) {
        sign
    } else {
        String::new()
    };
    format!("{sign}{numeral}{}", named_in(marks::MSG_QUALITY_MARKS, quality))
}

/// The setting a view shows, where it shows one.
fn setting_name(view: &SettingView) -> Option<&'static str> {
    match view {
        SettingView::Choice { setting, .. }
        | SettingView::Number { setting, .. }
        | SettingView::Toggle { setting, .. }
        | SettingView::Octave { setting, .. }
        | SettingView::Track { setting, .. }
        | SettingView::Offsets { setting, .. }
        | SettingView::InheritedChoice { setting, .. }
        | SettingView::Gauge { setting, .. }
        | SettingView::Time { setting, .. }
        | SettingView::Steps { setting, .. } => Some(setting),
        _ => None,
    }
}

impl PluginEditor {
    /// The setting the field of an id writes by name, where it is a cell that says so.
    fn cell_writes(&self, app: &App, id: usize) -> Option<String> {
        self.made(app).0.iter().find_map(|field| field.find(id)).and_then(|field| field.writes.clone())
    }

    /// The generator's mode, as its mode view chooses it, where its kind has one.
    fn mode(&self, app: &App) -> Option<String> {
        let Some(Item::Generator(settings)) = app.document.get_setlist().get_item(self.section(), &self.name) else {
            return None;
        };
        let made = Made::of(app, self.kind, settings.written_data(), false);
        made.mode()
    }

    /// Write one of the generator's settings, or take it out of the file with None.
    fn write(&self, app: &mut App, setting: &str, value: Option<Data>) {
        let (section, name) = (self.section(), self.name.clone());
        app.document.change_set(|setlist| {
            if let Some(Item::Generator(settings)) = setlist.get_item_mut(section, &name) {
                settings.set_written(setting, value);
            }
        });
    }

    /// An end of a range of octaves as the generator holds it, its default where the file leaves it out.
    fn octave_of(&self, app: &App, setting: &str, default: i64) -> i64 {
        match app.document.get_setlist().get_item(self.section(), &self.name) {
            Some(Item::Generator(settings)) => settings.get_written(setting).and_then(Data::as_whole).map_or(default, |whole| whole as i64),
            _ => default,
        }
    }

    /// The lowest and highest an end of a range of octaves may be: its description's, and never past the range's other end.
    fn octave_range(&self, app: &App, setting: &str) -> (i64, i64) {
        let (lowest, highest) = octave_limits(self.kind, setting);
        let other_end = |other: &str| {
            self.made(app).1.into_iter().find_map(|(_, view)| match view {
                SettingView::Octave { setting: found, default, .. } if *found == other => Some(self.octave_of(app, other, *default)),
                _ => None,
            })
        };
        match setting {
            LOWEST_OCTAVE => (lowest, other_end(HIGHEST_OCTAVE).unwrap_or(highest)),
            HIGHEST_OCTAVE => (other_end(LOWEST_OCTAVE).unwrap_or(lowest), highest),
            _ => (lowest, highest),
        }
    }

    /// Store what a key did to the generator's Bypass When statements, or open the dialog it asks for.
    fn change_statements(&self, app: &mut App, id: usize, edit: &Edit) {
        use crate::forms::statements::{statement_change, with_statement, StatementChange};
        let statements = match app.document.get_setlist().get_item(self.section(), &self.name) {
            Some(Item::Generator(settings)) => settings
                .get_written(BYPASS_WHEN)
                .and_then(Data::as_list)
                .map(<[Data]>::to_vec)
                .unwrap_or_default(),
            _ => Vec::new(),
        };
        match statement_change(&statements, STATEMENT_IDS, id, edit) {
            StatementChange::Ask(asked) => app.asking = Some(asked),
            StatementChange::Refuse(refusal) => app.refuse(refusal),
            StatementChange::Store { place, statement } => self.write(app, BYPASS_WHEN, with_statement(&statements, place, statement)),
            StatementChange::Nothing => {}
        }
    }

    fn section(&self) -> &'static str {
        PLUGINS.iter().find(|plugin| plugin.name == self.kind).map_or("", |plugin| plugin.section)
    }
}

impl Form for PluginEditor {
    fn name(&self) -> &'static str {
        "PluginEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn slot_keys(&self) -> Option<(&'static crate::keybindings::Binding, &'static crate::keybindings::Binding)> {
        Some((&Keys::SLOT_LESS, &Keys::SLOT_MORE))
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::GENERATORS.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
        ]
    }

    fn caption(&self, _app: &App) -> Option<String> {
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[
                ("what", caption_word(self.kind).to_uppercase().as_str().into()),
                ("name", self.name.as_str().into()),
            ],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GENERATORS)
    }

    fn form(&self, app: &App) -> Vec<Node> {
        self.made(app).0.into_iter().map(|field| Node::Field(Box::new(field))).collect()
    }

    fn remarks(&self, _app: &App, _width: usize) -> Vec<Text> {
        Vec::new()
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        if id >= STATEMENT_IDS {
            self.change_statements(app, id, &edit);
            return;
        }
        let view = self.made(app).1.into_iter().find(|(found, _)| *found == id).map(|(_, view)| view);
        match (view, edit) {
            (Some(SettingView::Offsets { setting, .. }), Edit::Enter) => {
                let (section, name) = (self.section(), self.name.clone());
                let has_offsets = matches!(app.document.get_setlist().get_item(section, &name), Some(Item::Generator(settings)) if settings.get_written(setting).is_some_and(|value| !value.is_null()));
                if !has_offsets {
                    app.document.change_set(|setlist| {
                        if let Some(Item::Generator(settings)) = setlist.get_item_mut(section, &name) {
                            settings.set_written(setting, Some(Data::List(vec![Data::Whole(0); NEW_OFFSET_STEPS])));
                        }
                    });
                }
                app.show_page(Box::new(crate::screens::one_row_editor::OneRowEditor::new(
                    crate::screens::generators::offsets_editor::OffsetsEditor { name },
                )));
            }
            (Some(SettingView::Steps { setting, row_name, note, .. }), Edit::Enter) => {
                let editor = crate::screens::generators::step_row_editor::StepRowEditor {
                    kind: self.kind,
                    section: self.section(),
                    name: self.name.clone(),
                    setting,
                    row_name,
                    note,
                };
                app.show_page(Box::new(crate::screens::one_row_editor::OneRowEditor::new(editor)));
            }
            (Some(SettingView::GuitarBar { .. }), Edit::Enter) => {
                let editor = crate::screens::generators::guitar_bar_editor::GuitarBarEditor { name: self.name.clone() };
                app.show_page(Box::new(crate::screens::one_row_editor::OneRowEditor::new(editor)));
            }
            (Some(SettingView::Progression { .. }), Edit::Enter) => {
                let editor = crate::screens::generators::chords_editor::ChordsEditor {
                    section: self.section(),
                    name: self.name.clone(),
                    edited_row: 0,
                };
                app.show_page(Box::new(crate::screens::one_row_editor::OneRowEditor::new(editor)));
            }
            (Some(SettingView::Octave { setting, label, default }), Edit::Enter) => {
                // The octave is typed as the set's octave labels show it, within the ends the other end of the range leaves.
                let (lowest, highest) = self.octave_range(app, setting);
                let current = self.octave_of(app, setting, *default);
                let setlist = app.document.get_setlist();
                app.asking = Some(Edit::AskNumber {
                    title: label.to_string(),
                    value: shown_octave(setlist, current),
                    lowest: Some(shown_octave(setlist, lowest)),
                    highest: Some(shown_octave(setlist, highest)),
                });
            }
            (Some(SettingView::Octave { setting, default, .. }), Edit::Number(shown)) => {
                let stored = shown - shown_octave(app.document.get_setlist(), 0);
                self.write(app, setting, (stored != *default).then_some(Data::Whole(stored as i128)));
            }
            (Some(SettingView::Octave { setting, default, .. }), Edit::Adjust(offset)) => {
                let written = self.octave_of(app, setting, *default);
                let (lowest, highest) = self.octave_range(app, setting);
                let moved = (written + offset).clamp(MIN_OCTAVE, MAX_OCTAVE).clamp(lowest, highest);
                self.write(app, setting, (moved != *default).then_some(Data::Whole(moved as i128)));
            }
            (Some(view), edit) => {
                let mode = self.mode(app);
                if let Some((setting, value)) = view_write(view, &edit, mode.as_deref()) {
                    self.write(app, setting, value);
                }
            }
            (None, edit) if self.cell_writes(app, id).is_some() => {
                let setting = self.cell_writes(app, id).unwrap_or_default();
                let written = match app.document.get_setlist().get_item(self.section(), &self.name) {
                    Some(Item::Generator(settings)) => settings.get_written(&setting).cloned(),
                    _ => None,
                };
                match edit {
                    Edit::Clear => self.write(app, &setting, None),
                    Edit::Enter if setting.ends_with("_scale") || setting.ends_with("_root") => {
                        let choices = drift_choices(app, &setting);
                        let label = self
                            .made(app)
                            .0
                            .iter()
                            .find_map(|field| field.find(id))
                            .map(|field| field.label.clone())
                            .unwrap_or_default();
                        let current = written.as_ref().and_then(Data::as_str).unwrap_or_default().to_string();
                        let mut options = vec![marks::MSG_NONE_SHOWN.to_string()];
                        options.extend(choices.iter().cloned());
                        let mut answers = vec![String::new()];
                        answers.extend(choices);
                        let place = answers.iter().position(|answer| *answer == current).unwrap_or(0);
                        app.asking = Some(Edit::AskChoice {
                            title: label,
                            options,
                            current: place,
                            choices: answers,
                        });
                    }
                    Edit::Choice(chosen) => self.write(app, &setting, (!chosen.is_empty()).then_some(Data::Text(chosen))),
                    Edit::Enter => {
                        let (lowest, highest) = setting_limits(self.kind, &setting);
                        let label = self
                            .made(app)
                            .0
                            .iter()
                            .find_map(|field| field.find(id))
                            .map(|field| field.label.clone())
                            .unwrap_or_default();
                        let number = written.as_ref().and_then(Data::as_whole).map_or(0, |whole| whole as i64);
                        let words = [("row", label.as_str().into()), ("low", lowest.into()), ("high", highest.into())];
                        app.asking = Some(Edit::AskNumber {
                            title: named(messages::MSG_NUMBER_PROMPT, &words),
                            value: number,
                            lowest: Some(lowest),
                            highest: Some(highest),
                        });
                    }
                    Edit::Number(number) => self.write(app, &setting, (number != 0).then_some(Data::Whole(number as i128))),
                    Edit::Adjust(offset) if setting.ends_with("_scale") || setting.ends_with("_root") => {
                        let mut choices = vec![None];
                        choices.extend(drift_choices(app, &setting).into_iter().map(Some));
                        let current = written.as_ref().and_then(Data::as_str).map(str::to_string);
                        let place = choices.iter().position(|choice| *choice == current).unwrap_or(0) as i64;
                        let chosen = choices[(place + offset).clamp(0, choices.len() as i64 - 1) as usize].clone();
                        self.write(app, &setting, chosen.map(Data::Text));
                    }
                    Edit::Adjust(offset) => {
                        let (lowest, highest) = setting_limits(self.kind, &setting);
                        let number = written.as_ref().and_then(Data::as_whole).map_or(0, |whole| whole as i64);
                        let moved = (number + offset).clamp(lowest, highest);
                        self.write(app, &setting, (moved != 0).then_some(Data::Whole(moved as i128)));
                    }
                    edit => {
                        let field = self.made(app).0.iter().find_map(|field| field.find(id).cloned());
                        if let Some(value) = field.and_then(|field| field.written(&edit)) {
                            self.write(app, &setting, value);
                        }
                    }
                }
            }
            (None, Edit::Toggle(on)) if id == ENABLED => self.write(app, GENERATOR_ENABLED, (!on).then_some(Data::Bool(false))),
            _ => {}
        }
    }
}

impl PluginEditor {
    /// The page's fields, each with the view it shows by its id.
    fn made(&self, app: &App) -> (Vec<Field>, Vec<(usize, &'static SettingView)>) {
        let Some(Item::Generator(settings)) = app.document.get_setlist().get_item(self.section(), &self.name) else {
            return (Vec::new(), Vec::new());
        };
        let data = settings.written_data();
        let mut made = Made::of(app, self.kind, data, false);
        let view = made.view;
        let mut fields = vec![Field::name(NAME, &self.name), made.enabled_field()];
        let mode = view.mode.map(|mode| made.chosen(mode));
        if let Some(mode_view) = view.mode {
            fields.extend(made.fields_of(mode_view));
        }
        for column in view.columns {
            if !column.modes.is_empty() && !column.modes.iter().any(|each| Some(plain_text(each)) == mode) {
                continue;
            }
            for setting in column.settings {
                fields.extend(made.fields_of(setting));
            }
        }
        if self.kind != "drift" {
            let id = made.id();
            fields.push(Field::heading(id, labels::MSG_BYPASS_WHEN_LABEL, false, Some(String::new()), false));
            let held = made.written(BYPASS_WHEN).and_then(Data::as_list).map(<[Data]>::to_vec).unwrap_or_default();
            fields.extend(crate::forms::statements::statement_lines(0, &held, STATEMENT_IDS));
        }
        (fields, made.views)
    }
}
