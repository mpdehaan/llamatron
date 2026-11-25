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
use crate::screens::field_page::{Form, Node};
use crate::screens::generators::generators_page::label_of;
use crate::screens::generators::plugin_editor::Made;
use crate::settings::{named_in, shown_octave};
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::Track;
use llamatron_model::schema::generated::file_format::{SceneSetting, Section, SongSetting, TrackSetting};
use llamatron_model::schema::generated::limits::{MAX_OCTAVE, MAX_TRANSPOSE, MIN_OCTAVE};
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_strings::{labels, legends, marks, messages, named};

const NAME: usize = 0;
/// The fields' ids, past the built-in tabs' own.
const FIRST_OWN: usize = 10_000;

pub struct TrackEditor {
    pub name: String,
}

fn whole(value: Option<&Data>) -> Option<i64> {
    value.and_then(Data::as_whole).map(|whole| whole as i64)
}

impl TrackEditor {
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
        let empty = Data::Map(Vec::new());
        let data = track
            .get_written(TrackSetting::BUILT_IN)
            .and_then(|built_ins| built_ins.get(kind))
            .unwrap_or(&empty);
        let bypass = data.get("bypass_when").and_then(Data::as_list).map_or(0, <[Data]>::len);
        let mut made = Made::of(app, kind, data, true);
        let mut tab = made.tab(&tab_label_of(kind), bypass);
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
        let names: Vec<String> = track
            .get_written(TrackSetting::CHAINS)
            .and_then(Data::as_list)
            .map_or(Vec::new(), |names| names.iter().filter_map(|name| name.as_str().map(str::to_string)).collect());
        let setlist = app.document.get_setlist();
        let listed: Vec<String> = names
            .iter()
            .map(|name| {
                let kind = PLUGINS
                    .iter()
                    .find(|plugin| setlist.get_item(plugin.section, name).is_some())
                    .map_or(labels::MSG_CHAIN_LABEL, |plugin| label_of(plugin.name));
                named(labels::MSG_LISTED_GENERATOR, &[("kind", kind.into()), ("name", name.as_str().into())])
            })
            .collect();
        let shown = if listed.is_empty() {
            marks::MSG_NONE_SHOWN.to_string()
        } else {
            listed.join(marks::MSG_CHAIN_JOIN)
        };
        let field = Field::custom(FIRST_OWN + 200, labels::MSG_GENERATORS_FIELD_LABEL, &shown)
            .with_enter(legends::What::EDIT)
            .with_clear(marks::MSG_NONE_SHOWN);
        Tab::new(labels::MSG_USER_TAB, vec![TabColumn::new(None, vec![field])])
    }
}

/// A built-in generator's tab's label.
fn tab_label_of(kind: &str) -> String {
    use llamatron_strings::plugin_texts::*;
    match kind {
        "chords" => chords::MSG_TAB_LABEL,
        "arp" => arp::MSG_TAB_LABEL,
        "guitarify" => guitarify::MSG_TAB_LABEL,
        "timing" => timing::MSG_TAB_LABEL,
        _ => phrasing::MSG_TAB_LABEL,
    }
    .to_string()
}

/// The kinds built into a track or a clip, in the order their tabs stand.
pub fn built_in_kinds() -> Vec<&'static str> {
    let mut kinds: Vec<(i64, &'static str)> = PLUGINS
        .iter()
        .filter_map(|plugin| plugin.built_in_place.map(|place| (place, plugin.name)))
        .collect();
    kinds.sort();
    kinds.into_iter().map(|(_, name)| name).collect()
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

    fn apply(&mut self, _app: &mut App, _id: usize, _edit: Edit) {}
}
