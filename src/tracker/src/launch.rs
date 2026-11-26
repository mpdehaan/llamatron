// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What the tracker does by itself once it opens, by the command line's launch options: play the song from the top on
//! Arrange, show a visualizer mode over its clips or its details view, quit when the song ends, or quit after so many
//! seconds whatever plays. A recording starts the tracker this way, so that a take needs no key pressed.
//!
//! Launched for recording, the tracker opens on the title for SPLASH_SECONDS, opens Arrange, waits LEAD_IN, plays the
//! song from the top, and once it stops waits LEAD_OUT, shows the title again for SPLASH_SECONDS, holds and quits. An
//! interactive take plays nothing by itself: the person recording starts the song from Arrange, performs, and ends the
//! take by stopping everything or leaving Arrange, after which the title shows again.

use std::time::{Duration, Instant};

/// How long the title shows at the opening and the close of a recording.
pub const SPLASH_SECONDS: f64 = 6.0;
/// How long Arrange shows before the song starts, and how long the last notes ring out after it stops.
const LEAD_IN: Duration = Duration::from_secs(1);
const LEAD_OUT: Duration = Duration::from_secs(2);
/// How long the tracker waits after the closing title before quitting, so that the recorder can end the video on black.
const HOLD: Duration = Duration::from_millis(500);

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
    /// Play for a recording: the title first and last, no save mark, and quit once the song is done.
    pub for_recording: bool,
    /// With for_recording, play nothing by itself: the person recording starts and ends the take.
    pub interactive: bool,
}

impl Launch {
    /// Whether the tracker plays the song by itself.
    pub fn plays(&self) -> bool {
        (self.autoplay || self.quit_when_finished || self.visualizer.is_some() || self.for_recording) && !self.interactive
    }

    /// Whether the tracker opens on Arrange rather than the main screen.
    pub fn opens_arrange(&self) -> bool {
        self.plays() || self.details || self.for_recording
    }

    /// Whether the tracker quits by itself once the song is done.
    fn quits_when_done(&self) -> bool {
        self.quit_when_finished || self.for_recording
    }
}

/// Where a launch stands.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Phase {
    /// The opening title, since a moment.
    Opening(Instant),
    /// Arrange shows, waiting to play, since a moment.
    LeadIn(Instant),
    /// The song may play, or plays; the tracker runs as ever.
    Running,
    /// The song stopped at a moment and its last notes ring out.
    LeadOut(Instant),
    /// The closing title, since a moment.
    Closing(Instant),
    /// The closing title is done; the tracker quits after a moment.
    Holding(Instant),
}

/// What the terminal does with this moment of a launch.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Tick {
    /// Draw the title, so many seconds in, shown for so many seconds in all.
    Title { elapsed: f64, seconds: f64 },
    /// Run the tracker as ever.
    Tracker,
    /// Open Arrange and play the song now.
    Start,
    /// Quit.
    Quit,
}

/// A launch as it runs.
pub struct Running {
    launch: Launch,
    began: Instant,
    phase: Phase,
    heard_playing: bool,
    lead_out: Duration,
}

impl Running {
    /// A launch beginning now: on its opening title when it records, else running.
    pub fn new(launch: Launch) -> Running {
        let now = Instant::now();
        let phase = if launch.for_recording { Phase::Opening(now) } else { Phase::Running };
        Running {
            launch,
            began: now,
            phase,
            heard_playing: false,
            lead_out: LEAD_OUT,
        }
    }

    /// What to do now, from whether the song plays and whether Arrange is still the page showing.
    pub fn tick(&mut self, playing: bool, on_arrange: bool) -> Tick {
        let now = Instant::now();
        if let Some(most) = self.launch.max_seconds {
            if now.duration_since(self.began) >= Duration::from_secs_f64(most.max(0.0)) {
                return Tick::Quit;
            }
        }
        let splash = Duration::from_secs_f64(SPLASH_SECONDS);
        let title = |since: Instant| Tick::Title {
            elapsed: now.duration_since(since).as_secs_f64(),
            seconds: SPLASH_SECONDS,
        };
        match self.phase {
            Phase::Opening(since) if now.duration_since(since) < splash => title(since),
            Phase::Opening(_) => {
                self.phase = if self.launch.plays() { Phase::LeadIn(now) } else { Phase::Running };
                Tick::Start
            }
            Phase::LeadIn(since) if now.duration_since(since) < LEAD_IN => Tick::Tracker,
            Phase::LeadIn(_) => {
                self.phase = Phase::Running;
                Tick::Start
            }
            Phase::Running => self.running(now, playing, on_arrange),
            Phase::LeadOut(since) if now.duration_since(since) < self.lead_out => Tick::Tracker,
            Phase::LeadOut(_) if self.launch.for_recording => {
                self.phase = Phase::Closing(now);
                title(now)
            }
            Phase::LeadOut(_) => Tick::Quit,
            Phase::Closing(since) if now.duration_since(since) < splash => title(since),
            Phase::Closing(_) => {
                self.phase = Phase::Holding(now);
                Tick::Title {
                    elapsed: SPLASH_SECONDS,
                    seconds: SPLASH_SECONDS,
                }
            }
            Phase::Holding(since) if now.duration_since(since) < HOLD => Tick::Title {
                elapsed: SPLASH_SECONDS,
                seconds: SPLASH_SECONDS,
            },
            Phase::Holding(_) => Tick::Quit,
        }
    }

    /// While the tracker runs: the song is done once it has played and stopped, or, in an interactive take, once the page
    /// leaves Arrange; done, it rings out.
    fn running(&mut self, now: Instant, playing: bool, on_arrange: bool) -> Tick {
        if playing {
            self.heard_playing = true;
            return Tick::Tracker;
        }
        let ended = self.heard_playing || (self.launch.interactive && !on_arrange);
        if self.launch.quits_when_done() && ended {
            self.phase = Phase::LeadOut(now);
        }
        Tick::Tracker
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
        assert_eq!(running.tick(false, true), Tick::Tracker, "nothing has played yet");
        assert_eq!(running.tick(true, true), Tick::Tracker, "the song plays");
        assert_eq!(running.tick(false, true), Tick::Tracker, "the song has stopped and rings out");
        assert_eq!(running.tick(false, true), Tick::Quit, "its lead-out has passed");
    }

    /// A recording opens on the title, and an interactive one plays nothing by itself.
    #[test]
    fn a_recording_opens_on_the_title_and_an_interactive_one_waits_to_be_played() {
        let recording = Launch {
            for_recording: true,
            ..Launch::default()
        };
        assert!(matches!(Running::new(recording.clone()).tick(false, false), Tick::Title { .. }));
        assert!(recording.plays() && recording.opens_arrange());
        let interactive = Launch {
            for_recording: true,
            interactive: true,
            ..Launch::default()
        };
        assert!(!interactive.plays() && interactive.opens_arrange());
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
