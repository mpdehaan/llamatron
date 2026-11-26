// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The player (the Python realtime/render_process/player.py): launches a score's scenes and clips, and hands each clip's
//! events to a sender as its moment comes.
//!
//! A scene launched by hand plays every clip of it. A scene is done when every clip launched in it that doesn't loop has
//! finished its repeats; then each clip whose follow action is With Scene, looping or not, sends a start to the clip
//! directly below, an empty slot counting as With Scene. A clip whose follow action is Next sends its start as its own
//! repeats end; Off sends nothing. A start reaching a scene that launches together launches the whole scene, stopping
//! what the scene above still plays; otherwise the one clip starts alone, cutting only its track. A clip launched by hand
//! plays on its own; a clip stopped or cut never finished, so it sends no start. A looping clip never finishes, so it
//! doesn't hold its scene, and a scene whose every clip loops waits for the human. A launch by hand while anything plays
//! is at the next bar, counted from the start of the earliest clip playing; with nothing playing it is at once.
//!
//! Everything is decided ahead: the moments to come are kept in order, and each tick turns those due within
//! LOOKAHEAD_SECONDS into plays, handing the sender every play's events due within the window ahead. The player reads
//! nothing but the score and a clock giving the sender's seconds, so it is driven on a stepped clock in the comparison.

use crate::realtime::clip_notes;
use crate::realtime::score::Score;
use crate::realtime::timeline::{ClipTag, Playing, CONTROL_CHANGE, NOTE_OFF, PLAY_STARTED, PLAY_STOPPED};
use llamatron_math::Rational;
use llamatron_model::schema::generated::file_format::{FollowAction, LiveResponsiveness};

/// How far ahead moments are turned into queued events, and how far ahead each play's events are handed to the sender.
pub const LOOKAHEAD_SECONDS: f64 = 0.5;
const WINDOW_SECONDS: f64 = LOOKAHEAD_SECONDS;
/// How soon after now an edit made while playing is heard at its quickest.
const LIVE_LATENCY_SECONDS: f64 = 0.05;
/// How far apart two moments may be and still count as one.
const SAME_MOMENT_SECONDS: f64 = 1e-6;
const FIRST_SCENE: usize = 0;
/// What a forget forgets from: every event of a tag, however early.
pub const BEFORE_EVERYTHING: f64 = f64::NEG_INFINITY;

/// What the player hands its events to: the backend's sender, or a recording one in the comparison.
pub trait Sender {
    /// Queue events, each at its seconds on the sender's clock.
    fn add(&mut self, events: Vec<Playing>);
    /// Forget a tag's events from a moment on.
    fn forget(&mut self, tag: &ClipTag, after: f64);
    /// Stop a tag at once: its sounding notes ended and its events forgotten.
    fn stop_tag(&mut self, tag: &ClipTag);
    /// Stop everything, silencing every channel used.
    fn stop_all(&mut self);
}

/// The kinds of moment, in the order they run at one time: a clip's and a scene's done checks and the launches their
/// follow actions send, then the launches by hand.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum MomentKind {
    ClipDone,
    SceneDone,
    LaunchScene,
    LaunchClips,
    SceneByHand,
    ClipByHand,
}

/// Something to do at a time, in order by time, then kind, then the order it was planned in.
#[derive(Clone, Debug)]
struct Moment {
    time: f64,
    kind: MomentKind,
    count: u64,
    scene: usize,
    tracks: Vec<String>,
    forever: bool,
}

impl Moment {
    /// Whether it comes before another.
    fn before(&self, other: &Moment) -> bool {
        (self.time, self.kind, self.count)
            .partial_cmp(&(other.time, other.kind, other.count))
            .is_some_and(|order| order.is_lt())
    }
}

/// One launch of one clip on its track: when it starts and ends on the sender's clock, its tag, how it was launched and
/// ended, and its events, each at offset plus its seconds, with how many are queued already.
#[derive(Clone, Debug)]
struct Play {
    scene: usize,
    track: String,
    start: f64,
    end: f64,
    tag: ClipTag,
    alone: bool,
    loops: bool,
    cut: bool,
    done: bool,
    preview: bool,
    events: Vec<Playing>,
    offset: f64,
    fed: usize,
}

