// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The title on black: LLAMATRON in block letters, a scanner sweeping under it, and the address, all in blue and centred,
//! after the start page of a classic video game. A recording opens and closes on it.
//!
//! The letters come in riding sine waves and settle into the word; then a wide glow, the scanner, sweeps right and back
//! left under them, shaded through many tones of the blue, and is gone; the address shows two lines under the word. A title
//! shown for a set time fades to black over its last moments. The letters are drawn twice as wide where the screen has
//! room, since a terminal's cells are about twice as tall as they are wide.

use crate::text::Text;
use llamatron_strings::texts::about;
use std::f64::consts::{PI, TAU};

type Rgb = [f64; 3];

/// The colours, on black: the word, the address and the scanner's brightest.
const TITLE_BLUE: Rgb = [60.0, 120.0, 255.0];
const ADDRESS_BLUE: Rgb = [80.0, 120.0, 210.0];
const SCANNER_BLUE: Rgb = [110.0, 165.0, 255.0];
const ON_BLACK: &str = "on rgb(0,0,0)";
/// The letters: a blank column between two, each block twice as wide where the screen has room.
const LETTER_GAP: usize = 1;
const WIDE: usize = 2;
const NARROW: usize = 1;
const LETTER_ROWS: usize = 5;
/// The entrance: the letters fade in over FADE_IN_SECONDS and ride waves WAVE_ROWS high for WAVE_SECONDS, settling over
/// SETTLE_SECONDS.
const FADE_IN_SECONDS: f64 = 0.8;
const WAVE_ROWS: f64 = 3.0;
const WAVE_SECONDS: f64 = 1.6;
const SETTLE_SECONDS: f64 = 0.8;
const WAVES_PER_SECOND: f64 = 1.2;
/// The scanner, after the letters settle: a glow SCANNER_SHARE of the title wide each side of its middle, sweeping right
/// and back left over SCAN_SECONDS.
const SCAN_DELAY_SECONDS: f64 = 0.2;
const SCAN_SECONDS: f64 = 2.4;
const SCANNER_SHARE: f64 = 0.25;
/// The address fades in as the letters settle.
const ADDRESS_FADE_SECONDS: f64 = 0.6;
/// The lines under the word: a blank line, the scanner, a blank line, the address, and the start screen's prompt on the
/// sixth line under the address.
const SCANNER_ROW: usize = LETTER_ROWS + 1;
const ADDRESS_ROW: usize = SCANNER_ROW + 2;
const PROMPT_ROW: usize = ADDRESS_ROW + 6;
/// The prompt fades in once the scanner is gone, then pulses once every PULSE_SECONDS between its dimmest and its
/// brightest blue; at its dimmest it keeps PULSE_FLOOR of its level, and its letters reach full a little before its
/// colour does.
const PROMPT_FADE_SECONDS: f64 = 0.5;
const PULSE_SECONDS: f64 = 1.6;
const PULSE_FLOOR: f64 = 0.4;
const PROMPT_LETTERS_LEAD: f64 = 2.5;
const PROMPT_DIM: Rgb = [40.0, 80.0, 170.0];
const PROMPT_BRIGHT: Rgb = [110.0, 160.0, 255.0];
/// A title shown for a set time fades to black over its last FADE_OUT_SECONDS.
const FADE_OUT_SECONDS: f64 = 0.8;
/// Levels are kept to this many steps, so that runs of one shade are long.
const LEVEL_STEPS: f64 = 64.0;
const SPACE: char = ' ';

/// A share from 0 to 1 eased by a cosine, so that a fade or a settling starts and ends gently.
fn eased(share: f64) -> f64 {
    (1.0 - (share.clamp(0.0, 1.0) * PI).cos()) / 2.0
}

fn settled_at() -> f64 {
    WAVE_SECONDS + SETTLE_SECONDS
}

fn scan_start() -> f64 {
    settled_at() + SCAN_DELAY_SECONDS
}

fn scan_end() -> f64 {
    scan_start() + SCAN_SECONDS
}

/// A letter's rows drawn scale columns to a block.
fn scaled_letter(letter: char, scale: usize) -> Vec<String> {
    let rows = about::MSG_BLOCK_LETTERS
        .iter()
        .find(|(found, _)| found.starts_with(letter))
        .map_or(&[][..], |(_, rows)| *rows);
    rows.iter()
        .map(|row| row.chars().map(|character| character.to_string().repeat(scale)).collect())
        .collect()
}

