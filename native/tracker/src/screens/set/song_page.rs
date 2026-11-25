// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Song page (the Python screens/set/song_page.py and pages/song.py): the current song's settings, its name, tempo,
//! time signature, entry size, scale, groove, style, how soon an edit is heard, the instrument a pattern is heard through
//! and its visualizer, then the Export button.

use crate::app::App;
use crate::forms::nodes::{Edit, Field, Kind};
use crate::keybindings::{KeyClass, SongPage as Keys};
use crate::page::Duration;
use crate::screens::field_page::{Form, Node};
use crate::settings::{mode_name, named_in, number_text, song_text, sorted_names};
use crate::themes::{self, Colour};
use llamatron_model::schema::generated::defaults;
use llamatron_model::schema::generated::file_format::{Section, SongSetting, LIVE_RESPONSIVENESSES, VISUALIZER_NAMES};
use llamatron_model::schema::generated::genres::{GENRES, SUBGENRES, VARIANTS};
use llamatron_model::schema::generated::limits::{MAX_TEMPO, MIN_TEMPO};
use llamatron_strings::{labels, legends, marks, named};

const NAME: usize = 0;
const TEMPO: usize = 1;
const TIME_SIGNATURE: usize = 2;
const ENTRY_SIZE: usize = 3;
const SCALE: usize = 4;
const GROOVE: usize = 5;
const GENRE: usize = 6;
const SUBGENRE: usize = 7;
const VARIANT: usize = 8;
const LIVE_RESPONSE: usize = 9;
const PREVIEW: usize = 10;
const VISUALIZER: usize = 11;
const EXPORT: usize = 12;

pub struct SongPage;

fn with_names(mut field: Field, names: Vec<String>) -> Field {
    if let Kind::Choice { names: held, .. } = &mut field.kind {
        *held = Some(names);
    }
    field
}

/// A field for the song's genre, subgenre or variant: one of the choices, or (none).
fn style_field(id: usize, label: &str, choices: &[&str], current: Option<String>) -> Field {
    let mut offered = vec![marks::MSG_NONE_SHOWN.to_string()];
    offered.extend(choices.iter().map(|choice| choice.to_string()));
    let current = current.unwrap_or_else(|| marks::MSG_NONE_SHOWN.to_string());
    Field::choice(id, label, offered, &current, None).with_clear(marks::MSG_NONE_SHOWN)
}