impl Play {
    /// Send these events from the first, each at offset plus its seconds, in place of any not yet queued.
    fn take_events(&mut self, events: Vec<Playing>, offset: f64) {
        self.events = events;
        self.offset = offset;
        self.fed = 0;
    }

    /// The events not yet queued that are due by a moment, placed on the sender's clock and tagged, marked queued; with
    /// before, only those due before it. A play cut short sends nothing from its end on.
    fn events_due(&mut self, end: f64, before: bool) -> Vec<Playing> {
        let limit = self.cut.then_some(self.end);
        let mut due = Vec::new();
        let mut place = self.fed;
        while place < self.events.len() {
            let seconds = self.offset + self.events[place].seconds;
            if seconds > end || (before && seconds == end) {
                break;
            }
            if limit.is_none_or(|limit| seconds < limit) {
                let mut event = self.events[place].clone();
                event.seconds = seconds;
                event.tag = self.tag.clone();
                due.push(event);
            }
            place += 1;
        }
        self.fed = place;
        due
    }

    fn is_running(&self, now: f64) -> bool {
        self.start <= now && now < self.end
    }
}

/// Launches scenes and clips of a score through a sender, following the follow actions and Launch together.
pub struct Player {
    score: Score,
    lead: f64,
    plays: Vec<Play>,
    moments: Vec<Moment>,
    count: u64,
    play_count: i64,
    laps: Vec<(usize, String)>,
    /// Whether this player is playing, from a start in silence to a stop or to everything having played out, which the
    /// built-in instruments are told of.
    running: bool,
}

impl Player {
    /// The player of a score; lead is how far ahead of now a launch from silence starts.
    pub fn new(score: Score, lead: f64) -> Player {
        Player {
            score,
            lead,
            plays: Vec::new(),
            moments: Vec::new(),
            count: 0,
            play_count: 0,
            laps: Vec::new(),
            running: false,
        }
    }

    /// Tell every built-in instrument of the score's routes, at a moment, that playback starts from silence or stops: a
    /// controller of the timeline's, so that its modulators run only while it plays.
    fn mark_playback(&mut self, sender: &mut dyn Sender, number: i64, at: f64) {
        let marks: Vec<Playing> = self
            .score
            .routes()
            .iter()
            .filter(|(_, route)| route.sound.is_some())
            .map(|(track, route)| Playing {
                whole: Rational::ZERO,
                seconds: at,
                port: route.port.clone(),
                channel: route.channel,
                kind: CONTROL_CHANGE,
                number,
                value: 0,
                tag: ClipTag {
                    scene: FIRST_SCENE,
                    track: track.clone(),
                    play: 0,
                },
                switch: false,
            })
            .collect();
        if !marks.is_empty() {
            sender.add(marks);
        }
    }

    /// Playback starting from silence at a moment, told to the built-in instruments once.
    fn start_running(&mut self, sender: &mut dyn Sender, at: f64) {
        if !self.running {
            self.running = true;
            self.mark_playback(sender, PLAY_STARTED, at);
        }
    }

    /// Playback stopped at a moment, by hand or by everything having played out, told to the built-in instruments once.
    fn stop_running(&mut self, sender: &mut dyn Sender, at: f64) {
        if self.running {
            self.running = false;
            self.mark_playback(sender, PLAY_STOPPED, at);
        }
    }

    pub fn get_score(&self) -> &Score {
        &self.score
    }

    /// Take a score rendered afresh, which the next launch plays from; what plays already keeps its events.
    pub fn set_score(&mut self, score: Score) {
        self.score = score;
    }

    /// The scene and track of each looping clip that started a lap since last asked, forgotten.
    pub fn take_laps(&mut self) -> Vec<(usize, String)> {
        std::mem::take(&mut self.laps)
    }

    /// Play the song from its first scene; when it starts.
    pub fn play_song(&mut self, sender: &mut dyn Sender, now: f64) -> f64 {
        self.play_scene(sender, now, FIRST_SCENE)
    }

    /// Launch every clip of a scene in place of everything playing; when it starts: now, or the next bar of what plays.
    pub fn play_scene(&mut self, sender: &mut dyn Sender, now: f64, scene: usize) -> f64 {
        let at = self.next_bar(now).unwrap_or(now + self.lead);
        self.plan(at, MomentKind::SceneByHand, scene, Vec::new(), false);
        self.tick(sender, now);
        at
    }

