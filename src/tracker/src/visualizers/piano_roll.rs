// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The piano roll: the notes as bars rolling in from the right, to give a feel for what the song is doing.
//!
//! Every key of the piano has a row, one half step each, with a line along each C, labelled at the left. A note comes in
//! at the right edge as it starts and rolls off to the left; while it sounds its bar keeps growing at the right, so a held
//! note looks long, and each bar's first cell is brighter. Each track has a bold colour of its own, given in the order the
//! tracks are first heard, and the legend across the top names the tracks with a note on the roll now. The rows stay still
//! while every pitch heard fits them, and otherwise ease slowly toward the notes that sound. Drum tracks have lanes of
//! their own at the bottom, where each hit is a short mark. The background is black.

use super::picture::Colour;
use super::{FrameClock, Hearing, Mode, REFERENCE_SECONDS_PER_BEAT};
use crate::text::Text;
use llamatron_model::schema::generated::file_format::LIVE_OCTAVE_OFFSET;
use llamatron_strings::texts::visualizers;

pub const OPTION: &str = "piano_roll";

/// How fast the notes roll, in columns a beat, so a sixteenth is one column.
const COLUMNS_PER_BEAT: f64 = 4.0;
/// The columns at the left for the octaves' and the lanes' labels, and the rows the legend takes.
const LABEL_COLUMNS: usize = 7;
const LEGEND_ROWS: usize = 1;
/// How fast the middle of the rows eases toward where it is wanted, as a share of the way a second, and where it starts.
const CENTRE_EASE_PER_SECOND: f64 = 0.2;
const START_CENTRE: f64 = 60.0;
const LOWEST_PITCH: i64 = 0;
const HIGHEST_PITCH: i64 = 127;
const HALF_STEPS_PER_OCTAVE: i64 = 12;
/// The colours: black behind everything, each track's bold colour on it in turn, the attack of a note this much nearer
/// white, the octave lines and labels dim.
const BLACK: Colour = [0, 0, 0];
const TRACK_COLOURS: [Colour; 10] = [
    [255, 64, 64],
    [255, 160, 0],
    [255, 224, 0],
    [64, 224, 96],
    [0, 208, 224],
    [64, 128, 255],
    [192, 96, 255],
    [255, 80, 176],
    [160, 255, 64],
    [255, 255, 255],
];
const ATTACK_WHITENING: f64 = 0.4;
const LINE_COLOUR: Colour = [70, 70, 90];
const LABEL_COLOUR: Colour = [140, 140, 160];
const LINE_CHARACTER: char = '─';
const SPACE: char = ' ';
/// Which drum lane each General MIDI drum note goes in, by its place in MSG_PIANO_ROLL_DRUM_LANES; any other goes in the
/// last.
const KICK_LANE: usize = 0;
const SNARE_LANE: usize = 1;
const HATS_LANE: usize = 2;
const TOMS_LANE: usize = 3;
const CYMBAL_LANE: usize = 4;
const OTHER_LANE: usize = 5;
const DRUM_LANES: [(i64, usize); 22] = [
    (35, KICK_LANE),
    (36, KICK_LANE),
    (37, SNARE_LANE),
    (38, SNARE_LANE),
    (39, SNARE_LANE),
    (40, SNARE_LANE),
    (42, HATS_LANE),
    (44, HATS_LANE),
    (46, HATS_LANE),
    (41, TOMS_LANE),
    (43, TOMS_LANE),
    (45, TOMS_LANE),
    (47, TOMS_LANE),
    (48, TOMS_LANE),
    (50, TOMS_LANE),
    (49, CYMBAL_LANE),
    (51, CYMBAL_LANE),
    (52, CYMBAL_LANE),
    (53, CYMBAL_LANE),
    (55, CYMBAL_LANE),
    (57, CYMBAL_LANE),
    (59, CYMBAL_LANE),
];

/// A colour that share of the way to white.
fn whitened(colour: Colour, share: f64) -> Colour {
    colour.map(|channel| (channel as f64 + (255 - channel) as f64 * share) as i32)
}

/// The lane a drum note goes in, counted from the bottom.
fn drum_lane(pitch: i64) -> usize {
    DRUM_LANES.iter().find(|(note, _)| *note == pitch).map_or(OTHER_LANE, |(_, lane)| *lane)
}

/// One cell of the roll: a character in a colour, and whether the colour fills the cell, as a note's bar does.
#[derive(Clone, Copy)]
struct Cell {
    character: char,
    colour: Colour,
    filled: bool,
}

const BLANK: Cell = Cell {
    character: SPACE,
    colour: BLACK,
    filled: false,
};

/// A note on the roll: its track's place, its pitch, whether it's a drum's, and when it started and ended, its end None
/// while it sounds.
struct RolledNote {
    track: usize,
    pitch: i64,
    drum: bool,
    start: f64,
    end: Option<f64>,
}

