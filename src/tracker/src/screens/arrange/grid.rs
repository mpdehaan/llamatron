// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What Arrange's grid is drawn with (the Python forms/arrange.py, renderers/arrange.py, components/length_bar.py and
//! frame.py): pieces of text laid on a line's canvas at their columns, the dividers and rules of the grid, the play marks,
//! the bars as long as a scene or a clip plays, and the double-lined frame around what the cursor is on.

use crate::drawing::{BoxCharacters as Box, Canvas, Style};
use crate::text::Text;
use llamatron_strings::marks;

/// How a piece of text is drawn.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Plain,
    Name,
    Faint,
    Playing,
    Sounding,
    /// The word stock, for a cell whose details hold nothing of its own.
    Stock,
    /// A muted track's M, in the amber of a refusal, and a soloed track's S, in the green of a sounding track.
    Muted,
    Soloed,
}

impl Kind {
    pub fn style(self) -> &'static str {
        match self {
            Kind::Plain => Style::PLAIN,
            Kind::Name => Style::BOLD,
            Kind::Faint => Style::DIM,
            Kind::Playing => Style::PLAYING,
            Kind::Sounding => Style::SOUNDING,
            Kind::Muted => Style::REFUSAL,
            Kind::Soloed => Style::SOUNDING,
            Kind::Stock => Style::DETAILS_STOCK,
        }
    }
}

/// One thing a line of the grid holds.
#[derive(Clone)]
pub enum Piece {
    Text {
        column: usize,
        text: String,
        kind: Kind,
    },
    /// The grid's dividers: the scene column's double bar and a bar before each track, faint under a visualizer.
    Dividers {
        double_at: usize,
        columns: Vec<usize>,
        faint: bool,
    },
    /// A rule across the grid, crossing the dividers, to its end.
    Rule {
        end: usize,
        double_at: usize,
        crosses: Vec<usize>,
    },
    /// The mark that more tracks are off to the right.
    More {
        column: usize,
    },
    PlayButton {
        column: usize,
        playing: bool,
    },
    /// A line of details at a column in its style, cut to room when given, and in brackets when it is the one picked.
    Detail {
        column: usize,
        text: String,
        style: String,
        picked: bool,
        room: Option<usize>,
    },
}

/// What frame a cell has: the cursor's.
pub struct CellFrame {
    pub left: usize,
    pub right: usize,
    pub top: usize,
    pub inside: usize,
    pub style: &'static str,
}

/// The grid's lines drawn at a width, each piece where it goes and the frames over them.
pub fn arrange_lines(lines: &[Vec<Piece>], width: usize, frames: &[CellFrame]) -> Vec<Text> {
    let mut canvases: Vec<Canvas> = lines
        .iter()
        .map(|pieces| {
            let mut canvas = Canvas::new(width);
            for piece in pieces {
                draw_piece(&mut canvas, piece);
            }
            canvas
        })
        .collect();
    for frame in frames {
        draw_frame(&mut canvases, frame);
    }
    canvases.iter().map(Canvas::text).collect()
}

fn draw_piece(canvas: &mut Canvas, piece: &Piece) {
    match piece {
        Piece::Text { column, text, kind } => canvas.write(*column as i64, text, kind.style()),
        Piece::Dividers { double_at, columns, faint } => {
            let style = if *faint { Style::DIM } else { Style::DETAILS_DIVIDER };
            canvas.write(*double_at as i64, if *faint { Box::BAR } else { Box::DOUBLE_BAR }, style);
            for column in columns {
                canvas.write(*column as i64, Box::BAR, style);
            }
        }
        Piece::Rule { end, double_at, crosses } => {
            canvas.write(0, &Box::RULE.repeat(*end), Style::DETAILS_DIVIDER);
            canvas.write(*double_at as i64, Box::DOUBLE_CROSS, Style::DETAILS_DIVIDER);
            for column in crosses {
                canvas.write(*column as i64, Box::CROSS, Style::DETAILS_DIVIDER);
            }
            canvas.write(*end as i64, Box::RIGHT_TEE, Style::DETAILS_DIVIDER);
        }
        Piece::More { column } => canvas.write(*column as i64, Box::MORE, Style::DIM),
        Piece::Detail {
            column,
            text,
            style,
            picked,
            room,
        } => {
            let text = match room {
                Some(room) if text.chars().count() > *room => crate::drawing::fit(text, *room).trim_end().to_string(),
                _ => text.clone(),
            };
            canvas.write(*column as i64, &text, style);
            if *picked {
                canvas.write(*column as i64 - 1, marks::MSG_PICKED_OPEN, Style::BOLD);
                canvas.write((*column + text.chars().count()) as i64, marks::MSG_PICKED_CLOSE, Style::BOLD);
            }
        }
        Piece::PlayButton { column, playing } => {
            if *playing {
                canvas.write(*column as i64, marks::MSG_STOP_MARK, Style::PLAYING);
            } else {
                canvas.write(*column as i64, marks::MSG_PLAY_MARK, Style::DIM);
            }
        }
    }
}

