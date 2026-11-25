// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A clip's page (the Python screens/arrange/clip_page.py, pages/clip.py and the clip's part of pages/arrange_tabs.py): its
//! name, its patterns with a + row, then its settings in tabs: its order and what it plays, its velocity, its shapes, the
//! draws it resets, a tab for each generator built into it and its other generators; then its Listen button, and under
//! them how long it plays.

use crate::app::App;
use crate::drawing::Style;
use crate::forms::nodes::{Edit, Field};
use crate::forms::tab_box::{Tab, TabBox, TabColumn};
use crate::keybindings::{ClipPage as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::lengths::Lengths;
use crate::page::{clock, Duration};
use crate::screens::arrange::arrange_tabs::{self, built_in_kinds, built_in_on, tab_label_of, whole};
use crate::screens::field_page::{Form, Node};
use crate::settings::named_in;
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::{ClipSlot, Scene};
use llamatron_model::schema::generated::defaults::DEFAULT_FOLLOW_ACTION;
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, SetlistSetting, TrackSetting, FOLLOW_ACTION_CHOICES, PATTERN_ORDERS};
use llamatron_model::schema::generated::limits::{MAX_CLIP_REPEAT, MAX_NAME_LENGTH};
use llamatron_strings::{labels, legends, marks, messages, named, names};

const NAME: usize = 0;
const PATTERN_ORDER: usize = 1;
const DIRECTION: usize = 2;
const REPEAT: usize = 3;
const LOOP: usize = 4;
const MORPH_TO: usize = 5;
const MORPH_STYLE: usize = 6;
const FOLLOW_ACTION: usize = 7;
const SCALE: usize = 8;
const GRAB_TRACK: usize = 9;
const LISTEN: usize = 10;
/// The pattern rows' ids, a row a pattern, then the + row's.
const FIRST_PATTERN: usize = 20;
const ADD_ROW: usize = 99;
/// How many ids each built-in tab's fields have to themselves, past the shared tabs' own.
const BUILT_IN_IDS: usize = 1000;
/// The morph style a clip takes where it names none.
const FIRST_MORPH_STYLE: &str = "left";

pub struct ClipPage {
    pub index: usize,
    pub track: String,
}

fn words(name: &str) -> String {
    name.replace('_', " ")
}

impl ClipPage {
    /// Write one of the clip's settings, or take it out of the file with None.
    fn write(&self, app: &mut App, setting: &str, value: Option<Data>) {
        arrange_tabs::write_in_song(app, |song| song.set_clip_written(self.index, &self.track, setting, value));
    }

