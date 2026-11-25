// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A track's page (the Python screens/arrange/track_editor.py and pages/track.py): its name, then its settings in tabs:
//! Settings, with its routing and its notes, its MIDI CC lanes, a tab for each generator built into it, and its other
//! generators.

use crate::app::App;
use crate::drawing::Style;
use crate::forms::nodes::{Edit, Field};
use crate::forms::tab_box::{Tab, TabBox, TabColumn};
use crate::keybindings::{KeyClass, TrackEditor as Keys};
use crate::screens::arrange::arrange_tabs::{self, built_in_kinds, tab_label_of};
use crate::screens::field_page::{Form, Node};
use crate::settings::{named_in, shown_octave};
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::Track;
use llamatron_model::schema::generated::file_format::{SceneSetting, Section, SongSetting, TrackSetting};
use llamatron_model::schema::generated::limits::{MAX_OCTAVE, MAX_TRANSPOSE, MIN_OCTAVE};
use llamatron_strings::{labels, legends, marks, messages, named};

const NAME: usize = 0;
/// How many ids each built-in tab's fields have to themselves.
const BUILT_IN_IDS: usize = 1000;
/// The fields' ids, past the built-in tabs' own.
const FIRST_OWN: usize = 10_000;

pub struct TrackEditor {
    pub name: String,
}

fn whole(value: Option<&Data>) -> Option<i64> {
    value.and_then(Data::as_whole).map(|whole| whole as i64)
}

/// The ids of the Settings tab's fields, in the order the tab makes them, and the first of the MIDI CC lanes'.
const INSTRUMENT: usize = FIRST_OWN + 1;
const DRUM: usize = FIRST_OWN + 2;
const MUTE: usize = FIRST_OWN + 3;
const GROOVE: usize = FIRST_OWN + 4;
const TRANSPOSE: usize = FIRST_OWN + 5;
const LOWEST_OCTAVE: usize = FIRST_OWN + 6;
const HIGHEST_OCTAVE: usize = FIRST_OWN + 7;
const DEFAULT_VELOCITY: usize = FIRST_OWN + 8;
const ACCENT: usize = FIRST_OWN + 9;
const VELOCITY: usize = FIRST_OWN + 10;
const FIRST_CC: usize = FIRST_OWN + 100;
const CC_LANES: usize = 4;

impl TrackEditor {
    /// Write one of the track's settings, or take it out of the file with None.
    fn write(&self, app: &mut App, setting: &str, value: Option<Data>) {
        let (song_name, track) = (app.document.get_current_song_name().to_string(), self.name.clone());
        app.document.change_set(|setlist| {
            if let Some(llamatron_model::objects::setlist::Item::Song(song)) = setlist.get_item_mut(Section::SONGS, &song_name) {
                song.set_track_written(&track, setting, value);
            }
        });
    }

