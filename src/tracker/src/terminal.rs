// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The tracker in a real terminal (what Textual's app does for the Python): the screen drawn in the alternate screen with
//! raw keys, each key pressed into the tracker by the name the pages bind, until the tracker quits. A panic puts the
//! terminal back before its message prints, so that a crash never leaves the shell garbled.

use crate::app::Tracker;
use crate::document::Document;
use crate::launch::{Launch, Running, Tick};
use crate::style::Style;
use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use crossterm::style::{Attribute, Color, Print, SetAttribute, SetBackgroundColor, SetForegroundColor};
use crossterm::terminal::{self, BeginSynchronizedUpdate, Clear, ClearType, EndSynchronizedUpdate, EnterAlternateScreen, LeaveAlternateScreen};
use crossterm::{cursor, queue};
use llamatron_strings::{messages, named};
use std::io::{self, Write};
use std::path::Path;

/// How long the loop waits for a key before planning real-time playback ahead and drawing again.
const TICK: std::time::Duration = std::time::Duration::from_millis(30);
/// The Arrange page's name, which a launch opens.
const ARRANGE_PAGE: &str = "ArrangePage";
/// How often the title is drawn while it shows, so that its letters move smoothly.
const TITLE_FRAME: std::time::Duration = std::time::Duration::from_millis(33);
/// How often the screen is drawn again while something plays, for its lights.
const LIGHTS: std::time::Duration = std::time::Duration::from_millis(100);

/// Open the tracker on a set's file, or on a new set where none is named, do what the launch asks, and run it until it
/// quits.
pub fn run(path: Option<&Path>, launch: Launch) -> Result<(), String> {
    let preferences = crate::preferences::Preferences::config_path()
        .map(|config| crate::preferences::Preferences::read(&config))
        .unwrap_or_default();
    let fluidsynth_installed = crate::wav::fluidsynth_installed();
    let instrument = |drum: bool| crate::track_instrument::for_new_track(&preferences, fluidsynth_installed, drum);
    let opened = match path {
        Some(path) => Some(Document::open_corrected(path).map_err(|error| format!("{}: {error}", path.display()))?),
        None => None,
    };
    // A set whose file's values had to be corrected opens only once the Corrections dialog is answered YES, over a new set.
    let (document, offered) = match opened {
        Some((document, corrections)) if corrections.is_empty() => (document, None),
        Some((document, corrections)) => (Document::new_set(instrument(false), instrument(true))?, Some((document, corrections))),
        None => (Document::new_set(instrument(false), instrument(true))?, None),
    };
    if launch.for_recording && !launch.interactive {
        refuse_endless(&document)?;
    }
    let mut tracker = Tracker::new(document);
    tracker.app.fluidsynth_installed = fluidsynth_installed;
    tracker.app.preferences = preferences;
    match offered {
        Some((document, corrections)) => crate::screens::set::open_page::offer_corrected(&mut tracker.app, document, &corrections),
        // A tracker playing on its own is never stopped by the warning's dialog.
        None if path.is_some() && !launch.opens_arrange() => crate::silent_instruments::warn_of_silent_instruments(&mut tracker.app),
        None => {}
    }
    start_terminal()?;
    tracker.app.session.recording = launch.for_recording;
    // A recording opens on its title, and opens Arrange when the launch says to start; any other launch starts at once.
    if !launch.for_recording {
        start(&mut tracker, &launch);
    }
    let mut running = Running::new(launch.clone());
    let finished = run_keys(&mut tracker, &mut running, &launch);
    tracker.app.transport.close();
    tracker.app.preview.close();
    end_terminal();
    finished
}

/// Refuse a recording of a song with a scene whose every clip loops: the song would wait there forever, and so would the
/// recording.
fn refuse_endless(document: &Document) -> Result<(), String> {
    let scenes: Vec<String> = document
        .song()
        .scenes()
        .iter()
        .enumerate()
        .filter(|(_, scene)| scene.every_clip_loops())
        .map(|(index, scene)| crate::screens::arrange::arrange_page::scene_name(scene, index))
        .collect();
    if scenes.is_empty() {
        return Ok(());
    }
    let listed = scenes.join(", ");
    Err(named(
        llamatron_strings::errors::ERR_RECORDING_SONG_LOOPS,
        &[("scenes", listed.as_str().into())],
    ))
}