fn draw_frame(canvases: &mut [Canvas], frame: &CellFrame) {
    let inner = frame.right - frame.left - 1;
    let (left, right) = (frame.left as i64, frame.right as i64);
    canvases[frame.top].write(
        left,
        &format!("{}{}{}", Box::DOUBLE_TOP_LEFT, Box::DOUBLE_RULE.repeat(inner), Box::DOUBLE_TOP_RIGHT),
        frame.style,
    );
    for line in canvases.iter_mut().skip(frame.top + 1).take(frame.inside) {
        line.write(left, Box::DOUBLE_BAR, frame.style);
        line.write(right, Box::DOUBLE_BAR, frame.style);
    }
    canvases[frame.top + 1 + frame.inside].write(
        left,
        &format!("{}{}{}", Box::DOUBLE_BOTTOM_LEFT, Box::DOUBLE_RULE.repeat(inner), Box::DOUBLE_BOTTOM_RIGHT),
        frame.style,
    );
}

const FULL_BLOCK: char = '█';
const HATCHING: char = '░';
/// What of a playing bar is still to play.
const TO_PLAY: char = '▒';
const PARTIAL_BLOCKS: [char; 7] = ['▏', '▎', '▍', '▌', '▋', '▊', '▉'];
const EIGHTHS: usize = 8;

/// A horizontal bar as long as a scene or a clip lasts against the longest, in eighths of a cell.
pub struct LengthBar {
    pub width: usize,
    pub hatched: bool,
}

impl LengthBar {
    pub fn full(&self) -> String {
        FULL_BLOCK.to_string().repeat(self.width)
    }

    pub fn draw(&self, amount: Option<f64>, total: Option<f64>) -> String {
        self.draw_played(amount, total, None)
    }

    /// The bar for an amount of a total; with played, the seconds of the amount played so far, a read head: full up to
    /// where play has reached, and the rest of the amount shaded, so that a playing bar fills from the left.
    pub fn draw_played(&self, amount: Option<f64>, total: Option<f64>, played: Option<f64>) -> String {
        let (Some(amount), Some(total)) = (amount, total) else {
            return " ".repeat(self.width);
        };
        if total == 0.0 {
            return " ".repeat(self.width);
        }
        let mut bar = self.filled(amount, total);
        if let Some(played) = played {
            let head = self.filled(played.max(0.0).min(amount), total);
            let shaded = bar.chars().count() - head.chars().count();
            bar = format!("{head}{}", TO_PLAY.to_string().repeat(shaded));
        }
        let filled = bar.chars().count();
        let rest = if self.hatched { HATCHING } else { ' ' };
        bar.push_str(&rest.to_string().repeat(self.width - filled));
        bar
    }

    /// The blocks for an amount of the total, the last one partial.
    fn filled(&self, amount: f64, total: f64) -> String {
        let eighths = ((amount * self.width as f64 * EIGHTHS as f64 / total).round_ties_even() as usize).min(self.width * EIGHTHS);
        let (whole, part) = (eighths / EIGHTHS, eighths % EIGHTHS);
        let mut bar = FULL_BLOCK.to_string().repeat(whole);
        if part > 0 {
            bar.push(PARTIAL_BLOCKS[part - 1]);
        }
        bar
    }
}
