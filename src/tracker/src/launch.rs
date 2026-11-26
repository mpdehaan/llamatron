// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What the tracker does by itself once it opens, by the command line's launch options: play the song from the top on
//! Arrange, show a visualizer mode over its clips or its details view, quit when the song ends, or quit after so many
//! seconds whatever plays. A recording starts the tracker this way, so that a take needs no key pressed.

use std::time::{Duration, Instant};

/// How long the tracker waits after the song stops before quitting when asked to quit when finished, so that its last notes
/// ring out.
const LEAD_OUT: Duration = Duration::from_secs(2);

/// What the tracker does by itself once it opens.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Launch {
    /// Play the song from the top on Arrange.
    pub autoplay: bool,
    /// Quit once the song has played and stopped; implies autoplay.
    pub quit_when_finished: bool,
    /// Quit this many seconds after opening, whatever plays.
    pub max_seconds: Option<f64>,
    /// Show this visualizer mode over Arrange's clips; implies autoplay.
    pub visualizer: Option<String>,
    /// Open Arrange with its details view showing.
    pub details: bool,
}

impl Launch {
    /// Whether the tracker plays the song by itself.
    pub fn plays(&self) -> bool {
        self.autoplay || self.quit_when_finished || self.visualizer.is_some()
    }

    /// Whether the tracker opens on Arrange rather than the main screen.
    pub fn opens_arrange(&self) -> bool {
        self.plays() || self.details
    }

    /// Whether anything was asked of the launch at all.
    pub fn is_asked(&self) -> bool {
        *self != Launch::default()
    }
}

/// A launch as it runs: when it began, whether the song has been heard playing, so that its end can be seen, and when it
/// stopped.
pub struct Running {
    launch: Launch,
    began: Instant,
    heard_playing: bool,
    stopped_at: Option<Instant>,
    lead_out: Duration,
}

impl Running {
    pub fn new(launch: Launch) -> Running {
        Running {
            launch,
            began: Instant::now(),
            heard_playing: false,
            stopped_at: None,
            lead_out: LEAD_OUT,
        }
    }

    /// Whether the tracker should quit now: past its most seconds, or LEAD_OUT after the song played and stopped when asked
    /// to quit then.
    pub fn should_quit(&mut self, playing: bool) -> bool {
        if let Some(most) = self.launch.max_seconds {
            if self.began.elapsed() >= Duration::from_secs_f64(most.max(0.0)) {
                return true;
            }
        }
        if playing {
            self.heard_playing = true;
            self.stopped_at = None;
            return false;
        }
        if !(self.launch.quit_when_finished && self.heard_playing) {
            return false;
        }
        let stopped_at = *self.stopped_at.get_or_insert_with(Instant::now);
        stopped_at.elapsed() >= self.lead_out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A launch asked to quit when finished waits for the song to have played, then quits once it stops and its lead-out
    /// passes.
    #[test]
    fn quitting_when_finished_waits_for_the_song_to_play_and_stop() {
        let launch = Launch {
            quit_when_finished: true,
            ..Launch::default()
        };
        let mut running = Running::new(launch);
        running.lead_out = Duration::ZERO;
        assert!(!running.should_quit(false), "nothing has played yet");
        assert!(!running.should_quit(true), "the song plays");
        assert!(running.should_quit(false), "the song has stopped and its lead-out passed");
    }

    /// A visualizer implies playing, and the details view alone opens Arrange without playing.
    #[test]
    fn a_visualizer_plays_and_the_details_alone_only_open_arrange() {
        let visual = Launch {
            visualizer: Some("lava_lamp".to_string()),
            ..Launch::default()
        };
        assert!(visual.plays() && visual.opens_arrange());
        let details = Launch {
            details: true,
            ..Launch::default()
        };
        assert!(!details.plays() && details.opens_arrange());
    }
}
