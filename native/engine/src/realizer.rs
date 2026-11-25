// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Realizer, which plays a song into clips (the Python engine/realizer/song_realizer.py and written_scene.py): every
//! scene in order, a scene that repeats written out once for each repeat, each track's clip in it played, and a scene's
//! length worked out without playing, as its longest clip that does not loop.
//!
//! The port plays a part of what the Python does so far; a song using a part not yet ported is refused as not ported,
//! named, before anything plays (`check_ported`).

use crate::clip::Clip;
use crate::clip_player::ClipSlotPlayer;
use crate::error::{RenderError, Rendered};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::{Scene, Song, Track};
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, InstrumentSetting, PatternSetting, SceneSetting, Section, SongSetting, TrackSetting};
use llamatron_model::schema::generated::settings::{Setting, CLIP_SLOT, INSTRUMENT, PATTERN, SCENE, SONG, TRACK};
use llamatron_strings::{errors, named, names};
use std::cell::RefCell;
use std::collections::HashMap;

/// A scene's place in the song, counted from 1, with the name and scale it plays with.
pub struct WrittenScene<'a> {
    pub number: i64,
    pub name: String,
    pub scale_name: Option<String>,
    pub scene: &'a Scene,
    pub first_play: bool,
}

impl WrittenScene<'_> {
    /// Every scene of a song in order, a scene that repeats written out once for each repeat, a repeat's name with its number.
    pub fn write_out(song: &Song) -> Vec<WrittenScene<'_>> {
        let mut written = Vec::new();
        for scene in song.scenes() {
            let scale_name = scene.get_scale_name().or_else(|| song.get_scale_name());
            let repeat = scene.get_repeat();
            for place in 0..repeat {
                let number = written.len() as i64 + 1;
                let mut name = match scene.get_name() {
                    Some(name) => name,
                    None => named(names::MSG_UNNAMED_SCENE, &[("number", number.into())]),
                };
                if repeat > 1 {
                    name = format!("{name} {}", place + 1);
                }
                written.push(WrittenScene {
                    number,
                    name,
                    scale_name: scale_name.clone(),
                    scene,
                    first_play: place == 0,
                });
            }
        }
        written
    }

    /// How error messages name it, like "scene 3 (verse)".
    pub fn describe(&self) -> String {
        named(
            names::MSG_SCENE_DESCRIPTION,
            &[("number", self.number.into()), ("name", self.name.as_str().into())],
        )
    }
}

/// A song rendered: its tracks, and each written-out scene's name and clips by track.
pub struct Grid {
    pub tracks: Vec<String>,
    pub rows: Vec<GridRow>,
}

pub struct GridRow {
    pub name: String,
    pub clips: Vec<(String, Clip)>,
}

pub struct SongRealizer<'a> {
    setlist: &'a Setlist,
    song: &'a Song,
    seed: Option<i64>,
    scenes: Vec<WrittenScene<'a>>,
    lengths: RefCell<HashMap<i64, Rational>>,
}

impl<'a> SongRealizer<'a> {
    pub fn new(setlist: &'a Setlist, song: &'a Song, seed: Option<i64>) -> SongRealizer<'a> {
        SongRealizer {
            setlist,
            song,
            seed,
            scenes: WrittenScene::write_out(song),
            lengths: RefCell::new(HashMap::new()),
        }
    }

    pub fn setlist(&self) -> &'a Setlist {
        self.setlist
    }

    pub fn song(&self) -> &'a Song {
        self.song
    }

    pub fn seed(&self) -> Option<i64> {
        self.seed
    }

    pub fn track(&self, name: &str) -> Rendered<&'a Track> {
        self.song
            .get_track(name)
            .ok_or_else(|| RenderError::Refused(format!("no track called ({name})")))
    }

    /// Every written-out scene's finished clips.
    pub fn render(&self) -> Rendered<Grid> {
        check_ported(self.setlist, self.song)?;
        let tracks: Vec<String> = self.song.get_track_names().into_iter().map(str::to_string).collect();
        let mut rows = Vec::new();
        for scene in &self.scenes {
            let mut clips = Vec::new();
            for track in &tracks {
                let Some(clip_slot) = scene.scene.get_clip_slot(track) else { continue };
                clips.push((track.clone(), ClipSlotPlayer::new(self, scene, track, clip_slot).play()?));
            }
            rows.push(GridRow {
                name: scene.name.clone(),
                clips,
            });
        }
        Ok(Grid { tracks, rows })
    }

    /// How long a scene lasts: its longest clip that does not loop, worked out without playing.
    pub fn get_scene_length(&self, scene: &WrittenScene) -> Rendered<Rational> {
        if let Some(length) = self.lengths.borrow().get(&scene.number) {
            return Ok(*length);
        }
        if scene.scene.every_clip_loops() {
            return Err(RenderError::Refused(named(
                errors::ERR_RENDERER_EVERY_CLIP_LOOPS,
                &[("scene", scene.describe().as_str().into())],
            )));
        }
        let mut length = Rational::ZERO;
        for (_, clip_slot) in scene.scene.clip_slots() {
            if !clip_slot.loops() {
                let mut one_pass = Rational::ZERO;
                for name in clip_slot.get_pattern_names() {
                    let pattern = self
                        .setlist
                        .get_pattern(&name)
                        .ok_or_else(|| RenderError::Refused(format!("no pattern called ({name})")))?;
                    one_pass = one_pass + self.setlist.get_pattern_length(pattern);
                }
                length = length.max(Rational::whole(clip_slot.get_repeat() as i128) * one_pass);
            }
        }
        self.lengths.borrow_mut().insert(scene.number, length);
        Ok(length)
    }
}

