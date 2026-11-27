// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The score (the Python realtime/render_process/score.py): a song rendered for real-time playback, each clip's events
//! counted from its scene's start, with what the song says about launching: how long each scene lasts, which clips loop,
//! each clip's follow action and whether each scene launches together. A scene that repeats is written out once a repeat
//! by the render, and the score keeps those rows together as one scene, so that launching a scene plays all of its
//! repeats. It is read once from the song as it is when something is launched, so the player asks the set nothing while it
//! runs.

use std::collections::HashMap;

use crate::realtime::row_clock::RowClock;
use crate::realtime::timeline::{clip_timeline, clock_of, row_length, ClipTag, Playing, Route, NOTE_OFF, NOTE_ON};
use llamatron_engine::error::Rendered;
use llamatron_engine::realizer::SongRealizer;
use llamatron_engine::registers::DrawPlaces;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::Song;
use llamatron_model::schema::generated::defaults::{DEFAULT_FOLLOW_ACTION, DEFAULT_LAUNCH_TOGETHER};
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, FollowAction, SceneSetting, SetlistSetting};

/// How close to a pass's start a moment may be and still count as that start, against rounding in the seconds.
const PASS_TOLERANCE: f64 = 1e-9;
const FIRST_ROW: usize = 0;

/// One written-out repeat of a scene: when it starts within the scene in seconds, how long it lasts, and its clock.
#[derive(Clone, Debug)]
pub struct ScoreRow {
    pub start: f64,
    pub seconds: f64,
    pub clock: RowClock,
}

/// What the player knows about a song: each scene's length and launch settings, and each clip's events from its
/// scene's start.
pub struct Score {
    tracks: Vec<String>,
    scene_seconds: Vec<f64>,
    scene_starts: Vec<f64>,
    rows: Vec<Vec<ScoreRow>>,
    events: HashMap<(usize, String), Vec<Playing>>,
    loops: HashMap<(usize, String), bool>,
    follow_actions: HashMap<(usize, String), String>,
    launches_together: Vec<bool>,
    repeats: HashMap<(usize, String), Option<i64>>,
    clip_seconds: HashMap<(usize, usize, String), f64>,
    bar: f64,
    routes: Vec<(String, Route)>,
    /// Each scene's moments a draw drew, in seconds from the scene's start, with where every draw then stood.
    draw_lights: Vec<Vec<(f64, DrawPlaces)>>,
}

impl Score {
    /// A song rendered and read into the score; a track with no route has no events, since it has nothing to play through.
    /// Where every draw stood a number of seconds into a scene: the slot each last took its value from, none before the
    /// scene's first draw.
    pub fn draw_places_at(&self, scene: usize, seconds: f64) -> Option<DrawPlaces> {
        let moments = self.draw_lights.get(scene)?;
        let found = moments.partition_point(|(time, _)| *time <= seconds);
        found.checked_sub(1).map(|place| moments[place].1)
    }

