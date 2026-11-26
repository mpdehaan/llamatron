// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The visualizer: modes that draw a moving picture over Arrange's clip area while a song plays, from the notes they hear.
//!
//! Each mode draws a frame for an area of terminal columns and rows at a moment, in seconds since it began, from what it
//! hears that frame: the notes that just started and those still held, by their track's place, and the beat. Only notes
//! that have started are heard, so a mode never knows what is coming, and no MIDI is read back. Most modes paint big
//! pixels (`picture.rs`), two columns wide and one row tall; a few draw their own characters. Every mode keeps its picture
//! under a limiter (`colour.rs`), so that nothing ever strobes or flashes.

pub mod colour;
pub mod cycle;
pub mod fields;
pub mod lava_lamp;
pub mod picture;
pub mod plasma;
pub mod showing;
pub mod spectrum;
pub mod warp;

use crate::text::Text;

/// A song plays at 120 quarter notes a minute when nothing says otherwise, which is what motion is scaled against.
pub const REFERENCE_SECONDS_PER_BEAT: f64 = 0.5;
/// The longest a frame is taken to have lasted, in seconds, however late it comes, so that nothing jumps after a pause.
const LONGEST_FRAME_SECONDS: f64 = 0.2;
/// A note at full velocity.
pub const FULL_VELOCITY: f64 = 127.0;

/// A note heard this frame: its track's place in the song's order, its MIDI number, its velocity, whether it started this
/// frame, and whether its track is a drum's.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct HeardNote {
    pub track: usize,
    pub pitch: i64,
    pub velocity: i64,
    pub started: bool,
    pub drum: bool,
}

/// What a frame hears: its notes, the seconds a beat lasts now, how many beats the song has played, and the song's track
/// names by the places the notes give.
#[derive(Clone, Debug, PartialEq)]
pub struct Hearing {
    pub notes: Vec<HeardNote>,
    pub seconds_per_beat: f64,
    pub beats: f64,
    pub names: Vec<String>,
}

impl Hearing {
    /// What a frame hears when nothing plays: no notes, at the reference tempo, on no beat.
    pub fn silence() -> Hearing {
        Hearing {
            notes: Vec::new(),
            seconds_per_beat: REFERENCE_SECONDS_PER_BEAT,
            beats: 0.0,
            names: Vec::new(),
        }
    }

    /// How much faster than 120 quarter notes a minute the song goes, which scales a mode's motion.
    pub fn tempo_factor(&self) -> f64 {
        REFERENCE_SECONDS_PER_BEAT / self.seconds_per_beat
    }
}

/// The seconds from one frame to the next, as a mode's motion counts them.
#[derive(Default)]
pub struct FrameClock {
    last: Option<f64>,
}

impl FrameClock {
    /// The seconds since the frame before this one, none for the first and never more than LONGEST_FRAME_SECONDS, taking
    /// now as the last frame's moment: a frame that comes late moves the picture on as one long frame would and no further.
    pub fn seconds_since_last_frame(&mut self, now: f64) -> f64 {
        let seconds = self.last.map_or(0.0, |last| (now - last).clamp(0.0, LONGEST_FRAME_SECONDS));
        self.last = Some(now);
        seconds
    }
}

/// One mode of the visualizer.
pub trait Mode {
    /// The mode's name in a set file and on the command line, such as `lava_lamp`.
    fn option(&self) -> &'static str;

    /// The name of what the mode shows now, which the page shows for a while when it changes: the mode's own, or for a mode
    /// of modes, the one showing.
    fn shown_name(&self) -> String {
        crate::settings::mode_name(self.option())
    }

    /// The lines that draw the frame for an area width columns by height rows, at a moment in seconds, from what it hears;
    /// none for an area with no room.
    fn frame(&mut self, width: usize, height: usize, now: f64, heard: &Hearing) -> Vec<Text>;
}

/// The modes built so far, by their names in a set file.
const BUILT: [&str; 4] = [lava_lamp::OPTION, spectrum::OPTION, plasma::OPTION, cycle::OPTION];