/// How many columns a word takes at a scale.
fn words_width(word: &str, scale: usize) -> usize {
    let letters: usize = word
        .chars()
        .map(|letter| scaled_letter(letter, scale).first().map_or(0, |row| row.chars().count()))
        .sum();
    letters + LETTER_GAP * scale * word.chars().count().saturating_sub(1)
}

/// How many rows a letter is above or below its place in the word at a moment, riding its wave as it comes in.
fn wave_offset(elapsed: f64, place: usize, count: usize) -> i64 {
    if elapsed >= settled_at() {
        return 0;
    }
    let height = if elapsed <= WAVE_SECONDS {
        WAVE_ROWS
    } else {
        WAVE_ROWS * (1.0 - eased((elapsed - WAVE_SECONDS) / SETTLE_SECONDS))
    };
    (height * (TAU * (WAVES_PER_SECOND * elapsed + place as f64 / count as f64)).sin()).round() as i64
}

/// How bright the scanner is at a column of a title width columns wide at a moment: 0 outside the glow, 1 at its middle.
fn scanner_level(column: usize, width: usize, elapsed: f64) -> f64 {
    if !(scan_start()..scan_end()).contains(&elapsed) {
        return 0.0;
    }
    let half = (width as f64 * SCANNER_SHARE).max(1.0);
    let sweep = (elapsed - scan_start()) % SCAN_SECONDS / SCAN_SECONDS * 2.0;
    let share = if sweep < 1.0 { sweep } else { 2.0 - sweep };
    let middle = -half + share * (width as f64 + 2.0 * half);
    let distance = (column as f64 - middle).abs();
    if distance >= half {
        return 0.0;
    }
    (PI / 2.0 * distance / half).cos().powi(2)
}

/// How bright the start screen's prompt is at a moment: nothing until the scanner is gone, then fading in and pulsing.
fn prompt_level(elapsed: f64) -> f64 {
    let since = elapsed - scan_end();
    if since < 0.0 {
        return 0.0;
    }
    let pulse = (1.0 + (TAU * since / PULSE_SECONDS).cos()) / 2.0;
    eased(since / PROMPT_FADE_SECONDS) * (PULSE_FLOOR + (1.0 - PULSE_FLOOR) * pulse)
}

/// Whether the start screen's prompt has come in at a moment, after which ENTER starts.
pub fn prompt_shown(elapsed: f64) -> bool {
    elapsed >= scan_end()
}

/// How much of the title shows at a moment: all of it, or less over the last moments of a title shown for seconds.
fn fade_level(elapsed: f64, seconds: Option<f64>) -> f64 {
    seconds.map_or(1.0, |seconds| eased((seconds - elapsed) / FADE_OUT_SECONDS))
}

/// The style of a colour turned down to a level from 0 to 1, on black, its level kept to LEVEL_STEPS.
fn shaded(colour: Rgb, level: f64) -> String {
    let step = (level.clamp(0.0, 1.0) * LEVEL_STEPS).round() / LEVEL_STEPS;
    let [red, green, blue] = colour.map(|channel| (channel * step).round() as i64);
    format!("rgb({red},{green},{blue}) {ON_BLACK}")
}

/// One cell of the title: its character and its style, or None for black.
type Cell = Option<(char, String)>;

/// One line of the title from its cells, a run of one style at a time.
fn drawn_line(cells: &[Cell]) -> Text {
    let black = format!("default {ON_BLACK}");
    let mut line = Text::default();
    let mut run = String::new();
    let mut style: Option<String> = None;
    for cell in cells {
        let (character, cell_style) = match cell {
            Some((character, style)) => (*character, style.clone()),
            None => (SPACE, black.clone()),
        };
        if style.as_ref() != Some(&cell_style) && !run.is_empty() {
            line.append(&run, style.as_deref().unwrap_or(""));
            run.clear();
        }
        style = Some(cell_style);
        run.push(character);
    }
    if !run.is_empty() {
        line.append(&run, style.as_deref().unwrap_or(""));
    }
    line
}

/// A line with text centred in a colour at a level, black where there is no text.
fn centred_text(text: &str, width: usize, colour: Rgb, level: f64) -> Text {
    let mut cells: Vec<Cell> = vec![None; width];
    if level > 0.0 {
        let left = width.saturating_sub(text.chars().count()) / 2;
        let style = shaded(colour, level);
        for (offset, character) in text.chars().enumerate().take(width.saturating_sub(left)) {
            cells[left + offset] = Some((character, style.clone()));
        }
    }
    drawn_line(&cells)
}

