// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Realizer, which plays a song into clips (the Python engine/realizer/song_realizer.py and written_scene.py): every
//! scene in order, a scene that repeats written out once for each repeat, each track's clip in it played, and a scene's
//! length worked out without playing, as its longest clip that does not loop.

use crate::chord_source::ChordSource;
use crate::clip::Clip;
use crate::clip_player::draws_named;
use crate::clip_player::ClipSlotPlayer;
use crate::drift::DriftPlay;
use crate::error::{RenderError, Rendered};
use crate::generators::chords::Continuation;
use crate::generators::timing::{MovingRow, NudgePlan};
use crate::generators::GeneratorState;
use crate::grab_source::GrabSource;
use crate::groove::{groove_for, Groove};
use crate::pattern_player::Hearing;
use crate::registers::{Change, Draw, DrawPlay, Registers, Timeline, Values};
use crate::sound::Sound;
use crate::timing::{NoteEvent, StrumPlan};
use crate::tune_source::TuneSource;
use llamatron_math::Rational;
use llamatron_math::{PythonRandom, Seed};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::{Scene, Song, Track};
use llamatron_model::schema::generated::defaults;
use llamatron_model::schema::generated::file_format::DRAW_NAMES;
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, SceneSetting, Section, SongSetting, TrackSetting};
use llamatron_model::schema::generated::file_format::{Restart, GENERATOR_ENABLED, GENERATOR_RESTART};
use llamatron_model::schema::generated::limits::{MAX_TEMPO, MIN_TEMPO};
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_strings::{errors, named, names};
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

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
/// The tempo a scene plays at: the song's, scaled by its own percentage where it has one.
pub fn tempo_in(scene: &Scene, song: &Song) -> Rational {
    own_tempo(scene, song).or_else(|| exact(&song.get_tempo())).unwrap_or(Rational::whole(120))
}

/// The tempo a song with none written plays at, and the milliseconds a whole note lasts at one beat a minute, four beats
/// of sixty thousand; a tempo is read to a thousandth of a beat a minute.
const DEFAULT_TEMPO: i128 = 120;
const MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE: i128 = 240_000;
const TEMPO_DENOMINATOR: i128 = 1000;

