// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A song and its parts as a set stores them (the Python model/objects/song.py, track.py, scene.py, clip_slot.py and
//! draw.py): the song's settings, its draws and tracks by name, and its scenes in order, each scene's clips by track.

use crate::file::data::Data;
use crate::file::layout::OBJECT_SCENE_TRACKS;
use crate::objects::holder::{in_table, passed_over, Holder};
use crate::objects::named::plugin_table;
use crate::schema::checking::{Context, InvalidValue};
use crate::schema::generated::file_format::{ClipSlotSetting, DrawSetting, Section, SongSetting, TrackSetting, DRAW_NAMES, VISUALIZER_NAMES};
use crate::schema::generated::genres::{GENRES, MASHUP, MASHUP_SUFFIX, SUBGENRES, VARIANTS};
use crate::schema::generated::limits;
use crate::schema::generated::plugins::PLUGINS;
use crate::schema::generated::settings::{CLIP_SLOT, DRAW, SCENE, SONG, TRACK};
use llamatron_strings::errors;
use llamatron_strings::named;

/// The names a song's settings may name: the set's, and the song's own tracks once read.
pub struct Names<'a> {
    pub set: &'a dyn Context,
    pub tracks: Vec<String>,
}

/// Refuse a track whose Lowest octave is above its Highest, once each is checked on its own.
fn checked_octave_order(settings: &Holder) -> Result<(), InvalidValue> {
    let octave = |name: &str, default: i64| settings.get(name).and_then(Data::as_whole).map_or(default, |octave| octave as i64);
    let lowest = octave(TrackSetting::LOWEST_OCTAVE, limits::MIN_OCTAVE);
    let highest = octave(TrackSetting::HIGHEST_OCTAVE, limits::MAX_OCTAVE);
    if lowest > highest {
        return Err(InvalidValue::new(named(
            errors::ERR_OCTAVE_RANGE_BACKWARDS,
            &[("lowest", lowest.into()), ("highest", highest.into())],
        )));
    }
    Ok(())
}

/// Refuse a draw whose lowest value is above its highest, or with a slot outside them.
fn checked_draw_range(settings: &Holder) -> Result<(), InvalidValue> {
    let value = |name: &str, default: i64| settings.get(name).and_then(Data::as_whole).map_or(default, |value| value as i64);
    let lowest = value(DrawSetting::VALUE_MIN, limits::MIN_DRAW_VALUE);
    let highest = value(DrawSetting::VALUE_MAX, limits::MAX_DRAW_VALUE);
    if lowest > highest {
        return Err(InvalidValue::new(named(
            errors::ERR_DRAW_VALUES_OUT_OF_ORDER,
            &[("lowest", lowest.into()), ("highest", highest.into())],
        )));
    }
    let slots = settings.get(DrawSetting::SLOTS).and_then(Data::as_list).unwrap_or(&[]);
    for slot in slots.iter().filter(|slot| !slot.is_null()) {
        let within = slot.as_whole().is_some_and(|slot| (lowest as i128..=highest as i128).contains(&slot));
        if !within {
            let message = named(
                errors::ERR_DRAW_SLOT_OUT_OF_RANGE,
                &[("lowest", lowest.into()), ("highest", highest.into()), ("value", slot.into())],
            );
            return Err(InvalidValue::new(message));
        }
    }
    Ok(())
}

/// The fewest repeats a morph needs: its first pass all the clip's own pattern and its last all the target.
pub const MIN_MORPH_REPEAT: i64 = 2;

/// Refuse a morph without both its settings, or without enough repeats to go from the pattern to its target.
fn checked_morph(settings: &Holder) -> Result<(), InvalidValue> {
    let written = |name: &str| settings.get(name).is_some_and(|value| !value.is_null());
    let morphs = written(ClipSlotSetting::MORPH_TO);
    if morphs != written(ClipSlotSetting::MORPH_STYLE) {
        return Err(InvalidValue::new(errors::ERR_MORPH_NEEDS_BOTH.to_string()));
    }
    let repeat = settings
        .get(ClipSlotSetting::REPEAT)
        .and_then(Data::as_whole)
        .map_or(crate::schema::generated::defaults::DEFAULT_REPEAT, |repeat| repeat as i64);
    if morphs && repeat < MIN_MORPH_REPEAT {
        return Err(InvalidValue::new(named(
            errors::ERR_MORPH_TOO_FEW_REPEATS,
            &[("lowest", MIN_MORPH_REPEAT.into())],
        )));
    }
    Ok(())
}