    /// Launch clips of one scene on their own, cutting whatever their tracks play; with forever they loop, as a listening
    /// page wants. When they start.
    pub fn play_clips(&mut self, sender: &mut dyn Sender, now: f64, scene: usize, tracks: Vec<String>, forever: bool) -> f64 {
        let at = self.next_bar(now).unwrap_or(now + self.lead);
        self.plan(at, MomentKind::ClipByHand, scene, tracks, forever);
        self.tick(sender, now);
        at
    }

    /// Cut what a track plays now, leaving the other tracks alone.
    pub fn stop_clip(&mut self, sender: &mut dyn Sender, now: f64, track: &str) {
        if let Some(place) = self.running_on(now, track) {
            self.cut(sender, now, place, now, None);
        }
    }

    /// Stop every clip and forget every moment to come.
    pub fn stop_all(&mut self, sender: &mut dyn Sender) {
        sender.stop_all();
        self.plays.clear();
        self.moments.clear();
        self.stop_running(sender, 0.0);
    }

    /// When the next bar starts, counted from the start of the earliest clip playing, or that clip's end if it comes
    /// first, or None when nothing plays.
    pub fn next_bar(&self, now: f64) -> Option<f64> {
        let first = self
            .plays
            .iter()
            .filter(|play| play.is_running(now))
            .min_by(|a, b| a.start.total_cmp(&b.start))?;
        let elapsed = now - first.start;
        let bar = self.score.bar_seconds(first.scene, elapsed);
        let at = if bar > 0.0 {
            first.start + ((elapsed / bar).floor() + 1.0) * bar
        } else {
            first.end
        };
        Some(at.min(first.end))
    }

    /// Turn every moment due within the lookahead into queued events and further moments, in time order, and forget the
    /// plays that are over.
    pub fn tick(&mut self, sender: &mut dyn Sender, now: f64) {
        let horizon = now + LOOKAHEAD_SECONDS;
        while let Some(place) = self.first_moment() {
            if self.moments[place].time > horizon {
                break;
            }
            let moment = self.moments.remove(place);
            match moment.kind {
                MomentKind::ClipDone => self.clip_done(moment.scene, &moment.tracks[0], moment.time),
                MomentKind::SceneDone => self.scene_done(sender, now, moment.scene, moment.time),
                MomentKind::LaunchScene => self.launch_scene(sender, now, moment.scene, moment.time),
                MomentKind::LaunchClips => {
                    for track in &moment.tracks {
                        self.start_play(sender, now, moment.scene, track, moment.time, true, false, false);
                    }
                }
                MomentKind::SceneByHand => {
                    self.stop_everything_at(sender, now, moment.time);
                    self.launch_scene(sender, now, moment.scene, moment.time);
                }
                MomentKind::ClipByHand => {
                    for track in &moment.tracks {
                        self.start_play(sender, now, moment.scene, track, moment.time, true, moment.forever, moment.forever);
                    }
                }
            }
        }
        self.send_windows(sender, now);
        self.plays.retain(|play| play.end > now || !(play.done || play.cut));
        if self.plays.is_empty() && self.moments.is_empty() {
            self.stop_running(sender, now);
        }
    }

