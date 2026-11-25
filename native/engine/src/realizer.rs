// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Realizer, which plays a song into clips (the Python engine/realizer/song_realizer.py and written_scene.py): every
//! scene in order, a scene that repeats written out once for each repeat, each track's clip in it played, and a scene's
//! length worked out without playing, as its longest clip that does not loop.
//!
//! The port plays a part of what the Python does so far; a song using a part not yet ported is refused as not ported,
//! named, before anything plays (`check_ported`).

use crate::chord_source::ChordSource;
use crate::clip::Clip;
use crate::clip_player::ClipSlotPlayer;
use crate::error::{RenderError, Rendered};
use crate::generators::chords::Continuation;
use crate::grab_source::GrabSource;
use crate::groove::{groove_for, Groove};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::{Scene, Song, Track};
use llamatron_model::schema::generated::defaults;
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, InstrumentSetting, PatternSetting, SceneSetting, Section, SongSetting, TrackSetting};
use llamatron_model::schema::generated::file_format::{Restart, BYPASS_WHEN, GENERATOR_ENABLED};
use llamatron_model::schema::generated::limits::{MAX_TEMPO, MIN_TEMPO};
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_model::schema::generated::settings::{Setting, CLIP_SLOT, INSTRUMENT, PATTERN, SCENE, SONG, TRACK};
use llamatron_strings::{errors, named, names};
use std::cell::RefCell;
use std::collections::HashMap;

/// A scene's place in the song, counted from 1, with the name and scale it plays with.
pub struct WrittenScene<'a> {
    pub number: i64,
    pub name: String,
    pub scale_name: Option<String>,
    /// The tempo it plays at where it changes the song's, or None where it plays at the song's.
    pub tempo: Option<Rational>,
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
                    tempo: own_tempo(scene, song),
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

/// A tempo or a percentage as the Python reads one, an exact number.
fn exact(value: &Data) -> Option<Rational> {
    llamatron_model::schema::checking::number(value).ok()
}

/// The tempo a scene plays at where it changes the song's: the song's scaled by the scene's percentage.
fn own_tempo(scene: &Scene, song: &Song) -> Option<Rational> {
    let percent = scene.get_written(SceneSetting::TEMPO)?;
    scaled_tempo(exact(&song.get_tempo())?, percent)
}

/// A tempo scaled by a percentage, held to the tempos a set may hold.
fn scaled_tempo(tempo: Rational, percent: &Data) -> Option<Rational> {
    let scaled = tempo * exact(percent)? / Rational::whole(100);
    Some(scaled.max(Rational::whole(MIN_TEMPO as i128)).min(Rational::whole(MAX_TEMPO as i128)))
}

/// The tempo a scene plays at, its own or the song's.
fn tempo_in(scene: &Scene, song: &Song) -> Rational {
    own_tempo(scene, song).or_else(|| exact(&song.get_tempo())).unwrap_or(Rational::whole(120))
}

/// A number rounded to some decimal places, as Python's round(number, places) rounds a float.
fn rounded(value: f64, places: usize) -> f64 {
    format!("{value:.places$}").parse().unwrap_or(value)
}

/// A scene's tempo ramp one way, its ends tempos or None where blank and its bars, or None where it changes nothing.
struct TempoRamp {
    start: Option<f64>,
    end: Option<f64>,
    over: Rational,
}

fn tempo_ramp(scene: &Scene, way: &str, base: Rational) -> Option<TempoRamp> {
    let written = |part: &str| scene.get_written(&format!("tempo_{way}_{part}")).filter(|value| !value.is_null());
    let over = written("over")?.as_whole()?;
    let (start, end) = (written("start"), written("end"));
    if start.is_none() && end.is_none() {
        return None;
    }
    Some(TempoRamp {
        start: start.and_then(|start| scaled_tempo(base, start)).map(|tempo| tempo.to_float()),
        end: end.and_then(|end| scaled_tempo(base, end)).map(|tempo| tempo.to_float()),
        over: Rational::whole(over),
    })
}

/// The tempo between a ramp's ends a share of the way along, a blank end being the tempo there would have been.
fn between(ramp: &TempoRamp, base: f64, share: Rational) -> f64 {
    let start = ramp.start.unwrap_or(base);
    let end = ramp.end.unwrap_or(base);
    rounded(start + (end - start) * share.to_float(), TEMPO_PLACES)
}