/// Whether a setting is written as something that does anything: false and an empty list are as good as not written.
fn holds_something(value: &Data) -> bool {
    !matches!(value, Data::Null | Data::Bool(false))
        && value.as_list().is_none_or(|items| !items.is_empty())
        && value.as_map().is_none_or(|pairs| !pairs.is_empty())
}

/// The first setting of a table an object holds that the port does not play yet.
fn unported(table: &[Setting], played: &[&str], written: &dyn Fn(&str) -> Option<Data>) -> Rendered<()> {
    for setting in table {
        if !played.contains(&setting.name) && written(setting.name).is_some_and(|value| holds_something(&value)) {
            return Err(RenderError::NotPorted(format!("the {} setting", setting.name)));
        }
    }
    Ok(())
}

/// Refuse a song that uses a part of the render not ported yet, naming the part.
fn check_ported(setlist: &Setlist, song: &Song) -> Rendered<()> {
    let song_played = [
        SongSetting::TEMPO,
        SongSetting::TIME_SIGNATURE,
        SongSetting::ENTRY_SIZE,
        SongSetting::SCALE,
        SongSetting::GENRE,
        SongSetting::SUBGENRE,
        SongSetting::VARIANT,
        SongSetting::LIVE_RESPONSIVENESS,
        SongSetting::VISUALIZER,
        SongSetting::PREVIEW_INSTRUMENT,
        SongSetting::WIZARD,
    ];
    unported(SONG, &song_played, &|name| song.get_written(name).cloned())?;
    if song.draws().iter().any(|(_, draw)| holds_something(&draw.to_data())) {
        return Err(RenderError::not_ported("draws"));
    }
    let track_played = [
        TrackSetting::DRUM,
        TrackSetting::MUTE,
        TrackSetting::TRANSPOSE,
        TrackSetting::CC,
        TrackSetting::INSTRUMENT,
        TrackSetting::DEFAULT_VELOCITY,
        TrackSetting::ACCENT,
    ];
    for (_, track) in song.tracks() {
        unported(TRACK, &track_played, &|name| track.get_written(name).cloned())?;
    }
    let scene_played = [
        SceneSetting::NAME,
        SceneSetting::SECTION,
        SceneSetting::REPEAT,
        SceneSetting::SCALE,
        SceneSetting::LAUNCH_TOGETHER,
    ];
    let clip_played = [
        ClipSlotSetting::NAME,
        ClipSlotSetting::PATTERNS,
        ClipSlotSetting::LOOP,
        ClipSlotSetting::PATTERN_ORDER,
        ClipSlotSetting::REPEAT,
        ClipSlotSetting::DIRECTION,
        ClipSlotSetting::FOLLOW_ACTION,
        ClipSlotSetting::SCALE,
    ];
    for scene in song.scenes() {
        unported(SCENE, &scene_played, &|name| scene.get_written(name).cloned())?;
        for (_, clip_slot) in scene.clip_slots() {
            unported(CLIP_SLOT, &clip_played, &|name| clip_slot.get_written(name).cloned())?;
        }
    }
    let instrument_played = [
        InstrumentSetting::DEVICE,
        InstrumentSetting::CHANNEL,
        InstrumentSetting::GM_SOUND,
        InstrumentSetting::KEYSWITCHES,
        InstrumentSetting::KEYSWITCH_LEAD,
        InstrumentSetting::DEFAULT_VELOCITY,
        InstrumentSetting::ACCENT,
        InstrumentSetting::KIND,
        InstrumentSetting::LATENCY,
        InstrumentSetting::SOUND,
        InstrumentSetting::PREVIEW,
        InstrumentSetting::ROLE,
    ];
    for (_, item) in setlist.items(Section::INSTRUMENTS) {
        if let llamatron_model::objects::setlist::Item::Instrument(instrument) = item {
            unported(INSTRUMENT, &instrument_played, &|name| instrument.get_written(name).cloned())?;
        }
    }
    let pattern_played = [
        PatternSetting::STEP_SIZE,
        PatternSetting::TIME_SIGNATURE,
        PatternSetting::ENTRY_SIZE,
        PatternSetting::DRUM,
        PatternSetting::DIRECTION,
        PatternSetting::GROUP,
    ];
    for (_, item) in setlist.items(Section::PATTERNS) {
        if let llamatron_model::objects::setlist::Item::Pattern(pattern) = item {
            unported(PATTERN, &pattern_played, &|name| pattern.get_written(name).cloned())?;
        }
    }
    Ok(())
}