    pub fn new(setlist: &Setlist, song: &Song, routes: &[(String, Route)], seed: Option<i64>) -> Rendered<Score> {
        let realizer = SongRealizer::new(setlist, song, seed).looping_scenes_go_round();
        let grid = realizer.render()?;
        let tracks: Vec<String> = song.get_track_names().into_iter().map(str::to_string).collect();
        let mut score = Score {
            tracks: tracks.clone(),
            scene_seconds: Vec::new(),
            scene_starts: Vec::new(),
            rows: Vec::new(),
            events: HashMap::new(),
            loops: HashMap::new(),
            follow_actions: HashMap::new(),
            launches_together: Vec::new(),
            repeats: HashMap::new(),
            clip_seconds: HashMap::new(),
            bar: song.get_time_signature().bar_length().to_float(),
            routes: routes.to_vec(),
            draw_lights: Vec::new(),
        };
        let default_action = setlist
            .get_written(SetlistSetting::DEFAULT_FOLLOW_ACTION)
            .and_then(Data::as_str)
            .unwrap_or(DEFAULT_FOLLOW_ACTION)
            .to_string();
        let mut song_start = 0.0;
        for (index, scene) in song.scenes().iter().enumerate() {
            let together = scene
                .get_written(SceneSetting::LAUNCH_TOGETHER)
                .and_then(|value| match value {
                    Data::Bool(on) => Some(*on),
                    _ => None,
                })
                .unwrap_or(DEFAULT_LAUNCH_TOGETHER);
            score.launches_together.push(together);
            score.scene_starts.push(song_start);
            score.rows.push(Vec::new());
            score.draw_lights.push(Vec::new());
            for track in &tracks {
                let key = (index, track.clone());
                score.events.insert(key.clone(), Vec::new());
                let clip_slot = scene.get_clip_slot(track);
                score.loops.insert(key.clone(), clip_slot.is_some() && realizer.loops_through(index, track));
                let Some(clip_slot) = clip_slot else {
                    // An empty slot is done when its scene is done and counts as With Scene, so the track below starts as
                    // the export has it start.
                    score.follow_actions.insert(key.clone(), FollowAction::WITH_SCENE.to_string());
                    score.repeats.insert(key, None);
                    continue;
                };
                let action = clip_slot
                    .get_written(ClipSlotSetting::FOLLOW_ACTION)
                    .and_then(Data::as_str)
                    .map_or(default_action.clone(), str::to_string);
                score.follow_actions.insert(key.clone(), action);
                score.repeats.insert(key, (!clip_slot.loops()).then(|| clip_slot.get_repeat()));
            }
            let mut scene_start = 0.0;
            for place in realizer.rows_of_scene(index) {
                let row = &grid.rows[place];
                let clock = clock_of(&grid, row);
                let row_seconds = clock.seconds_at_exact(row_length(row)?);
                let row_place = score.rows[index].len();
                for (time, places) in realizer.draw_moments(place)? {
                    score.draw_lights[index].push((scene_start + clock.seconds_at_exact(time), places));
                }
                score.rows[index].push(ScoreRow {
                    start: scene_start,
                    seconds: row_seconds,
                    clock: clock.clone(),
                });
                for column in &grid.columns {
                    let Some((_, clip)) = row.clips.iter().find(|(name, _)| *name == column.name) else {
                        continue;
                    };
                    score
                        .clip_seconds
                        .insert((index, row_place, column.name.clone()), clock.seconds_at_exact(clip.total_length()?));
                    let Some((_, route)) = routes.iter().find(|(name, _)| *name == column.name) else {
                        continue;
                    };
                    if column.mute {
                        continue;
                    }
                    let tag = ClipTag {
                        scene: index,
                        track: column.name.clone(),
                        play: 0,
                    };
                    // Each row's events are put in time order within the row, and the rows follow one another, so that a
                    // clip's events are in time order across every repeat of its scene.
                    let mut events = clip_timeline(clip, route, &tag, Rational::ZERO, scene_start, &clock)?;
                    events.sort_by_key(|event| {
                        (
                            event.whole,
                            if event.kind == NOTE_OFF || event.kind == crate::realtime::timeline::PROGRAM_CHANGE {
                                0
                            } else {
                                1
                            },
                        )
                    });
                    score.events.entry((index, column.name.clone())).or_default().extend(events);
                }
                scene_start += row_seconds;
            }
            score.scene_seconds.push(scene_start);
            song_start += scene_start;
        }
        Ok(score)
    }

    /// The routes the score was made for.
    pub fn routes(&self) -> &[(String, Route)] {
        &self.routes
    }

    pub fn get_tracks(&self) -> &[String] {
        &self.tracks
    }

    pub fn scene_count(&self) -> usize {
        self.scene_seconds.len()
    }

    /// How long a scene lasts, all of its repeats together, in seconds.
    pub fn get_scene_seconds(&self, scene: usize) -> f64 {
        self.scene_seconds[scene]
    }

    /// When a scene starts when the song plays from the top, in seconds.
    pub fn get_scene_start(&self, scene: usize) -> f64 {
        self.scene_starts[scene]
    }