impl Context for Names<'_> {
    fn has_scale(&self, name: &str) -> bool {
        self.set.has_scale(name)
    }
    fn has_pattern(&self, name: &str) -> bool {
        self.set.has_pattern(name)
    }
    fn is_drum_pattern(&self, name: &str) -> bool {
        self.set.is_drum_pattern(name)
    }
    fn has_track(&self, name: &str) -> bool {
        self.tracks.iter().any(|track| track == name)
    }
    fn has_instrument(&self, name: &str) -> bool {
        self.set.has_instrument(name)
    }
    fn has_groove(&self, name: &str) -> bool {
        self.set.has_groove(name)
    }
    fn has_generator_named(&self, name: &str) -> bool {
        self.set.has_generator_named(name)
    }
}

/// A visualizer setting made sensible: a mode's name as it is, anything else nothing.
pub fn sensible_visualizer(value: Option<Data>) -> Option<Data> {
    value.filter(|value| value.as_str().is_some_and(|name| VISUALIZER_NAMES.contains(&name)))
}

/// A file's built-in generators with each kind's unknown settings passed over, as reading the set's list does.
fn built_ins_passed_over(data: &Data, name: &str) -> Data {
    let mut data = data.clone();
    let Some(Data::Map(built_ins)) = data.get(name).cloned() else { return data };
    let kept = built_ins
        .into_iter()
        .map(|(kind, settings)| {
            let built_in = PLUGINS
                .iter()
                .any(|plugin| plugin.built_in_place.is_some() && Some(plugin.name) == kind.as_str());
            match (built_in, kind.as_str().and_then(plugin_table), &settings) {
                (true, Some(table), Data::Map(_)) => (kind, passed_over(&settings, &|setting| in_table(table, setting))),
                _ => (kind, settings),
            }
        })
        .collect();
    data.set(name, Data::Map(kept));
    data
}

/// A draw's settings.
#[derive(Clone, Debug, PartialEq)]
pub struct Draw {
    settings: Holder,
}

impl Draw {
    pub fn from_data(data: &Data) -> Result<Draw, InvalidValue> {
        let data = if data.is_null() { Data::Map(Vec::new()) } else { data.clone() };
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(named(errors::ERR_DRAW_EXPECTED_SETTINGS, &[("data", (&data).into())])));
        }
        // A setting left at its default, written as nothing, is not checked.
        let data = passed_over(&data, &|name| in_table(DRAW, name));
        let without_blanks = Data::Map(data.as_map().unwrap_or(&[]).iter().filter(|(_, value)| !value.is_null()).cloned().collect());
        let settings = Holder::read(DRAW, &without_blanks, None, &[])?;
        checked_draw_range(&settings)?;
        Ok(Draw { settings })
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    pub fn to_data(&self) -> Data {
        self.settings.to_data()
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Track {
    settings: Holder,
}

impl Track {
    pub fn from_data(data: &Data, names: &dyn Context) -> Result<Track, InvalidValue> {
        let data = if data.is_null() { Data::Map(Vec::new()) } else { data.clone() };
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(named(errors::ERR_TRACK_EXPECTED_SETTINGS, &[("data", (&data).into())])));
        }
        let data = built_ins_passed_over(&passed_over(&data, &|name| in_table(TRACK, name)), TrackSetting::BUILT_IN);
        let settings = Holder::read(TRACK, &data, Some(names), &[])?;
        checked_octave_order(&settings)?;
        Ok(Track { settings })
    }

    pub fn is_drum(&self) -> bool {
        self.settings.get(TrackSetting::DRUM) == Some(&Data::Bool(true))
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    /// Write one of its settings as a file holds it, or take it out with None.
    pub fn set_written(&mut self, name: &str, value: Option<Data>) {
        self.settings.put(name, value);
    }

    pub fn to_data(&self) -> Data {
        self.settings.to_data()
    }
}

/// What a track plays in a scene.
#[derive(Clone, Debug, PartialEq)]
pub struct ClipSlot {
    settings: Holder,
}