/// The notes as bars rolling in from the right, every key a row, each track in its colour, the drums in lanes at the
/// bottom.
pub struct PianoRoll {
    notes: Vec<RolledNote>,
    centre: f64,
    names: Vec<String>,
    /// The tracks heard so far, in the order they were first heard, which gives each its colour.
    heard_tracks: Vec<usize>,
    /// The lowest and highest pitch heard so far, drums apart, and whether the rows have been put on the first notes yet.
    lowest: Option<i64>,
    highest: Option<i64>,
    placed: bool,
    clock: FrameClock,
}

impl PianoRoll {
    pub fn new() -> PianoRoll {
        PianoRoll {
            notes: Vec::new(),
            centre: START_CENTRE,
            names: Vec::new(),
            heard_tracks: Vec::new(),
            lowest: None,
            highest: None,
            placed: false,
            clock: FrameClock::default(),
        }
    }

    /// A track's colour, by the order it was first heard in.
    fn track_colour(&self, track: usize) -> Colour {
        let place = self.heard_tracks.iter().position(|each| *each == track).unwrap_or(0);
        TRACK_COLOURS[place % TRACK_COLOURS.len()]
    }

    /// Start a note for each one heard starting, and end each that is no longer heard.
    fn hear(&mut self, heard: &Hearing, now: f64) {
        for note in self.notes.iter_mut().filter(|note| note.end.is_none()) {
            if !heard.notes.iter().any(|each| each.track == note.track && each.pitch == note.pitch) {
                note.end = Some(now);
            }
        }
        for note in heard.notes.iter().filter(|note| note.started) {
            for older in self.notes.iter_mut().filter(|older| older.end.is_none()) {
                if older.track == note.track && older.pitch == note.pitch {
                    older.end = Some(now);
                }
            }
            self.notes.push(RolledNote {
                track: note.track,
                pitch: note.pitch,
                drum: note.drum,
                start: now,
                end: None,
            });
            if !self.heard_tracks.contains(&note.track) {
                self.heard_tracks.push(note.track);
            }
            if !note.drum {
                self.lowest = Some(self.lowest.map_or(note.pitch, |lowest| lowest.min(note.pitch)));
                self.highest = Some(self.highest.map_or(note.pitch, |highest| highest.max(note.pitch)));
            }
        }
    }

    /// Keep the rows still where they can be: on the middle of every pitch heard while those fit the rows, otherwise easing
    /// slowly toward the middle of the notes that sound now; the first notes heard place the rows at once.
    fn follow(&mut self, elapsed: f64, pitch_rows: usize) {
        let (Some(lowest), Some(highest)) = (self.lowest, self.highest) else { return };
        let wanted = if ((highest - lowest) as usize) < pitch_rows {
            (lowest + highest) as f64 / 2.0
        } else {
            let sounding: Vec<i64> = self
                .notes
                .iter()
                .filter(|note| note.end.is_none() && !note.drum)
                .map(|note| note.pitch)
                .collect();
            if sounding.is_empty() {
                return;
            }
            sounding.iter().sum::<i64>() as f64 / sounding.len() as f64
        };
        if !self.placed {
            self.placed = true;
            self.centre = wanted;
            return;
        }
        self.centre += (wanted - self.centre) * (CENTRE_EASE_PER_SECOND * elapsed).min(1.0);
    }

    /// The row a note is drawn on: its pitch's below the legend, or its lane's among the drum rows at the bottom, or None
    /// off the rows shown.
    fn row_of(note: &RolledNote, top: i64, pitch_rows: usize, drums: bool) -> Option<usize> {
        let lanes = visualizers::MSG_PIANO_ROLL_DRUM_LANES.len();
        if note.drum {
            return drums.then(|| LEGEND_ROWS + pitch_rows + lanes - 1 - drum_lane(note.pitch));
        }
        let row = LEGEND_ROWS as i64 + top - note.pitch;
        (row >= LEGEND_ROWS as i64 && row < (LEGEND_ROWS + pitch_rows) as i64).then_some(row as usize)
    }

    /// Draw a line along each C with its label at the left, and the drum lanes' labels.
    fn draw_grid(cells: &mut [Vec<Cell>], top: i64, pitch_rows: usize, drums: bool) {
        let width = cells[0].len();
        for offset in 0..pitch_rows {
            let pitch = top - offset as i64;
            if pitch.rem_euclid(HALF_STEPS_PER_OCTAVE) != 0 {
                continue;
            }
            let octave = pitch.div_euclid(HALF_STEPS_PER_OCTAVE) - LIVE_OCTAVE_OFFSET;
            let label: Vec<char> = llamatron_strings::named(visualizers::MSG_PIANO_ROLL_OCTAVE_LABEL, &[("octave", octave.into())])
                .chars()
                .collect();
            for (column, cell) in cells[LEGEND_ROWS + offset].iter_mut().enumerate().take(width) {
                *cell = match label.get(column) {
                    Some(character) => Cell {
                        character: *character,
                        colour: LABEL_COLOUR,
                        filled: false,
                    },
                    None => Cell {
                        character: LINE_CHARACTER,
                        colour: LINE_COLOUR,
                        filled: false,
                    },
                };
            }
        }
        if drums {
            let lanes = visualizers::MSG_PIANO_ROLL_DRUM_LANES;
            for (lane, label) in lanes.iter().enumerate() {
                let row = LEGEND_ROWS + pitch_rows + lanes.len() - 1 - lane;
                for (column, character) in label.chars().take(LABEL_COLUMNS - 1).enumerate() {
                    cells[row][column] = Cell {
                        character,
                        colour: LABEL_COLOUR,
                        filled: false,
                    };
                }
            }
        }
    }