    /// How long the whole song lasts, in seconds.
    pub fn song_seconds(&self) -> f64 {
        self.scene_seconds.iter().sum()
    }

    /// Whether a start reaching any clip of a scene launches the whole scene.
    pub fn launches_together(&self, scene: usize) -> bool {
        self.launches_together[scene]
    }

    /// What a clip sends down when its scene is done.
    pub fn get_follow_action(&self, scene: usize, track: &str) -> &str {
        self.follow_actions
            .get(&(scene, track.to_string()))
            .map_or(FollowAction::WITH_SCENE, String::as_str)
    }

    /// Whether a clip loops for as long as its scene lasts.
    pub fn loops(&self, scene: usize, track: &str) -> bool {
        self.loops.get(&(scene, track.to_string())).copied().unwrap_or(false)
    }

    /// When a clip's own repeats end, in seconds from its scene's start, on the scene's first play, or None for a looping
    /// clip or an empty slot.
    pub fn clip_end(&self, scene: usize, track: &str) -> Option<f64> {
        if self.loops(scene, track) {
            return None;
        }
        self.clip_seconds.get(&(scene, FIRST_ROW, track.to_string())).copied()
    }

    /// A clip's events in time order, counted from its scene's start, tagged with play 0.
    pub fn clip_events(&self, scene: usize, track: &str) -> &[Playing] {
        self.events.get(&(scene, track.to_string())).map_or(&[], Vec::as_slice)
    }

    /// A clip's events played from a moment, start, tagged with tag, leaving out those before after and the note offs of
    /// notes that started before it, for a clip whose notes change while it plays.
    pub fn events_from(&self, scene: usize, track: &str, start: f64, tag: &ClipTag, after: f64) -> Vec<Playing> {
        let mut events = Vec::new();
        let mut started_before: Vec<(String, i64, i64)> = Vec::new();
        for event in self.clip_events(scene, track) {
            let seconds = start + event.seconds;
            let key = (event.port.clone(), event.channel, event.number);
            if seconds < after {
                if event.kind == NOTE_ON {
                    started_before.push(key);
                } else if event.kind == NOTE_OFF {
                    started_before.retain(|held| *held != key);
                }
                continue;
            }
            if event.kind == NOTE_OFF && started_before.contains(&key) {
                started_before.retain(|held| *held != key);
                continue;
            }
            let mut moved = event.clone();
            moved.seconds = seconds;
            moved.tag = tag.clone();
            events.push(moved);
        }
        events
    }

    /// The scene's row playing at a moment counted from the scene's start, and its place among the scene's rows.
    pub fn row_at(&self, scene: usize, elapsed: f64) -> (usize, &ScoreRow) {
        let rows = &self.rows[scene];
        let place = rows.iter().rposition(|row| row.start <= elapsed).unwrap_or(0);
        (place, &rows[place])
    }

    /// When a clip next starts a pass of its pattern, in seconds from its scene's start, at or after a moment, or None for a
    /// slot with no clip.
    pub fn next_pass_start(&self, scene: usize, track: &str, elapsed: f64) -> Option<f64> {
        if self.rows[scene].is_empty() {
            return None;
        }
        let (place, row) = self.row_at(scene, elapsed);
        let clip_seconds = *self.clip_seconds.get(&(scene, place, track.to_string()))?;
        if clip_seconds == 0.0 {
            return None;
        }
        let pass_seconds = match self.repeats.get(&(scene, track.to_string())).copied().flatten() {
            Some(repeat) if repeat != 0 => clip_seconds / repeat as f64,
            _ => clip_seconds,
        };
        let passes = ((elapsed - row.start).max(0.0) / pass_seconds - PASS_TOLERANCE).ceil();
        Some((row.start + passes * pass_seconds).min(row.start + row.seconds))
    }