    /// Take a score rendered afresh after an edit, and change what plays to it from the moment the song's Live response
    /// says, keeping its place in the music. scene_map and track_map give each old scene's place and track's name in the
    /// new score, None for one that has gone.
    pub fn update_score(
        &mut self,
        sender: &mut dyn Sender,
        now: f64,
        score: Score,
        responsiveness: &str,
        scene_map: &dyn Fn(usize) -> Option<usize>,
        track_map: &dyn Fn(&str) -> Option<String>,
    ) {
        let bar = self.next_bar(now);
        let old = std::mem::replace(&mut self.score, score);
        for place in 0..self.plays.len() {
            let (old_scene, old_track) = (self.plays[place].scene, self.plays[place].track.clone());
            let new_scene = scene_map(old_scene);
            let new_track = track_map(&old_track);
            if self.plays[place].end <= now {
                if let (Some(scene), Some(track)) = (new_scene, new_track) {
                    self.plays[place].scene = scene;
                    self.plays[place].track = track;
                }
                continue;
            }
            let at = Self::switch_time(&self.plays[place], &old, responsiveness, now, bar);
            let (Some(new_scene), Some(new_track)) = (new_scene, new_track) else {
                self.cut(sender, now, place, at.max(now), Some(&old));
                continue;
            };
            let play_start = self.plays[place].start;
            let start = if play_start >= at {
                sender.forget(&self.plays[place].tag, BEFORE_EVERYTHING);
                play_start
            } else if at >= self.plays[place].end {
                let play = &mut self.plays[place];
                play.scene = new_scene;
                play.track = new_track.clone();
                play.loops = play.preview || self.score.loops(new_scene, &new_track);
                continue;
            } else {
                let earlier = self.plays[place].events_due(at, true);
                if !earlier.is_empty() {
                    sender.add(earlier);
                }
                sender.forget(&self.plays[place].tag, at);
                let notes = clip_notes::sounding_across(old.clip_events(old_scene, &old_track), at - play_start);
                Self::send_note_offs(sender, notes, at, &self.plays[place].tag);
                let whole = old.whole_at(old_scene, at - play_start);
                at - self.score.seconds_at(new_scene, whole)
            };
            let tag = self.plays[place].tag.clone();
            let events = self.score.events_from(new_scene, &new_track, start, &tag, at.max(start));
            let scene_seconds = self.score.get_scene_seconds(new_scene);
            let loops = self.score.loops(new_scene, &new_track);
            let play = &mut self.plays[place];
            play.scene = new_scene;
            play.track = new_track;
            play.start = start;
            play.loops = play.preview || loops;
            if !play.cut {
                play.end = start + scene_seconds;
            }
            play.take_events(events, 0.0);
        }
        let mut moments = Vec::new();
        for moment in std::mem::take(&mut self.moments) {
            let Some(scene) = scene_map(moment.scene) else { continue };
            let tracks = moment.tracks.iter().filter_map(|track| track_map(track)).collect();
            moments.push(Moment { scene, tracks, ..moment });
        }
        self.moments = moments;
        self.plan_ends_again(now);
        self.send_windows(sender, now);
    }

    /// Whether anything plays now or is still to come.
    pub fn is_playing(&self, now: f64) -> bool {
        self.plays.iter().any(|play| play.end > now) || self.moments.iter().any(|moment| self.can_act(moment))
    }

    /// The scenes with a clip playing now, in order.
    pub fn playing_scenes(&self, now: f64) -> Vec<usize> {
        let mut scenes: Vec<usize> = self.plays.iter().filter(|play| play.is_running(now)).map(|play| play.scene).collect();
        scenes.sort_unstable();
        scenes.dedup();
        scenes
    }

    /// Whether a scene's clip on a track plays now.
    pub fn is_clip_playing(&self, now: f64, scene: usize, track: &str) -> bool {
        self.running_on(now, track).is_some_and(|place| self.plays[place].scene == scene)
    }

    /// Whether a note sounds on a track now, read from the score.
    pub fn is_track_sounding(&self, now: f64, track: &str) -> bool {
        self.running_on(now, track).is_some_and(|place| {
            let play = &self.plays[place];
            clip_notes::is_sounding(self.score.clip_events(play.scene, track), now - play.start)
        })
    }

    /// How far into a scene its earliest running clip is, in seconds, or None when none plays.
    pub fn scene_elapsed(&self, now: f64, scene: usize) -> Option<f64> {
        let start = self
            .plays
            .iter()
            .filter(|play| play.is_running(now) && play.scene == scene)
            .map(|play| play.start)
            .min_by(f64::total_cmp)?;
        Some(now - start)
    }

    /// How far into its play a clip is, in seconds, or None when it isn't playing.
    pub fn clip_elapsed(&self, now: f64, scene: usize, track: &str) -> Option<f64> {
        let place = self.running_on(now, track)?;
        let play = &self.plays[place];
        if play.scene != scene {
            return None;
        }
        self.score.clip_elapsed(scene, track, now - play.start)
    }