    /// Store what a key did to one of the track's fields, its built-in generators' among them; false where the field writes
    /// nothing so.
    fn write_edit(&self, app: &mut App, id: usize, edit: &Edit) -> bool {
        let Some(track) = self.track(app) else { return false };
        let whole = |name: &str| track.get_written(name).and_then(Data::as_whole).map(|whole| whole as i64);
        if (BUILT_IN_IDS..FIRST_OWN).contains(&id) {
            let kinds = built_in_kinds();
            let Some(kind) = kinds.get(id / BUILT_IN_IDS - 1).copied() else {
                return false;
            };
            let built_ins = track.get_written(TrackSetting::BUILT_IN);
            let Some((setting, value)) = arrange_tabs::built_in_edit(app, built_ins, kind, BUILT_IN_IDS * (id / BUILT_IN_IDS), id, edit) else {
                return false;
            };
            let built_ins = arrange_tabs::with_built_in(built_ins, kind, setting, value);
            self.write(app, TrackSetting::BUILT_IN, built_ins);
            return true;
        }
        let number = match edit {
            Edit::Number(number) => Some(*number),
            _ => None,
        };
        match (id, edit) {
            (DRUM | MUTE, Edit::Toggle(on)) => {
                let setting = if id == DRUM { TrackSetting::DRUM } else { TrackSetting::MUTE };
                if id == DRUM {
                    if let Some(refusal) = self.drum_refusal(app, *on) {
                        app.refuse(&refusal);
                        return true;
                    }
                }
                self.write(app, setting, on.then_some(Data::Bool(true)));
            }
            (INSTRUMENT, Edit::Clear) => self.write(app, TrackSetting::INSTRUMENT, None),
            (GROOVE, Edit::Adjust(offset)) => {
                let names = crate::settings::sorted_names(&crate::screens::set::grooves_page::groove_names(app));
                let mut choices = vec![None, Some(Data::Bool(false))];
                choices.extend(names.into_iter().map(|name| Some(Data::Text(name))));
                let current = track.get_written(TrackSetting::GROOVE).filter(|value| !value.is_null()).cloned();
                let place = choices.iter().position(|choice| *choice == current).unwrap_or(0) as i64;
                let chosen = choices[(place + offset).clamp(0, choices.len() as i64 - 1) as usize].clone();
                self.write(app, TrackSetting::GROOVE, chosen);
            }
            (GROOVE, Edit::Clear) => self.write(app, TrackSetting::GROOVE, None),
            (TRANSPOSE, Edit::Number(transpose)) => self.write(app, TrackSetting::TRANSPOSE, (*transpose != 0).then_some(Data::Whole(*transpose as i128))),
            (TRANSPOSE, Edit::Clear) => self.write(app, TrackSetting::TRANSPOSE, None),
            (LOWEST_OCTAVE | HIGHEST_OCTAVE, Edit::Adjust(offset)) => {
                let lowest = whole(TrackSetting::LOWEST_OCTAVE).unwrap_or(MIN_OCTAVE);
                let highest = whole(TrackSetting::HIGHEST_OCTAVE).unwrap_or(MAX_OCTAVE);
                if id == LOWEST_OCTAVE {
                    let moved = (lowest + offset).clamp(MIN_OCTAVE, MAX_OCTAVE).clamp(MIN_OCTAVE, highest);
                    self.write(app, TrackSetting::LOWEST_OCTAVE, (moved != MIN_OCTAVE).then_some(Data::Whole(moved as i128)));
                } else {
                    let moved = (highest + offset).clamp(MIN_OCTAVE, MAX_OCTAVE).clamp(lowest, MAX_OCTAVE);
                    self.write(app, TrackSetting::HIGHEST_OCTAVE, (moved != MAX_OCTAVE).then_some(Data::Whole(moved as i128)));
                }
            }
            (DEFAULT_VELOCITY | ACCENT | VELOCITY, _) => {
                let setting = match id {
                    DEFAULT_VELOCITY => TrackSetting::DEFAULT_VELOCITY,
                    ACCENT => TrackSetting::ACCENT,
                    _ => TrackSetting::VELOCITY,
                };
                match edit {
                    Edit::Clear => self.write(app, setting, None),
                    _ => self.write(app, setting, number.map(|number| Data::Whole(number as i128))),
                }
            }
            (cc, _) if (FIRST_CC..FIRST_CC + CC_LANES).contains(&cc) => {
                let mut lanes: Vec<Data> = track
                    .get_written(TrackSetting::CC)
                    .and_then(Data::as_list)
                    .map(<[Data]>::to_vec)
                    .unwrap_or_default();
                lanes.resize(CC_LANES, Data::Null);
                lanes[cc - FIRST_CC] = number.map_or(Data::Null, |number| Data::Whole(number as i128));
                let value = lanes.iter().any(|lane| !lane.is_null()).then_some(Data::List(lanes));
                self.write(app, TrackSetting::CC, value);
            }
            _ => return false,
        }
        true
    }