impl Form for SongPage {
    fn name(&self) -> &'static str {
        "SongPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, app: &App) -> Vec<String> {
        vec![labels::Crumb::SONGS.to_string(), app.document.get_current_song_name().to_string()]
    }

    fn caption(&self, app: &App) -> Option<String> {
        let what = named_in(labels::MSG_CAPTION_WORDS, Section::SONGS).to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", app.document.get_current_song_name().into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::SONGS)
    }

    fn duration(&self, app: &App) -> Duration {
        let document = &app.document;
        Duration::Seconds(crate::lengths::Lengths::of(document.get_setlist(), document.song()).song_seconds())
    }

    fn form(&self, app: &App) -> Vec<Node> {
        let song = app.document.song();
        let tempo = number_text(&song.get_tempo());
        let tempo_number = tempo.split('.').next().and_then(|whole| whole.parse().ok());
        let tempo_field = Field::number(
            TEMPO,
            labels::MSG_TEMPO_LABEL,
            tempo_number,
            Some(MIN_TEMPO),
            Some(MAX_TEMPO),
            0,
            Some(named(marks::MSG_TEMPO_SHOWN, &[("tempo", tempo.as_str().into())])),
        );
        let entry_size = song_text(song, SongSetting::ENTRY_SIZE).unwrap_or_else(|| marks::MSG_ONE_STEP_SHOWN.to_string());
        let scale = song.get_scale_name().unwrap_or_else(|| marks::MSG_NONE_SHOWN.to_string());
        let groove = song_text(song, SongSetting::GROOVE).unwrap_or_else(|| defaults::DEFAULT_GROOVE.to_string());
        let genre = song_text(song, SongSetting::GENRE);
        let subgenre = song_text(song, SongSetting::SUBGENRE);
        let subgenres: &[&str] = genre
            .as_deref()
            .and_then(|genre| SUBGENRES.iter().find(|(found, _)| *found == genre))
            .map_or(&[], |(_, found)| found);
        let variants: &[&str] = VARIANTS
            .iter()
            .find(|(found, _)| Some(*found) == genre.as_deref())
            .and_then(|(_, by_subgenre)| by_subgenre.iter().find(|(found, _)| Some(*found) == subgenre.as_deref()))
            .map_or(&[], |(_, found)| found);
        let response = song_text(song, SongSetting::LIVE_RESPONSIVENESS).unwrap_or_else(|| defaults::DEFAULT_LIVE_RESPONSIVENESS.to_string());
        let response_names = LIVE_RESPONSIVENESSES
            .iter()
            .map(|choice| named_in(labels::MSG_LIVE_RESPONSIVENESS_NAMES, choice))
            .collect();
        let response_field = with_names(
            Field::choice(
                LIVE_RESPONSE,
                labels::MSG_LIVE_RESPONSIVENESS_LABEL,
                LIVE_RESPONSIVENESSES.iter().map(|each| each.to_string()).collect(),
                &response,
                Some(named_in(labels::MSG_LIVE_RESPONSIVENESS_NAMES, &response)),
            ),
            response_names,
        );
        let preview = song_text(song, SongSetting::PREVIEW_INSTRUMENT).unwrap_or_else(|| labels::MSG_PREVIEW_INSTRUMENT_UNSET.to_string());
        let visualizer = song_text(song, SongSetting::VISUALIZER);
        let first = labels::MSG_SETS_VISUALIZER_CHOICE;
        let mut choices = vec![first.to_string()];
        choices.extend(VISUALIZER_NAMES.iter().map(|name| name.to_string()));
        let mut names = vec![first.to_string()];
        names.extend(VISUALIZER_NAMES.iter().map(|name| mode_name(name)));
        let shown = visualizer.as_deref().map_or(first.to_string(), mode_name);
        let visualizer_field = with_names(
            Field::choice(
                VISUALIZER,
                labels::MSG_VISUALIZER_LABEL,
                choices,
                visualizer.as_deref().unwrap_or(first),
                Some(shown),
            ),
            names,
        );
        let fields = vec![
            Field::name(NAME, app.document.get_current_song_name()),
            tempo_field,
            Field::custom(TIME_SIGNATURE, labels::MSG_TIME_SIGNATURE_LABEL, &song.get_time_signature().to_text())
                .with_adjust()
                .with_enter(legends::What::EDIT),
            Field::custom(ENTRY_SIZE, labels::MSG_ENTRY_SIZE_LABEL, &entry_size)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(marks::MSG_ONE_STEP_SHOWN),
            Field::custom(SCALE, labels::MSG_SCALE_LABEL, &scale)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(marks::MSG_NONE_SHOWN),
            Field::custom(GROOVE, labels::MSG_GROOVE_LABEL, &groove)
                .with_adjust()
                .with_enter(legends::What::CHOOSE),
            style_field(GENRE, labels::MSG_GENRE_LABEL, GENRES, genre.clone()),
            style_field(SUBGENRE, labels::MSG_SUBGENRE_LABEL, subgenres, subgenre.clone()),
            style_field(VARIANT, labels::MSG_VARIANT_LABEL, variants, song_text(song, SongSetting::VARIANT)),
            response_field,
            Field::custom(PREVIEW, labels::MSG_PREVIEW_INSTRUMENT_LABEL, &preview)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(labels::MSG_PREVIEW_INSTRUMENT_UNSET),
            visualizer_field,
            Field::button(EXPORT, labels::PageName::EXPORT, Keys::EXPORT.name, Keys::EXPORT.what),
        ];
        fields.into_iter().map(|field| Node::Field(Box::new(field))).collect()
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        use llamatron_model::file::data::Data;
        use llamatron_model::schema::generated::file_format::{STEP_SIZE_CHOICES, TIME_SIGNATURE_CHOICES};
        let song = app.document.song();
        let setlist = app.document.get_setlist();
        let text = |name: &str| song.get_written(name).and_then(Data::as_str).map(str::to_string);
        // A step along a list of choices, None first where the list starts with it, stopping at both ends.
        let along = |values: &[Option<String>], current: &Option<String>, offset: i64| {
            let place = values.iter().position(|value| value == current).unwrap_or(0) as i64;
            values[(place + offset).clamp(0, values.len() as i64 - 1) as usize].clone()
        };
        let none_first = |names: Vec<String>| {
            let mut values = vec![None];
            values.extend(names.into_iter().map(Some));
            values
        };
        let style = |name: &str| text(name).map(Data::Text);
        let none_or = |chosen: String| (chosen != marks::MSG_NONE_SHOWN).then_some(Data::Text(chosen));
        let written: Option<(&str, Option<Data>)> = match (id, edit) {
            (TEMPO, Edit::Number(tempo)) => Some((SongSetting::TEMPO, Some(Data::Whole(tempo as i128)))),
            (TIME_SIGNATURE, Edit::Adjust(offset)) => {
                let choices: Vec<Option<String>> = TIME_SIGNATURE_CHOICES.iter().map(|choice| Some(choice.to_string())).collect();
                let mut current = Some(song.get_time_signature().to_text());
                if !choices.contains(&current) {
                    current = Some(defaults::DEFAULT_TIME_SIGNATURE.to_string());
                }
                Some((SongSetting::TIME_SIGNATURE, along(&choices, &current, offset).map(Data::Text)))
            }
            (ENTRY_SIZE, Edit::Adjust(offset)) => {
                let choices = none_first(STEP_SIZE_CHOICES.iter().map(|choice| choice.to_string()).collect());
                Some((
                    SongSetting::ENTRY_SIZE,
                    along(&choices, &song_text(song, SongSetting::ENTRY_SIZE), offset).map(Data::Text),
                ))
            }
            (ENTRY_SIZE, Edit::Clear) => Some((SongSetting::ENTRY_SIZE, None)),
            (SCALE, Edit::Adjust(offset)) => {
                let names = sorted_names(&setlist.items(Section::SCALES).iter().map(|(name, _)| name.clone()).collect::<Vec<_>>());
                Some((SongSetting::SCALE, along(&none_first(names), &song.get_scale_name(), offset).map(Data::Text)))
            }
            (SCALE, Edit::Clear) => Some((SongSetting::SCALE, None)),
            (GROOVE, Edit::Adjust(offset)) => {
                let names = sorted_names(&crate::screens::set::grooves_page::groove_names(app));
                let current = song_text(song, SongSetting::GROOVE).unwrap_or_else(|| defaults::DEFAULT_GROOVE.to_string());
                Some((SongSetting::GROOVE, Some(Data::Text(crate::forms::nodes::stepped(&names, &current, offset)))))
            }
            (PREVIEW, Edit::Adjust(offset)) => {
                let names = sorted_names(&setlist.items(Section::INSTRUMENTS).iter().map(|(name, _)| name.clone()).collect::<Vec<_>>());
                Some((
                    SongSetting::PREVIEW_INSTRUMENT,
                    along(&none_first(names), &song_text(song, SongSetting::PREVIEW_INSTRUMENT), offset).map(Data::Text),
                ))
            }
            (PREVIEW, Edit::Clear) => Some((SongSetting::PREVIEW_INSTRUMENT, None)),
            (LIVE_RESPONSE, Edit::Choice(chosen)) => Some((SongSetting::LIVE_RESPONSIVENESS, Some(Data::Text(chosen)))),
            (VISUALIZER, Edit::Choice(chosen)) => {
                let value = (chosen != labels::MSG_SETS_VISUALIZER_CHOICE).then_some(Data::Text(chosen));
                Some((SongSetting::VISUALIZER, llamatron_model::objects::song::sensible_visualizer(value)))
            }
            (GENRE | SUBGENRE | VARIANT, edit) => {
                let chosen = match edit {
                    Edit::Choice(chosen) => none_or(chosen),
                    Edit::Clear => None,
                    _ => return,
                };
                let (mut genre, mut subgenre, mut variant) = (style(SongSetting::GENRE), style(SongSetting::SUBGENRE), style(SongSetting::VARIANT));
                match id {
                    GENRE => genre = chosen,
                    SUBGENRE => subgenre = chosen,
                    _ => variant = chosen,
                }
                let name = app.document.get_current_song_name().to_string();
                app.document.change_set(|setlist| {
                    if let Some(llamatron_model::objects::setlist::Item::Song(song)) = setlist.get_item_mut(Section::SONGS, &name) {
                        song.set_style(genre, subgenre, variant);
                    }
                });
                return;
            }
            _ => None,
        };
        let Some((setting, value)) = written else { return };
        let name = app.document.get_current_song_name().to_string();
        app.document.change_set(|setlist| {
            if let Some(llamatron_model::objects::setlist::Item::Song(song)) = setlist.get_item_mut(Section::SONGS, &name) {
                song.set_written(setting, value);
            }
        });
    }
}