/// A time in milliseconds as a share of a whole note at a tempo, a whole note lasting four beats.
fn milliseconds_as_whole_notes(milliseconds: i64, tempo: Rational) -> Rational {
    Rational::whole(milliseconds as i128) * tempo.limit_denominator(TEMPO_DENOMINATOR) / Rational::whole(MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE)
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

/// Whether either of a scene's tempo ramps changes its tempo.
pub fn ramps_tempo(scene: &Scene, song: &Song) -> bool {
    let base = tempo_in(scene, song);
    ["in", "out"].iter().any(|way| tempo_ramp(scene, way, base).is_some())
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
    pub columns: Vec<GridColumn>,
    pub rows: Vec<GridRow>,
    /// The song's tempo, and its time signature.
    pub tempo: f64,
    pub time_signature: llamatron_model::values::time_signature::TimeSignature,
}

/// A track as the exports write it: its name, whether it is muted or plays drums, its instrument's General MIDI sound, and
/// the pan CC's value its instrument's Pan gives, where set.
pub struct GridColumn {
    pub name: String,
    pub mute: bool,
    pub drum: bool,
    pub gm_sound: Option<i64>,
    pub pan: Option<i64>,
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
    // What each Hocket deals out in each written scene, by the scene's number and the Hocket's name: the notes each track takes.
    dealt: RefCell<HashMap<(i64, String), Dealt>>,
    // The song's drifts as it plays, which every clip naming one hears.
    drift: Rc<RefCell<DriftPlay>>,
    // The song's draws, AD first, whether any holds a value, and whether playing can take one at all.
    draws: Rc<Vec<Draw>>,
    uses_draws: bool,
    changes_registers: bool,
    // What draws the draws' random values, for the whole render, and each written scene's timeline of the draws' values.
    register_chooser: RefCell<PythonRandom>,
    timelines: RefCell<HashMap<i64, Rc<Timeline>>>,
    // Each clip played to count what its steps draw, with what they draw, by written scene and track.
    counted: RefCell<HashMap<(i64, String), Counted>>,
    // How long each clip the draws can cut short lasts, found by playing, and how a scene still being settled guesses.
    decided: RefCell<HashMap<(i64, String), Rational>>,
    guesses: RefCell<HashMap<i64, Guess>>,
    // How many chords each track's finished clip in each written scene holds, for a strum's down up that carries on.
    chord_counts: RefCell<HashMap<(i64, String), i64>>,
    /// Whether a scene in which every clip loops lasts as long as its longest clip played once and goes round, as real-time
    /// playback and Scene View render, rather than being refused as an export refuses it.
    looping_scenes_go_round: bool,
}

/// What keeps a generator's end state apart from another's in a clip: its kind, its name, and how many times before it
/// came up in the clip's chains.
pub type GeneratorKey = (String, String, i64);

/// The state a generator leaves a clip in, for the next to carry on from: a voicing's last chord, or none.
pub type EndState = Option<GeneratorState>;

/// What a Hocket deals out in a scene: the notes each track takes, by the track.
type Dealt = Vec<(String, Vec<NoteEvent>)>;

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
            chord_counts: RefCell::new(HashMap::new()),
            dealt: RefCell::new(HashMap::new()),
            drift: Rc::new(RefCell::new(DriftPlay::new(
                seed,
                song.get_time_signature().bar_length(),
                drift_settings(setlist),
            ))),
            draws: Rc::new(song_draws(song)),
            uses_draws: song_draws(song).iter().any(|draw| !draw.filled_places().is_empty()),
            changes_registers: takes_draws(setlist),
            register_chooser: RefCell::new(match seed {
                Some(seed) => PythonRandom::new(Seed::Whole(seed as i128 * SEED_SONG_FACTOR + REGISTER_SEED_OFFSET)),
                None => PythonRandom::unseeded(),
            }),
            timelines: RefCell::new(HashMap::new()),
            counted: RefCell::new(HashMap::new()),
            decided: RefCell::new(HashMap::new()),
            guesses: RefCell::new(HashMap::new()),
            looping_scenes_go_round: false,
        }
    }

    /// The same render, a scene in which every clip loops lasting as long as its longest clip played once.
    pub fn looping_scenes_go_round(mut self) -> SongRealizer<'a> {
        self.looping_scenes_go_round = true;
        self
    }

    /// Whether a track's clip in a scene of the song loops for as long as the scene lasts, as its first written-out play has it.
    pub fn loops_through(&self, index: usize, track: &str) -> bool {
        self.rows_of_scene(index)
            .first()
            .is_some_and(|place| self.fills_its_scene(&self.scenes[*place], track))
    }

    /// The places among the written-out scenes of a scene of the song, one for each repeat, in order.
    /// The moments in a written-out row at which a draw drew, in whole notes from the row's start, with where every draw
    /// then stood.
    pub fn draw_moments(&self, place: usize) -> Rendered<Vec<(Rational, crate::registers::DrawPlaces)>> {
        let Some(scene) = self.scenes.get(place) else { return Ok(Vec::new()) };
        Ok(self.get_timeline(scene)?.draw_moments().to_vec())
    }

    pub fn rows_of_scene(&self, index: usize) -> Vec<usize> {
        let Some(scene) = self.song.scenes().get(index) else { return Vec::new() };
        self.scenes
            .iter()
            .enumerate()
            .filter(|(_, written)| std::ptr::eq(written.scene, scene))
            .map(|(place, _)| place)
            .collect()
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
        let tracks: Vec<String> = self.song.get_track_names().into_iter().map(str::to_string).collect();
        let mut rows = Vec::new();
        for scene in &self.scenes {
            let mut clips = Vec::new();
            for track in &tracks {
                if let Some(mut clip) = self.get_clip(scene, track)? {
                    // The groove goes on last, so that generators, grabs and lengths never see it.
                    clip.groove = self.groove_at(scene, track)?;
                    clip.strum = self.strum_plan(scene, track)?;
                    self.chord_counts.borrow_mut().insert((scene.number, track.clone()), chords_in(&clip));
                    clip.nudge = self.nudge_plan(scene, track)?;
                    clip.handed = self.handed_notes(scene, track)?;
                    if !clip.keyswitches.is_empty() {
                        clip.keyswitch_lead = self.keyswitch_lead(scene, track)?;
                    }
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
        // A soloed track plays alone: every other track is heard as muted, in real time and in every export.
        let is_soloed = |name: &str| {
            self.track(name)
                .ok()
                .is_some_and(|track| track.get_written(TrackSetting::SOLO) == Some(&Data::Bool(true)))
        };
        let soloing = tracks.iter().any(|name| is_soloed(name));
        let mut columns = Vec::new();
        for name in &tracks {
            let track = self.track(name)?;
            let instrument = self.song.instrument_of(track, self.setlist);
            let gm_sound = instrument
                .and_then(|instrument| instrument.get_written("gm_sound"))
                .and_then(Data::as_whole)
                .map(|sound| sound as i64);
            let pan = instrument.and_then(|instrument| instrument.pan_control());
            columns.push(GridColumn {
                name: name.clone(),
                mute: track.get_written(TrackSetting::MUTE) == Some(&Data::Bool(true)) || (soloing && !is_soloed(name)),
                drum: track.is_drum(),
                gm_sound,
                pan,
            });
        }
        let tempo = exact(&self.song.get_tempo()).unwrap_or(Rational::whole(120)).to_float();
        Ok(Grid {
            tracks,
            columns,
            rows,
            tempo,
            time_signature: self.song.get_time_signature(),
        })
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

    /// The drifts a track's clip in a written-out scene hears, or None where its chains name none.
    pub fn hearing(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Option<Hearing>> {
        let mut names = Vec::new();
        let mut origins = Vec::new();
        for step in self.chains_of(scene, track)? {
            if step.kind == "drift" {
                let restart = step.settings.get(GENERATOR_RESTART).map(Data::python_str);
                let start = self.run_start(scene, restart.as_deref());
                origins.push((step.name.clone(), self.scene_start(&self.scenes[start])?));
                names.push(step.name);
            }
        }
        if names.is_empty() {
            return Ok(None);
        }
        Ok(Some(Hearing {
            drift: Rc::clone(&self.drift),
            names,
            origins,
            scene_start: self.scene_start(scene)?,
        }))
    }

    /// Where a written-out scene starts from the song's top: the scenes before it laid end to end.
    fn scene_start(&self, scene: &WrittenScene<'a>) -> Rendered<Rational> {
        let mut start = Rational::ZERO;
        for written in &self.scenes[..(scene.number - 1) as usize] {
            start = start + self.get_scene_length(written)?;
        }
        Ok(start)
    }

    /// The notes the Hockets a track's clip names hand it in a written-out scene, in time order.
    fn handed_notes(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Vec<NoteEvent>> {
        let mut named: Vec<ChainStep> = Vec::new();
        for step in self.chains_of(scene, track)? {
            if step.kind == "hocket" && !named.iter().any(|found| found.name == step.name) {
                named.push(step);
            }
        }
        let mut handed = Vec::new();
        for step in named {
            let dealt = self.notes_dealt(scene, &step)?;
            if let Some((_, notes)) = dealt.iter().find(|(name, _)| name == track) {
                handed.extend(notes.iter().copied());
            }
        }
        handed.sort_by_key(|note| (note.start, note.end, note.midi_number, note.velocity));
        Ok(handed)
    }

    /// What a Hocket deals out in a written-out scene: each turn, the source's notes that start together, going round the
    /// tracks naming it from the first, carrying on from the scenes before in its run as its Restart says.
    fn notes_dealt(&self, scene: &WrittenScene<'a>, step: &ChainStep) -> Rendered<Dealt> {
        let key = (scene.number, step.name.clone());
        if let Some(found) = self.dealt.borrow().get(&key) {
            return Ok(found.clone());
        }
        let source = step
            .settings
            .get("source")
            .filter(|source| !source.is_null())
            .map(Data::python_str)
            .unwrap_or_default();
        let restart = step.settings.get(GENERATOR_RESTART).map(Data::python_str);
        let mut dealt: Dealt = Vec::new();
        let pool = self.pool(scene, &step.name, &source)?;
        if !pool.is_empty() && self.plays_source(scene, &source) {
            let mut turn = 0;
            let start = self.run_start(scene, restart.as_deref());
            for written in &self.scenes[start..(scene.number - 1) as usize] {
                if !self.pool(written, &step.name, &source)?.is_empty() && self.plays_source(written, &source) {
                    turn += self.source_turns(written, &source)?.len();
                }
            }
            for notes in self.source_turns(scene, &source)? {
                let taker = &pool[turn % pool.len()];
                match dealt.iter_mut().find(|(name, _)| name == taker) {
                    Some((_, held)) => held.extend(notes),
                    None => dealt.push((taker.clone(), notes)),
                }
                turn += 1;
            }
        }
        self.dealt.borrow_mut().insert(key, dealt.clone());
        Ok(dealt)
    }

    /// The tracks of the song whose clips name a generator in a written-out scene, but the source.
    fn pool(&self, scene: &WrittenScene<'a>, name: &str, source: &str) -> Rendered<Vec<String>> {
        let mut pool = Vec::new();
        for track in self.song.get_track_names() {
            if track != source && self.chains_of(scene, track)?.iter().any(|step| step.name == name) {
                pool.push(track.to_string());
            }
        }
        Ok(pool)
    }

    fn plays_source(&self, scene: &WrittenScene, source: &str) -> bool {
        self.song.get_track(source).is_some() && scene.scene.get_clip_slot(source).is_some()
    }

    /// A source track's notes in a written-out scene, where the grid puts them, in turns of the notes that start together.
    fn source_turns(&self, scene: &WrittenScene<'a>, source: &str) -> Rendered<Vec<Vec<NoteEvent>>> {
        let Some(clip) = self.get_clip(scene, source)? else { return Ok(Vec::new()) };
        let (mut notes, _) = crate::timing::timed_events(&clip, clip.scale.as_ref())?;
        notes.sort_by_key(|note| (note.start, note.end, note.midi_number, note.velocity));
        let mut turns: Vec<(Rational, Vec<NoteEvent>)> = Vec::new();
        for note in notes {
            match turns.last_mut() {
                Some((start, held)) if *start == note.start => held.push(note),
                _ => turns.push((note.start, vec![note])),
            }
        }
        Ok(turns.into_iter().map(|(_, notes)| notes).collect())
    }

    /// How a clip strums its chords at its scene's tempo, from the last Guitarify in Strum mode its chains name, or None.
    fn strum_plan(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Option<StrumPlan>> {
        let mut found = None;
        for step in self.chains_of(scene, track)? {
            if step.kind == "guitarify" {
                if let Some(values) = crate::generators::guitarify::strum_values(&step.settings) {
                    found = Some((values, step.settings.get(GENERATOR_RESTART).map(Data::python_str)));
                }
            }
        }
        let Some(((direction, spread, fade, loose_timing, upstroke_count), restart)) = found else {
            return Ok(None);
        };
        let tempo = scene.tempo.or_else(|| exact(&self.song.get_tempo())).unwrap_or(Rational::whole(DEFAULT_TEMPO));
        let gap = milliseconds_as_whole_notes(spread, tempo);
        let start = self.run_start(scene, restart.as_deref());
        let chords_before = self.scenes[start..(scene.number - 1) as usize]
            .iter()
            .map(|written| self.chord_counts.borrow().get(&(written.number, track.to_string())).copied().unwrap_or(0))
            .sum();
        Ok(Some(StrumPlan {
            direction,
            gap,
            fade,
            loose_timing,
            upstroke_count,
            beat: self.song.get_time_signature().beat_length(),
            seed: self.strum_seed(scene, track),
            offset: self.run_offset(scene, restart.as_deref())?,
            chords_before,
        }))
    }

    /// The seed a clip's strum draws its loose timing from: one the render draws once from its own seed, made different for
    /// every scene and track.
    fn strum_seed(&self, scene: &WrittenScene, track: &str) -> Option<i128> {
        let seed = self.seed? as i128;
        let drawn = llamatron_math::PythonRandom::new(llamatron_math::Seed::Whole(seed * SEED_SONG_FACTOR + STRUM_SEED_OFFSET)).randrange_to(STRUM_SEEDS);
        let place = self.song.get_track_names().iter().position(|name| *name == track).unwrap_or(0) as i128;
        Some(drawn + scene.number as i128 * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR)
    }

    /// How a clip's notes are rushed and dragged, from every lit Rush and Drag of the Timing generators its chains name, or
    /// None where there is none.
    /// How much earlier than its note a track's instrument wants each keyswitch, in whole notes at the scene's tempo, or
    /// None for at the same moment.
    fn keyswitch_lead(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Option<Rational>> {
        let track = self.track(track)?;
        let milliseconds = self.song.instrument_of(track, self.setlist).map_or(0, |instrument| instrument.keyswitch_lead());
        if milliseconds == 0 {
            return Ok(None);
        }
        let tempo = scene.tempo.or_else(|| exact(&self.song.get_tempo())).unwrap_or(Rational::whole(DEFAULT_TEMPO));
        Ok(Some(milliseconds_as_whole_notes(milliseconds, tempo)))
    }

    fn nudge_plan(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Option<NudgePlan>> {
        let mut rows = Vec::new();
        let bar = self.song.get_time_signature().bar_length();
        for step in self.chains_of(scene, track)? {
            if step.kind != "timing" {
                continue;
            }
            let pattern = self
                .setlist
                .get_pattern(&scene.scene.get_clip_slot(track).map(|clip| clip.get_pattern_name()).unwrap_or_default());
            let pattern_step = pattern
                .map(|pattern| self.setlist.get_pattern_step_size(pattern))
                .unwrap_or(self.setlist.get_step_size());
            let restart = step.settings.get(GENERATOR_RESTART).map(Data::python_str);
            let offset = self.run_offset(scene, restart.as_deref())?;
            rows.extend(MovingRow::of(&step.settings, pattern_step, bar, offset)?);
        }
        Ok((!rows.is_empty()).then_some(NudgePlan { rows }))
    }

    /// The finished clip a track plays in a written-out scene, or None where it plays nothing there.
    pub fn get_clip(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Option<Clip>> {
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else { return Ok(None) };
        let key = (scene.number, track.to_string());
        if let Some(clip) = self.clips.borrow().get(&key) {
            return Ok(Some(clip.clone()));
        }
        let registers = Registers::Reader {
            place: self.track_place(track),
            timeline: self.get_timeline(scene)?,
        };
        let clip = ClipSlotPlayer::new(self, scene, track, clip_slot, &registers).play()?;
        self.clips.borrow_mut().insert(key, clip.clone());
        Ok(Some(clip))
    }

    /// A track's place in the song, which orders the changes to the draws made at one time.
    fn track_place(&self, track: &str) -> Rational {
        Rational::whole(self.song.get_track_names().iter().position(|name| *name == track).unwrap_or(0) as i128)
    }

    /// Which of the song's draws a statement reading them draws from.
    pub fn redrawing(&self) -> [bool; 8] {
        std::array::from_fn(|name| self.draws[name].redraws_in_conditions)
    }

    /// Whether a step of the pattern a track's clip plays in a scene can stop the clip or start the pattern over.
    fn cuts_passes(&self, scene: &WrittenScene, track: &str) -> bool {
        self.patterns_hold(scene, track, &[STOP_REGISTER_ROW, RESTART_REGISTER_ROW])
    }

    /// Whether a track's clip in a scene loops for as long as the scene lasts: a looping clip no step of its pattern can stop.
    pub fn fills_its_scene(&self, scene: &WrittenScene, track: &str) -> bool {
        scene.scene.get_clip_slot(track).is_some_and(|clip| clip.loops()) && !self.patterns_hold(scene, track, &[STOP_REGISTER_ROW])
    }

    fn patterns_hold(&self, scene: &WrittenScene, track: &str, rows: &[&str]) -> bool {
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else { return false };
        clip_slot
            .get_pattern_names()
            .iter()
            .filter_map(|name| self.setlist.get_pattern(name))
            .any(|pattern| {
                rows.iter().any(|row| {
                    pattern
                        .row(row)
                        .is_some_and(|values| values.iter().any(|value| !value.is_null() && *value != Data::Bool(false)))
                })
            })
    }

    /// Whether any clip of a scene can be cut short by the draws, so that its length and its draws are found together.
    fn is_settled_by_playing(&self, scene: &WrittenScene) -> bool {
        scene.scene.get_track_names().iter().any(|track| self.cuts_passes(scene, track))
    }

    /// The draws' values through a written-out scene: a scene starts where the one before left them, the draws it resets on
    /// its first play sent back to their start; a scene before it that can't be played changes nothing.
    pub fn get_timeline(&self, scene: &WrittenScene<'a>) -> Rendered<Rc<Timeline>> {
        if let Some(found) = self.timelines.borrow().get(&scene.number) {
            return Ok(Rc::clone(found));
        }
        let mut values: Values = [0; 8];
        let mut draws = self.uses_draws.then(|| DrawPlay::new(Rc::clone(&self.draws)));
        for written in &self.scenes[..scene.number as usize] {
            let known = self.timelines.borrow().get(&written.number).cloned();
            let timeline = match known {
                Some(timeline) => timeline,
                None => {
                    let mut start = values;
                    if let Some(draws) = &mut draws {
                        if written.first_play {
                            for name in written.scene.get_written(SceneSetting::RESET_DRAWS).map(draws_named).unwrap_or_default() {
                                draws.reset(name);
                            }
                        }
                        start = draws.values();
                    }
                    match self.timeline_of(written, start, draws.as_ref()) {
                        Ok(timeline) => {
                            let timeline = Rc::new(timeline);
                            self.timelines.borrow_mut().insert(written.number, Rc::clone(&timeline));
                            timeline
                        }
                        Err(problem) if written.number == scene.number => return Err(problem),
                        Err(_) => continue,
                    }
                }
            };
            values = timeline.end_values();
            draws = timeline.end_draws().cloned();
        }
        self.timelines
            .borrow()
            .get(&scene.number)
            .cloned()
            .ok_or_else(|| RenderError::Refused(format!("{} cannot be played", scene.describe())))
    }

    /// A scene's draws' values from where they start: found by playing where a statement can cut a clip of it short, and
    /// from the draws its clips take otherwise.
    fn timeline_of(&self, scene: &WrittenScene<'a>, start: Values, draws: Option<&DrawPlay>) -> Rendered<Timeline> {
        if self.is_settled_by_playing(scene) {
            return self.decide(scene, start, draws);
        }
        let changes = self.scene_changes(scene)?;
        Ok(Timeline::new(start, &changes, &mut self.register_chooser.borrow_mut(), draws))
    }

    /// Every change a scene's clips make before the scene ends, and at its very end those that draw: a step that stops its
    /// clip, ending the scene, takes its draws before its statements stop it.
    fn scene_changes(&self, scene: &WrittenScene<'a>) -> Rendered<Vec<Change>> {
        if !self.changes_registers {
            return Ok(Vec::new());
        }
        let length = self.get_scene_length(scene)?;
        let mut changes = Vec::new();
        for track in scene.scene.get_track_names() {
            let (_, counted) = self.counted_clip(scene, track)?;
            changes.extend(
                counted
                    .into_iter()
                    .filter(|change| change.time < length || (change.time == length && (!change.draws.is_empty() || !change.resets.is_empty()))),
            );
        }
        Ok(changes)
    }

    /// A track's clip in a scene played without grabs or the draws' values, and what its steps draw.
    fn counted_clip(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Counted> {
        let key = (scene.number, track.to_string());
        if let Some(found) = self.counted.borrow().get(&key) {
            return Ok(found.clone());
        }
        if self.cuts_passes(scene, track) {
            if self.guesses.borrow().contains_key(&scene.number) {
                return self.tried(scene, track);
            }
            self.get_timeline(scene)?;
            return self
                .counted
                .borrow()
                .get(&key)
                .cloned()
                .ok_or_else(|| RenderError::Refused(format!("{} cannot be played", scene.describe())));
        }
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else {
            return Ok((Clip::of(Vec::new(), None), Vec::new()));
        };
        let registers = Registers::Recorder {
            place: self.track_place(track),
            changes: RefCell::new(Vec::new()),
        };
        let clip = ClipSlotPlayer::new(self, scene, track, clip_slot, &registers).play()?;
        let counted = (clip, registers.get_changes());
        self.counted.borrow_mut().insert(key, counted.clone());
        Ok(counted)
    }

    /// A clip the draws can cut short, played against the scene's draws as they are guessed so far, and what it draws.
    fn tried(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Counted> {
        let place = self.track_place(track);
        let registers = match self.guesses.borrow().get(&scene.number) {
            Some(Guess::Solo { start, draws, chooser }) => Registers::Solo {
                place,
                changes: RefCell::new(Vec::new()),
                values: RefCell::new(*start),
                draws: RefCell::new(draws.clone()),
                chooser: Rc::clone(chooser),
            },
            Some(Guess::Trial(timeline)) => Registers::Trial {
                place,
                changes: RefCell::new(Vec::new()),
                timeline: Rc::clone(timeline),
            },
            None => return Err(RenderError::Refused(format!("{} has no guess", scene.describe()))),
        };
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else {
            return Ok((Clip::of(Vec::new(), None), Vec::new()));
        };
        let clip = ClipSlotPlayer::new(self, scene, track, clip_slot, &registers).play()?;
        Ok((clip, registers.get_changes()))
    }

    /// The draws' values through a scene in which a step's statement can stop a clip or start a pattern over, finding how long
    /// its clips and the scene last: each such clip is played first as if no other track drew, the scene's timeline made from
    /// what every clip then draws, the clips played again reading it, and so on until a play changes nothing.
    fn decide(&self, scene: &WrittenScene<'a>, start: Values, draws: Option<&DrawPlay>) -> Rendered<Timeline> {
        let number = scene.number;
        let every: Vec<&str> = scene.scene.get_track_names();
        let cut: Vec<&str> = every.iter().copied().filter(|track| self.cuts_passes(scene, track)).collect();
        let ending: Vec<&str> = cut.iter().copied().filter(|track| !self.fills_its_scene(scene, track)).collect();
        let filling: Vec<&str> = cut.iter().copied().filter(|track| !ending.contains(track)).collect();
        let mut fixed = Vec::new();
        for track in &every {
            let clip_slot = scene.scene.get_clip_slot(track);
            if !cut.contains(track) && !clip_slot.is_some_and(|clip| clip.loops()) {
                fixed.push(self.played_once(scene, track)?);
            }
        }
        if ending.is_empty() && fixed.is_empty() {
            // Nothing in the scene ends: it is refused, or goes round once, as any scene whose every clip loops.
            if !self.looping_scenes_go_round {
                return Err(RenderError::Refused(named(
                    errors::ERR_RENDERER_EVERY_CLIP_LOOPS,
                    &[("scene", scene.describe().as_str().into())],
                )));
            }
            for track in &every {
                fixed.push(self.played_once(scene, track)?);
            }
        }
        let guess = Rc::new(RefCell::new(PythonRandom::new(Seed::Whole(0))));
        self.guesses.borrow_mut().insert(
            number,
            Guess::Solo {
                start,
                draws: draws.cloned().map(Box::new),
                chooser: guess,
            },
        );
        self.lengths.borrow_mut().insert(number, fixed.iter().copied().max().unwrap_or(Rational::ZERO));
        let drawn = self.register_chooser.borrow().clone();
        let mut settled: Option<(Vec<Change>, Vec<Rational>)> = None;
        let result = (|| loop {
            let mut plays = Vec::new();
            for track in &ending {
                plays.push((track.to_string(), self.tried(scene, track)?));
            }
            self.counted.borrow_mut().retain(|(found, _), _| *found != number);
            let mut lengths = Vec::new();
            for (track, play) in plays {
                let length = play.0.total_length()?;
                self.decided.borrow_mut().insert((number, track.clone()), length);
                self.counted.borrow_mut().insert((number, track), play);
                lengths.push(length);
            }
            self.lengths
                .borrow_mut()
                .insert(number, fixed.iter().chain(&lengths).copied().max().unwrap_or(Rational::ZERO));
            for track in &filling {
                let play = self.tried(scene, track)?;
                self.counted.borrow_mut().insert((number, track.to_string()), play);
            }
            let changes = self.scene_changes(scene)?;
            // Every round draws the draws' random values from the same place, so that the same changes make the same timeline.
            *self.register_chooser.borrow_mut() = drawn.clone();
            let timeline = Timeline::new(start, &changes, &mut self.register_chooser.borrow_mut(), draws);
            let found = (changes, lengths);
            if settled.as_ref() == Some(&found) {
                return Ok(timeline);
            }
            settled = Some(found);
            self.guesses.borrow_mut().insert(number, Guess::Trial(Rc::new(timeline)));
        })();
        self.guesses.borrow_mut().remove(&number);
        result
    }

    /// How long a clip lasts played once: its patterns repeat times, whether or not it loops.
    fn played_once(&self, scene: &WrittenScene, track: &str) -> Rendered<Rational> {
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else {
            return Ok(Rational::ZERO);
        };
        let mut one_pass = Rational::ZERO;
        for name in clip_slot.get_pattern_names() {
            let pattern = self
                .setlist
                .get_pattern(&name)
                .ok_or_else(|| RenderError::Refused(format!("no pattern called ({name})")))?;
            one_pass = one_pass + self.setlist.get_pattern_length(pattern);
        }
        Ok(Rational::whole(clip_slot.get_repeat() as i128) * one_pass)
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

    /// The finished clip of a track another one follows in a written-out scene, after its own chains, or None where it
    /// plays nothing there, is no track of the song or is the track that follows; tracks following in a circle refused.
    fn followed_clip(&self, scene: &WrittenScene<'a>, track: &str, source: Option<&str>) -> Rendered<Option<Clip>> {
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
        clip
    }

    /// The chords a track followed plays in a written-out scene, after its own chains, or None.
    pub fn chords_followed(&self, scene: &WrittenScene<'a>, track: &str, source: Option<&str>) -> Rendered<Option<ChordSource>> {
        self.followed_clip(scene, track, source)?.map(|clip| ChordSource::of(&clip)).transpose()
    }

    /// When the tune sounds on the track a musician reads it from, in a written-out scene, or None.
    pub fn tune_heard(&self, scene: &WrittenScene<'a>, track: &str, source: Option<&str>) -> Rendered<Option<TuneSource>> {
        self.followed_clip(scene, track, source)?.map(|clip| TuneSource::of(&clip)).transpose()
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

    fn earlier_state(&self, start: usize, here: usize, track: &str, key: &GeneratorKey, state: &mut EndState) -> Rendered<()> {
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

    pub fn keep_end_state(&self, scene: &WrittenScene, track: &str, key: GeneratorKey, state: EndState) {
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

    /// How long a track's clip lasts in a written-out scene, in whole notes, without playing: as long as its scene where it
    /// loops, as long as it played where the draws can cut it short, and otherwise its patterns repeat times.
    pub fn get_clip_length(&self, scene: &WrittenScene<'a>, track: &str) -> Rendered<Rational> {
        let Some(clip_slot) = scene.scene.get_clip_slot(track) else {
            return Ok(Rational::ZERO);
        };
        if self.cuts_passes(scene, track) && !self.fills_its_scene(scene, track) {
            self.get_scene_length(scene)?;
            if let Some(length) = self.decided.borrow().get(&(scene.number, track.to_string())) {
                return Ok(*length);
            }
        }
        if clip_slot.loops() {
            return self.get_scene_length(scene);
        }
        self.played_once(scene, track)
    }

    /// Each written-out scene's estimate, as the Python's estimate gives it: how long it lasts and each of its clips, in
    /// seconds, or its problem, worked out without playing.
    /// Refuse a scene whose playing would fail without playing it: a pattern with scale degrees where neither its clip, nor
    /// the scene, nor the song has a scale, or grabs that go round in a circle.
    fn check_plays(&self, scene: &WrittenScene<'a>) -> Rendered<()> {
        for track in scene.scene.get_track_names() {
            let Some(clip) = scene.scene.get_clip_slot(track) else { continue };
            let mut names = clip.get_pattern_names();
            if let Some(target) = clip.get_written("morph_to").and_then(llamatron_model::file::data::Data::as_str) {
                names.push(target.to_string());
            }
            let has_scale = clip.get_scale_name().is_some() || scene.scale_name.is_some();
            for name in names {
                let Some(pattern) = self.setlist.get_pattern(&name) else { continue };
                if !has_scale && !pattern.is_drum() && pattern.has_note_steps() {
                    let place = named(errors::ERR_WHERE_PATTERN, &[("name", name.as_str().into())]);
                    return Err(RenderError::Refused(named(
                        errors::ERR_NO_SCALE,
                        &[("where", place.as_str().into()), ("scene", scene.number.into())],
                    )));
                }
            }
        }
        if let Some(circle) = grab_circle(scene.scene) {
            let looped = circle.join(llamatron_strings::marks::MSG_CIRCLE_ARROW);
            return Err(RenderError::Refused(named(
                errors::ERR_CIRCULAR_GRAB,
                &[("scene", scene.describe().as_str().into()), ("loop", looped.as_str().into())],
            )));
        }
        Ok(())
    }

    pub fn estimate(&self) -> Vec<SceneEstimate> {
        let mut estimates = Vec::new();
        for scene in &self.scenes {
            let tempos = self.tempos_of(scene);
            let whole = Rational::whole(240) / tempo_in(scene.scene, self.song);
            let seconds_of = |length: Rational, tempos: &Option<Vec<(Rational, f64)>>| match tempos {
                Some(tempos) => row_seconds_at(tempos, length),
                None => (length * whole).to_float(),
            };
            let worked_out = self.get_scene_length(scene).and_then(|length| {
                self.check_plays(scene)?;
                let tempos = tempos.clone()?;
                let mut clips = Vec::new();
                for track in scene.scene.get_track_names() {
                    clips.push((track.to_string(), seconds_of(self.get_clip_length(scene, track)?, &tempos)));
                }
                Ok((seconds_of(length, &tempos), clips))
            });
            estimates.push(match worked_out {
                Ok((seconds, clips)) => SceneEstimate {
                    seconds: Some(seconds),
                    clips,
                    problem: None,
                },
                Err(RenderError::Refused(problem)) => SceneEstimate {
                    seconds: None,
                    clips: Vec::new(),
                    problem: Some(problem),
                },
            });
        }
        estimates
    }

    /// How long the song lasts in seconds, every written-out scene's length at its tempo, timed beat by beat where it ramps,
    /// or None where any scene's length can't be worked out, as the Python's estimate sums its plays.
    pub fn song_seconds(&self) -> Option<f64> {
        let mut exact = Rational::ZERO;
        let mut float: Option<f64> = None;
        for scene in &self.scenes {
            let length = self.get_scene_length(scene).ok()?;
            match self.tempos_of(scene).ok()? {
                Some(tempos) => {
                    let seconds = row_seconds_at(&tempos, length);
                    float = Some(float.unwrap_or_else(|| exact.to_float()) + seconds);
                }
                None => {
                    let whole = Rational::whole(240) / tempo_in(scene.scene, self.song);
                    match float.as_mut() {
                        Some(sum) => *sum += (length * whole).to_float(),
                        None => exact = exact + length * whole,
                    }
                }
            }
        }
        Some(float.unwrap_or_else(|| exact.to_float()))
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
    pub fn get_scene_length(&self, scene: &WrittenScene<'a>) -> Rendered<Rational> {
        if let Some(length) = self.lengths.borrow().get(&scene.number) {
            return Ok(*length);
        }
        if self.is_settled_by_playing(scene) {
            // A statement can cut one of its clips short, so its length is found by playing it, with its draws.
            self.get_timeline(scene)?;
            return self
                .lengths
                .borrow()
                .get(&scene.number)
                .copied()
                .ok_or_else(|| RenderError::Refused(format!("{} cannot be played", scene.describe())));
        }
        if scene.scene.every_clip_loops() {
            if !self.looping_scenes_go_round {
                return Err(RenderError::Refused(named(
                    errors::ERR_RENDERER_EVERY_CLIP_LOOPS,
                    &[("scene", scene.describe().as_str().into())],
                )));
            }
            let mut length = Rational::ZERO;
            for track in scene.scene.get_track_names() {
                length = length.max(self.played_once(scene, track)?);
            }
            self.lengths.borrow_mut().insert(scene.number, length);
            return Ok(length);
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

/// Every drift of a set, by its name, with its settings.
fn drift_settings(setlist: &Setlist) -> HashMap<String, Data> {
    setlist
        .items("drifts")
        .iter()
        .filter_map(|(name, item)| match item {
            Item::Generator(settings) => Some((name.clone(), settings.to_data())),
            _ => None,
        })
        .collect()
}

/// What the draws' seed adds, so that their random values draw apart from everything else.
const REGISTER_SEED_OFFSET: i128 = 7;
/// The rows naming a Stop's and a Restart's register, which say a step holds one.
const STOP_REGISTER_ROW: &str = "stop_c1";
const RESTART_REGISTER_ROW: &str = "restart_c1";

/// A clip played to count what its steps draw, with what they draw.
type Counted = (Clip, Vec<Change>);

/// How a scene still being settled guesses the draws its clips read: as if no other track drew, or from the timeline the last
/// round made.
enum Guess {
    Solo {
        start: Values,
        draws: Option<Box<DrawPlay>>,
        chooser: Rc<RefCell<PythonRandom>>,
    },
    Trial(Rc<Timeline>),
}

/// The song's eight draws, AD first, as the song holds them or blank.
fn song_draws(song: &Song) -> Vec<Draw> {
    DRAW_NAMES
        .iter()
        .map(|name| Draw::of(song.draws().iter().find(|(found, _)| found == name).map(|(_, draw)| draw.to_data()).as_ref()))
        .collect()
}

/// Whether playing any song of a set can take a draw: a pattern that uses a draw or holds a statement, which reads one, or a
/// song whose draw holding a value redraws in conditions.
fn takes_draws(setlist: &Setlist) -> bool {
    let draw_row = |row: &str| row.ends_with("_note") || row.ends_with("_velocity") || row.ends_with("_reset") || row.contains("_c");
    let patterns = setlist.items(Section::PATTERNS).iter().any(|(_, item)| match item {
        Item::Pattern(pattern) => llamatron_model::schema::generated::file_format::PATTERN_ROWS
            .iter()
            .filter(|row| draw_row(row) && **row != "ratchet_offset")
            .any(|row| {
                pattern.row(row).is_some_and(|values| {
                    values
                        .iter()
                        .any(|value| !value.is_null() && *value != Data::Bool(false) && *value != Data::Whole(0))
                })
            }),
        _ => false,
    });
    patterns
        || setlist.items(Section::SONGS).iter().any(|(_, item)| match item {
            Item::Song(song) => song_draws(song)
                .iter()
                .any(|draw| draw.redraws_in_conditions && !draw.filled_places().is_empty()),
            _ => false,
        })
}

/// What a strum's seed adds, so that its loose timing draws apart from everything else, and how many seeds a render picks from.
const STRUM_SEED_OFFSET: i128 = 977;
const STRUM_SEEDS: i128 = 1_000_000;

/// How many chords a clip holds, a held chord counted.
fn chords_in(clip: &Clip) -> i64 {
    clip.sounds
        .iter()
        .filter(|sound| match sound {
            Sound::Held { sound, .. } => matches!(sound.as_ref(), Sound::Chord { .. }),
            other => matches!(other, Sound::Chord { .. }),
        })
        .count() as i64
}

/// The decimal places a ramped tempo is rounded to.
const TEMPO_PLACES: usize = 4;

/// The factors a chain step's seed is made with, so that it differs for every song, scene, track and place in the chain.
const SEED_SONG_FACTOR: i128 = 1_000_003;
const SEED_SCENE_FACTOR: i128 = 1_009;
const SEED_TRACK_FACTOR: i128 = 31;

/// A chain step: a generator's kind, its name and its settings.
fn ported_step(kind: &str, name: &str, settings: Data) -> Rendered<ChainStep> {
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

/// What a written-out scene lasts by the estimate: its seconds and each clip's, by track, or the problem that stops it.
#[derive(Clone, Debug, PartialEq)]
pub struct SceneEstimate {
    pub seconds: Option<f64>,
    pub clips: Vec<(String, f64)>,
    pub problem: Option<String>,
}

/// How many seconds into a row of tempos a time in whole notes falls, as the Python's RowClock works it out.
fn row_seconds_at(tempos: &[(Rational, f64)], time: Rational) -> f64 {
    let whole = |tempo: f64| 240.0 / tempo;
    let mut starts = Vec::new();
    let mut seconds = Vec::new();
    let mut at = 0.0;
    for (place, (start, _)) in tempos.iter().enumerate() {
        let start = start.to_float();
        if place > 0 {
            at += (start - starts[place - 1]) * whole(tempos[place - 1].1);
        }
        starts.push(start);
        seconds.push(at);
    }
    let time = time.to_float();
    if starts.len() == 1 {
        return time * whole(tempos[0].1);
    }
    let place = starts.iter().rposition(|start| *start <= time).unwrap_or(0);
    seconds[place] + (time - starts[place]) * whole(tempos[place].1)
}

/// The tracks of a scene whose grabs go round in a circle, back to where they start, or None: a clip grabbing from a track
/// follows that track's grab, and a grab from a track with nothing in the scene grabs nothing.
fn grab_circle(scene: &Scene) -> Option<Vec<String>> {
    for start in scene.get_track_names() {
        let mut path = vec![start.to_string()];
        loop {
            let last = path.last().cloned().unwrap_or_default();
            let following = scene
                .get_clip_slot(&last)
                .and_then(|clip| clip.get_written("grab_track"))
                .and_then(llamatron_model::file::data::Data::as_str)
                .map(str::to_string);
            let Some(following) = following else { break };
            if scene.get_clip_slot(&following).is_none() || path[1..].contains(&following) {
                break;
            }
            if following == start {
                path.push(start.to_string());
                return Some(path);
            }
            path.push(following);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A song with a pattern written for a scale of seven notes, as every pattern the tracker makes is.
    const SCALE_LENGTH_SET: &str = "scales:\n  - { name: C Major, root: C, type: major }\npatterns:\n  tune: { steps: 4, scale_length: 7, rows: { degree: [1, 2, 3, 4] } }\nsongs:\n  - name: song\n    scale: C Major\n    tracks: [{ name: lead }]\n    scenes:\n      - { name: one, clips: [{ track: lead, pattern: tune }] }\n";

    /// A pattern's scale length changes no note, so a song using such a pattern renders.
    #[test]
    fn a_pattern_written_for_a_scale_length_renders() {
        let setlist = Setlist::read_text(SCALE_LENGTH_SET, None).expect("the scenario's set is valid");
        let song = setlist.get_song("song").expect("the scenario has its song");
        let rendered = SongRealizer::new(&setlist, song, Some(1)).render();
        assert!(rendered.is_ok(), "{:?}", rendered.err());
    }
}