    /// How many repeats a playing clip has left, or None.
    pub fn repeats_left(&self, now: f64, scene: usize, track: &str) -> Option<i64> {
        let place = self.running_on(now, track)?;
        let play = &self.plays[place];
        if play.scene != scene {
            return None;
        }
        self.score.repeats_left(scene, track, now - play.start)
    }

    /// Where the song is, in seconds from its top, by the earliest scene playing, or None when nothing plays.
    pub fn song_position(&self, now: f64) -> Option<f64> {
        let scene = *self.playing_scenes(now).first()?;
        Some(self.score.get_scene_start(scene) + self.scene_elapsed(now, scene)?)
    }

    /// The notes heard on each track with a clip running, those started after since and those still sounding, for the
    /// visualizer.
    pub fn heard(&self, now: f64, since: f64) -> Vec<(String, Vec<clip_notes::HeardClipNote>, Vec<clip_notes::HeardClipNote>)> {
        let mut heard = Vec::new();
        for play in self.plays.iter().filter(|play| play.is_running(now)) {
            let (started, held) = clip_notes::heard(self.score.clip_events(play.scene, &play.track), since - play.start, now - play.start);
            if !started.is_empty() || !held.is_empty() {
                heard.push((play.track.clone(), started, held));
            }
        }
        heard
    }

    /// When an edit is heard on a play: at once, at the next bar of what plays, or at the play's next pass by the old
    /// score, never before LIVE_LATENCY_SECONDS from now.
    fn switch_time(play: &Play, score: &Score, responsiveness: &str, now: f64, bar: Option<f64>) -> f64 {
        let soonest = now + LIVE_LATENCY_SECONDS;
        let at = if responsiveness == LiveResponsiveness::NEXT_BAR {
            bar
        } else if responsiveness == LiveResponsiveness::CLIP_RESTART && play.start < now {
            score.next_pass_start(play.scene, &play.track, now - play.start).map(|into| play.start + into)
        } else {
            Some(soonest)
        };
        at.map_or(soonest, |at| at.max(soonest))
    }

    /// A note off at a moment for each note given, tagged with a play's tag.
    fn send_note_offs(sender: &mut dyn Sender, notes: Vec<(String, i64, i64)>, at: f64, tag: &ClipTag) {
        let offs = notes
            .into_iter()
            .map(|(port, channel, number)| Playing {
                whole: Rational::ZERO,
                seconds: at,
                port,
                channel,
                kind: NOTE_OFF,
                number,
                value: 0,
                tag: tag.clone(),
                switch: false,
            })
            .collect();
        sender.add(offs);
    }

    /// Plan again when each playing clip's scene and repeats end, by the score as it is now.
    fn plan_ends_again(&mut self, now: f64) {
        self.moments
            .retain(|moment| !matches!(moment.kind, MomentKind::SceneDone | MomentKind::ClipDone) || moment.time <= now);
        let mut planned: Vec<(i64, usize)> = Vec::new();
        let plays: Vec<(f64, f64, usize, String)> = self
            .plays
            .iter()
            .filter(|play| !(play.end <= now || play.cut || play.done))
            .map(|play| (play.start, play.end, play.scene, play.track.clone()))
            .collect();
        for (start, end, scene, track) in plays {
            let key = ((end / SAME_MOMENT_SECONDS).round() as i64, scene);
            if !planned.contains(&key) {
                planned.push(key);
                self.plan(end, MomentKind::SceneDone, scene, Vec::new(), false);
            }
            if let Some(clip_end) = self.score.clip_end(scene, &track) {
                if self.score.get_follow_action(scene, &track) == FollowAction::NEXT && start + clip_end > now {
                    self.plan(start + clip_end, MomentKind::ClipDone, scene, vec![track], false);
                }
            }
        }
    }

    /// Queue with the sender, in one message, every play's events due within the window ahead of now.
    fn send_windows(&mut self, sender: &mut dyn Sender, now: f64) {
        let end = now + WINDOW_SECONDS;
        let mut due = Vec::new();
        for play in &mut self.plays {
            due.extend(play.events_due(end, false));
        }
        if !due.is_empty() {
            sender.add(due);
        }
    }