/// The title's lines for a screen width by height at a moment, fading out over its last moments when it is shown for
/// seconds.
pub fn title_lines(width: usize, height: usize, elapsed: f64, seconds: Option<f64>) -> Vec<Text> {
    drawn_title(width, height, elapsed, seconds, false)
}

/// The start screen's lines: the title with "Press ENTER to Start" under it, pulsing once the scanner is gone, shown until
/// ENTER.
pub fn start_lines(width: usize, height: usize, elapsed: f64) -> Vec<Text> {
    drawn_title(width, height, elapsed, None, true)
}

/// The title's lines, with the start screen's prompt or without.
fn drawn_title(width: usize, height: usize, elapsed: f64, seconds: Option<f64>, prompt: bool) -> Vec<Text> {
    let word = about::MSG_SPLASH_WORD;
    let scale = if words_width(word, WIDE) <= width { WIDE } else { NARROW };
    let letters_width = words_width(word, scale);
    let left = width.saturating_sub(letters_width) / 2;
    let tall = if prompt { PROMPT_ROW } else { ADDRESS_ROW } + 1;
    let top = height.saturating_sub(tall) / 2;
    let fade = fade_level(elapsed, seconds);
    let letters_level = eased(elapsed / FADE_IN_SECONDS) * fade;
    let letter_style = shaded(TITLE_BLUE, letters_level);
    let mut cells: Vec<Vec<Cell>> = vec![vec![None; width]; height];
    let count = word.chars().count();
    let mut column = left;
    for (place, letter) in word.chars().enumerate() {
        let rows = scaled_letter(letter, scale);
        let lift = wave_offset(elapsed, place, count);
        for (row, text) in rows.iter().enumerate() {
            let line = top as i64 + row as i64 - lift;
            if line < 0 || line >= height as i64 {
                continue;
            }
            for (offset, character) in text.chars().enumerate() {
                if character != SPACE && column + offset < width {
                    cells[line as usize][column + offset] = Some((character, letter_style.clone()));
                }
            }
        }
        column += rows.first().map_or(0, |row| row.chars().count()) + LETTER_GAP * scale;
    }
    let scanner_line = top + SCANNER_ROW;
    let block = about::MSG_BLOCK.chars().next().unwrap_or(SPACE);
    if scanner_line < height {
        for offset in 0..letters_width {
            let level = scanner_level(offset, letters_width, elapsed);
            if level > 0.0 && left + offset < width {
                cells[scanner_line][left + offset] = Some((block, shaded(SCANNER_BLUE, level * fade)));
            }
        }
    }
    let mut lines: Vec<Text> = cells.iter().map(|row| drawn_line(row)).collect();
    let address_line = top + ADDRESS_ROW;
    if address_line < height {
        let level = eased((elapsed - settled_at()) / ADDRESS_FADE_SECONDS) * fade;
        lines[address_line] = centred_text(about::MSG_SPLASH_ADDRESS, width, ADDRESS_BLUE, level);
    }
    let prompt_line = top + PROMPT_ROW;
    if prompt && prompt_line < height {
        let level = prompt_level(elapsed);
        let colour: Rgb = std::array::from_fn(|channel| PROMPT_DIM[channel] + (PROMPT_BRIGHT[channel] - PROMPT_DIM[channel]) * level);
        lines[prompt_line] = centred_text(about::MSG_START_PROMPT, width, colour, (level * PROMPT_LETTERS_LEAD).min(1.0) * fade);
    }
    lines
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The title fills the screen it is drawn for, its letters settled once they have come in.
    #[test]
    fn the_title_fills_its_screen_once_settled() {
        let (width, height) = (100, 30);
        let settled = settled_at() + SCAN_SECONDS + 1.0;
        let lines = title_lines(width, height, settled, None);
        assert_eq!(lines.len(), height);
        assert!(lines.iter().all(|line| line.cell_len() == width));
        assert!(lines.iter().any(|line| line.text().contains(about::MSG_SPLASH_ADDRESS)));
    }

    /// The start screen shows the title with its prompt once the scanner is gone, and not before.
    #[test]
    fn the_start_screen_prompts_once_the_title_has_come_in() {
        let (width, height) = (100, 30);
        let shows = |elapsed: f64| {
            start_lines(width, height, elapsed)
                .iter()
                .any(|line| line.text().contains(about::MSG_START_PROMPT))
        };
        let early = settled_at();
        let settled = scan_end() + PROMPT_FADE_SECONDS;
        assert!(!prompt_shown(early) && !shows(early));
        assert!(prompt_shown(settled) && shows(settled));
    }
}
