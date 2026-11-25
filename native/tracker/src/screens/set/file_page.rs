// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The File/Global page (the Python screens/set/file_page.py and pages/file_global.py): the set's own settings in three
//! tabs, Settings, Notes & Octaves and Visualizers, its buttons New, Open, Save and Save As, and under them where the set's
//! file is and where the current song exports.

use crate::app::App;
use crate::drawing::Style;
use crate::forms::nodes::{Edit, Field};
use crate::forms::tab_box::{Tab, TabBox, TabColumn};
use crate::keybindings::{FilePage as Keys, KeyClass};
use crate::screens::field_page::{Form, Node};
use crate::settings::{bool_of, choice_of, hidden_visualizers, mode_name, named_in, octave_labels, shown_octave, text_of, whole_of};
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::defaults;
use llamatron_model::schema::generated::file_format::{SetlistSetting, FOLLOW_ACTION_CHOICES, OCTAVE_LABEL_CHOICES, STEP_SIZE_CHOICES, VISUALIZER_NAMES};
use llamatron_model::schema::generated::limits::{MAX_OCTAVE, MIN_OCTAVE};
use llamatron_strings::{labels, legends, marks, messages, named};

/// The fields, by id.
const TITLE: usize = 0;
const AUTHOR: usize = 1;
const DESCRIPTION: usize = 2;
const NOTES: usize = 3;
const FOLLOW: usize = 4;
const PROTECTED: usize = 5;
const DRUM_OCTAVE: usize = 6;
const OCTAVE: usize = 7;
const OCTAVE_LABELS: usize = 8;
const STEP_SIZE: usize = 9;
const VISUALIZER: usize = 10;
const HIDDEN: usize = 11;
const NEW: usize = 12;
const OPEN: usize = 13;
const SAVE: usize = 14;
const SAVE_AS: usize = 15;

pub struct FilePage;

fn strings(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| value.to_string()).collect()
}

impl FilePage {
    fn settings_fields(&self, app: &App) -> Vec<Field> {
        let setlist = app.document.get_setlist();
        let follow = choice_of(setlist, SetlistSetting::DEFAULT_FOLLOW_ACTION, defaults::DEFAULT_FOLLOW_ACTION);
        let mut follow_field = Field::choice(
            FOLLOW,
            labels::MSG_DEFAULT_FOLLOW_ACTION_LABEL,
            strings(FOLLOW_ACTION_CHOICES),
            &follow,
            Some(named_in(labels::MSG_FOLLOW_ACTION_NAMES, &follow)),
        );
        set_names(
            &mut follow_field,
            FOLLOW_ACTION_CHOICES
                .iter()
                .map(|choice| named_in(labels::MSG_FOLLOW_ACTION_NAMES, choice))
                .collect(),
        );
        let notes = text_of(setlist, SetlistSetting::NOTES);
        let first = notes.split('\n').next().unwrap_or("").trim().to_string();
        vec![
            Field::text(TITLE, labels::MSG_TITLE_LABEL, &text_of(setlist, SetlistSetting::TITLE), ""),
            Field::text(AUTHOR, labels::MSG_AUTHOR_LABEL, &text_of(setlist, SetlistSetting::AUTHOR), ""),
            Field::text(DESCRIPTION, labels::MSG_DESCRIPTION_LABEL, &text_of(setlist, SetlistSetting::DESCRIPTION), ""),
            Field::custom(NOTES, labels::MSG_NOTES_LABEL, if first.is_empty() { marks::MSG_NONE_SHOWN } else { &first }).with_enter(legends::What::EDIT),
            follow_field,
            Field::toggle(
                PROTECTED,
                labels::MSG_PROTECTED_LABEL,
                bool_of(setlist, SetlistSetting::PROTECTED, defaults::DEFAULT_PROTECTED),
            ),
        ]
    }