    /// Draw the name of each track with a note on the roll now, in its colour, across the top, in the song's order of the
    /// tracks, as far as they fit.
    fn draw_legend(&self, cells: &mut [Vec<Cell>], width: usize) {
        let mut tracks: Vec<usize> = self.notes.iter().map(|note| note.track).collect();
        tracks.sort_unstable();
        tracks.dedup();
        let mut column = LABEL_COLUMNS;
        for track in tracks {
            let Some(name) = self.names.get(track) else { continue };
            let text: Vec<char> = format!("{}{name}", visualizers::MSG_PIANO_ROLL_LEGEND_MARK).chars().collect();
            if column + text.len() > width {
                break;
            }
            let colour = self.track_colour(track);
            for (offset, character) in text.iter().enumerate() {
                cells[0][column + offset] = Cell {
                    character: *character,
                    colour,
                    filled: false,
                };
            }
            column += text.len() + visualizers::MSG_PIANO_ROLL_LEGEND_GAP.chars().count();
        }
    }

    /// A row of cells as text, each in its colour on black, a note's bar filling its cells with its colour.
    fn line(cells: &[Cell]) -> Text {
        let mut text = Text::default();
        let mut run = String::new();
        let mut style = String::new();
        for cell in cells {
            let [red, green, blue] = cell.colour;
            let cell_style = if cell.filled {
                format!("rgb({red},{green},{blue}) on rgb({red},{green},{blue})")
            } else {
                format!("rgb({red},{green},{blue}) on rgb(0,0,0)")
            };
            if cell_style != style && !run.is_empty() {
                text.append(&run, &style);
                run.clear();
            }
            style = cell_style;
            run.push(cell.character);
        }
        if !run.is_empty() {
            text.append(&run, &style);
        }
        text
    }
}

impl Default for PianoRoll {
    fn default() -> PianoRoll {
        PianoRoll::new()
    }
}

impl Mode for PianoRoll {
    fn option(&self) -> &'static str {
        OPTION
    }

    fn frame(&mut self, width: usize, height: usize, now: f64, heard: &Hearing) -> Vec<Text> {
        if width <= LABEL_COLUMNS || height <= LEGEND_ROWS {
            return Vec::new();
        }
        let elapsed = self.clock.seconds_since_last_frame(now);
        if !heard.names.is_empty() {
            self.names = heard.names.clone();
        }
        self.hear(heard, now);
        let seconds_per_beat = if heard.seconds_per_beat > 0.0 {
            heard.seconds_per_beat
        } else {
            REFERENCE_SECONDS_PER_BEAT
        };
        let columns_per_second = COLUMNS_PER_BEAT / seconds_per_beat;
        let oldest = now - (width - LABEL_COLUMNS) as f64 / columns_per_second;
        self.notes.retain(|note| note.end.is_none_or(|end| end >= oldest));
        let drums = self.notes.iter().any(|note| note.drum);
        let lanes = visualizers::MSG_PIANO_ROLL_DRUM_LANES.len();
        let pitch_rows = height.saturating_sub(LEGEND_ROWS + if drums { lanes } else { 0 });
        self.follow(elapsed, pitch_rows);
        let top = ((self.centre + pitch_rows as f64 / 2.0).round() as i64).clamp(LOWEST_PITCH + pitch_rows as i64 - 1, HIGHEST_PITCH);
        let mut cells = vec![vec![BLANK; width]; height];
        Self::draw_grid(&mut cells, top, pitch_rows, drums);
        let right = width - 1;
        for note in &self.notes {
            let Some(row) = Self::row_of(note, top, pitch_rows, drums) else { continue };
            let start = right as i64 - ((now - note.start) * columns_per_second) as i64;
            let end = note
                .end
                .map_or(right as i64, |end| right as i64 - ((now - end) * columns_per_second) as i64 - 1)
                .max(start);
            let colour = self.track_colour(note.track);
            for column in start.max(LABEL_COLUMNS as i64)..=end.min(right as i64) {
                let shade = if column == start { whitened(colour, ATTACK_WHITENING) } else { colour };
                cells[row][column as usize] = Cell {
                    character: SPACE,
                    colour: shade,
                    filled: true,
                };
            }
        }
        self.draw_legend(&mut cells, width);
        cells.iter().map(|row| Self::line(row)).collect()
    }
}