    /// Store what a key did to one of the clip's fields, its built-in generators' among them; false where the field writes
    /// nothing so.
    fn write_edit(&self, app: &mut App, id: usize, edit: &Edit) -> bool {
        use llamatron_model::schema::generated::file_format::DIRECTIONS;
        let Some(clip) = self.clip_slot(app) else { return false };
        if (BUILT_IN_IDS..BUILT_IN_IDS * (built_in_kinds().len() + 1)).contains(&id) {
            let Some(kind) = built_in_kinds().get(id / BUILT_IN_IDS - 1).copied() else {
                return false;
            };
            let built_ins = clip.get_written(ClipSlotSetting::BUILT_IN);
            let Some((setting, value)) = arrange_tabs::built_in_edit(app, built_ins, kind, BUILT_IN_IDS * (id / BUILT_IN_IDS), id, edit) else {
                return false;
            };
            let built_ins = arrange_tabs::with_built_in(built_ins, kind, setting, value);
            self.write(app, ClipSlotSetting::BUILT_IN, built_ins);
            return true;
        }
        match (id, edit) {
            (PATTERN_ORDER, Edit::Choice(chosen)) => self.write(app, ClipSlotSetting::PATTERN_ORDER, (chosen != PATTERN_ORDERS[0]).then(|| Data::text(chosen))),
            (DIRECTION, Edit::Adjust(offset)) => {
                let mut options = vec![None];
                options.extend(DIRECTIONS.iter().map(|direction| Some(direction.to_string())));
                let place = options.iter().position(|option| *option == clip.get_direction()).unwrap_or(0) as i64;
                let chosen = options[(place + offset).rem_euclid(options.len() as i64) as usize].clone();
                self.write(app, ClipSlotSetting::DIRECTION, chosen.map(Data::Text));
            }
            (DIRECTION, Edit::Clear) => self.write(app, ClipSlotSetting::DIRECTION, None),
            (REPEAT, Edit::Number(repeat)) => {
                let repeat = (*repeat).max(1);
                self.write(app, ClipSlotSetting::REPEAT, (repeat != 1).then_some(Data::Whole(repeat as i128)));
                if repeat < 2 {
                    self.write(app, ClipSlotSetting::MORPH_TO, None);
                    self.write(app, ClipSlotSetting::MORPH_STYLE, None);
                }
            }
            (LOOP, Edit::Toggle(on)) => self.write(app, ClipSlotSetting::LOOP, on.then_some(Data::Bool(true))),
            (FOLLOW_ACTION, Edit::Choice(chosen)) => self.write(app, ClipSlotSetting::FOLLOW_ACTION, Some(Data::text(chosen))),
            (SCALE, Edit::Clear) => self.write(app, ClipSlotSetting::SCALE, None),
            (GRAB_TRACK, Edit::Clear) => self.write(app, ClipSlotSetting::GRAB_TRACK, None),
            (DIRECTION, Edit::Enter) => {
                let mut rows = vec![(
                    labels::MSG_PATTERN_DIRECTION_OPTION.to_string(),
                    legends::MSG_PATTERN_DIRECTION_WHAT.to_string(),
                )];
                rows.extend(
                    DIRECTIONS
                        .iter()
                        .map(|direction| (words(direction), named_in(labels::MSG_DIRECTION_NAMES, direction))),
                );
                let mut choices = vec![arrange_tabs::FROM_ABOVE.to_string()];
                choices.extend(DIRECTIONS.iter().map(|direction| direction.to_string()));
                let current = clip.get_direction().unwrap_or_default();
                arrange_tabs::ask_choice(app, messages::MSG_PLAY_DIRECTION_TITLE, lined_up(&rows), choices, &current);
            }
            (DIRECTION, Edit::Choice(chosen)) => self.write(app, ClipSlotSetting::DIRECTION, arrange_tabs::chosen_name(chosen)),
            (SCALE, Edit::Enter) => {
                let scales = arrange_tabs::scale_names(app);
                let current = clip.get_written(ClipSlotSetting::SCALE).and_then(Data::as_str).map(str::to_string);
                arrange_tabs::ask_name_or_above(app, messages::MSG_CLIP_SCALE_TITLE, labels::MSG_SCENE_OPTION, scales, current.as_deref());
            }
            (SCALE, Edit::Choice(chosen)) => self.write(app, ClipSlotSetting::SCALE, arrange_tabs::chosen_name(chosen)),
            (GRAB_TRACK, Edit::Enter) => {
                let names: Vec<String> = app
                    .document
                    .song()
                    .get_track_names()
                    .into_iter()
                    .filter(|name| *name != self.track)
                    .map(str::to_string)
                    .collect();
                let tracks = crate::settings::sorted_names(&names);
                let current = clip.get_written(ClipSlotSetting::GRAB_TRACK).and_then(Data::as_str).map(str::to_string);
                arrange_tabs::ask_name_or_above(app, labels::MSG_GRAB_TRACK_LABEL, marks::MSG_NONE_SHOWN, tracks, current.as_deref());
            }
            (GRAB_TRACK, Edit::Choice(chosen)) => {
                // A grab that would go round in a circle is refused; the Python tells why in a dialog not ported yet.
                if chosen.is_empty() {
                    self.write(app, ClipSlotSetting::GRAB_TRACK, None);
                } else if !crate::screens::arrange::arrange_page::ArrangePage::grab_circles(app, self.index, &self.track, chosen) {
                    self.write(app, ClipSlotSetting::GRAB_TRACK, Some(Data::text(chosen)));
                }
            }
            (MORPH_TO, Edit::Clear) => {
                self.write(app, ClipSlotSetting::MORPH_TO, None);
                self.write(app, ClipSlotSetting::MORPH_STYLE, None);
            }
            (reset, Edit::Toggle(on)) if (arrange_tabs::RESET_IDS..arrange_tabs::GENERATORS).contains(&reset) => {
                let draws = arrange_tabs::draws_with_values(app.document.song());
                let Some(draw) = draws.get(reset - arrange_tabs::RESET_IDS) else {
                    return false;
                };
                let value = arrange_tabs::resets_after(clip.get_written(ClipSlotSetting::RESET_DRAWS), draw, *on);
                self.write(app, ClipSlotSetting::RESET_DRAWS, value);
            }
            _ => {
                let Some(field) = arrange_tabs::field_of(&self.form(app), id) else {
                    return false;
                };
                let (Some(setting), Some(value)) = (field.writes.clone(), field.written(edit)) else {
                    return false;
                };
                self.write(app, &setting, value);
            }
        }
        true
    }