/// A scene's tempos across its whole play, step by step, each change of tempo with when it starts.
fn ramped_tempos(
    base: Rational,
    ramp_in: Option<TempoRamp>,
    ramp_out: Option<TempoRamp>,
    length: Rational,
    bar: Rational,
    step: Rational,
) -> Vec<(Rational, f64)> {
    let base_float = base.to_float();
    let in_span = ramp_in.as_ref().map(|ramp| ramp.over * bar).unwrap_or(length);
    let out_span = ramp_out.as_ref().map(|ramp| ramp.over * bar).unwrap_or(length);
    let out_from = length - out_span;
    let mut tempos: Vec<(Rational, f64)> = Vec::new();
    let mut time = Rational::ZERO;
    while time < length || tempos.is_empty() {
        let tempo = match (&ramp_in, &ramp_out) {
            (Some(ramp), _) if time < in_span => between(ramp, base_float, time / in_span),
            (_, Some(ramp)) if time >= out_from => between(ramp, base_float, ((time - out_from + step) / out_span).min(Rational::whole(1))),
            _ => base_float,
        };
        if tempos.last().is_none_or(|(_, last)| *last != tempo) {
            tempos.push((time, tempo));
        }
        time = time + step;
    }
    tempos
}

/// A song rendered: its tracks, and each written-out scene's name and clips by track.
pub struct Grid {
    pub tracks: Vec<String>,
    pub rows: Vec<GridRow>,
}

pub struct GridRow {
    pub name: String,
    pub tempo: Option<f64>,
    /// The changes of tempo inside the row after its start, where its scene ramps, each with its time from the row's start.
    pub tempo_changes: Vec<(Rational, f64)>,
    pub clips: Vec<(String, Clip)>,
}

pub struct SongRealizer<'a> {
    setlist: &'a Setlist,
    song: &'a Song,
    seed: Option<i64>,
    scenes: Vec<WrittenScene<'a>>,
    lengths: RefCell<HashMap<i64, Rational>>,
    // Each finished clip, by written scene and track, played once, since another clip can ask for it: one that follows its
    // chords, or one that carries on from it.
    clips: RefCell<HashMap<(i64, String), Clip>>,
    // The state each generator left each track's clip in, by written scene, track and the generator's key.
    end_states: RefCell<HashMap<(i64, String, GeneratorKey), EndState>>,
    // The clips being made that wait on another's chords, so that tracks that follow each other in a circle are refused.
    following: RefCell<Vec<(i64, String)>>,
    // The tracks whose clips wait on another's notes to grab, so that tracks that grab from each other in a circle are refused.
    grabbing: RefCell<Vec<String>>,
}

/// What keeps a generator's end state apart from another's in a clip: its kind, its name, and how many times before it
/// came up in the clip's chains.
pub type GeneratorKey = (String, String, i64);

/// The state a generator leaves a clip in, for the next to carry on from: a voicing's last chord, or none.
pub type EndState = Option<Vec<i64>>;

/// A step of a clip's chains: its generator's kind, the name it goes by, and its settings, a built-in's its own and a
/// named generator's the set's.
pub struct ChainStep {
    pub kind: String,
    pub name: String,
    pub settings: Data,
}

