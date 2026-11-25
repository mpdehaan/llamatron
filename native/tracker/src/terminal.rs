// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The tracker in a real terminal (what Textual's app does for the Python): the screen drawn in the alternate screen with
//! raw keys, each key pressed into the tracker by the name the pages bind, until the tracker quits. A panic puts the
//! terminal back before its message prints, so that a crash never leaves the shell garbled.

use crate::app::Tracker;
use crate::document::Document;
use crate::style::Style;
use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use crossterm::style::{Attribute, Color, Print, SetAttribute, SetBackgroundColor, SetForegroundColor};
use crossterm::terminal::{self, BeginSynchronizedUpdate, Clear, ClearType, EndSynchronizedUpdate, EnterAlternateScreen, LeaveAlternateScreen};
use crossterm::{cursor, queue};
use std::io::{self, Write};
use std::path::Path;

/// Open the tracker on a set's file, or on a new set where none is named, and run it until it quits.
pub fn run(path: Option<&Path>) -> Result<(), String> {
    let document = match path {
        Some(path) => Document::open(path).map_err(|error| format!("{}: {error}", path.display()))?,
        None => Document::new_set()?,
    };
    let mut tracker = Tracker::new(document);
    start_terminal()?;
    let finished = run_keys(&mut tracker);
    end_terminal();
    finished
}

/// Draw the screen, then press each key into the tracker, until it quits or Ctrl+C is pressed, which quits at once.
fn run_keys(tracker: &mut Tracker) -> Result<(), String> {
    let mut out = io::stdout();
    loop {
        let (width, height) = terminal::size().map_err(|error| error.to_string())?;
        draw(&mut out, tracker, width as usize, height as usize).map_err(|error| error.to_string())?;
        let Event::Key(pressed) = event::read().map_err(|error| error.to_string())? else {
            continue;
        };
        if pressed.kind != KeyEventKind::Press {
            continue;
        }
        let Some(name) = key_name(&pressed, tracker.top().takes_text()) else {
            continue;
        };
        if name == "ctrl+c" {
            return Ok(());
        }
        tracker.press(&name);
        if tracker.app.quitting {
            return Ok(());
        }
    }
}

/// Raw keys, the alternate screen and no cursor, with a panic hook that puts the terminal back first.
fn start_terminal() -> Result<(), String> {
    let earlier = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        end_terminal();
        earlier(info);
    }));
    terminal::enable_raw_mode().map_err(|error| error.to_string())?;
    let mut out = io::stdout();
    queue!(out, EnterAlternateScreen, cursor::Hide).map_err(|error| error.to_string())?;
    out.flush().map_err(|error| error.to_string())
}

/// Put the terminal back as the shell had it.
fn end_terminal() {
    let mut out = io::stdout();
    // The terminal is put back as well as it can be on the way out: a failure here has nowhere left to be reported.
    let _ = queue!(out, SetAttribute(Attribute::Reset), cursor::Show, LeaveAlternateScreen);
    let _ = out.flush();
    let _ = terminal::disable_raw_mode();
}

/// Draw the tracker's screen at a size, each piece in its style, in one update so that nothing flickers.
fn draw(out: &mut impl Write, tracker: &Tracker, width: usize, height: usize) -> io::Result<()> {
    queue!(out, BeginSynchronizedUpdate)?;
    for (row, line) in tracker.screen(width, height).into_iter().take(height).enumerate() {
        queue!(out, cursor::MoveTo(0, row as u16))?;
        for segment in line.segments() {
            write_styled(out, &segment.style)?;
            queue!(out, Print(segment.text))?;
        }
        queue!(out, SetAttribute(Attribute::Reset), Clear(ClearType::UntilNewLine))?;
    }
    queue!(out, Clear(ClearType::FromCursorDown), EndSynchronizedUpdate)?;
    out.flush()
}

