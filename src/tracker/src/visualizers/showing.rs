// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A visualizer showing over Arrange's clip area: its mode, when it began, when it last heard the notes, and the mode's
//! name, which shows for NAME_SECONDS each time it changes, by a key or by a mode of modes moving on.

use super::{made, Mode};
use crate::app::App;
use crate::text::Text;
use llamatron_names::words;
use std::time::{Duration, Instant};

/// How long a mode's name shows when it changes.
const NAME_SECONDS: f64 = 8.0;
/// How often the page draws a frame while the visualizer shows.
pub const FRAME_INTERVAL: Duration = Duration::from_millis(50);
/// A name is shown with a space either side, in reverse video.
const NAME_STYLE: &str = words::REVERSE;
const NAME_PADDING: &str = " ";

/// A visualizer showing: its mode, and what it needs to draw each frame.
pub struct Showing {
    mode: Box<dyn Mode>,
    began: Instant,
    /// The player's clock when the mode last heard the notes, so that each frame hears what started since.
    heard_since: Option<f64>,
    /// The name last shown, and since when.
    name: String,
    name_since: Instant,
}

impl Showing {
    /// A mode by its name in a set file, fresh, hidden naming the modes the set leaves out; None for a mode not built.
    pub fn of(option: &str, hidden: &[String]) -> Option<Showing> {
        let mode = made(option, hidden)?;
        let name = mode.shown_name();
        let now = Instant::now();
        Some(Showing {
            mode,
            began: now,
            heard_since: None,
            name,
            name_since: now,
        })
    }

    /// The mode's name in a set file.
    pub fn option(&self) -> &'static str {
        self.mode.option()
    }

    /// The lines of the frame for an area, from what the song playing has sounded since the last frame.
    pub fn frame(&mut self, app: &App, width: usize, height: usize) -> Vec<Text> {
        let (heard_at, heard) = app.transport.heard(&app.document, self.heard_since);
        self.heard_since = heard_at;
        let now = self.began.elapsed().as_secs_f64();
        self.mode.frame(width, height, now, &heard)
    }

    /// The mode's name to show now, in reverse video with a space either side, for NAME_SECONDS after it changes; None
    /// after that.
    pub fn name_to_show(&mut self) -> Option<Text> {
        let name = self.mode.shown_name();
        if name != self.name {
            self.name = name;
            self.name_since = Instant::now();
        }
        if self.name_since.elapsed().as_secs_f64() >= NAME_SECONDS {
            return None;
        }
        Some(Text::styled(&format!("{NAME_PADDING}{}{NAME_PADDING}", self.name), NAME_STYLE))
    }
}
