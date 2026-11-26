// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Big pixels: a picture of colours, each pixel drawn two terminal columns wide and one row tall so that it comes out
//! square, as full blocks in its colour, and the modes that paint them.
//!
//! Runs of one colour along a line are one piece of text, since a frame draws thousands of pixels many times a second.

use super::{FrameClock, Hearing, Mode};
use crate::text::Text;

/// How many terminal columns and rows one big pixel takes: a terminal's cell is about twice as tall as it is wide.
pub const PIXEL_COLUMNS: usize = 2;
pub const PIXEL_ROWS: usize = 1;
const FULL_BLOCK: &str = "█";
const SPACE: &str = " ";

/// A colour as red, green and blue, each from 0 to 255 once limited; whole numbers, so that the modes' arithmetic on
/// fields of them stays exact and fast.
pub type Colour = [i32; 3];

/// A picture of rows by columns of colours, row by row.
#[derive(Clone, Debug, PartialEq)]
pub struct Picture {
    pub rows: usize,
    pub columns: usize,
    pub cells: Vec<Colour>,
}

impl Picture {
    /// A picture of one colour throughout.
    pub fn filled(rows: usize, columns: usize, colour: Colour) -> Picture {
        Picture {
            rows,
            columns,
            cells: vec![colour; rows * columns],
        }
    }

    pub fn get(&self, row: usize, column: usize) -> Colour {
        self.cells[row * self.columns + column]
    }

    /// The picture averaged down by a factor in each direction, every pixel the mean of the fine ones it covers.
    pub fn derezzed(&self, factor: usize) -> Picture {
        let rows = self.rows / factor;
        let columns = self.columns / factor;
        let count = (factor * factor) as i32;
        let mut cells = Vec::with_capacity(rows * columns);
        for row in 0..rows {
            for column in 0..columns {
                let mut sum = [0; 3];
                for down in 0..factor {
                    for across in 0..factor {
                        let fine = self.get(row * factor + down, column * factor + across);
                        for channel in 0..3 {
                            sum[channel] += fine[channel];
                        }
                    }
                }
                cells.push(sum.map(|channel| channel / count));
            }
        }
        Picture { rows, columns, cells }
    }

    /// The picture with every channel rounded down to a step of a power of two, so that runs of one colour are longer and
    /// the pixels read as a few clean colours.
    pub fn stepped(mut self, shift: u32) -> Picture {
        for cell in &mut self.cells {
            *cell = cell.map(|channel| (channel >> shift) << shift);
        }
        self
    }
}

/// How many big pixels fit an area of terminal columns and rows, as (columns, rows).
pub fn pixel_size(width: usize, height: usize) -> (usize, usize) {
    (width / PIXEL_COLUMNS, height / PIXEL_ROWS)
}

/// The style that draws a colour, on the terminal's own background.
pub fn colour_style(colour: Colour) -> String {
    let [red, green, blue] = colour.map(|channel| channel.clamp(0, 255));
    format!("rgb({red},{green},{blue})")
}

/// The text lines that draw a picture in an area width columns by height rows, any columns left over blank.
pub fn pixel_lines(picture: &Picture, width: usize, height: usize) -> Vec<Text> {
    let mut lines = Vec::new();
    for row in 0..picture.rows.min(height / PIXEL_ROWS) {
        let mut line = Text::default();
        let mut run: Option<(Colour, usize)> = None;
        for column in 0..picture.columns {
            let colour = picture.get(row, column);
            match &mut run {
                Some((held, length)) if *held == colour => *length += 1,
                _ => {
                    if let Some((held, length)) = run {
                        line.append(&FULL_BLOCK.repeat(length * PIXEL_COLUMNS), &colour_style(held));
                    }
                    run = Some((colour, 1));
                }
            }
        }
        if let Some((held, length)) = run {
            line.append(&FULL_BLOCK.repeat(length * PIXEL_COLUMNS), &colour_style(held));
        }
        let drawn = line.cell_len();
        if drawn < width {
            line.append(&SPACE.repeat(width - drawn), "");
        }
        for _ in 0..PIXEL_ROWS {
            lines.push(line.clone());
        }
    }
    lines
}

/// A mode that paints big pixels.
pub trait Painter {
    /// The mode's name in a set file.
    const OPTION: &'static str;

    /// Start again for an area of this many big pixels, columns by rows.
    fn resized(&mut self, columns: usize, rows: usize);

    /// The frame's big pixels, the seconds since the frame before and what it hears.
    fn pixels(&mut self, seconds: f64, heard: &Hearing) -> Picture;
}

/// A painting mode as the visualizer shows it: sized to its area, starting again when the area changes.
pub struct Painted<P: Painter> {
    painter: P,
    size: Option<(usize, usize)>,
    clock: FrameClock,
}

impl<P: Painter> Painted<P> {
    pub fn new(painter: P) -> Painted<P> {
        Painted {
            painter,
            size: None,
            clock: FrameClock::default(),
        }
    }
}

impl<P: Painter> Mode for Painted<P> {
    fn option(&self) -> &'static str {
        P::OPTION
    }

    fn frame(&mut self, width: usize, height: usize, now: f64, heard: &Hearing) -> Vec<Text> {
        let size = pixel_size(width, height);
        if size.0 == 0 || size.1 == 0 {
            return Vec::new();
        }
        if self.size != Some(size) {
            self.size = Some(size);
            self.painter.resized(size.0, size.1);
        }
        let seconds = self.clock.seconds_since_last_frame(now);
        let picture = self.painter.pixels(seconds, heard);
        pixel_lines(&picture, width, height)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A run of one colour is one piece of text, two columns a pixel, and the line is padded out to its width.
    #[test]
    fn a_picture_draws_as_runs_of_full_blocks() {
        let red: Colour = [200, 0, 0];
        let blue: Colour = [0, 0, 200];
        let mut picture = Picture::filled(1, 3, red);
        picture.cells[2] = blue;
        let width = 7;
        let lines = pixel_lines(&picture, width, 1);
        let segments = lines[0].segments();
        assert_eq!(segments[0].text, FULL_BLOCK.repeat(2 * PIXEL_COLUMNS));
        assert_eq!(segments[1].text, FULL_BLOCK.repeat(PIXEL_COLUMNS));
        assert_eq!(lines[0].cell_len(), width);
    }
}