    fn scene<'a>(&self, app: &'a App) -> Option<&'a Scene> {
        app.document.song().scenes().get(self.index)
    }

    fn clip_slot<'a>(&self, app: &'a App) -> Option<&'a ClipSlot> {
        self.scene(app).and_then(|scene| scene.get_clip_slot(&self.track))
    }

    fn scene_name(&self, app: &App) -> String {
        self.scene(app)
            .and_then(Scene::get_name)
            .unwrap_or_else(|| named(names::MSG_NEW_SCENE_NAME, &[("number", (self.index + 1).into())]))
    }

    fn name_shown(clip: &ClipSlot) -> String {
        match clip
            .get_written(ClipSlotSetting::NAME)
            .and_then(Data::as_str)
            .filter(|name| !name.is_empty())
            .map(str::to_string)
        {
            Some(name) if name.chars().count() <= MAX_NAME_LENGTH as usize => name,
            Some(name) => {
                let cut: String = name.chars().take(MAX_NAME_LENGTH as usize - 1).collect();
                format!("{cut}{}", marks::MSG_NAME_CUT)
            }
            None => named(marks::MSG_CLIP_NAMED_FOR_PATTERN, &[("pattern", clip.get_pattern_name().as_str().into())]),
        }
    }

    fn pattern_rows(clip: &ClipSlot) -> Vec<Field> {
        let mut rows: Vec<Field> = clip
            .get_pattern_names()
            .iter()
            .enumerate()
            .map(|(place, name)| {
                let label = if place == 0 { labels::MSG_PATTERNS_LABEL } else { "" };
                Field::custom(FIRST_PATTERN + place, label, name)
                    .with_enter(legends::What::EDIT)
                    .with_clear(legends::What::REMOVE)
            })
            .collect();
        rows.push(Field::custom(ADD_ROW, "", marks::MSG_NEW_ROW).with_enter(legends::What::ADD));
        rows
    }

    fn direction_text(app: &App, clip: &ClipSlot) -> String {
        if let Some(direction) = clip.get_direction() {
            return words(&direction);
        }
        if clip.get_pattern_names().len() > 1 {
            return marks::MSG_EACH_PATTERN_DIRECTION_SHOWN.to_string();
        }
        let direction = app
            .document
            .get_setlist()
            .get_pattern(&clip.get_pattern_name())
            .and_then(|pattern| pattern.get_direction())
            .unwrap_or_else(|| "forward".to_string());
        named(marks::MSG_PATTERN_DIRECTION_SHOWN, &[("direction", words(&direction).as_str().into())])
    }

    fn settings_tab(&self, app: &App, clip: &ClipSlot) -> Tab {
        let setlist = app.document.get_setlist();
        let order = clip.get_pattern_order().unwrap_or_else(|| PATTERN_ORDERS[0].to_string());
        let order_names: Vec<String> = PATTERN_ORDERS.iter().map(|choice| named_in(labels::MSG_PATTERN_ORDER_NAMES, choice)).collect();
        let mut order_field = Field::choice(
            PATTERN_ORDER,
            labels::MSG_PATTERN_ORDER_LABEL,
            PATTERN_ORDERS.iter().map(|choice| choice.to_string()).collect(),
            &order,
            Some(named_in(labels::MSG_PATTERN_ORDER_NAMES, &order)),
        );
        if let crate::forms::nodes::Kind::Choice { names: held, .. } = &mut order_field.kind {
            *held = Some(order_names);
        }
        let repeat = clip.get_repeat();
        let mut order_fields = vec![
            order_field,
            Field::custom(DIRECTION, labels::MSG_DIRECTION_LABEL, &Self::direction_text(app, clip))
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(legends::MSG_FROM_PATTERN_WHAT),
            Field::number(REPEAT, labels::MSG_REPEAT_LABEL, Some(repeat), Some(1), Some(MAX_CLIP_REPEAT), 1, None),
            Field::toggle(LOOP, labels::MSG_LOOP_LABEL, clip.loops()),
        ];
        if repeat > 1 {
            let target = clip.get_written(ClipSlotSetting::MORPH_TO).and_then(Data::as_str);
            order_fields.push(
                Field::custom(MORPH_TO, labels::MSG_MORPH_TO_LABEL, target.unwrap_or(marks::MSG_NONE_SHOWN))
                    .with_enter(legends::What::CHOOSE)
                    .with_clear(marks::MSG_NONE_SHOWN),
            );
            if target.is_some() {
                let style = clip
                    .get_written(ClipSlotSetting::MORPH_STYLE)
                    .and_then(Data::as_str)
                    .unwrap_or(FIRST_MORPH_STYLE);
                order_fields.push(
                    Field::custom(MORPH_STYLE, labels::MSG_MORPH_DIRECTION_LABEL, style)
                        .with_adjust()
                        .with_enter(legends::What::NEXT),
                );
            }
        }
        let written_action = clip.get_written(ClipSlotSetting::FOLLOW_ACTION).and_then(Data::as_str);
        let action = written_action
            .or_else(|| setlist.get_written(SetlistSetting::DEFAULT_FOLLOW_ACTION).and_then(Data::as_str))
            .unwrap_or(DEFAULT_FOLLOW_ACTION)
            .to_string();
        let action_name = named_in(labels::MSG_FOLLOW_ACTION_NAMES, &action);
        let shown = if written_action.is_none() {
            named(marks::MSG_FROM_SET_SHOWN, &[("value", action_name.as_str().into())])
        } else {
            action_name
        };
        let mut action_field = Field::choice(
            FOLLOW_ACTION,
            labels::MSG_FOLLOW_ACTION_LABEL,
            FOLLOW_ACTION_CHOICES.iter().map(|choice| choice.to_string()).collect(),
            &action,
            Some(shown),
        );
        if let crate::forms::nodes::Kind::Choice { names: held, .. } = &mut action_field.kind {
            *held = Some(
                FOLLOW_ACTION_CHOICES
                    .iter()
                    .map(|choice| named_in(labels::MSG_FOLLOW_ACTION_NAMES, choice))
                    .collect(),
            );
        }
        order_fields.push(action_field);
        let scale = match clip.get_scale_name() {
            Some(own) => own,
            None => {
                let scene_scale = self.scene(app).and_then(Scene::get_scale_name);
                let scale = scene_scale
                    .or_else(|| app.document.song().get_scale_name())
                    .unwrap_or_else(|| messages::MSG_NO_SCALE.to_string());
                named(marks::MSG_SCENE_SCALE_SHOWN, &[("scale", scale.as_str().into())])
            }
        };
        let grab = clip
            .get_written(ClipSlotSetting::GRAB_TRACK)
            .and_then(Data::as_str)
            .unwrap_or(marks::MSG_NONE_SHOWN);
        let playing = vec![
            Field::custom(SCALE, labels::MSG_SCALE_LABEL, &scale)
                .with_enter(legends::What::CHOOSE)
                .with_clear(legends::MSG_FROM_SCENE_WHAT),
            Field::custom(GRAB_TRACK, labels::MSG_GRAB_TRACK_LABEL, grab)
                .with_enter(legends::What::CHOOSE)
                .with_clear(marks::MSG_NONE_SHOWN),
        ];
        Tab::new(
            labels::MSG_SETTINGS_TAB,
            vec![
                TabColumn::new(Some(labels::MSG_ORDER_HEADING), order_fields),
                TabColumn::new(Some(labels::MSG_PLAYING_HEADING), playing),
            ],
        )
    }

    /// A built-in generator's tab, saying so where the clip's own switched on overrides the track's.
    fn built_in_tab(&self, app: &App, clip: &ClipSlot, kind: &'static str) -> Tab {
        let place = built_in_kinds().iter().position(|each| *each == kind).unwrap_or(0);
        let built_ins = clip.get_written(ClipSlotSetting::BUILT_IN);
        let mut tab = arrange_tabs::built_in_tab(app, built_ins, kind, BUILT_IN_IDS * (place + 1));
        let clip_on = built_in_on(built_ins.and_then(|built_ins| built_ins.get(kind)));
        let track_on = app
            .document
            .song()
            .get_track(&self.track)
            .and_then(|track| track.get_written(TrackSetting::BUILT_IN))
            .is_some_and(|built_ins| built_in_on(built_ins.get(kind)));
        if clip_on && track_on {
            let word = tab_label_of(kind).to_lowercase();
            tab.remarks = vec![named(messages::MSG_BUILT_IN_OVERRIDES_TRACKS, &[("word", word.as_str().into())])];
        }
        tab
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl Form for ClipPage {
    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        crate::page::follow_name(&mut self.track, llamatron_model::schema::generated::file_format::Section::TRACKS, renames);
    }

    /// The clip is gone when its scene or its track is, or the cell no longer holds a clip.
    fn still_exists(&self, app: &App) -> bool {
        let song = app.document.song();
        song.scenes().get(self.index).is_some_and(|scene| scene.get_clip_slot(&self.track).is_some())
    }

    fn name(&self) -> &'static str {
        "ClipPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, app: &App) -> Vec<String> {
        let scene = self.scene_name(app);
        vec![
            labels::Crumb::ARRANGE.to_string(),
            named(
                labels::MSG_CLIP_CRUMB,
                &[("scene", scene.as_str().into()), ("track", self.track.as_str().into())],
            ),
        ]
    }

    fn caption(&self, app: &App) -> Option<String> {
        let scene = self.scene_name(app);
        let name = named(
            labels::MSG_CLIP_CAPTION_NAME,
            &[("scene", scene.as_str().into()), ("track", self.track.as_str().into())],
        );
        let what = labels::MSG_CLIP_CAPTION_WORD.to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", name.as_str().into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::FROM_ARRANGE)
    }

    fn duration(&self, app: &App) -> Duration {
        Duration::Seconds(Lengths::of(app.document.get_setlist(), app.document.song()).clip_seconds(self.index, &self.track))
    }

    fn form(&self, app: &App) -> Vec<Node> {
        let Some(clip) = self.clip_slot(app) else { return Vec::new() };
        let scene = self.scene(app);
        let data = clip.to_data();
        let own = |name: &str| whole(clip.get_written(name));
        let above = |name: &str| scene.and_then(|scene| whole(scene.get_written(name)));
        let mut tabs = vec![
            self.settings_tab(app, clip),
            arrange_tabs::velocity_tab(&own, &above),
            arrange_tabs::shapes_tab(app, &data),
            arrange_tabs::reset_draws_tab(app.document.song(), clip.get_written(ClipSlotSetting::RESET_DRAWS)),
        ];
        for kind in built_in_kinds() {
            tabs.push(self.built_in_tab(app, clip, kind));
        }
        tabs.push(arrange_tabs::generators_tab(app, clip.get_written(ClipSlotSetting::CHAINS)));
        let mut nodes = vec![Node::Field(Box::new(
            Field::name(NAME, &Self::name_shown(clip)).with_clear(legends::MSG_FROM_PATTERN_WHAT),
        ))];
        nodes.extend(Self::pattern_rows(clip).into_iter().map(|row| Node::Field(Box::new(row))));
        nodes.push(Node::TabBox(TabBox {
            label: labels::MSG_TABS_LABEL.to_string(),
            tabs,
        }));
        nodes.push(Node::Field(Box::new(Field::button(
            LISTEN,
            labels::MSG_LISTEN_LABEL,
            legends::KeyName::L,
            legends::MSG_LISTEN_WHAT,
        ))));
        nodes
    }

    fn remarks(&self, app: &App, _width: usize) -> Vec<Text> {
        let Some(clip) = self.clip_slot(app) else { return Vec::new() };
        let lengths = Lengths::of(app.document.get_setlist(), app.document.song());
        let length = clock(lengths.clip_seconds(self.index, &self.track));
        let scene_length = clock(lengths.scene_seconds(self.index));
        let mut lines = vec![Text::styled(
            &named(
                messages::MSG_CLIP_LENGTH_NOTE,
                &[("length", length.as_str().into()), ("scene", scene_length.as_str().into())],
            ),
            Style::DIM,
        )];
        if clip.loops() {
            lines.push(Text::styled(messages::MSG_LOOP_NOTE, Style::DIM));
        } else if clip.get_repeat() == 1 {
            lines.push(Text::styled(messages::MSG_MORPH_HINT_NOTE, Style::DIM));
        }
        let grabs = clip.get_written(ClipSlotSetting::GRAB_TRACK).is_some_and(|value| !value.is_null());
        if grabs {
            let setlist = app.document.get_setlist();
            let any = clip.get_pattern_names().iter().any(|name| {
                setlist.get_pattern(name).is_some_and(|pattern| {
                    pattern
                        .row("grab")
                        .is_some_and(|steps| steps.iter().any(|step| matches!(step, Data::Bool(true))))
                })
            });
            if !any {
                lines.push(Text::styled(messages::MSG_GRAB_HINT_NOTE, Style::DIM));
            }
        }
        lines
    }

    fn ends_a_list(&self, field: &Field) -> bool {
        field.id == ADD_ROW
    }

    fn page_keys(&self, _app: &App, row: Option<&Field>) -> Vec<KeyItem> {
        let mut keys = vec![Self::bind(&Keys::ADD_PATTERN)];
        if row.is_some_and(|row| (FIRST_PATTERN..ADD_ROW).contains(&row.id)) {
            keys.push(Self::bind(&Keys::MOVE_PATTERN));
        }
        keys.push(Self::bind(&Keys::OPEN_PATTERN));
        keys.push(Self::bind(&Keys::LISTEN));
        keys
    }

    fn press_own(&mut self, app: &mut App, item: &KeyItem, _key: &str, row: Option<&Field>) {
        if item.is(&Keys::OPEN_PATTERN) {
            let place = row
                .filter(|row| (FIRST_PATTERN..ADD_ROW).contains(&row.id))
                .map_or(0, |row| row.id - FIRST_PATTERN);
            self.open_pattern(app, place);
        }
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        // ENTER opens a picker only on the fields whose choices the page asks for itself; elsewhere it opens a page.
        let picks = matches!(id, DIRECTION | SCALE | GRAB_TRACK);
        if (edit != Edit::Enter || picks) && self.write_edit(app, id, &edit) {
            return;
        }
        if edit == Edit::Enter && (FIRST_PATTERN..ADD_ROW).contains(&id) {
            self.open_pattern(app, id - FIRST_PATTERN);
        } else if edit == Edit::Enter && id == arrange_tabs::GENERATORS {
            // The list of a clip's generators is not ported yet.
            app.show_page(Box::new(crate::screens::list_page::ListPage::new(
                crate::screens::generators::generator_list_page::GeneratorListPage {
                    holder: crate::screens::generators::generator_list_page::Holder::Clip(self.index, self.track.clone()),
                    opener_crumbs: self.crumbs(app),
                },
            )));
        }
    }
}

impl ClipPage {
    /// The pattern editor is ported, but not yet as a clip opens it, with the clip in its crumbs.
    /// Open the pattern editor on one pattern of the clip's list, with this page's crumbs before the pattern's.
    fn open_pattern(&self, app: &mut App, place: usize) {
        let Some(clip) = self.clip_slot(app) else { return };
        let Some(name) = clip.get_pattern_names().get(place).cloned() else { return };
        let crumbs = self.crumbs(app);
        app.show_page(crate::screens::pattern::open_clip_pattern(&name, crumbs));
    }
}

/// One line for each name and description, the descriptions lined up, for a picker's choices.
fn lined_up(rows: &[(String, String)]) -> Vec<String> {
    let widest = rows.iter().map(|(name, _)| name.chars().count()).max().unwrap_or(0);
    rows.iter()
        .map(|(name, description)| {
            let padded = format!("{name:<widest$}");
            named(
                marks::MSG_COLUMN_LINE,
                &[("name", padded.as_str().into()), ("description", description.as_str().into())],
            )
            .trim_end()
            .to_string()
        })
        .collect()
}