    fn notes_and_octaves_fields(&self, app: &App) -> Vec<Field> {
        let setlist = app.document.get_setlist();
        let drum = whole_of(setlist, SetlistSetting::DEFAULT_DRUM_OCTAVE, defaults::DEFAULT_DRUM_OCTAVE);
        let octave = whole_of(setlist, SetlistSetting::DEFAULT_OCTAVE, defaults::DEFAULT_OCTAVE);
        let labels_now = octave_labels(setlist);
        let mut octave_labels_field = Field::choice(
            OCTAVE_LABELS,
            labels::MSG_OCTAVE_LABELS_LABEL,
            strings(OCTAVE_LABEL_CHOICES),
            &labels_now,
            Some(named_in(labels::MSG_OCTAVE_LABEL_NAMES, &labels_now)),
        );
        set_names(
            &mut octave_labels_field,
            OCTAVE_LABEL_CHOICES
                .iter()
                .map(|choice| named_in(labels::MSG_OCTAVE_LABEL_NAMES, choice))
                .collect(),
        );
        let step_size = choice_of(setlist, SetlistSetting::STEP_SIZE, defaults::DEFAULT_STEP_SIZE);
        vec![
            Field::custom(DRUM_OCTAVE, labels::MSG_DEFAULT_DRUM_OCTAVE_LABEL, &shown_octave(setlist, drum).to_string()).with_adjust(),
            Field::custom(OCTAVE, labels::MSG_DEFAULT_OCTAVE_LABEL, &shown_octave(setlist, octave).to_string()).with_adjust(),
            octave_labels_field,
            Field::choice(STEP_SIZE, labels::MSG_STEP_SIZE_LABEL, strings(STEP_SIZE_CHOICES), &step_size, None),
        ]
    }

    fn visualizer_fields(&self, app: &App) -> Vec<Field> {
        let setlist = app.document.get_setlist();
        let current = setlist
            .get_written(SetlistSetting::VISUALIZER)
            .and_then(|value| value.as_str())
            .map(str::to_string);
        let first = marks::MSG_NONE_SHOWN;
        let mut choices = vec![first.to_string()];
        choices.extend(strings(VISUALIZER_NAMES));
        let mut names = vec![first.to_string()];
        names.extend(VISUALIZER_NAMES.iter().map(|name| mode_name(name)));
        let shown = current.as_deref().map_or(first.to_string(), mode_name);
        let mut visualizer = Field::choice(
            VISUALIZER,
            labels::MSG_VISUALIZER_LABEL,
            choices,
            current.as_deref().unwrap_or(first),
            Some(shown),
        );
        set_names(&mut visualizer, names);
        let hidden = hidden_visualizers(setlist);
        let hidden_shown = if hidden.is_empty() {
            marks::MSG_NONE_SHOWN.to_string()
        } else {
            hidden
                .iter()
                .map(|name| mode_name(name))
                .collect::<Vec<_>>()
                .join(marks::MSG_DETAILS_LIST_SEPARATOR)
        };
        vec![
            visualizer,
            Field::custom(HIDDEN, labels::MSG_HIDE_VISUALIZERS_LABEL, &hidden_shown).with_enter(legends::What::CHOOSE),
        ]
    }

    fn buttons(&self) -> Vec<Field> {
        vec![
            Field::button(NEW, labels::MSG_NEW_SET_BUTTON, "", legends::MSG_NEW_WHAT),
            Field::button(OPEN, labels::PageName::OPEN, Keys::OPEN_SET.name, Keys::OPEN_SET.what),
            Field::button(SAVE, labels::PageName::SAVE, Keys::SAVE.name, Keys::SAVE.what),
            Field::button(SAVE_AS, labels::MSG_SAVE_AS_BUTTON, "", legends::MSG_SAVE_AS_WHAT),
        ]
    }
}

/// A choice's names in its picker, where they aren't the choices themselves.
fn set_names(field: &mut Field, names: Vec<String>) {
    if let crate::forms::nodes::Kind::Choice { names: held, .. } = &mut field.kind {
        *held = Some(names);
    }
}