/// Do what a launch asks once the tracker is open: open Arrange, with its details view or a visualizer mode showing,
/// then play the song from the top when the launch plays and nothing plays yet.
fn start(tracker: &mut Tracker, launch: &Launch) {
    if !launch.opens_arrange() {
        return;
    }
    if tracker.top().name() != ARRANGE_PAGE {
        tracker.app.session.shows_arrange_details = launch.details;
        tracker.press(crate::keys::first_key(&crate::keybindings::MainPage::ARRANGE));
        if let Some(mode) = &launch.visualizer {
            tracker.top().launch_visualizer(&tracker.app, mode);
        }
    }
    if launch.plays() && !tracker.app.transport.is_playing() {
        let scene = named(messages::MSG_SCENE_NUMBER, &[("number", 1.into())]);
        let said = named(messages::MSG_PLAYING_FROM, &[("scene", scene.as_str().into())]);
        crate::screens::arrange::arrange_page::play_through(&mut tracker.app, &scene, &said, |app| app.transport.play_scene(&app.document, 0));
        tracker.settle();
    }
}

/// Draw the screen, then press each key into the tracker, until it quits, Ctrl+C is pressed, which quits at once, or the
/// launch says to. While the launch shows its title, the title is drawn in place of the pages and no key but Ctrl+C acts.
fn run_keys(tracker: &mut Tracker, running: &mut Running, launch: &Launch) -> Result<(), String> {
    let mut out = io::stdout();
    let mut changed = true;
    let mut drawn = std::time::Instant::now();
    loop {
        let playing = tracker.app.transport.is_playing() || tracker.app.preview.is_playing();
        let on_arrange = tracker.top().name() == ARRANGE_PAGE;
        let showing_title = match running.tick(playing, on_arrange) {
            Tick::Quit => return Ok(()),
            Tick::Start => {
                start(tracker, launch);
                changed = true;
                None
            }
            Tick::Title { elapsed, seconds } => Some((elapsed, seconds)),
            Tick::Tracker => None,
        };
        let (width, height) = terminal::size().map_err(|error| error.to_string())?;
        if let Some((elapsed, seconds)) = showing_title {
            if drawn.elapsed() >= TITLE_FRAME {
                let lines = crate::screens::title_card::title_lines(width as usize, height as usize, elapsed, Some(seconds));
                draw_lines(&mut out, lines, height as usize).map_err(|error| error.to_string())?;
                drawn = std::time::Instant::now();
            }
            changed = true;
        } else {
            // The screen is drawn after each key, and while something plays every LIGHTS so that its lights move, less
            // often than the ticks, which keep the player ahead; a page that animates, such as Arrange under a visualizer,
            // as often as it asks.
            let lights_due = playing && drawn.elapsed() >= LIGHTS;
            let frame_due = tracker.top().frame_interval().is_some_and(|interval| drawn.elapsed() >= interval);
            if changed || lights_due || frame_due {
                draw(&mut out, tracker, width as usize, height as usize).map_err(|error| error.to_string())?;
                changed = false;
                drawn = std::time::Instant::now();
            }
        }
        // While waiting for a key, real-time playback is planned ahead a tick at a time.
        // An edit made while something plays is heard once it settles; one that cannot be heard says why.
        let song_said = tracker.app.transport.tick(&tracker.app.document);
        let preview_said = tracker.app.preview.tick(&tracker.app.document);
        if let Some(said) = song_said.or(preview_said) {
            tracker.app.say(&said);
            changed = true;
        }
        if !event::poll(TICK).map_err(|error| error.to_string())? {
            continue;
        }
        changed = true;
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
        if showing_title.is_none() {
            tracker.press(&name);
        }
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
    draw_lines(out, tracker.screen(width, height), height)
}

/// Draw lines as the screen, each piece in its style, in one update so that nothing flickers.
fn draw_lines(out: &mut impl Write, lines: Vec<crate::text::Text>, height: usize) -> io::Result<()> {
    queue!(out, BeginSynchronizedUpdate)?;
    for (row, line) in lines.into_iter().take(height).enumerate() {
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
    // A numbered colour of the terminal's own palette, as Rich writes a dialog's colours.
    if let Some(number) = name.strip_prefix("color(").and_then(|rest| rest.strip_suffix(')')) {
        return number.trim().parse().ok().map(Color::AnsiValue);
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