    /// How far into a scene a moment is in whole notes, each of its rows at its own tempo, so that a moment keeps its place
    /// in the music when the tempo changes.
    pub fn whole_at(&self, scene: usize, elapsed: f64) -> f64 {
        let rows = &self.rows[scene];
        let mut whole = 0.0;
        for (place, row) in rows.iter().enumerate() {
            if elapsed <= row.start + row.seconds || place == rows.len() - 1 {
                return whole + row.clock.whole_at((elapsed - row.start).max(0.0));
            }
            whole += row.clock.whole_at(row.seconds);
        }
        whole
    }

    /// The moment in seconds from a scene's start that is so many whole notes into it.
    pub fn seconds_at(&self, scene: usize, whole: f64) -> f64 {
        let rows = &self.rows[scene];
        let mut counted = 0.0;
        for (place, row) in rows.iter().enumerate() {
            let row_whole = row.clock.whole_at(row.seconds);
            if whole <= counted + row_whole || place == rows.len() - 1 {
                return row.start + row.clock.seconds_at(whole - counted);
            }
            counted += row_whole;
        }
        0.0
    }

    /// How long a bar of the song's time signature lasts in seconds at a moment of a scene, at that moment's tempo.
    pub fn bar_seconds(&self, scene: usize, elapsed: f64) -> f64 {
        self.bar * self.seconds_per_whole(scene, elapsed)
    }

    /// How long a whole note lasts at a moment of a scene, in seconds.
    pub fn seconds_per_whole(&self, scene: usize, elapsed: f64) -> f64 {
        if self.rows[scene].is_empty() {
            return 2.0;
        }
        let (_, row) = self.row_at(scene, elapsed);
        row.clock.seconds_per_whole_at(elapsed - row.start)
    }

    /// How far into a clip's play a moment counted from the scene's start is, in seconds, for the clip's bar on Arrange:
    /// a looping clip starting over each time it ends; None for a slot with no clip.
    pub fn clip_elapsed(&self, scene: usize, track: &str, elapsed: f64) -> Option<f64> {
        if self.rows[scene].is_empty() {
            return None;
        }
        let (place, row) = self.row_at(scene, elapsed);
        let clip_seconds = *self.clip_seconds.get(&(scene, place, track.to_string()))?;
        if clip_seconds == 0.0 {
            return None;
        }
        let into_row = (elapsed - row.start).max(0.0);
        if self.loops(scene, track) {
            return Some(into_row.rem_euclid(clip_seconds));
        }
        Some(into_row.min(clip_seconds))
    }

    /// How many of a clip's repeats are still to play at a moment counted from the scene's start, or None for a clip that
    /// loops or has none.
    pub fn repeats_left(&self, scene: usize, track: &str, elapsed: f64) -> Option<i64> {
        let repeat = self.repeats.get(&(scene, track.to_string())).copied().flatten()?;
        if self.rows[scene].is_empty() {
            return None;
        }
        let (place, row) = self.row_at(scene, elapsed);
        let clip_seconds = *self.clip_seconds.get(&(scene, place, track.to_string()))?;
        if clip_seconds == 0.0 {
            return None;
        }
        let played = ((elapsed - row.start) / (clip_seconds / repeat as f64)).floor() as i64;
        Some((repeat - played).max(0))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Each step that draws lights the slot it took, from the step's time on, and nothing is lit before the first draw.
    #[test]
    fn draw_places_follow_each_step_that_draws() {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/one_draw_stepping.yml");
        let text = std::fs::read_to_string(path).expect("the scenario's set is there");
        let setlist = Setlist::read_text(&text, None).expect("the scenario's set is valid");
        let song = setlist.get_song("song").expect("the song");
        let score = Score::new(&setlist, song, &[], None).expect("the song renders");
        let first_draw = 0;
        // At 120 a minute a sixteenth lasts 0.125 s, so the middle of the third step is 0.3125 s in.
        let third_step_middle = 0.3125;
        let third_slot = 2;
        let at = |seconds: f64| score.draw_places_at(0, seconds).and_then(|places| places[first_draw]);
        assert_eq!(at(third_step_middle), Some(third_slot));
        assert_eq!(score.draw_places_at(0, -1.0), None);
    }
}
