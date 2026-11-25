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
        if edit == Edit::Enter && (FIRST_PATTERN..ADD_ROW).contains(&id) {
            self.open_pattern(app, id - FIRST_PATTERN);
        } else if edit == Edit::Enter && id == arrange_tabs::GENERATORS {
            // The list of a clip's generators is not ported yet.
            app.show_page(Box::new(crate::screens::not_ported::NotPorted {
                name: "GeneratorListPage".to_string(),
            }));
        }
    }
}

impl ClipPage {
    /// The pattern editor is ported, but not yet as a clip opens it, with the clip in its crumbs.
    fn open_pattern(&self, app: &mut App, _place: usize) {
        app.show_page(Box::new(crate::screens::not_ported::NotPorted {
            name: "PatternEditor".to_string(),
        }));
    }
}