/// The modes built so far, by their names in a set file, in the order the visualizer key steps through them, the mode of
/// modes last.
pub fn ported_modes() -> Vec<&'static str> {
    llamatron_model::schema::generated::file_format::VISUALIZER_NAMES
        .iter()
        .copied()
        .filter(|name| BUILT.contains(name))
        .collect()
}

/// A new mode by its name in a set file, hidden naming the modes the set leaves out, which only the mode of modes heeds;
/// None for a name no mode has, or one not built yet.
pub fn made(option: &str, hidden: &[String]) -> Option<Box<dyn Mode>> {
    let mode: Box<dyn Mode> = match option {
        lava_lamp::OPTION => Box::new(picture::Painted::new(lava_lamp::LavaLamp::new())),
        spectrum::OPTION => Box::new(spectrum::Spectrum::new()),
        plasma::OPTION => Box::new(picture::Painted::new(plasma::Plasma::new())),
        cycle::OPTION => Box::new(cycle::Cycle::new(hidden)),
        _ => return None,
    };
    Some(mode)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app::Tracker;
    use crate::keybindings::{ArrangePage as ArrangeKeys, MainPage as MainKeys};
    use crate::keys::first_key;

    /// What a frame hears while a bass note and a drum hit start, on two tracks.
    fn two_notes() -> Hearing {
        let (bass, drums) = (0, 1);
        let (low_note, kick, loud) = (40, 36, 110);
        Hearing {
            notes: vec![
                HeardNote {
                    track: bass,
                    pitch: low_note,
                    velocity: loud,
                    started: true,
                    drum: false,
                },
                HeardNote {
                    track: drums,
                    pitch: kick,
                    velocity: loud,
                    started: true,
                    drum: true,
                },
            ],
            seconds_per_beat: REFERENCE_SECONDS_PER_BEAT,
            beats: 0.0,
            names: vec!["bass".to_string(), "drums".to_string()],
        }
    }

    /// Every mode built draws a frame that fills its area, line for line and column for column, from the notes it hears.
    #[test]
    fn every_mode_fills_its_area_from_the_notes_heard() {
        let (width, height, frames, frame_seconds) = (40, 12, 5, 0.05);
        for option in ported_modes() {
            let mut mode = made(option, &[]).expect("a built mode is made");
            let mut lines = Vec::new();
            for frame in 0..frames {
                lines = mode.frame(width, height, frame as f64 * frame_seconds, &two_notes());
            }
            assert_eq!(lines.len(), height, "{option}");
            assert!(lines.iter().all(|line| line.cell_len() == width), "{option}");
        }
    }

    /// A set whose Real Time switch is on, of one song and one scene.
    const REAL_TIME_SET: &str = "real_time: true\nsongs:\n  - name: song\n    tracks: [{ name: lead }]\n    scenes: [{ name: one }]\n";

    /// On Arrange, Z shows the first mode, Z again the next, and ESC brings the clips back.
    #[test]
    fn the_visualizer_key_steps_through_the_modes_and_esc_brings_the_clips_back() {
        let setlist = llamatron_model::objects::setlist::Setlist::read_text(REAL_TIME_SET, None).expect("the scenario's set is valid");
        let mut tracker = Tracker::new(crate::document::Document::new(setlist, None));
        tracker.press(first_key(&MainKeys::ARRANGE));
        let shown = ported_modes();
        let shows_visualizer = |tracker: &Tracker| tracker.top().keys(&tracker.app).iter().any(|key| key.is(&ArrangeKeys::TO_CLIPS));
        tracker.press(first_key(&ArrangeKeys::VISUALIZER));
        assert!(shows_visualizer(&tracker), "the first mode shows");
        let screen = tracker.screen(80, 24);
        let first = crate::settings::mode_name(shown[0]);
        assert!(screen.iter().any(|line| line.text().contains(&first)), "its name shows");
        tracker.press(first_key(&ArrangeKeys::TO_CLIPS));
        assert!(!shows_visualizer(&tracker), "the clips are back");
    }
}
