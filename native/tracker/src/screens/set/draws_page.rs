// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Draws page (the Python screens/set/draws_page.py and pages/draws.py): a section for each draw of the song, AD to HD,
//! with how it moves through its slots, how many it has, the values a slot may hold, whether a condition draws again, and
//! the strip of its slots.

use crate::app::App;
use crate::forms::nodes::{Drawn, Edit, Field};
use crate::keybindings::{Binding, DrawsPage as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::field_page::{Form, Node};
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::{DrawSetting, DRAW_DIRECTIONS, DRAW_NAMES};
use llamatron_model::schema::generated::limits::{MAX_DRAW_SLOTS, MAX_DRAW_VALUE, MIN_DRAW_SLOTS, MIN_DRAW_VALUE};
use llamatron_strings::{labels, legends};

const DEFAULT_SLOT_COUNT: usize = 8;
/// How many ids each draw's fields have to themselves.
const IDS_PER_DRAW: usize = 100;
const DIRECTION: usize = 1;
const SLOTS: usize = 2;
const VALUE_MIN: usize = 3;
const VALUE_MAX: usize = 4;
const CONDITIONS_REDRAW: usize = 5;
const STRIP: usize = 6;
const FIRST_SLOT: usize = 10;

pub struct DrawsPage;

fn whole(value: Option<&Data>) -> Option<i64> {
    value.filter(|value| !value.is_null()).and_then(Data::as_whole).map(|whole| whole as i64)
}

impl DrawsPage {
    fn draw_fields(app: &App, place: usize, name: &str) -> Vec<Field> {
        let song = app.document.song();
        let draw = song.draws().iter().find(|(found, _)| found == name).map(|(_, draw)| draw);
        let written = |setting: &str| draw.and_then(|draw| draw.get_written(setting)).filter(|value| !value.is_null());
        let base = IDS_PER_DRAW * (place + 1);
        let direction = written(DrawSetting::DIRECTION).and_then(Data::as_str).unwrap_or(DRAW_DIRECTIONS[0]).to_string();
        let slots: Vec<Option<i64>> = written(DrawSetting::SLOTS)
            .and_then(Data::as_list)
            .map_or(vec![None; DEFAULT_SLOT_COUNT], |slots| slots.iter().map(|slot| whole(Some(slot))).collect());
        let lowest = whole(written(DrawSetting::VALUE_MIN)).unwrap_or(MIN_DRAW_VALUE);
        let highest = whole(written(DrawSetting::VALUE_MAX)).unwrap_or(MAX_DRAW_VALUE);
        let redraws = matches!(written(DrawSetting::CONDITIONS_REDRAW), Some(Data::Bool(true)));
        let start = lowest.max(0.min(highest));
        let cells = slots
            .iter()
            .enumerate()
            .map(|(slot, value)| {
                let shown = if value.is_none() { Some(String::new()) } else { None };
                Field::number(
                    base + FIRST_SLOT + slot,
                    labels::MSG_DRAW_STRIP_LABEL,
                    *value,
                    Some(lowest),
                    Some(highest),
                    start,
                    shown,
                )
                .with_clear(legends::What::CLEAR)
            })
            .collect();
        let mut strip = Field::cells(base + STRIP, labels::MSG_DRAW_STRIP_LABEL, cells).stepped();
        strip.drawn = Drawn::Strip { lit: None };
        vec![
            Field::choice(
                base + DIRECTION,
                labels::MSG_DRAW_DIRECTION_LABEL,
                DRAW_DIRECTIONS.iter().map(|each| each.to_string()).collect(),
                &direction,
                None,
            ),
            Field::number(
                base + SLOTS,
                labels::MSG_DRAW_SLOTS_LABEL,
                Some(slots.len() as i64),
                Some(MIN_DRAW_SLOTS),
                Some(MAX_DRAW_SLOTS),
                0,
                None,
            ),
            Field::number(
                base + VALUE_MIN,
                labels::MSG_DRAW_VALUE_MIN_LABEL,
                Some(lowest),
                Some(MIN_DRAW_VALUE),
                Some(MAX_DRAW_VALUE),
                0,
                None,
            )
            .with_clear(&MIN_DRAW_VALUE.to_string()),
            Field::number(
                base + VALUE_MAX,
                labels::MSG_DRAW_VALUE_MAX_LABEL,
                Some(highest),
                Some(MIN_DRAW_VALUE),
                Some(MAX_DRAW_VALUE),
                0,
                None,
            )
            .with_clear(&MAX_DRAW_VALUE.to_string()),
            Field::toggle(base + CONDITIONS_REDRAW, labels::MSG_DRAW_CONDITIONS_REDRAW_LABEL, redraws),
            strip,
        ]
    }

    /// Whether a draw's file holds anything of it.
    fn is_set(app: &App, name: &str) -> bool {
        let song = app.document.song();
        song.draws()
            .iter()
            .any(|(found, draw)| found == name && draw.to_data().as_map().is_some_and(|pairs| !pairs.is_empty()))
    }
}

impl Form for DrawsPage {
    fn name(&self) -> &'static str {
        "DrawsPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::DRAWS.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::DRAWS)
    }

    fn form(&self, app: &App) -> Vec<Node> {
        let mut nodes = Vec::new();
        for (place, name) in DRAW_NAMES.iter().enumerate() {
            nodes.push(Node::Field(Box::new(Field::heading(
                IDS_PER_DRAW * (place + 1),
                name,
                Self::is_set(app, name),
                None,
                false,
            ))));
            nodes.extend(Self::draw_fields(app, place, name).into_iter().map(|field| Node::Field(Box::new(field))));
        }
        nodes
    }

    fn headings_apart(&self) -> bool {
        true
    }

    fn slot_keys(&self) -> Option<(&'static Binding, &'static Binding)> {
        Some((&Keys::SLOT_LESS, &Keys::SLOT_MORE))
    }

    fn page_keys(&self, _app: &App, row: Option<&Field>) -> Vec<KeyItem> {
        if row.is_some_and(|row| matches!(row.drawn, Drawn::Strip { .. }) && !row.cells.is_empty()) {
            return vec![KeyItem::of(&Keys::CLASS, &Keys::TYPE_SLOT).wanting_key()];
        }
        Vec::new()
    }

    fn apply(&mut self, _app: &mut App, _id: usize, _edit: Edit) {}
}