    /// Whether a moment can still do something: a launch can, and a check of a scene's or a clip's end can while a play of
    /// it is neither cut nor done.
    fn can_act(&self, moment: &Moment) -> bool {
        if !matches!(moment.kind, MomentKind::SceneDone | MomentKind::ClipDone) {
            return true;
        }
        self.plays
            .iter()
            .any(|play| play.scene == moment.scene && !play.cut && !play.done && play.start < moment.time)
    }

    /// The place of the play running on a track now, or None.
    fn running_on(&self, now: f64, track: &str) -> Option<usize> {
        self.plays.iter().position(|play| play.is_running(now) && play.track == track)
    }

    /// The place of the moment due first.
    fn first_moment(&self) -> Option<usize> {
        let mut first: Option<usize> = None;
        for (place, moment) in self.moments.iter().enumerate() {
            if first.is_none_or(|held| moment.before(&self.moments[held])) {
                first = Some(place);
            }
        }
        first
    }

    fn plan(&mut self, time: f64, kind: MomentKind, scene: usize, tracks: Vec<String>, forever: bool) {
        self.count += 1;
        self.moments.push(Moment {
            time,
            kind,
            count: self.count,
            scene,
            tracks,
            forever,
        });
    }

    fn launch_scene(&mut self, sender: &mut dyn Sender, now: f64, scene: usize, at: f64) {
        let tracks = self.score.get_tracks().to_vec();
        for track in &tracks {
            self.start_play(sender, now, scene, track, at, false, false, false);
        }
        let seconds = self.score.get_scene_seconds(scene);
        self.plan(at + seconds, MomentKind::SceneDone, scene, Vec::new(), false);
    }

    /// Queue one clip's events from a moment on its track, cutting what the track plays then, and cut where a play
    /// already queued ahead on the track starts.
    #[allow(clippy::too_many_arguments)]
    fn start_play(&mut self, sender: &mut dyn Sender, now: f64, scene: usize, track: &str, at: f64, alone: bool, forever: bool, preview: bool) {
        let mut next_start: Option<f64> = None;
        let mut place = 0;
        while place < self.plays.len() {
            if self.plays[place].track != track {
                place += 1;
                continue;
            }
            let (start, end) = (self.plays[place].start, self.plays[place].end);
            if start == at {
                sender.forget(&self.plays[place].tag, BEFORE_EVERYTHING);
                self.plays.remove(place);
                continue;
            }
            if start < at && at < end {
                self.cut(sender, now, place, at, None);
            } else if start > at {
                next_start = Some(next_start.map_or(start, |held: f64| held.min(start)));
            }
            place += 1;
        }
        self.start_running(sender, at);
        self.play_count += 1;
        let end = at + self.score.get_scene_seconds(scene);
        let loops = forever || self.score.loops(scene, track);
        let mut play = Play {
            scene,
            track: track.to_string(),
            start: at,
            end,
            tag: ClipTag {
                scene,
                track: track.to_string(),
                play: self.play_count,
            },
            alone,
            loops,
            cut: false,
            done: false,
            preview,
            events: Vec::new(),
            offset: 0.0,
            fed: 0,
        };
        play.take_events(self.score.clip_events(scene, track).to_vec(), at);
        self.plays.push(play);
        if loops {
            self.laps.push((scene, track.to_string()));
        }
        if let Some(next) = next_start.filter(|next| *next < end) {
            let last = self.plays.len() - 1;
            self.cut(sender, now, last, next, None);
        }
        // A clip launched with its scene is checked by the scene's own moment; one launched alone, or played again to
        // loop, needs a moment of its own.
        if alone || forever {
            self.plan(end, MomentKind::SceneDone, scene, Vec::new(), false);
        }
        if let Some(clip_end) = self.score.clip_end(scene, track) {
            if self.score.get_follow_action(scene, track) == FollowAction::NEXT {
                self.plan(at + clip_end, MomentKind::ClipDone, scene, vec![track.to_string()], false);
            }
        }
    }

    /// When a clip whose follow action is Next ends its repeats, uncut and not yet done, send its start to the clip below.
    fn clip_done(&mut self, scene: usize, track: &str, at: f64) {
        let found = self
            .plays
            .iter()
            .position(|play| play.scene == scene && play.track == track && play.start < at && at <= play.end && !play.cut && !play.done);
        if let Some(place) = found {
            self.plays[place].done = true;
            self.send_starts(scene, at, vec![track.to_string()]);
        }
    }