impl ClipSlot {
    pub fn from_data(data: &Data, names: &dyn Context, track: &str) -> Result<ClipSlot, InvalidValue> {
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(named(errors::ERR_CLIP_SLOT_EXPECTED_SETTINGS, &[("data", data.into())])));
        }
        let mut data = built_ins_passed_over(
            &passed_over(data, &|name| in_table(CLIP_SLOT, name) || name == ClipSlotSetting::PATTERN),
            ClipSlotSetting::BUILT_IN,
        );
        // One pattern, as a file names it, is read as a list of one.
        if let Some(pattern) = data.get(ClipSlotSetting::PATTERN).cloned() {
            if data.get(ClipSlotSetting::PATTERNS).is_some() {
                return Err(InvalidValue::new(errors::ERR_PATTERN_AND_PATTERNS.to_string()));
            }
            data = Data::Map(
                data.as_map()
                    .unwrap_or(&[])
                    .iter()
                    .map(|(key, value)| {
                        if key.as_str() == Some(ClipSlotSetting::PATTERN) {
                            (Data::text(ClipSlotSetting::PATTERNS), Data::List(vec![pattern.clone()]))
                        } else {
                            (key.clone(), value.clone())
                        }
                    })
                    .collect(),
            );
        }
        let settings = Holder::read(CLIP_SLOT, &data, Some(names), &[])?;
        if settings.get(ClipSlotSetting::GRAB_TRACK).and_then(Data::as_str) == Some(track) {
            return Err(InvalidValue::new(errors::ERR_GRABS_ITSELF.to_string()));
        }
        if settings.get(ClipSlotSetting::PATTERNS).is_none() {
            return Err(InvalidValue::new(errors::ERR_NEEDS_PATTERN.to_string()));
        }
        checked_morph(&settings)?;
        Ok(ClipSlot { settings })
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    /// Write one of its settings as a file holds it, or take it out with None.
    pub fn set_written(&mut self, name: &str, value: Option<Data>) {
        self.settings.put(name, value);
    }

    /// The clip as a file holds it: one pattern named as pattern, several listed as patterns.
    pub fn to_data(&self) -> Data {
        let pairs = self
            .settings
            .written()
            .into_iter()
            .map(|(key, value)| match (&value, key.as_str()) {
                (Data::List(items), Some(ClipSlotSetting::PATTERNS)) if items.len() == 1 => (Data::text(ClipSlotSetting::PATTERN), items[0].clone()),
                _ => (key, value),
            })
            .collect();
        Data::Map(pairs)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Scene {
    settings: Holder,
    clip_slots: Option<Vec<(String, ClipSlot)>>,
}

impl Scene {
    pub fn from_data(data: &Data, names: &dyn Context) -> Result<Scene, InvalidValue> {
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(errors::ERR_SCENE_EXPECTED_SETTINGS.to_string()));
        }
        let data = passed_over(data, &|name| in_table(SCENE, name) || name == OBJECT_SCENE_TRACKS);
        let settings = Holder::read(SCENE, &data, Some(names), &[])?;
        let mut clip_slots = None;
        if let Some(tracks) = data.get(OBJECT_SCENE_TRACKS) {
            let mut read = Vec::new();
            for (track, clip_slot) in tracks.as_map().unwrap_or(&[]) {
                let track = track.python_str();
                if !names.has_track(&track) {
                    return Err(InvalidValue::new(named(errors::ERR_NO_SUCH_TRACK, &[("track", track.as_str().into())])));
                }
                read.push((track.clone(), ClipSlot::from_data(clip_slot, names, &track)?));
            }
            clip_slots = Some(read);
        }
        Ok(Scene { settings, clip_slots })
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    /// Write one of its settings as a file holds it, or take it out with None.
    pub fn set_written(&mut self, name: &str, value: Option<Data>) {
        self.settings.put(name, value);
    }

    pub fn clip_slots(&self) -> &[(String, ClipSlot)] {
        self.clip_slots.as_deref().unwrap_or(&[])
    }

    pub fn to_data(&self) -> Data {
        let mut pairs = self.settings.written();
        if let Some(clip_slots) = &self.clip_slots {
            pairs.push((
                Data::text(OBJECT_SCENE_TRACKS),
                Data::Map(clip_slots.iter().map(|(track, clip)| (Data::text(track), clip.to_data())).collect()),
            ));
        }
        Data::Map(pairs)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Song {
    settings: Holder,
    draws: Option<Vec<(String, Draw)>>,
    tracks: Option<Vec<(String, Track)>>,
    scenes: Option<Vec<Scene>>,
}

/// A text matching one of some choices without regard to capitals or the spaces around it, as the choice writes it.
fn known(text: Option<&Data>, choices: &[&'static str]) -> Option<&'static str> {
    let wanted = text?.as_str()?.trim().to_lowercase();
    choices.iter().find(|choice| choice.to_lowercase() == wanted).copied()
}

fn lookup<T: Copy>(table: &[(&str, T)], key: Option<&str>) -> Option<T> {
    let key = key?;
    table.iter().find(|(found, _)| *found == key).map(|(_, value)| *value)
}

/// A genre, subgenre and variant made sensible, each as the program writes it, or nothing where it names nothing known.
fn sensible_style(genre: Option<&Data>, subgenre: Option<&Data>, variant: Option<&Data>) -> (Option<&'static str>, Option<&'static str>, Option<&'static str>) {
    let mut subgenre_text = subgenre.cloned();
    let mut genre_text = genre.cloned();
    if let Some(written) = genre.and_then(Data::as_str).map(str::trim).filter(|written| written.ends_with(MASHUP_SUFFIX)) {
        subgenre_text = Some(Data::text(&written[..written.len() - MASHUP_SUFFIX.len()]));
        genre_text = Some(Data::text(MASHUP));
    }
    let genre = known(genre_text.as_ref(), GENRES);
    let subgenre = known(subgenre_text.as_ref(), lookup(SUBGENRES, genre).unwrap_or(&[]));
    let variants = lookup(VARIANTS, genre).and_then(|by_subgenre| lookup(by_subgenre, subgenre)).unwrap_or(&[]);
    (genre, subgenre, known(variant, variants))
}

impl Song {
    /// Change one of the song's draws, AD to HD, as its settings' data, refusing values out of order and holding its slots
    /// within its values; the file names only the draws whose settings differ from the default, in their order.
    pub fn change_draw(&mut self, name: &str, change: impl FnOnce(&mut Vec<(Data, Data)>)) -> Result<(), String> {
        let draws = self.draws.get_or_insert_with(Vec::new);
        let held = draws.iter().find(|(found, _)| found == name).map(|(_, draw)| draw.to_data());
        let mut pairs = held.and_then(|data| data.as_map().map(<[(Data, Data)]>::to_vec)).unwrap_or_default();
        change(&mut pairs);
        pairs.retain(|(_, value)| !value.is_null());
        let of = |pairs: &[(Data, Data)], key: &str| {
            pairs
                .iter()
                .find(|(found, _)| found.as_str() == Some(key))
                .and_then(|(_, value)| value.as_whole())
        };
        let lowest = of(&pairs, DrawSetting::VALUE_MIN).unwrap_or(limits::MIN_DRAW_VALUE as i128);
        let highest = of(&pairs, DrawSetting::VALUE_MAX).unwrap_or(limits::MAX_DRAW_VALUE as i128);
        if lowest > highest {
            return Err(named(
                errors::ERR_DRAW_VALUES_OUT_OF_ORDER,
                &[("lowest", (lowest as i64).into()), ("highest", (highest as i64).into())],
            ));
        }
        for (key, value) in pairs.iter_mut() {
            if key.as_str() == Some(DrawSetting::SLOTS) {
                if let Data::List(slots) = value {
                    for slot in slots.iter_mut() {
                        if let Some(number) = slot.as_whole() {
                            *slot = Data::Whole(number.clamp(lowest, highest));
                        }
                    }
                }
            }
        }
        let draw = Draw::from_data(&Data::Map(pairs.clone())).map_err(|problem| problem.message)?;
        draws.retain(|(found, _)| found != name);
        if !pairs.is_empty() {
            draws.push((name.to_string(), draw));
            draws.sort_by_key(|(found, _)| DRAW_NAMES.iter().position(|each| each == found).unwrap_or(usize::MAX));
        }
        if draws.is_empty() {
            self.draws = None;
        }
        Ok(())
    }

    /// Write one of the song's own settings as a file holds it, or take it out with None.
    pub fn set_written(&mut self, name: &str, value: Option<Data>) {
        self.settings.put(name, value);
    }

    /// Write the song's genre, subgenre and variant together, each kept only where it fits the ones before it.
    pub fn set_style(&mut self, genre: Option<Data>, subgenre: Option<Data>, variant: Option<Data>) {
        let (genre, subgenre, variant) = sensible_style(genre.as_ref(), subgenre.as_ref(), variant.as_ref());
        self.settings.put(SongSetting::GENRE, genre.map(Data::text));
        self.settings.put(SongSetting::SUBGENRE, subgenre.map(Data::text));
        self.settings.put(SongSetting::VARIANT, variant.map(Data::text));
    }

    /// Move a scene one place up or down, as Move mode carries it; false where it would leave the list.
    pub fn move_scene(&mut self, index: usize, offset: i64) -> bool {
        let Some(scenes) = self.scenes.as_mut() else { return false };
        let to = index as i64 + offset;
        if index >= scenes.len() || to < 0 || to as usize >= scenes.len() {
            return false;
        }
        scenes.swap(index, to as usize);
        true
    }

    /// Move a track one place left or right, by its place; false where it would leave the list.
    pub fn move_track(&mut self, place: usize, offset: i64) -> bool {
        let Some(tracks) = self.tracks.as_mut() else { return false };
        let to = place as i64 + offset;
        if place >= tracks.len() || to < 0 || to as usize >= tracks.len() {
            return false;
        }
        tracks.swap(place, to as usize);
        true
    }

    /// Take a clip out of its cell, by its scene's place and its track, and hand it back.
    pub fn take_clip(&mut self, index: usize, track: &str) -> Option<ClipSlot> {
        let scene = self.scenes.as_mut()?.get_mut(index)?;
        let clips = scene.clip_slots.as_mut()?;
        let place = clips.iter().position(|(found, _)| found == track)?;
        Some(clips.remove(place).1)
    }

    /// Put a clip in a cell, by its scene's place and its track, the scene's clips kept in the order of the song's tracks.
    pub fn put_clip(&mut self, index: usize, track: &str, clip: ClipSlot) {
        let order: Vec<String> = self.tracks.iter().flatten().map(|(name, _)| name.clone()).collect();
        let Some(scene) = self.scenes.as_mut().and_then(|scenes| scenes.get_mut(index)) else {
            return;
        };
        let clips = scene.clip_slots.get_or_insert_with(Vec::new);
        clips.retain(|(found, _)| found != track);
        let rank = |name: &str| order.iter().position(|each| each == name).unwrap_or(usize::MAX);
        let place = clips.iter().position(|(found, _)| rank(found) > rank(track)).unwrap_or(clips.len());
        clips.insert(place, (track.to_string(), clip));
    }

    /// Write one of a track's settings, by the track's name.
    pub fn set_track_written(&mut self, track: &str, name: &str, value: Option<Data>) {
        if let Some((_, found)) = self.tracks.iter_mut().flatten().find(|(found, _)| found == track) {
            found.set_written(name, value);
        }
    }

    /// Write one of a scene's settings, by the scene's place.
    pub fn set_scene_written(&mut self, index: usize, name: &str, value: Option<Data>) {
        if let Some(scene) = self.scenes.iter_mut().flatten().nth(index) {
            scene.set_written(name, value);
        }
    }

    /// Write one of a clip's settings, by its scene's place and its track.
    pub fn set_clip_written(&mut self, index: usize, track: &str, name: &str, value: Option<Data>) {
        let Some(scene) = self.scenes.iter_mut().flatten().nth(index) else { return };
        if let Some((_, clip)) = scene.clip_slots.iter_mut().flatten().find(|(found, _)| found == track) {
            clip.set_written(name, value);
        }
    }

    pub fn from_data(data: &Data, set: &dyn Context) -> Result<Song, InvalidValue> {
        let data = if data.is_null() { Data::Map(Vec::new()) } else { data.clone() };
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(named(errors::ERR_NOT_A_SONG, &[("value", (&data).into())])));
        }
        let data = passed_over(&data, &|name| {
            in_table(SONG, name) || [Section::DRAWS, Section::TRACKS, Section::SCENES].contains(&name)
        });
        let mut names = Names { set, tracks: Vec::new() };
        let mut settings = Holder::read(SONG, &data, Some(&names), &[])?;
        settings.put(SongSetting::VISUALIZER, sensible_visualizer(settings.get(SongSetting::VISUALIZER).cloned()));
        let (genre, subgenre, variant) = sensible_style(
            settings.get(SongSetting::GENRE),
            settings.get(SongSetting::SUBGENRE),
            settings.get(SongSetting::VARIANT),
        );
        settings.put(SongSetting::GENRE, genre.map(Data::text));
        settings.put(SongSetting::SUBGENRE, subgenre.map(Data::text));
        settings.put(SongSetting::VARIANT, variant.map(Data::text));
        let draws = match data.get(Section::DRAWS) {
            None => None,
            Some(draws) => {
                let mut read = Vec::new();
                for (name, draw) in draws.as_map().unwrap_or(&[]) {
                    if !name.as_str().is_some_and(|name| DRAW_NAMES.contains(&name)) {
                        return Err(InvalidValue::new(named(
                            errors::ERR_DRAWS_NOT_NAMED,
                            &[("names", DRAW_NAMES.join(", ").into())],
                        )));
                    }
                    read.push((name.python_str(), Draw::from_data(draw)?));
                }
                Some(read)
            }
        };
        let tracks = match data.get(Section::TRACKS) {
            None => None,
            Some(tracks) => {
                names.tracks = tracks.as_map().unwrap_or(&[]).iter().map(|(name, _)| name.python_str()).collect();
                let mut read = Vec::new();
                for (name, track) in tracks.as_map().unwrap_or(&[]) {
                    read.push((name.python_str(), Track::from_data(track, &names)?));
                }
                Some(read)
            }
        };
        let scenes = match data.get(Section::SCENES) {
            None => None,
            Some(scenes) => {
                let mut read = Vec::new();
                for scene in scenes.as_list().unwrap_or(&[]) {
                    read.push(Scene::from_data(scene, &names)?);
                }
                Some(read)
            }
        };
        Ok(Song {
            settings,
            draws,
            tracks,
            scenes,
        })
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    pub fn tracks(&self) -> &[(String, Track)] {
        self.tracks.as_deref().unwrap_or(&[])
    }

    /// The tracks as Arrange shows them: the melodic tracks in the file's order, then the drum tracks in the file's order.
    /// The file keeps its own order, which the exports follow.
    pub fn shown_tracks(&self) -> Vec<&(String, Track)> {
        let (melodic, drums): (Vec<_>, Vec<_>) = self.tracks().iter().partition(|(_, track)| !track.is_drum());
        melodic.into_iter().chain(drums).collect()
    }

    /// How many of the tracks are melodic, the first group Arrange shows.
    pub fn melodic_count(&self) -> usize {
        self.tracks().iter().filter(|(_, track)| !track.is_drum()).count()
    }

    /// Move a track to just before another in the file's order, or to the end of the file when there is none to go before,
    /// as a paste on Arrange places it; false when the track is not found.
    pub fn move_track_before(&mut self, name: &str, before: Option<&str>) -> bool {
        let Some(tracks) = self.tracks.as_mut() else { return false };
        let Some(from) = tracks.iter().position(|(found, _)| found == name) else {
            return false;
        };
        let moved = tracks.remove(from);
        let to = before
            .and_then(|other| tracks.iter().position(|(found, _)| found == other))
            .unwrap_or(tracks.len());
        tracks.insert(to, moved);
        true
    }

    pub fn draws(&self) -> &[(String, Draw)] {
        self.draws.as_deref().unwrap_or(&[])
    }

    pub fn scenes(&self) -> &[Scene] {
        self.scenes.as_deref().unwrap_or(&[])
    }

    pub fn to_data(&self) -> Data {
        let mut pairs = self.settings.written();
        if let Some(draws) = &self.draws {
            pairs.push((
                Data::text(Section::DRAWS),
                Data::Map(draws.iter().map(|(name, draw)| (Data::text(name), draw.to_data())).collect()),
            ));
        }
        if let Some(tracks) = &self.tracks {
            pairs.push((
                Data::text(Section::TRACKS),
                Data::Map(tracks.iter().map(|(name, track)| (Data::text(name), track.to_data())).collect()),
            ));
        }
        if let Some(scenes) = &self.scenes {
            pairs.push((Data::text(Section::SCENES), Data::List(scenes.iter().map(Scene::to_data).collect())));
        }
        Data::Map(pairs)
    }
}
