// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! How long the current song's scenes and clips last in seconds (the Python interface/tracker/lengths.py), from the
//! realizer's estimate of each written-out scene: a scene plays once a repeat, its plays one after another.

use llamatron_engine::realizer::{SceneEstimate, SongRealizer};
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::Song;

pub struct Lengths {
    plays: Vec<SceneEstimate>,
    /// Each scene's plays, by their places among every play.
    scene_plays: Vec<std::ops::Range<usize>>,
}

impl Lengths {
    pub fn of(setlist: &Setlist, song: &Song) -> Lengths {
        let mut scene_plays = Vec::new();
        let mut start = 0;
        for scene in song.scenes() {
            let repeat = scene.get_repeat().max(0) as usize;
            scene_plays.push(start..start + repeat);
            start += repeat;
        }
        Lengths {
            plays: SongRealizer::new(setlist, song, None).estimate(),
            scene_plays,
        }
    }

    fn all_or_none(values: impl Iterator<Item = Option<f64>>) -> Option<f64> {
        let mut total = 0.0;
        for value in values {
            total += value?;
        }
        Some(total)
    }

    /// How long a scene and all of its repeats last, or None where any play of it can't be worked out.
    pub fn scene_seconds(&self, index: usize) -> Option<f64> {
        let places = self.scene_plays.get(index)?.clone();
        Self::all_or_none(places.map(|place| self.plays.get(place).and_then(|play| play.seconds)))
    }

    pub fn longest_scene_seconds(&self) -> Option<f64> {
        (0..self.scene_plays.len()).filter_map(|index| self.scene_seconds(index)).reduce(f64::max)
    }

    /// How long one play of a scene lasts, its first, which its clips are measured against.
    pub fn scene_play_seconds(&self, index: usize) -> Option<f64> {
        let first = self.scene_plays.get(index)?.start;
        self.plays.get(first).and_then(|play| play.seconds)
    }

    /// How long a track's clip lasts in a scene's first play.
    pub fn clip_seconds(&self, index: usize, track: &str) -> Option<f64> {
        let first = self.scene_plays.get(index)?.start;
        self.plays
            .get(first)?
            .clips
            .iter()
            .find(|(found, _)| found == track)
            .map(|(_, seconds)| *seconds)
    }

    pub fn song_seconds(&self) -> Option<f64> {
        Self::all_or_none(self.plays.iter().map(|play| play.seconds))
    }
}