    /// Why the track cannot be made a drum track, or the other way, where its instrument is of the other role.
    fn drum_refusal(&self, app: &App, on: bool) -> Option<String> {
        use llamatron_model::objects::setlist::Item;
        let track = self.track(app)?;
        let instrument = track.get_instrument_name()?;
        let Some(Item::Instrument(held)) = app.document.get_setlist().get_item(Section::INSTRUMENTS, &instrument) else {
            return None;
        };
        let role = held
            .get_written(llamatron_model::schema::generated::file_format::InstrumentSetting::ROLE)
            .and_then(Data::as_str)
            .unwrap_or("normal");
        let wanted = if on { "percussion" } else { "normal" };
        (role != wanted).then(|| {
            let role = named_in(labels::MSG_ROLE_NAMES, role).to_lowercase();
            named(
                llamatron_strings::errors::ERR_INSTRUMENT_DOES_NOT_FIT,
                &[("instrument", instrument.as_str().into()), ("role", role.as_str().into())],
            )
        })
    }

    fn track<'a>(&self, app: &'a App) -> Option<&'a Track> {
        app.document.song().get_track(&self.name)
    }

    fn settings_tab(&self, app: &App, track: &Track) -> Tab {
        let song = app.document.song();
        let setlist = app.document.get_setlist();
        let mut id = FIRST_OWN;
        let mut next = || {
            id += 1;
            id
        };
        let instrument = track.get_instrument_name().unwrap_or_else(|| marks::MSG_NONE_SHOWN.to_string());
        let drum = matches!(track.get_written(TrackSetting::DRUM), Some(Data::Bool(true)));
        let mute = matches!(track.get_written(TrackSetting::MUTE), Some(Data::Bool(true)));
        let groove = match track.get_written(TrackSetting::GROOVE) {
            None | Some(Data::Null) => {
                let scenes_choose = song
                    .scenes()
                    .iter()
                    .any(|scene| scene.get_written(SceneSetting::GROOVE).is_some_and(|value| !value.is_null()));
                if scenes_choose {
                    marks::MSG_SCENE_OR_SONG_GROOVE_SHOWN.to_string()
                } else {
                    let song_groove = song.get_written(SongSetting::GROOVE).and_then(Data::as_str).unwrap_or("none");
                    named(marks::MSG_SONG_GROOVE_SHOWN, &[("groove", song_groove.into())])
                }
            }
            Some(Data::Bool(false)) => marks::MSG_GROOVE_OFF_SHOWN.to_string(),
            Some(value) => value.as_str().unwrap_or("").to_string(),
        };
        let groove_cleared = if song
            .scenes()
            .iter()
            .any(|scene| scene.get_written(SceneSetting::GROOVE).is_some_and(|value| !value.is_null()))
        {
            legends::MSG_FROM_SCENE_OR_SONG_WHAT
        } else {
            legends::MSG_FROM_SONG_WHAT
        };
        let routing = vec![
            Field::custom(next(), labels::MSG_INSTRUMENT_LABEL, &instrument)
                .with_enter(legends::What::CHOOSE)
                .with_clear(marks::MSG_NONE_SHOWN),
            Field::toggle(next(), labels::MSG_DRUM_LABEL, drum),
            Field::toggle(next(), labels::MSG_MUTE_LABEL, mute),
            Field::custom(next(), labels::MSG_GROOVE_LABEL, &groove)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(groove_cleared),
        ];
        let transpose = if drum {
            Field::custom(next(), labels::MSG_TRANSPOSE_LABEL, marks::MSG_DRUM_TRACK_SHOWN)
        } else {
            let number = whole(track.get_written(TrackSetting::TRANSPOSE)).unwrap_or(0);
            let shown = if number == 0 { "0".to_string() } else { format!("{number:+}") };
            Field::number(
                next(),
                labels::MSG_TRANSPOSE_LABEL,
                Some(number),
                Some(-MAX_TRANSPOSE),
                Some(MAX_TRANSPOSE),
                0,
                Some(shown),
            )
            .with_clear("0")
        };
        let lowest = whole(track.get_written(TrackSetting::LOWEST_OCTAVE)).unwrap_or(MIN_OCTAVE);
        let highest = whole(track.get_written(TrackSetting::HIGHEST_OCTAVE)).unwrap_or(MAX_OCTAVE);
        let octave = |id: usize, label: &str, octave: i64, default: i64| {
            Field::custom(id, label, &shown_octave(setlist, octave).to_string())
                .with_adjust()
                .with_enter(legends::What::EDIT)
                .with_clear(&shown_octave(setlist, default).to_string())
        };
        let velocity_above = song.default_velocity_of(track, setlist);
        let has_instrument = song.instrument_of(track, setlist).is_some();
        let velocity_shown = if track.get_default_velocity().is_some() {
            None
        } else if has_instrument {
            Some(named(marks::MSG_FROM_INSTRUMENT_SHOWN, &[("value", velocity_above.into())]))
        } else {
            Some(velocity_above.to_string())
        };
        let velocity_cleared = if has_instrument {
            legends::MSG_FROM_INSTRUMENT_WHAT.to_string()
        } else {
            "127".to_string()
        };
        let accent = song.accent_of(track, setlist);
        let percent = whole(track.get_written(TrackSetting::VELOCITY)).unwrap_or(100);
        let notes = vec![
            transpose,
            octave(next(), labels::MSG_LOWEST_OCTAVE_LABEL, lowest, MIN_OCTAVE),
            octave(next(), labels::MSG_HIGHEST_OCTAVE_LABEL, highest, MAX_OCTAVE),
            Field::number(
                next(),
                labels::MSG_DEFAULT_VELOCITY_LABEL,
                Some(velocity_above),
                Some(1),
                Some(127),
                velocity_above,
                velocity_shown,
            )
            .with_clear(&velocity_cleared),
            Field::number(
                next(),
                labels::MSG_ACCENT_LABEL,
                Some(accent),
                Some(0),
                Some(127),
                0,
                Some(named(marks::MSG_ACCENT_SHOWN, &[("accent", accent.into())])),
            )
            .with_clear(&named(marks::MSG_ACCENT_SHOWN, &[("accent", 15.into())])),
            Field::number(
                next(),
                labels::MSG_VELOCITY_PERCENT_LABEL,
                Some(percent),
                Some(0),
                Some(200),
                100,
                Some(named(marks::MSG_PERCENT_SHOWN, &[("percent", percent.into())])),
            )
            .with_clear(&named(marks::MSG_PERCENT_SHOWN, &[("percent", 100.into())])),
        ];
        Tab::new(
            labels::MSG_SETTINGS_TAB,
            vec![
                TabColumn::new(Some(labels::MSG_ROUTING_HEADING), routing),
                TabColumn::new(Some(labels::MSG_NOTES_HEADING), notes),
            ],
        )
    }

    fn cc_tab(&self, track: &Track) -> Tab {
        let lanes = track
            .get_written(TrackSetting::CC)
            .and_then(Data::as_list)
            .map(<[Data]>::to_vec)
            .unwrap_or_default();
        let fields = (0..4)
            .map(|lane| {
                let number = lanes.get(lane).and_then(Data::as_whole).map(|whole| whole as i64);
                let shown = number.map_or(marks::MSG_NONE_SHOWN.to_string(), |number| number.to_string());
                Field::number(
                    FIRST_OWN + 100 + lane,
                    &named(labels::MSG_CC_LABEL, &[("number", (lane + 1).into())]),
                    number,
                    Some(0),
                    Some(127),
                    0,
                    Some(shown),
                )
                .with_clear(marks::MSG_NONE_SHOWN)
            })
            .collect();
        Tab::new(labels::MSG_CC_LANES_TAB, vec![TabColumn::new(None, fields)])
    }

    /// A built-in generator's tab, with what it says of the clips whose own built-in of its kind overrides it.
    fn built_in_tab(&self, app: &App, track: &Track, kind: &'static str) -> Tab {
        let place = built_in_kinds().iter().position(|each| *each == kind).unwrap_or(0);
        let mut tab = arrange_tabs::built_in_tab(app, track.get_written(TrackSetting::BUILT_IN), kind, BUILT_IN_IDS * (place + 1));
        let word = tab_label_of(kind).to_lowercase();
        let song = app.document.song();
        let mut overriding = Vec::new();
        for (index, scene) in song.scenes().iter().enumerate() {
            let Some(clip) = scene.get_clip_slot(&self.name) else { continue };
            let on = clip
                .get_written("built_in")
                .and_then(|built_ins| built_ins.get(kind))
                .and_then(|settings| settings.get("enabled"))
                .is_some_and(|value| matches!(value, Data::Bool(true)));
            if on {
                let name = scene
                    .get_name()
                    .unwrap_or_else(|| named(llamatron_strings::names::MSG_NEW_SCENE_NAME, &[("number", (index + 1).into())]));
                overriding.push(named(
                    messages::MSG_BUILT_IN_OVERRIDING_CLIP,
                    &[("scene", name.as_str().into()), ("track", self.name.as_str().into())],
                ));
            }
        }
        if !overriding.is_empty() {
            let template = if overriding.len() == 1 {
                messages::MSG_BUILT_IN_OVERRIDDEN_ONCE
            } else {
                messages::MSG_BUILT_IN_OVERRIDDEN
            };
            let clips = overriding.iter().take(3).cloned().collect::<Vec<_>>().join(", ");
            tab.remarks = vec![named(
                template,
                &[
                    ("word", word.as_str().into()),
                    ("count", overriding.len().into()),
                    ("clips", clips.as_str().into()),
                ],
            )];
        }
        tab
    }

    fn generators_tab(&self, app: &App, track: &Track) -> Tab {
        arrange_tabs::generators_tab(app, track.get_written(TrackSetting::CHAINS))
    }
}