    /// When a scene comes to its end, send the starts its clips' follow actions say, and play its looping clips again; a
    /// loop with no scene below to go to ends with the scene, so the song ends when the export does.
    fn scene_done(&mut self, sender: &mut dyn Sender, now: f64, scene: usize, at: f64) {
        let places: Vec<usize> = (0..self.plays.len())
            .filter(|place| {
                let play = &self.plays[*place];
                play.scene == scene && play.start < at && !play.cut && !play.done
            })
            .collect();
        if places.is_empty() || places.iter().any(|place| self.plays[*place].end > at) {
            return;
        }
        for place in &places {
            self.plays[*place].done = true;
        }
        let done = !places.iter().all(|place| self.plays[*place].loops);
        let last_scene = scene + 1 >= self.score.scene_count();
        let plays: Vec<(String, bool, bool, bool)> = places
            .iter()
            .map(|place| {
                let play = &self.plays[*place];
                (play.track.clone(), play.loops, play.alone, play.preview)
            })
            .collect();
        for (track, loops, alone, preview) in &plays {
            let ends_here = done && last_scene && self.score.get_follow_action(scene, track) != FollowAction::OFF;
            if *loops && !ends_here {
                self.start_play(sender, now, scene, track, at, *alone, true, *preview);
            }
        }
        if done {
            let starts: Vec<String> = plays
                .iter()
                .filter(|(track, ..)| self.score.get_follow_action(scene, track) != FollowAction::OFF)
                .map(|(track, ..)| track.clone())
                .collect();
            self.send_starts(scene, at, starts);
        }
    }

    /// Send a start from each track's clip in a scene to the clip directly below: the whole scene below when it launches
    /// together, the clips alone otherwise, each planned once.
    fn send_starts(&mut self, scene: usize, at: f64, tracks: Vec<String>) {
        let below = scene + 1;
        if tracks.is_empty() || below >= self.score.scene_count() {
            return;
        }
        if self.score.launches_together(below) {
            if !self.is_planned(at, MomentKind::LaunchScene, below, None) {
                self.plan(at, MomentKind::LaunchScene, below, Vec::new(), false);
            }
        } else {
            let new: Vec<String> = tracks
                .into_iter()
                .filter(|track| !self.is_planned(at, MomentKind::LaunchClips, below, Some(track)))
                .collect();
            if !new.is_empty() {
                self.plan(at, MomentKind::LaunchClips, below, new, false);
            }
        }
    }

    fn is_planned(&self, time: f64, kind: MomentKind, scene: usize, track: Option<&str>) -> bool {
        self.moments.iter().any(|moment| {
            moment.time == time && moment.kind == kind && moment.scene == scene && track.is_none_or(|track| moment.tracks.iter().any(|held| held == track))
        })
    }

    /// End every play at a moment and forget every moment to come, for a scene launched by hand.
    fn stop_everything_at(&mut self, sender: &mut dyn Sender, now: f64, at: f64) {
        let mut place = 0;
        while place < self.plays.len() {
            if self.plays[place].start >= at {
                sender.forget(&self.plays[place].tag, BEFORE_EVERYTHING);
                self.plays.remove(place);
                continue;
            }
            if self.plays[place].end > at {
                self.cut(sender, now, place, at, None);
            }
            place += 1;
        }
        self.moments.clear();
    }

    /// End a play at a moment: now, by stopping its tag, or later, by dropping its events from then and ending the notes
    /// sounding across it, by the score it was queued from.
    fn cut(&mut self, sender: &mut dyn Sender, now: f64, place: usize, at: f64, score: Option<&Score>) {
        let play = &self.plays[place];
        if at <= now {
            sender.stop_tag(&play.tag);
        } else {
            sender.forget(&play.tag, at);
            let score = score.unwrap_or(&self.score);
            let notes = clip_notes::sounding_across(score.clip_events(play.scene, &play.track), at - play.start);
            Self::send_note_offs(sender, notes, at, &play.tag);
        }
        let play = &mut self.plays[place];
        play.end = play.end.min(at);
        play.cut = true;
    }
}
