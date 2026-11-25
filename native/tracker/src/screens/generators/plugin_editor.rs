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
use llamatron_model::objects::named::GeneratorSettings;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::{GENERATOR_ENABLED, GENERATOR_RESTART, RESTARTS, TIME_CHOICES};
use llamatron_model::schema::generated::limits::MAX_STATEMENTS;
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_model::schema::generated::settings::{Described, Plain};
use llamatron_strings::{labels, legends, marks, named};

const NAME: usize = 0;
/// How many steps an arpeggiator's offsets start with when its Offsets field first opens them.
const NEW_OFFSET_STEPS: usize = 8;

pub struct PluginEditor {
    pub kind: &'static str,
    pub name: String,
}

/// A plugin's word for what its page edits.
fn caption_word(kind: &str) -> &'static str {
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

fn data_text(value: &Data) -> String {
    match value {
        Data::Text(text) => text.clone(),
        Data::Whole(whole) => whole.to_string(),
        Data::Bool(flag) => if *flag { "True" } else { "False" }.to_string(),
        _ => String::new(),
    }
}

/// What a page asks of a generator's settings while its fields are made.
struct Made<'a> {
    settings: &'a GeneratorSettings,
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
        self.settings.get_written(setting).filter(|value| !value.is_null())
    }

    fn chosen(&self, setting: &SettingView) -> String {
        let SettingView::Choice { setting, default, .. } = setting else {
            return String::new();
        };
        self.written(setting).map_or_else(|| plain_text(default), data_text)
    }

    fn limits_of(&self, setting: &str) -> (Option<i64>, Option<i64>) {
        match self
            .settings
            .get_table()
            .iter()
            .find(|found| found.name == setting)
            .map(|found| found.described)
        {
            Some(Described::WholeNumber { lowest, highest, .. }) => (lowest, highest),
            _ => (None, None),
        }
    }

    fn enabled_field(&mut self) -> Field {
        let on = self.written(GENERATOR_ENABLED).is_none_or(|value| matches!(value, Data::Bool(true)));
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
            SettingView::Time { setting, label, first } => {
                let first = first.unwrap_or(marks::MSG_PATTERN_STEP_SHOWN).to_string();
                let mut times: Vec<String> = TIME_CHOICES.iter().filter(|time| **time != first).map(|time| time.to_string()).collect();
                let current = self.written(setting).map_or(first.clone(), data_text);
                if current != first && !times.contains(&current) {
                    times.push(current.clone());
                }
                let mut choices = vec![first.clone()];
                choices.extend(times);
                let name = |choice: &str| named_in(labels::MSG_TIME_NAMES, choice);
                let names: Vec<String> = choices.iter().map(|choice| name(choice)).collect();
                let mut field = Field::choice(id, label, choices, &current, Some(name(&current))).with_clear(&name(&first));
                if let crate::forms::nodes::Kind::Choice { names: held, .. } = &mut field.kind {
                    *held = Some(names);
                }
                vec![field]
            }
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
                if self.written(when).is_none() {
                    return Vec::new();
                }
                self.fields_of(view)
            }
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
            _ => vec![Field::custom(id, "(not ported)", "")],
        }
    }
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

    /// Whether the plugin's view uses only the kinds of field ported so far.
    fn is_ported(&self, app: &App) -> bool {
        self.made(app).1.iter().all(|(_, view)| {
            !matches!(
                view,
                SettingView::Progression { .. }
                    | SettingView::GuitarBar { .. }
                    | SettingView::DriftValues
                    | SettingView::Sections { .. }
                    | SettingView::Shape { .. }
                    | SettingView::InheritedChoice { .. }
            )
        })
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
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
            (Some(SettingView::Steps { .. }), Edit::Enter) => app.show_page(Box::new(crate::screens::not_ported::NotPorted {
                name: "StepRowEditor".to_string(),
            })),
            (Some(SettingView::GuitarBar { .. }), Edit::Enter) => app.show_page(Box::new(crate::screens::not_ported::NotPorted {
                name: "GuitarBarEditor".to_string(),
            })),
            (Some(SettingView::Progression { .. }), Edit::Enter) => app.show_page(Box::new(crate::screens::not_ported::NotPorted {
                name: "ChordsEditor".to_string(),
            })),
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
        let view = VIEWS
            .iter()
            .find(|(name, _)| *name == self.kind)
            .map(|(_, view)| *view)
            .expect("every plugin has a view");
        let mut made = Made {
            settings,
            view,
            app,
            next_id: NAME,
            views: Vec::new(),
        };
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
            for place in 0..MAX_STATEMENTS as usize {
                let id = made.id();
                let label = labels::MSG_STATEMENT_LINE_LABEL.repeat(place + 1);
                fields.push(Field::cells(
                    id,
                    &label,
                    vec![
                        Field::custom(id, labels::MSG_STATEMENT_REGISTER_TITLE, &format!("{:<4}", labels::MSG_STATEMENT_IGNORED))
                            .with_enter(legends::What::CHOOSE),
                    ],
                ));
            }
        }
        (fields, made.views)
    }
}