impl Form for TrackEditor {
    fn name(&self) -> &'static str {
        "TrackEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::ARRANGE.to_string(),
            named(labels::MSG_TRACK_CRUMB, &[("name", self.name.as_str().into())]),
        ]
    }

    fn caption(&self, _app: &App) -> Option<String> {
        let what = named_in(labels::MSG_CAPTION_WORDS, Section::TRACKS).to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.name.as_str().into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::FROM_ARRANGE)
    }

    fn form(&self, app: &App) -> Vec<Node> {
        let Some(track) = self.track(app) else { return Vec::new() };
        let mut tabs = vec![self.settings_tab(app, track), self.cc_tab(track)];
        for kind in built_in_kinds() {
            tabs.push(self.built_in_tab(app, track, kind));
        }
        tabs.push(self.generators_tab(app, track));
        vec![
            Node::Field(Box::new(Field::name(NAME, &self.name))),
            Node::TabBox(TabBox {
                label: labels::MSG_TABS_LABEL.to_string(),
                tabs,
            }),
        ]
    }

    fn remarks(&self, _app: &App, _width: usize) -> Vec<Text> {
        vec![Text::styled(messages::MSG_TRANSPOSE_NOTE, Style::DIM)]
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        if edit != Edit::Enter && self.write_edit(app, id, &edit) {
            return;
        }
        if edit == Edit::Enter && id == arrange_tabs::GENERATORS {
            // The list of a track's generators is not ported yet.
            app.show_page(Box::new(crate::screens::list_page::ListPage::new(
                crate::screens::generators::generator_list_page::GeneratorListPage {
                    holder: crate::screens::generators::generator_list_page::Holder::Track(self.name.clone()),
                    opener_crumbs: self.crumbs(app),
                },
            )));
            return;
        }
        if edit != Edit::Enter || !(BUILT_IN_IDS..FIRST_OWN).contains(&id) {
            return;
        }
        let kinds = built_in_kinds();
        let Some(kind) = kinds.get(id / BUILT_IN_IDS - 1).copied() else { return };
        let Some(track) = self.track(app) else { return };
        let tab = self.built_in_tab(app, track, kind);
        let is_bypass = tab.every_field().iter().any(|field| field.id == id && field.is_button());
        if is_bypass {
            use crate::screens::generators::statements_page::{GeneratorStatementsPage, Holder};
            let holder = Holder::BuiltIn {
                track: self.name.clone(),
                kind,
                opener_crumbs: self.crumbs(app),
            };
            let opened = GeneratorStatementsPage { holder };
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(opened)));
        }
    }
}