impl<'a> SongRealizer<'a> {
    pub fn new(setlist: &'a Setlist, song: &'a Song, seed: Option<i64>) -> SongRealizer<'a> {
        SongRealizer {
            setlist,
            song,
            seed,
            scenes: WrittenScene::write_out(song),
            lengths: RefCell::new(HashMap::new()),
            clips: RefCell::new(HashMap::new()),
            end_states: RefCell::new(HashMap::new()),
            following: RefCell::new(Vec::new()),
            grabbing: RefCell::new(Vec::new()),
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
                if let Some(mut clip) = self.get_clip(scene, track)? {
                    // The groove goes on last, so that generators, grabs and lengths never see it.
                    clip.groove = self.groove_at(scene, track)?;
                    clips.push((track.clone(), clip));
                }
            }
            let tempos = self.tempos_of(scene)?;
            rows.push(GridRow {
                name: scene.name.clone(),
                tempo: tempos.as_ref().map(|tempos| tempos[0].1).or(scene.tempo.map(|tempo| tempo.to_float())),
                tempo_changes: tempos.map(|tempos| tempos[1..].to_vec()).unwrap_or_default(),
                clips,
            });
        }
        Ok(Grid { tracks, rows })
    }

    /// The groove a track's clip plays with in a written-out scene: its track's choice, else its scene's, else its song's.
    fn groove_at(&self, scene: &WrittenScene, track: &str) -> Rendered<Option<Groove>> {
        let song_groove = Data::text(defaults::DEFAULT_GROOVE);
        let choices = [
            self.track(track)?.get_written(TrackSetting::GROOVE),
            scene.scene.get_written(SceneSetting::GROOVE),
            Some(self.song.get_written(SongSetting::GROOVE).unwrap_or(&song_groove)),
        ];
        groove_for(self.setlist, &choices)
    }

    /// The finished clip a track plays in a written-out scene, or None where it plays nothing there.
    pub fn get_clip(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Option<Clip>> {
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else { return Ok(None) };
        let key = (scene.number, track.to_string());
        if let Some(clip) = self.clips.borrow().get(&key) {
            return Ok(Some(clip.clone()));
        }
        let clip = ClipSlotPlayer::new(self, scene, track, clip_slot).play()?;
        self.clips.borrow_mut().insert(key, clip.clone());
        Ok(Some(clip))
    }

    /// What a track's grab steps take notes from in a written-out scene: the finished clip of the track it grabs, or None
    /// where that track plays nothing there.
    pub fn grab_source(&self, scene: &WrittenScene<'a>, track: &str, other: &str) -> Rendered<Option<GrabSource>> {
        if scene.scene.get_clip_slot(other).is_none() {
            return Ok(None);
        }
        let mut waiting = self.grabbing.borrow().clone();
        waiting.push(track.to_string());
        if let Some(first) = waiting.iter().position(|name| name == other) {
            let mut circle = waiting[first..].to_vec();
            circle.push(other.to_string());
            let looped = circle.join(llamatron_strings::marks::MSG_CIRCLE_ARROW);
            return Err(RenderError::Refused(named(
                errors::ERR_CIRCULAR_GRAB,
                &[("scene", scene.describe().as_str().into()), ("loop", looped.as_str().into())],
            )));
        }
        self.grabbing.borrow_mut().push(track.to_string());
        let clip = self.get_clip(scene, other);
        self.grabbing.borrow_mut().pop();
        match clip? {
            Some(clip) => Ok(Some(GrabSource::of(&clip)?)),
            None => Ok(None),
        }
    }

    /// The chords a track followed plays in a written-out scene, after its own chains, or None where it plays nothing there,
    /// is no track of the song or is the track that follows.
    pub fn chords_followed(&self, scene: &WrittenScene<'a>, track: &str, source: Option<&str>) -> Rendered<Option<ChordSource>> {
        let Some(source) = source.filter(|source| *source != track && self.song.get_track(source).is_some() && scene.scene.get_clip_slot(source).is_some())
        else {
            return Ok(None);
        };
        let mut waiting = self.following.borrow().clone();
        waiting.push((scene.number, track.to_string()));
        if let Some(first) = waiting.iter().position(|(number, name)| *number == scene.number && name == source) {
            let mut circle: Vec<String> = waiting[first..].iter().map(|(_, name)| name.clone()).collect();
            circle.push(source.to_string());
            let looped = circle.join(llamatron_strings::marks::MSG_CIRCLE_ARROW);
            return Err(RenderError::Refused(named(
                errors::ERR_CIRCULAR_FOLLOW,
                &[("scene", scene.describe().as_str().into()), ("loop", looped.as_str().into())],
            )));
        }
        self.following.borrow_mut().push((scene.number, track.to_string()));
        let clip = self.get_clip(scene, source);
        self.following.borrow_mut().pop();
        match clip? {
            Some(clip) => Ok(Some(ChordSource::of(&clip)?)),
            None => Ok(None),
        }
    }

    /// What a track's clip in a written-out scene runs its notes through, in order: its built-ins switched on, a clip's
    /// standing in for its track's of the same kind, then the chains of its own list, its scene's and its track's.
    pub fn chains_of(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Vec<ChainStep>> {
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else {
            return Ok(Vec::new());
        };
        let on_track = self.track(track)?;
        let mut kinds: Vec<_> = PLUGINS.iter().filter(|plugin| plugin.built_in_place.is_some()).collect();
        kinds.sort_by_key(|plugin| plugin.built_in_place);
        let mut steps = Vec::new();
        for plugin in kinds {
            let held = [clip_slot.get_written(ClipSlotSetting::BUILT_IN), on_track.get_written(TrackSetting::BUILT_IN)]
                .into_iter()
                .flatten()
                .filter_map(|built_ins| built_ins.get(plugin.name))
                .find(|settings| is_switched_on(settings));
            if let Some(settings) = held {
                steps.push(ported_step(plugin.name, llamatron_strings::names::MSG_BUILT_IN_NAME, settings.clone())?);
            }
        }
        let lists = [
            clip_slot.get_written(ClipSlotSetting::CHAINS),
            scene.scene.get_written(SceneSetting::CHAINS),
            on_track.get_written(TrackSetting::CHAINS),
        ];
        for name in lists.into_iter().flatten().filter_map(Data::as_list).flatten() {
            steps.extend(self.chain_run(&name.python_str())?);
        }
        Ok(steps)
    }

    /// The steps of a chain the set names, its generators switched off left out; or a generator of another kind, a chain of
    /// that generator alone.
    fn chain_run(&self, name: &str) -> Rendered<Vec<ChainStep>> {
        if let Some(Item::Chain(chain)) = self.setlist.get_item(Section::CHAINS, name) {
            if chain.get_bypass_when().is_some() {
                return Err(RenderError::not_ported("statements that bypass a chain"));
            }
            let mut steps = Vec::new();
            for (kind, generator) in chain.get_steps() {
                if let Some(settings) = self.generator_settings(kind, generator)? {
                    steps.push(ported_step(kind, generator, settings)?);
                }
            }
            return Ok(steps);
        }
        for plugin in PLUGINS {
            if self.setlist.get_item(plugin.section, name).is_some() {
                return match self.generator_settings(plugin.name, name)? {
                    Some(settings) => Ok(vec![ported_step(plugin.name, name, settings)?]),
                    None => Ok(Vec::new()),
                };
            }
        }
        Err(RenderError::Refused(format!("no chain or generator called ({name})")))
    }

    /// A named generator's settings, or None where it is switched off.
    fn generator_settings(&self, kind: &str, name: &str) -> Rendered<Option<Data>> {
        let section = PLUGINS.iter().find(|plugin| plugin.name == kind).map(|plugin| plugin.section).unwrap_or("");
        let Some(Item::Generator(settings)) = self.setlist.get_item(section, name) else {
            return Err(RenderError::Refused(format!("no {kind} generator called ({name})")));
        };
        let data = settings.to_data();
        if data.get(GENERATOR_ENABLED) == Some(&Data::Bool(false)) {
            return Ok(None);
        }
        Ok(Some(data))
    }

    /// Where a generator carries on from in a track's clip: how far into its run the clip starts, and the state the same
    /// track's latest clip before in the run left it in, the clips before played first if they are not yet.
    pub fn continuation(&self, scene: &WrittenScene<'a>, track: &str, key: &GeneratorKey, restart: Option<&str>) -> Rendered<Continuation> {
        let offset = self.run_offset(scene, restart)?;
        let start = self.run_start(scene, restart);
        let here = (scene.number - 1) as usize;
        let mut state = None;
        // The clips before are played without the grabs waiting on this one, since a clip before can't be in a grab circle with it.
        let waiting = self.grabbing.replace(Vec::new());
        let found = self.earlier_state(start, here, track, key, &mut state);
        self.grabbing.replace(waiting);
        found?;
        Ok(Continuation { offset, state })
    }

    fn earlier_state(&self, start: usize, here: usize, track: &str, key: &GeneratorKey, state: &mut Option<Vec<i64>>) -> Rendered<()> {
        for written in self.scenes[start..here].iter().rev() {
            if written.scene.get_clip_slot(track).is_none() {
                continue;
            }
            self.get_clip(written, track)?;
            if let Some(found) = self.end_states.borrow().get(&(written.number, track.to_string(), key.clone())) {
                *state = found.clone();
                break;
            }
        }
        Ok(())
    }

    pub fn keep_end_state(&self, scene: &WrittenScene, track: &str, key: GeneratorKey, state: Option<Vec<i64>>) {
        self.end_states.borrow_mut().insert((scene.number, track.to_string(), key), state);
    }

    /// The place among the written-out scenes that a generator's run starts at, as its Restart says: this scene, the first
    /// play of this scene, or the song's first.
    fn run_start(&self, scene: &WrittenScene, restart: Option<&str>) -> usize {
        let here = (scene.number - 1) as usize;
        match restart {
            Some(Restart::WHOLE_SONG) => 0,
            Some(Restart::ON_NEW_SCENE) => {
                let mut place = here;
                while place > 0 && !self.scenes[place].first_play {
                    place -= 1;
                }
                place
            }
            _ => here,
        }
    }

    /// How far into its run a generator is as a written-out scene starts.
    pub fn run_offset(&self, scene: &WrittenScene<'a>, restart: Option<&str>) -> Rendered<Rational> {
        let start = self.run_start(scene, restart);
        let mut offset = Rational::ZERO;
        for written in &self.scenes[start..(scene.number - 1) as usize] {
            offset = offset + self.get_scene_length(written)?;
        }
        Ok(offset)
    }

    /// The seed a generator that chooses at random takes at a place in a clip's chains, or None for an unseeded render.
    pub fn chain_step_seed(&self, scene: &WrittenScene, track: &str, index: i128) -> Rendered<Option<i128>> {
        let Some(seed) = self.seed else { return Ok(None) };
        let place = self.song.get_track_names().iter().position(|name| *name == track).unwrap_or(0) as i128;
        Ok(Some(
            seed as i128 * SEED_SONG_FACTOR + scene.number as i128 * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR + index,
        ))
    }

    /// How long a generator's whole run lasts: the clip, every play of the scene in a row, or the whole song.
    pub fn run_span(&self, scene: &WrittenScene<'a>, restart: Option<&str>, clip_length: Rational) -> Rendered<Rational> {
        if restart.is_none_or(|restart| restart == Restart::EVERY_CLIP) {
            return Ok(clip_length);
        }
        let start = self.run_start(scene, restart);
        let mut end = start + 1;
        while end < self.scenes.len() && (restart == Some(Restart::WHOLE_SONG) || !self.scenes[end].first_play) {
            end += 1;
        }
        let mut length = Rational::ZERO;
        for written in &self.scenes[start..end] {
            length = length + self.get_scene_length(written)?;
        }
        Ok(length)
    }

    /// Whether a track's clip in a written-out scene plays a drum pattern.
    pub fn plays_drums(&self, scene: &WrittenScene, track: &str) -> bool {
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else { return false };
        self.setlist.get_pattern(&clip_slot.get_pattern_name()).is_some_and(|pattern| pattern.is_drum())
    }

    /// A written-out scene's tempos where its scene ramps its tempo, the first at its start, or None for one tempo: a scene's
    /// ramps count bars across its whole play, every repeat together, so each repeat takes the part of them inside it.
    fn tempos_of(&self, scene: &WrittenScene<'a>) -> Rendered<Option<Vec<(Rational, f64)>>> {
        let played = scene.scene;
        let base = tempo_in(played, self.song);
        let (ramp_in, ramp_out) = (tempo_ramp(played, "in", base), tempo_ramp(played, "out", base));
        if ramp_in.is_none() && ramp_out.is_none() {
            return Ok(None);
        }
        let mut start = Rational::ZERO;
        let mut here = (Rational::ZERO, Rational::ZERO);
        let mut length = Rational::ZERO;
        for written in self.scenes.iter().filter(|written| std::ptr::eq(written.scene, played)) {
            let own = self.get_scene_length(written)?;
            if written.number == scene.number {
                here = (start, start + own);
            }
            start = start + own;
            length = length + own;
        }
        let bar = self.song.get_time_signature().bar_length();
        let tempos = ramped_tempos(base, ramp_in, ramp_out, length, bar, self.setlist.get_step_size());
        let (start, end) = here;
        let before = tempos.iter().rfind(|(time, _)| *time <= start).map(|(_, tempo)| *tempo).unwrap_or(120.0);
        let mut within = vec![(Rational::ZERO, before)];
        within.extend(
            tempos
                .iter()
                .filter(|(time, _)| start < *time && *time < end)
                .map(|(time, tempo)| (*time - start, *tempo)),
        );
        Ok(Some(within))
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

/// The decimal places a ramped tempo is rounded to.
const TEMPO_PLACES: usize = 4;

/// The kinds of generator the port runs so far.
const PORTED_KINDS: &[&str] = &["chords", "arp", "guitarify", "shapes"];

/// The factors a chain step's seed is made with, so that it differs for every song, scene, track and place in the chain.
const SEED_SONG_FACTOR: i128 = 1_000_003;
const SEED_SCENE_FACTOR: i128 = 1_009;
const SEED_TRACK_FACTOR: i128 = 31;

/// A chain step of a kind the port runs, with no statements that bypass it, or what is not ported yet.
fn ported_step(kind: &str, name: &str, settings: Data) -> Rendered<ChainStep> {
    if !PORTED_KINDS.contains(&kind) {
        return Err(RenderError::NotPorted(format!("the {kind} generator")));
    }
    if settings
        .get(BYPASS_WHEN)
        .is_some_and(|statements| statements.as_list().is_some_and(|items| !items.is_empty()))
    {
        return Err(RenderError::not_ported("statements that bypass a generator"));
    }
    Ok(ChainStep {
        kind: kind.to_string(),
        name: name.to_string(),
        settings,
    })
}

/// Whether a built-in generator's settings switch it on: a built-in is off unless written on.
fn is_switched_on(settings: &Data) -> bool {
    settings.get(GENERATOR_ENABLED) == Some(&Data::Bool(true))
}

/// Whether a setting is written as something that does anything: false and an empty list are as good as not written.
fn holds_something(value: &Data) -> bool {
    !matches!(value, Data::Null | Data::Bool(false))
        && value.as_list().is_none_or(|items| !items.is_empty())
        && value.as_map().is_none_or(|pairs| !pairs.is_empty())
}

/// Whether a setting is one of how a clip is shaped and how loud it plays, which every object that holds one plays.
fn is_shaping(name: &str) -> bool {
    ["density_", "articulate_", "velocity"].iter().any(|start| name.starts_with(start))
}

/// The first setting of a table an object holds that the port does not play yet.
fn unported(table: &[Setting], played: &[&str], written: &dyn Fn(&str) -> Option<Data>) -> Rendered<()> {
    for setting in table {
        if !played.contains(&setting.name) && !is_shaping(setting.name) && written(setting.name).is_some_and(|value| holds_something(&value)) {
            return Err(RenderError::NotPorted(format!("the {} setting", setting.name)));
        }
    }
    Ok(())
}

/// Refuse a song that uses a part of the render not ported yet, naming the part.
fn check_ported(setlist: &Setlist, song: &Song) -> Rendered<()> {
    let song_played = [
        SongSetting::TEMPO,
        SongSetting::GROOVE,
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
        TrackSetting::GROOVE,
        TrackSetting::CHAINS,
        TrackSetting::BUILT_IN,
    ];
    for (_, track) in song.tracks() {
        unported(TRACK, &track_played, &|name| track.get_written(name).cloned())?;
    }
    let scene_played = [
        SceneSetting::TEMPO,
        SceneSetting::TEMPO_IN_START,
        SceneSetting::TEMPO_IN_END,
        SceneSetting::TEMPO_IN_OVER,
        SceneSetting::TEMPO_OUT_START,
        SceneSetting::TEMPO_OUT_END,
        SceneSetting::TEMPO_OUT_OVER,
        SceneSetting::GROOVE,
        SceneSetting::CHAINS,
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
        ClipSlotSetting::BUILT_IN,
        ClipSlotSetting::CHAINS,
        ClipSlotSetting::MORPH_TO,
        ClipSlotSetting::GRAB_TRACK,
        ClipSlotSetting::MORPH_STYLE,
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