impl Form for FilePage {
    fn name(&self) -> &'static str {
        "FilePage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::FILE.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::SET_FILE)
    }

    fn form(&self, app: &App) -> Vec<Node> {
        let tabs = vec![
            Tab::new(labels::MSG_SETTINGS_TAB, vec![TabColumn::new(None, self.settings_fields(app))]),
            Tab::new(
                labels::MSG_NOTES_AND_OCTAVES_TAB,
                vec![TabColumn::new(None, self.notes_and_octaves_fields(app))],
            ),
            Tab::new(labels::MSG_VISUALIZERS_TAB, vec![TabColumn::new(None, self.visualizer_fields(app))]),
        ];
        let mut nodes = vec![Node::TabBox(TabBox {
            label: labels::MSG_TABS_LABEL.to_string(),
            tabs,
        })];
        nodes.extend(self.buttons().into_iter().map(|field| Node::Field(Box::new(field))));
        nodes
    }

    fn remarks(&self, app: &App, _width: usize) -> Vec<Text> {
        let document = &app.document;
        let path = document
            .get_path()
            .map_or(marks::MSG_NOT_SAVED_YET.to_string(), |path| path.to_string_lossy().to_string());
        let exports = match document.get_path() {
            None => marks::MSG_EXPORTS_AFTER_SAVING.to_string(),
            Some(path) => {
                let directory = path
                    .parent()
                    .map(|parent| parent.to_string_lossy().to_string())
                    .filter(|parent| !parent.is_empty())
                    .unwrap_or_else(|| ".".to_string());
                let stem = path.file_stem().map(|stem| stem.to_string_lossy().to_string()).unwrap_or_default();
                let prefix = format!("{directory}/{stem}_{}", document.get_current_song_name());
                named(marks::MSG_EXPORTS_BESIDE, &[("prefix", prefix.as_str().into())])
            }
        };
        vec![
            Text::styled(&named(messages::MSG_FILE_NOTE, &[("path", path.as_str().into())]), Style::DIM),
            Text::styled(&named(messages::MSG_EXPORTS_NOTE, &[("where", exports.as_str().into())]), Style::DIM),
        ]
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        let setlist = app.document.get_setlist();
        let whole = |name: &str, default: i64| setlist.get_written(name).and_then(Data::as_whole).map_or(default, |whole| whole as i64);
        let octave = |current: i64, offset: i64| (current + offset).clamp(MIN_OCTAVE, MAX_OCTAVE);
        let written: Option<(&str, Option<Data>)> = match (id, &edit) {
            (TITLE | AUTHOR | DESCRIPTION, Edit::Text(text)) => {
                let setting = match id {
                    TITLE => SetlistSetting::TITLE,
                    AUTHOR => SetlistSetting::AUTHOR,
                    _ => SetlistSetting::DESCRIPTION,
                };
                let text = text.trim();
                Some((setting, (!text.is_empty()).then(|| Data::text(text))))
            }
            (FOLLOW, Edit::Choice(chosen)) => Some((SetlistSetting::DEFAULT_FOLLOW_ACTION, Some(Data::text(chosen)))),
            (PROTECTED, Edit::Toggle(on)) => Some((SetlistSetting::PROTECTED, Some(Data::Bool(*on)))),
            (DRUM_OCTAVE, Edit::Adjust(offset)) => {
                let current = whole(SetlistSetting::DEFAULT_DRUM_OCTAVE, defaults::DEFAULT_DRUM_OCTAVE);
                Some((SetlistSetting::DEFAULT_DRUM_OCTAVE, Some(Data::Whole(octave(current, *offset) as i128))))
            }
            (OCTAVE, Edit::Adjust(offset)) => {
                let current = whole(SetlistSetting::DEFAULT_OCTAVE, defaults::DEFAULT_OCTAVE);
                Some((SetlistSetting::DEFAULT_OCTAVE, Some(Data::Whole(octave(current, *offset) as i128))))
            }
            (OCTAVE_LABELS, Edit::Choice(chosen)) => Some((SetlistSetting::OCTAVE_LABELS, Some(Data::text(chosen)))),
            (STEP_SIZE, Edit::Choice(chosen)) => Some((SetlistSetting::STEP_SIZE, Some(Data::text(chosen)))),
            (VISUALIZER, Edit::Choice(chosen)) => {
                let value = (chosen != marks::MSG_NONE_SHOWN).then(|| Data::text(chosen));
                Some((SetlistSetting::VISUALIZER, llamatron_model::objects::song::sensible_visualizer(value)))
            }
            _ => None,
        };
        if let Some((setting, value)) = written {
            app.document.change_set(|setlist| setlist.set_written(setting, value));
            return;
        }
        if id == NOTES && edit == Edit::Enter {
            let page = crate::screens::set::notes_page::NotesPage::new(app, true);
            app.show_page(Box::new(page));
        }
    }
}