/// Set the terminal to draw a piece in a style: its attributes, then its colour and its background.
fn write_styled(out: &mut impl Write, style: &Style) -> io::Result<()> {
    queue!(out, SetAttribute(Attribute::Reset))?;
    let attributes = [
        ("bold", Attribute::Bold),
        ("dim", Attribute::Dim),
        ("italic", Attribute::Italic),
        ("underline", Attribute::Underlined),
        ("reverse", Attribute::Reverse),
        ("strike", Attribute::CrossedOut),
    ];
    for (name, attribute) in attributes {
        if style.is_on(name) {
            queue!(out, SetAttribute(attribute))?;
        }
    }
    if let Some(color) = style.color.as_deref().and_then(color_of) {
        queue!(out, SetForegroundColor(color))?;
    }
    if let Some(color) = style.bgcolor.as_deref().and_then(color_of) {
        queue!(out, SetBackgroundColor(color))?;
    }
    Ok(())
}

/// A colour as the pages name one: a name, #rrggbb or rgb(r,g,b), and default for the terminal's own.
fn color_of(name: &str) -> Option<Color> {
    if let Some(hex) = name.strip_prefix('#') {
        let part = |at: usize| u8::from_str_radix(hex.get(at..at + 2)?, 16).ok();
        return Some(Color::Rgb {
            r: part(0)?,
            g: part(2)?,
            b: part(4)?,
        });
    }
    if let Some(parts) = name.strip_prefix("rgb(").and_then(|rest| rest.strip_suffix(')')) {
        let numbers: Vec<u8> = parts.split(',').filter_map(|part| part.trim().parse().ok()).collect();
        if let [r, g, b] = numbers[..] {
            return Some(Color::Rgb { r, g, b });
        }
        return None;
    }
    let named = match name {
        "default" => Color::Reset,
        "black" => Color::Black,
        "red" => Color::DarkRed,
        "green" => Color::DarkGreen,
        "yellow" => Color::DarkYellow,
        "blue" => Color::DarkBlue,
        "magenta" => Color::DarkMagenta,
        "cyan" => Color::DarkCyan,
        "white" => Color::Grey,
        "bright_black" | "grey50" => Color::DarkGrey,
        "bright_red" => Color::Red,
        "bright_green" => Color::Green,
        "bright_yellow" => Color::Yellow,
        "bright_blue" => Color::Blue,
        "bright_magenta" => Color::Magenta,
        "bright_cyan" => Color::Cyan,
        "bright_white" => Color::White,
        _ => return None,
    };
    Some(named)
}

/// The name the pages bind a key by, as Textual names it: a letter as it is typed where the page takes text and in lower
/// case otherwise, since no key binds Shift, ctrl+ before a letter held with Control, and the other keys by their names.
fn key_name(pressed: &KeyEvent, takes_text: bool) -> Option<String> {
    let shift = pressed.modifiers.contains(KeyModifiers::SHIFT);
    let name = match pressed.code {
        KeyCode::Char(character) if pressed.modifiers.contains(KeyModifiers::CONTROL) => format!("ctrl+{}", character.to_ascii_lowercase()),
        KeyCode::Char(' ') => "space".to_string(),
        KeyCode::Char(character) if takes_text => character.to_string(),
        KeyCode::Char(character) => character.to_lowercase().to_string(),
        KeyCode::Enter => "enter".to_string(),
        KeyCode::Esc => "escape".to_string(),
        KeyCode::Backspace | KeyCode::Delete => "backspace".to_string(),
        KeyCode::Tab => "tab".to_string(),
        KeyCode::BackTab => "shift+tab".to_string(),
        KeyCode::Up if shift => "shift+up".to_string(),
        KeyCode::Down if shift => "shift+down".to_string(),
        KeyCode::Left if shift => "shift+left".to_string(),
        KeyCode::Right if shift => "shift+right".to_string(),
        KeyCode::Up => "up".to_string(),
        KeyCode::Down => "down".to_string(),
        KeyCode::Left => "left".to_string(),
        KeyCode::Right => "right".to_string(),
        KeyCode::Home => "home".to_string(),
        KeyCode::End => "end".to_string(),
        KeyCode::PageUp => "pageup".to_string(),
        KeyCode::PageDown => "pagedown".to_string(),
        KeyCode::F(number) => format!("f{number}"),
        _ => return None,
    };
    Some(name)
}
