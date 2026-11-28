// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron-compare: what llamatron makes of a set, printed for internal_tools/compare_llamatron.py to hold against
//! the retired Python program's answers, and the walks, screenshots and key map built on llamatron's own pages.
//!
//! `llamatron-compare load SET` prints the set file's data as JSON, as Python's json.dumps writes what PyYAML loaded;
//! `llamatron-compare layout SET` writes that data back as a set file, as the Python writer lays it out;
//! `llamatron-compare migrate SET` moves the data to today's layout, into the objects' layout and back, and writes it;
//! `llamatron-compare save SET` reads the set into objects and saves it, as the Python program saves a set.

use llamatron_model::file::data::{json_text, load, Data};
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_names::keys;
use llamatron_names::spec;
use llamatron_names::words;
use std::fmt::Write;
use std::process::ExitCode;

/// The made-up routes give every fourth track a built-in sound; an edited step's velocity; the steps the pattern
/// edits add; and how many times the tour presses a key in a row.
const SYNTH_EVERY: usize = 4;
const EDITED_VELOCITY: i128 = 100;
const ADDED_STEPS: i128 = 2;
const FOUR_TIMES: usize = 4;
const FIVE_TIMES: usize = 5;
const SIX_TIMES: usize = 6;

/// Data as Python's json.dumps writes it, with its default separators, keys in their order, every key made text.
fn json(data: &Data) -> String {
    match data {
        Data::Null => words::NULL.into(),
        Data::Bool(flag) => if *flag { words::TRUE } else { words::FALSE }.into(),
        Data::Whole(whole) => whole.to_string(),
        Data::Float(float) if float.is_nan() => "NaN".into(),
        Data::Float(float) if float.is_infinite() => if *float > 0.0 { "Infinity" } else { "-Infinity" }.into(),
        Data::Float(float) => llamatron_math::number::python_float_text(*float),
        Data::Text(text) => json_text(text),
        Data::List(items) => format!("[{}]", items.iter().map(json).collect::<Vec<_>>().join(", ")),
        Data::Map(pairs) => format!(
            "{{{}}}",
            pairs
                .iter()
                .map(|(key, value)| format!("{}: {}", json_key(key), json(value)))
                .collect::<Vec<_>>()
                .join(", ")
        ),
    }
}

/// A mapping's key as json.dumps writes one: text as it is, a number or flag as its text.
fn json_key(key: &Data) -> String {
    match key {
        Data::Text(text) => json_text(text),
        Data::Null => "\"null\"".into(),
        Data::Bool(flag) => format!("\"{}\"", if *flag { words::TRUE } else { words::FALSE }),
        Data::Whole(whole) => format!("\"{whole}\""),
        Data::Float(float) => format!("\"{}\"", llamatron_math::number::python_float_text(*float)),
        other => json(other),
    }
}

/// Put one set through one step, writing what the step prints into out and what went wrong into err; the code the step
/// ends with, 0 where it went well.
fn run_step(command: &str, path: &str, out: &mut String, err: &mut String) -> u8 {
    // A MIDI file is read as bytes by the step that imports it.
    let read = if path.ends_with(".mid") {
        Ok(String::new())
    } else {
        std::fs::read_to_string(path)
    };
    let text = match read {
        Ok(text) => text,
        Err(problem) => {
            let _ = writeln!(err, "{path}: {problem}");
            return 1;
        }
    };
    match command {
        words::LOAD => match load(&text) {
            Ok(data) => {
                let _ = writeln!(out, "{}", json(&data));
                0
            }
            Err(problem) => {
                let _ = writeln!(err, "{path}: {}", problem.0);
                1
            }
        },
        words::LAYOUT => match load(&text) {
            Ok(data) => {
                let _ = write!(out, "{}", llamatron_model::file::writing::dump_file_layout(&data));
                0
            }
            Err(problem) => {
                let _ = writeln!(err, "{path}: {}", problem.0);
                1
            }
        },
        words::MIGRATE => match load(&text) {
            Ok(data) => {
                let (moved, _) = llamatron_model::file::migrations::migrated(data);
                match llamatron_model::file::layout::as_object_layout(&moved) {
                    Ok(objects) => {
                        let file = llamatron_model::file::layout::as_file_layout(&objects);
                        let _ = write!(out, "{}", llamatron_model::file::writing::dump_file_layout(&file));
                        0
                    }
                    Err(problem) => {
                        let _ = writeln!(err, "{path}: {}: {}", problem.section, problem.problem.message);
                        1
                    }
                }
            }
            Err(problem) => {
                let _ = writeln!(err, "{path}: {}", problem.0);
                1
            }
        },
        words::PATTERN_EDITS => match llamatron_model::objects::setlist::Setlist::read_text(&text) {
            Ok(setlist) => {
                let _ = writeln!(out, "{}", pattern_edits_of(&setlist));
                0
            }
            Err(problem) => {
                let _ = writeln!(err, "{path}: {}", problem.message);
                1
            }
        },
        words::EDITS => match llamatron_model::objects::setlist::Setlist::read_text(&text) {
            Ok(setlist) => {
                let _ = writeln!(out, "{}", edits_of(&setlist));
                0
            }
            Err(problem) => {
                let _ = writeln!(err, "{path}: {}", problem.message);
                1
            }
        },
        words::SAVE => match llamatron_model::objects::setlist::Setlist::read_text(&text) {
            Ok(setlist) => {
                let file = llamatron_model::file::layout::as_file_layout(&setlist.to_data());
                let _ = write!(out, "{}", llamatron_model::file::writing::dump_file_layout(&file));
                0
            }
            Err(problem) => {
                let _ = writeln!(err, "{path}: {}", problem.message);
                1
            }
        },
        words::IMPORT => match imported(path, &text) {
            Ok(json) => {
                let _ = writeln!(out, "{json}");
                0
            }
            Err(problem) => {
                let _ = writeln!(err, "{path}: {problem}");
                1
            }
        },
        words::PLAYER => {
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    let _ = writeln!(err, "{path}: {}", problem.message);
                    return 1;
                }
            };
            match players(&setlist) {
                Ok(text) => {
                    let _ = writeln!(out, "{text}");
                    0
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    let _ = writeln!(err, "{path}: {problem}");
                    1
                }
            }
        }
        words::TIMELINE => {
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    let _ = writeln!(err, "{path}: {}", problem.message);
                    return 1;
                }
            };
            match timelines(&setlist) {
                Ok(text) => {
                    let _ = writeln!(out, "{text}");
                    0
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    let _ = writeln!(err, "{path}: {problem}");
                    1
                }
            }
        }
        file_format::OctaveLabels::LIVE | file_format::InstrumentKind::MIDI => {
            let stem = std::path::Path::new(path)
                .file_stem()
                .map(|stem| stem.to_string_lossy().to_string())
                .unwrap_or_default();
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    let _ = writeln!(err, "{path}: {}", problem.message);
                    return 1;
                }
            };
            let exported = if command == file_format::OctaveLabels::LIVE {
                exported_live(&setlist)
            } else {
                exported_midi(&setlist, &stem)
            };
            match exported {
                Ok(text) => {
                    let _ = writeln!(out, "{text}");
                    0
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    let _ = writeln!(err, "{path}: {problem}");
                    1
                }
            }
        }
        words::RENDER => {
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    let _ = writeln!(err, "{path}: {}", problem.message);
                    return 1;
                }
            };
            match rendered_songs(&setlist) {
                Ok(text) => {
                    let _ = writeln!(out, "{text}");
                    0
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    let _ = writeln!(err, "{path}: {problem}");
                    1
                }
            }
        }
        _ => {
            let _ = writeln!(err, "no step called ({command})");
            2
        }
    }
}

/// Answer step after step on one process, so that no set starts a program of its own: each line read is a step and a
/// set's path, separated by a tab, and each answer is its code, the lengths in bytes of what it printed and of what went
/// wrong, separated by tabs, on a line, then the two texts.
fn serve() -> ExitCode {
    use std::io::{BufRead, Write as _};
    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout().lock();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        let Some((command, path)) = line.split_once('\t') else { continue };
        let (mut out, mut err) = (String::new(), String::new());
        let code = run_step(command, path, &mut out, &mut err);
        let _ = write!(stdout, "{code}\t{}\t{}\n{out}{err}", out.len(), err.len());
        let _ = stdout.flush();
    }
    ExitCode::SUCCESS
}

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    if arguments.first().map(String::as_str) == Some(words::KEYMAP) {
        return keymap(arguments.get(1).map(String::as_str), arguments.get(2).map(String::as_str));
    }
    if arguments.first().map(String::as_str) == Some(words::EXPLORE) {
        return explore(arguments.get(1).map(String::as_str));
    }
    if arguments.first().map(String::as_str) == Some(words::SCREENSHOTS) {
        return screenshots(arguments.get(1).map(String::as_str));
    }
    if arguments.first().map(String::as_str) == Some(words::SERVE) {
        return serve();
    }
    let (Some(command), Some(path)) = (arguments.first(), arguments.get(1)) else {
        eprintln!("usage: llamatron-compare load SET");
        return ExitCode::from(2);
    };
    if command == words::SERVE {
        return serve();
    }
    if !matches!(command.as_str(), words::PLAY | words::WAV | words::SCREENS) {
        let (mut out, mut err) = (String::new(), String::new());
        let code = run_step(command, path, &mut out, &mut err);
        print!("{out}");
        eprint!("{err}");
        return ExitCode::from(code);
    }
    match command.as_str() {
        words::PLAY => {
            // The current song's first scene played in real time through its instruments for a few seconds, for checking
            // the sender with a loopback audio device (LLAMATRON_AUDIO_DEVICE) that a check records.
            let seconds: f64 = arguments.get(2).and_then(|text| text.parse().ok()).unwrap_or(3.0);
            let played = llamatron_tracker::document::Document::open(std::path::Path::new(path)).and_then(|document| {
                let mut transport = llamatron_tracker::realtime::transport::Transport::default();
                transport.play_scene(&document, 0)?;
                let started = std::time::Instant::now();
                while started.elapsed().as_secs_f64() < seconds {
                    transport.tick(&document);
                    std::thread::sleep(std::time::Duration::from_millis(30));
                }
                transport.close();
                Ok(())
            });
            match played {
                Ok(()) => ExitCode::SUCCESS,
                Err(problem) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        words::WAV => {
            // The set's current song exported to a WAV file, as Ctrl+X does, for checking the built-in synths and FluidSynth.
            let Some(out) = arguments.get(2) else {
                eprintln!("usage: llamatron-compare wav SET OUT.wav");
                return ExitCode::from(2);
            };
            let exported = llamatron_tracker::document::Document::open(std::path::Path::new(path)).and_then(|document| {
                let grid = llamatron_engine::realizer::SongRealizer::new(document.get_setlist(), document.song(), Some(RENDER_SEED))
                    .render()
                    .map_err(|problem| format!("{problem:?}"))?;
                llamatron_tracker::wav::export(&document, &grid, std::path::Path::new(out))
            });
            match exported {
                Ok(()) => ExitCode::SUCCESS,
                Err(problem) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        words::SCREENS => {
            let (Some(keys), Some(width), Some(height)) = (arguments.get(2), arguments.get(3), arguments.get(4)) else {
                eprintln!("usage: llamatron-compare screens SET KEYS WIDTH HEIGHT");
                return ExitCode::from(2);
            };
            match toured(path, keys, width.parse().unwrap_or(80), height.parse().unwrap_or(24)) {
                Ok(text) => {
                    println!("{text}");
                    ExitCode::SUCCESS
                }
                Err(problem) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        other => {
            eprintln!("llamatron-compare: a command it does not know: {other}");
            ExitCode::from(2)
        }
    }
}

/// The seed every comparison renders from, the harness's RENDER_SEED.
const RENDER_SEED: i64 = 1;

/// Every song of a set rendered from one seed, as the harness's rendered_text writes it: each scene, then each clip's length
/// and its notes, each start, end, MIDI number and velocity.
/// A route for every track, made up so that every kind of route is tried: three ports, channels in turn, a program on every
/// other track, a built-in sound on every fourth and a device's latency on every fifth.
fn made_up_routes(track_names: &[&str]) -> Vec<(String, llamatron_tracker::realtime::timeline::Route)> {
    track_names
        .iter()
        .enumerate()
        .map(|(place, name)| {
            let route = llamatron_tracker::realtime::timeline::Route {
                port: format!("port{}", place % 3),
                channel: (place % 16) as i64,
                program: (place % 2 == 1).then_some(place as i64),
                pan: None,
                keyswitches: true,
                sound: (place % SYNTH_EVERY == 0).then(|| words::SYNTH.to_string()),
                early: if place % 5 == 0 { 0.01 } else { 0.0 },
            };
            (name.to_string(), route)
        })
        .collect()
}

/// Whether an event is the song's tempo or playback starting or stopping, told to a built-in instrument for its
/// modulators beyond what the retired Python sent, and so left out of what the timeline and player steps hold to it.
fn is_tempo_message(event: &llamatron_tracker::realtime::timeline::Playing) -> bool {
    use llamatron_tracker::realtime::timeline::{CONTROL_CHANGE, PLAY_STARTED, PLAY_STOPPED, TEMPO_COARSE, TEMPO_FINE};
    let beyond_python = [TEMPO_COARSE, TEMPO_FINE, PLAY_STARTED, PLAY_STOPPED];
    event.kind == CONTROL_CHANGE && beyond_python.contains(&event.number)
}

/// A sender that writes down everything a player hands it, a line each, for the player step.
struct RecordingSender {
    lines: Vec<String>,
}

impl llamatron_tracker::realtime::player::Sender for RecordingSender {
    fn add(&mut self, events: Vec<llamatron_tracker::realtime::timeline::Playing>) {
        for event in events.into_iter().filter(|event| !is_tempo_message(event)) {
            self.lines.push(format!(
                "add {} {} {} {} {} {} {} {} {} {}",
                event.whole,
                llamatron_math::number::python_float_text(event.seconds),
                event.port,
                event.channel,
                event.kind,
                event.number,
                event.value,
                event.tag.scene,
                event.tag.track,
                event.tag.play
            ));
        }
    }

    fn forget(&mut self, tag: &llamatron_tracker::realtime::timeline::ClipTag, after: f64) {
        let after = if after == f64::NEG_INFINITY {
            "-inf".to_string()
        } else {
            llamatron_math::number::python_float_text(after)
        };
        self.lines.push(format!("forget {} {} {} {after}", tag.scene, tag.track, tag.play));
    }

    fn stop_tag(&mut self, tag: &llamatron_tracker::realtime::timeline::ClipTag) {
        self.lines.push(format!("stop {} {} {}", tag.scene, tag.track, tag.play));
    }

    fn stop_all(&mut self) {
        self.lines.push("stop all".to_string());
    }
}

/// The clock's step, and how the player step's scenario runs, as the Python's played_lines.
const PLAYER_STEP: f64 = 0.1;
const PLAYER_STEPS_PAST_THE_END: usize = 100;
const PLAYER_SCENARIO_STEPS: usize = 60;
const PLAYER_CLIP_STEP: usize = 10;
const PLAYER_STOP_STEP: usize = 20;

/// What the real-time player hands its sender for every song of a set, every track on a made-up route: played from the
/// top to its end on a clock stepped a tenth of a second at a time, then the second scene launched by hand, the first
/// track's first clip launched alone a second later and the second track stopped a second after that, for six seconds.
fn players(setlist: &llamatron_model::objects::setlist::Setlist) -> llamatron_engine::error::Rendered<String> {
    use llamatron_tracker::realtime::player::Player;
    let mut texts = Vec::new();
    for name in setlist.song_names() {
        let Some(song) = setlist.get_song(name) else { continue };
        texts.push(format!("song {name}"));
        let routes = made_up_routes(&song.get_track_names());
        let score = llamatron_tracker::realtime::score::Score::new(setlist, song, &routes, Some(RENDER_SEED))?;
        let steps = (score.song_seconds() / PLAYER_STEP) as usize + PLAYER_STEPS_PAST_THE_END;
        let scenes = score.scene_count();
        if scenes == 0 {
            texts.push("no scenes".to_string());
            continue;
        }
        let mut sender = RecordingSender { lines: Vec::new() };
        let mut player = Player::new(score, 0.0);
        let mut now = 0.0;
        player.play_song(&mut sender, now);
        for _ in 0..steps {
            if !player.is_playing(now) {
                break;
            }
            now += PLAYER_STEP;
            player.tick(&mut sender, now);
        }
        sender.lines.push(format!("ended {}", llamatron_math::number::python_float_text(now)));
        let tracks: Vec<String> = song.get_track_names().into_iter().map(str::to_string).collect();
        player.play_scene(&mut sender, now, 1.min(scenes.saturating_sub(1)));
        for step in 0..PLAYER_SCENARIO_STEPS {
            now += PLAYER_STEP;
            player.tick(&mut sender, now);
            if step == PLAYER_CLIP_STEP && !tracks.is_empty() {
                player.play_clips(&mut sender, now, 0, vec![tracks[0].clone()], false);
            }
            if step == PLAYER_STOP_STEP && tracks.len() > 1 {
                player.stop_clip(&mut sender, now, &tracks[1]);
            }
        }
        player.stop_all(&mut sender);
        texts.extend(sender.lines);
    }
    // The live edits play a copy of the set of their own, so that each song's edits start from the set as its file holds it.
    for name in setlist.song_names() {
        texts.push(format!("live {name}"));
        texts.extend(live_edit_lines(setlist, name)?);
    }
    Ok(texts.join("\n").trim_end_matches('\n').to_string())
}

/// What a player hands its sender for a song played from the top and edited while it plays, each edit's score rendered
/// afresh with the play's seed and taken at a live response of its own: two seconds in, the tempo set to LIVE_EDIT_TEMPO
/// at once; a second later a scene inserted at the top, at the next bar; a second later the last track removed, where
/// there are two or more, at the clip's restart; then two seconds more.
fn live_edit_lines(setlist: &llamatron_model::objects::setlist::Setlist, name: &str) -> llamatron_engine::error::Rendered<Vec<String>> {
    use llamatron_model::schema::generated::file_format::{Section, SongSetting};
    use llamatron_tracker::realtime::player::Player;
    use llamatron_tracker::realtime::score::Score;
    let mut document = llamatron_tracker::document::Document::new(setlist.clone(), None);
    document.select_song(name);
    let mut sender = RecordingSender { lines: Vec::new() };
    if document.song().scenes().is_empty() {
        return Ok(sender.lines);
    }
    let score_now = |document: &llamatron_tracker::document::Document| {
        let routes = made_up_routes(&document.song().get_track_names());
        Score::new(document.get_setlist(), document.song(), &routes, Some(RENDER_SEED))
    };
    let mut player = Player::new(score_now(&document)?, 0.0);
    let mut now = 0.0;
    player.play_song(&mut sender, now);
    let run = |player: &mut Player, sender: &mut RecordingSender, now: &mut f64, seconds: f64| {
        for _ in 0..(seconds / PLAYER_STEP).round() as usize {
            *now += PLAYER_STEP;
            player.tick(sender, *now);
        }
    };
    run(&mut player, &mut sender, &mut now, LIVE_EDIT_FIRST_SECONDS);
    let scenes = document.song().scenes().len();
    let tracks: Vec<String> = document.song().get_track_names().into_iter().map(str::to_string).collect();
    document.change_set(|setlist| {
        if let Some(llamatron_model::objects::setlist::Item::Song(song)) = setlist.get_item_mut(Section::SONGS, name) {
            song.set_written(SongSetting::TEMPO, Some(llamatron_model::file::data::Data::Whole(LIVE_EDIT_TEMPO)));
        }
    });
    sender.lines.push("edit asap".to_string());
    player.update_score(
        &mut sender,
        now,
        score_now(&document)?,
        file_format::LiveResponsiveness::ASAP,
        &|old| Some(old),
        &|old| Some(old.to_string()),
    );
    run(&mut player, &mut sender, &mut now, LIVE_EDIT_GAP_SECONDS);
    // Both programs check the edits as a person makes them; a refusal would show as a difference.
    let _ = document.add_scene(0, LIVE_EDIT_SCENE);
    sender.lines.push("edit next_bar".to_string());
    player.update_score(
        &mut sender,
        now,
        score_now(&document)?,
        file_format::LiveResponsiveness::NEXT_BAR,
        &|old| (old < scenes).then_some(old + 1),
        &|old| Some(old.to_string()),
    );
    run(&mut player, &mut sender, &mut now, LIVE_EDIT_GAP_SECONDS);
    if tracks.len() > 1 {
        let last = tracks[tracks.len() - 1].clone();
        let _ = document.delete_named(Section::TRACKS, &last);
        sender.lines.push("edit clip_restart".to_string());
        let gone = |old: &str| (old != last).then(|| old.to_string());
        player.update_score(
            &mut sender,
            now,
            score_now(&document)?,
            file_format::LiveResponsiveness::CLIP_RESTART,
            &|old| Some(old),
            &gone,
        );
    }
    run(&mut player, &mut sender, &mut now, LIVE_EDIT_LAST_SECONDS);
    player.stop_all(&mut sender);
    Ok(sender.lines)
}

const LIVE_EDIT_TEMPO: i128 = 150;
const LIVE_EDIT_SCENE: &str = words::LIVE_EDIT;
const LIVE_EDIT_FIRST_SECONDS: f64 = 2.0;
const LIVE_EDIT_GAP_SECONDS: f64 = 1.0;
const LIVE_EDIT_LAST_SECONDS: f64 = 2.0;

/// Every song of a set rendered from one seed and laid out as real-time playback's timeline, an event a line.
fn timelines(setlist: &llamatron_model::objects::setlist::Setlist) -> llamatron_engine::error::Rendered<String> {
    let mut texts = Vec::new();
    for name in setlist.song_names() {
        let Some(song) = setlist.get_song(name) else { continue };
        texts.push(format!("song {name}"));
        let grid = llamatron_engine::realizer::SongRealizer::new(setlist, song, Some(RENDER_SEED)).render()?;
        let routes = made_up_routes(&song.get_track_names());
        for event in llamatron_tracker::realtime::timeline::song_timeline(&grid, &routes)?
            .into_iter()
            .filter(|event| !is_tempo_message(event))
        {
            texts.push(format!(
                "{} {} {} {} {} {} {} {} {}",
                event.whole,
                llamatron_math::number::python_float_text(event.seconds),
                event.port,
                event.channel,
                event.kind,
                event.number,
                event.value,
                event.tag.scene,
                event.tag.track
            ));
        }
    }
    Ok(texts.join("\n").trim_end_matches('\n').to_string())
}

fn rendered_songs(setlist: &llamatron_model::objects::setlist::Setlist) -> llamatron_engine::error::Rendered<String> {
    let mut texts = Vec::new();
    for name in setlist.song_names() {
        let Some(song) = setlist.get_song(name) else { continue };
        texts.push(format!("song {name}"));
        let grid = llamatron_engine::realizer::SongRealizer::new(setlist, song, Some(RENDER_SEED)).render()?;
        let mut lines = Vec::new();
        for (place, row) in grid.rows.iter().enumerate() {
            let tempo = row.tempo.map(llamatron_math::number::python_float_text).unwrap_or("None".to_string());
            lines.push(format!("scene {place} tempo {tempo}"));
            for (time, tempo) in &row.tempo_changes {
                lines.push(format!("  tempo {time} {}", llamatron_math::number::python_float_text(*tempo)));
            }
            for track in &grid.tracks {
                let Some((_, clip)) = row.clips.iter().find(|(found, _)| found == track) else {
                    continue;
                };
                let (notes, length) = llamatron_engine::timing::timed_events(clip, clip.scale.as_ref())?;
                lines.push(format!("  {track} length {length}"));
                for note in notes {
                    lines.push(format!("    {} {} {} {}", note.start, note.end, note.midi_number, note.velocity));
                }
                for control in &clip.controls {
                    let slide = if control.slide { "True" } else { "False" };
                    lines.push(format!("    cc {} {} {} {slide}", control.time, control.number, control.value));
                }
            }
        }
        texts.push(lines.join("\n"));
    }
    Ok(texts.join("\n"))
}

/// Every MIDI file each song of a set exports from one seed, one line a file with its name and its SHA-512.
fn exported_midi(setlist: &llamatron_model::objects::setlist::Setlist, stem: &str) -> llamatron_engine::error::Rendered<String> {
    use llamatron_exporters::midi;
    let mut lines = Vec::new();
    for name in setlist.song_names() {
        let Some(song) = setlist.get_song(name) else { continue };
        let grid = llamatron_engine::realizer::SongRealizer::new(setlist, song, Some(RENDER_SEED)).render()?;
        let base = format!("{stem}_{name}");
        let mut files = midi::clip_tree(&grid, &base)?;
        files.push(midi::song_file(&grid, &base, false)?);
        files.extend(midi::stems(&grid, &base)?);
        files.push(midi::song_file(&grid, &base, true)?);
        for (filename, bytes) in files {
            let digest: String = llamatron_math::sha512::sha512(&bytes).iter().map(|byte| format!("{byte:02x}")).collect();
            lines.push(format!("{filename} {digest}"));
        }
    }
    Ok(lines.join("\n"))
}

/// Each song of a set as a Live set from one seed, the SHA-512 of its XML before it is zipped, or that it is refused.
fn exported_live(setlist: &llamatron_model::objects::setlist::Setlist) -> llamatron_engine::error::Rendered<String> {
    let mut lines = Vec::new();
    for name in setlist.song_names() {
        let Some(song) = setlist.get_song(name) else { continue };
        let grid = llamatron_engine::realizer::SongRealizer::new(setlist, song, Some(RENDER_SEED)).render()?;
        match llamatron_exporters::live::live_set(&grid, llamatron_exporters::live::DEFAULT_TEMPLATE) {
            Ok(xml) => {
                let digest: String = llamatron_math::sha512::sha512(&xml).iter().map(|byte| format!("{byte:02x}")).collect();
                lines.push(format!("{name} {digest}"));
            }
            Err(llamatron_engine::error::RenderError::Refused(_)) => lines.push(format!("{name} refused")),
        }
    }
    Ok(lines.join("\n"))
}

/// A new set, as the Python's Setlist.new() makes one.
const NEW_SET: &str = include_str!("../sets/new_set.yml");

/// Data as JSON, which the harness reads back as YAML.
fn json_written(data: &Data, out: &mut String) {
    match data {
        Data::Null => out.push_str(words::NULL),
        Data::Bool(value) => out.push_str(if *value { words::TRUE } else { words::FALSE }),
        Data::Whole(value) => out.push_str(&value.to_string()),
        Data::Float(value) => out.push_str(&llamatron_math::number::python_float_text(*value)),
        Data::Text(text) => {
            out.push('"');
            for character in text.chars() {
                match character {
                    '"' => out.push_str("\\\""),
                    '\\' => out.push_str("\\\\"),
                    '\n' => out.push_str("\\n"),
                    character if (character as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", character as u32)),
                    character => out.push(character),
                }
            }
            out.push('"');
        }
        Data::List(items) => {
            out.push('[');
            for (place, item) in items.iter().enumerate() {
                if place > 0 {
                    out.push_str(", ");
                }
                json_written(item, out);
            }
            out.push(']');
        }
        Data::Map(pairs) => {
            out.push('{');
            for (place, (key, value)) in pairs.iter().enumerate() {
                if place > 0 {
                    out.push_str(", ");
                }
                json_written(&Data::text(&key.python_str()), out);
                out.push_str(": ");
                json_written(value, out);
            }
            out.push('}');
        }
    }
}

/// What importing each MIDI file a path stands for into a new set makes, as JSON: the file itself, or each song of a set
/// as its whole-song MIDI export.
/// What the import dialog shows of one MIDI file under each of its choices changed in turn: what the file holds, and for
/// each choice the song's data and what the import makes and warns; and the import with unique names off into a set that
/// holds the file's song already, so that its patterns are shared.
fn import_choices(import: &llamatron_importers::import::MidiImport, name: &str, new_set: &llamatron_model::objects::setlist::Setlist) -> Result<Data, String> {
    use llamatron_importers::import::ImportChoices;
    let found = import.found();
    let shown = Data::List(vec![
        Data::Whole(found.tracks as i128),
        Data::Whole(found.bars as i128),
        found.time_signature.as_deref().map_or(Data::Null, Data::text),
        Data::text(&found.tempo.python_str()),
        Data::List(
            found
                .keys
                .iter()
                .map(|key| Data::text(&llamatron_importers::writing::default_scale_name(key)))
                .collect(),
        ),
    ]);
    let mut changes: Vec<ImportChoices> = Vec::new();
    let start = ImportChoices::named(name);
    changes.push(start.clone());
    changes.push(ImportChoices {
        chords: false,
        ..start.clone()
    });
    changes.push(ImportChoices {
        controls: false,
        ..start.clone()
    });
    changes.push(ImportChoices {
        longest_pattern: 8,
        ..start.clone()
    });
    changes.push(ImportChoices {
        longest_pattern: 128,
        ..start.clone()
    });
    changes.push(ImportChoices {
        step_size: Some(llamatron_math::Rational::new(1, 16)),
        ..start.clone()
    });
    changes.push(ImportChoices {
        step_size: Some(llamatron_math::Rational::new(1, 4)),
        ..start.clone()
    });
    let mut tried = Vec::new();
    for choices in &changes {
        let made = import.imported(new_set, choices);
        tried.push(Data::List(vec![
            made.song.song.clone(),
            Data::Whole(made.tracks as i128),
            Data::Whole(made.patterns as i128),
            Data::Whole(made.scenes as i128),
            Data::Whole(made.long_patterns as i128),
            Data::List(made.warnings.iter().map(|warning| Data::text(warning)).collect()),
            Data::text(&rational_text(made.step_size)),
            Data::Whole(made.song.shared as i128),
        ]));
    }
    let first = import.imported(new_set, &start);
    let holding = llamatron_importers::writing::add_imported(new_set, &first.song)?;
    let again = import.imported(
        &holding,
        &ImportChoices {
            unique_names: false,
            ..start.clone()
        },
    );
    let mut names: Vec<String> = holding.items(file_format::Section::PATTERNS).iter().map(|(name, _)| name.clone()).collect();
    names.sort();
    tried.push(Data::List(vec![
        Data::text(&again.song.name),
        again.song.song.clone(),
        Data::Whole(again.patterns as i128),
        Data::Whole(again.song.shared as i128),
        Data::List(names.iter().map(|name| Data::text(name)).collect()),
    ]));
    Ok(Data::Map(vec![
        (Data::text(words::FOUND), shown),
        (Data::text(words::TRIED), Data::List(tried)),
    ]))
}

fn imported(path: &str, text: &str) -> Result<String, String> {
    let file = std::path::Path::new(path);
    let stem = file.file_stem().map(|stem| stem.to_string_lossy().to_string()).unwrap_or_default();
    let mut inputs: Vec<(String, Vec<u8>)> = Vec::new();
    if path.ends_with(".mid") {
        inputs.push((stem, std::fs::read(file).map_err(|problem| problem.to_string())?));
    } else {
        let setlist = llamatron_model::objects::setlist::Setlist::read_text(text).map_err(|problem| problem.message)?;
        for name in setlist.song_names() {
            let Some(song) = setlist.get_song(name) else { continue };
            let grid = llamatron_engine::realizer::SongRealizer::new(&setlist, song, Some(RENDER_SEED))
                .render()
                .map_err(|problem| format!("{problem:?}"))?;
            let base = format!("{stem}_{name}");
            let (_, bytes) = llamatron_exporters::midi::song_file(&grid, &base, false).map_err(|problem| format!("{problem:?}"))?;
            inputs.push((base, bytes));
        }
    }
    let new_set = llamatron_model::objects::setlist::Setlist::read_text(NEW_SET).map_err(|problem| problem.message)?;
    let mut made = Vec::new();
    let first_input = inputs.first().cloned();
    for (name, bytes) in inputs {
        let entry = match llamatron_importers::import::imported(&bytes, &new_set, &name) {
            Err(_) => Data::Map(vec![(Data::text(words::REFUSED), Data::text(&name))]),
            Ok(song) => Data::Map(vec![
                (Data::text(file_format::FileLayout::NAME), Data::text(&song.name)),
                (Data::text(spec::SONG), song.song),
                (
                    Data::text(file_format::Section::PATTERNS),
                    Data::Map(song.patterns.into_iter().map(|(name, data)| (Data::text(&name), data)).collect()),
                ),
                (
                    Data::text(file_format::Section::SCALES),
                    Data::Map(song.scales.into_iter().map(|(name, data)| (Data::text(&name), data)).collect()),
                ),
                (
                    Data::text(file_format::Section::INSTRUMENTS),
                    Data::Map(song.instruments.into_iter().map(|(name, data)| (Data::text(&name), data)).collect()),
                ),
            ]),
        };
        made.push(entry);
    }
    if let Some((name, bytes)) = first_input {
        if let Ok(import) = llamatron_importers::import::MidiImport::new(&bytes) {
            made.push(import_choices(&import, &name, &new_set)?);
        }
    }
    let mut out = String::new();
    json_written(&Data::List(made), &mut out);
    Ok(out)
}

fn folder_of(path: &str) -> std::path::PathBuf {
    std::path::Path::new(path).parent().map(std::path::Path::to_path_buf).unwrap_or_default()
}

/// The screen tour played on a set: the keys file holds a line for each stop, its keys between tabs; the answer is every
/// stop's page and screen as JSON, the set's folder written as FOLDER, as the Python capture writes it.
fn toured(path: &str, keys: &str, width: usize, height: usize) -> Result<String, String> {
    let document = llamatron_tracker::document::Document::open(std::path::Path::new(path))?;
    let text = std::fs::read_to_string(keys).map_err(|problem| problem.to_string())?;
    let stops: Vec<llamatron_tracker::tour::TourStop> = text
        .lines()
        .map(|line| {
            let mut parts = line.split('\t');
            let stack = parts
                .next()
                .unwrap_or("")
                .split(',')
                .filter(|name| !name.is_empty())
                .map(str::to_string)
                .collect();
            let set = parts.next().filter(|name| !name.is_empty()).map(|name| folder_of(path).join(name));
            let dirty = parts.next() == Some("True");
            let song = parts.next().unwrap_or("").to_string();
            let open_types = parts
                .next()
                .unwrap_or("")
                .split(',')
                .filter(|kind| !kind.is_empty())
                .map(str::to_string)
                .collect();
            let keys = parts
                .filter(|key| !key.is_empty())
                .map(|key| {
                    let mut parts = key.split('\x1f');
                    let name = parts.next().unwrap_or("").to_string();
                    let stack = parts
                        .next()
                        .unwrap_or("")
                        .split(',')
                        .filter(|page| !page.is_empty())
                        .map(str::to_string)
                        .collect();
                    let set = match (parts.next(), parts.next(), parts.next()) {
                        (Some(file), Some(dirty), Some(song)) => Some((folder_of(path).join(file), dirty == "True", song.to_string())),
                        _ => None,
                    };
                    llamatron_tracker::tour::TourKey { key: name, stack, set }
                })
                .collect();
            llamatron_tracker::tour::TourStop {
                stack,
                set,
                dirty,
                song,
                open_types,
                keys,
            }
        })
        .collect();
    let mut tracker = llamatron_tracker::app::Tracker::new(document);
    // The folder by every name it goes by, the longer first, so that a resolved name such as /private/tmp is not left half
    // written.
    let parent = std::path::Path::new(path).parent().map(std::path::Path::to_path_buf).unwrap_or_default();
    let mut folders: Vec<String> = vec![parent.to_string_lossy().to_string()];
    if let Ok(resolved) = parent.canonicalize() {
        folders.push(resolved.to_string_lossy().to_string());
    }
    folders.retain(|folder| !folder.is_empty());
    folders.sort_by_key(|folder| std::cmp::Reverse(folder.len()));
    let mut out = String::from("[");
    let recorded = llamatron_tracker::tour::tour(&mut tracker, width, height, &stops)?;
    for (number, stop) in recorded.into_iter().enumerate() {
        if number > 0 {
            out.push(',');
        }
        out.push_str("{\"page\":");
        json_written(&Data::Text(stop.page), &mut out);
        out.push_str(",\"screen\":[");
        for (line_number, line) in stop.screen.iter().enumerate() {
            if line_number > 0 {
                out.push(',');
            }
            out.push('[');
            for (piece_number, (text, style)) in line.iter().enumerate() {
                if piece_number > 0 {
                    out.push(',');
                }
                out.push('[');
                let shown = folders.iter().fold(text.clone(), |shown, folder| shown.replace(folder.as_str(), "FOLDER"));
                json_written(&Data::Text(shown), &mut out);
                out.push(',');
                json_written(&Data::Text(style.clone()), &mut out);
                out.push(']');
            }
            out.push(']');
        }
        out.push_str("]}");
    }
    out.push(']');
    Ok(out)
}

/// What the note munges of the pattern_edits step are given, as the Python's: the step length long notes are divided by, how
/// often a step is cleared, and the scale and default octave a melody is inverted in.
const DIVIDED_STEP_PARTS: i128 = 16;
const EVERY_OTHER: i64 = 2;
const INVERTED_SCALE: i64 = 7;
const INVERTED_OCTAVE: i64 = 3;
/// The octave a step's chord tones are worked out in, as a step with none takes the default.
const TONES_OCTAVE: i64 = 3;

/// The sections whose first item the edits step renames, copies, deletes, moves and sorts, and what a renamed item's name adds.
const EDITED_SECTIONS: [&str; 15] = [
    "scales",
    "patterns",
    "instruments",
    "grooves",
    "chains",
    "arps",
    "chords",
    "drifts",
    "guitarifies",
    "hockets",
    "musicians",
    "phrasings",
    "shapes",
    "timings",
    "songs",
];
const RENAMED: &str = "-renamed";

/// A set's data after each edit of the first item of each section and of each song's first track, as JSON: renamed, copied,
/// deleted, moved down one and sorted, each on a fresh copy of the set.
fn edits_of(setlist: &llamatron_model::objects::setlist::Setlist) -> String {
    use llamatron_model::objects::edits::*;
    use llamatron_model::objects::naming::copy_name;
    let data = setlist.to_data();
    let generator_sections: Vec<&str> = llamatron_model::schema::generated::plugins::PLUGINS
        .iter()
        .map(|plugin| plugin.section)
        .chain([file_format::Section::CHAINS])
        .collect();
    let names_in = |section: &str| -> Vec<String> {
        data.get(section).and_then(Data::as_map).map_or(Vec::new(), |pairs| {
            pairs.iter().filter_map(|(name, _)| name.as_str().map(str::to_string)).collect()
        })
    };
    let every_generator: Vec<String> = generator_sections.iter().flat_map(|section| names_in(section)).collect();
    let mut results: Vec<Data> = Vec::new();
    let mut add = |kind: &str, place: &str, name: &str, edited: Data| {
        results.push(Data::List(vec![Data::text(kind), Data::text(place), Data::text(name), edited]));
    };
    let with_section = |section: &str, items: Option<Data>| -> Data {
        let mut edited = data.clone();
        if let (Data::Map(pairs), Some(items)) = (&mut edited, items) {
            if let Some(pair) = pairs.iter_mut().find(|(key, _)| key.as_str() == Some(section)) {
                pair.1 = items;
            }
        }
        edited
    };
    for section in EDITED_SECTIONS {
        let held = names_in(section);
        let Some(first) = held.first() else { continue };
        let taken = if generator_sections.contains(&section) {
            every_generator.clone()
        } else {
            held.clone()
        };
        let new = copy_name(first, &taken);
        add(
            words::RENAME,
            section,
            first,
            renamed_in_set(&data, section, first, &format!("{first}{RENAMED}")),
        );
        add(fill::COPY, section, first, copied_in_set(&data, section, first, &new));
        add(keys::DELETE, section, first, removed_from_set(&data, section, first));
        let items = data.get(section).cloned().unwrap_or(Data::Null);
        if held.len() > 1 {
            add(words::MOVE, section, first, with_section(section, moved_in_section(&items, 0, 1)));
        }
        add(words::SORT, section, first, with_section(section, Some(sorted_section(&items))));
    }
    for song in setlist.song_names() {
        let Some(tracks) = data
            .get(file_format::Section::SONGS)
            .and_then(|songs| songs.get(song))
            .and_then(|held| held.get(file_format::Section::TRACKS))
            .cloned()
        else {
            continue;
        };
        let names: Vec<String> = tracks.as_map().map_or(Vec::new(), |pairs| {
            pairs.iter().filter_map(|(name, _)| name.as_str().map(str::to_string)).collect()
        });
        let Some(first) = names.first() else { continue };
        let new = copy_name(first, &names);
        let with_tracks = |items: Option<Data>| -> Data {
            let mut edited = data.clone();
            if let (Some(items), Data::Map(pairs)) = (items, &mut edited) {
                if let Some((_, Data::Map(songs))) = pairs.iter_mut().find(|(key, _)| key.as_str() == Some(file_format::Section::SONGS)) {
                    if let Some((_, Data::Map(settings))) = songs.iter_mut().find(|(key, _)| key.as_str() == Some(song)) {
                        if let Some(pair) = settings.iter_mut().find(|(key, _)| key.as_str() == Some(file_format::Section::TRACKS)) {
                            pair.1 = items;
                        }
                    }
                }
            }
            edited
        };
        add(words::RENAME, song, first, renamed_track(&data, song, first, &format!("{first}{RENAMED}")));
        add(fill::COPY, song, first, copied_track(&data, song, first, &new));
        add(keys::DELETE, song, first, removed_track(&data, song, first));
        if names.len() > 1 {
            add(words::MOVE, song, first, with_tracks(moved_in_section(&tracks, 0, 1)));
        }
        add(words::SORT, song, first, with_tracks(Some(sorted_section(&tracks))));
        add(words::ADD_TRACK, song, ADDED, added_track(&data, song, ADDED, None, false, None));
        add(words::ADD_TRACK, song, ADDED, added_track(&data, song, ADDED, Some(0), false, None));
        add(words::FRACTURE, song, "", fractured(&data, song).0);
        let scenes = setlist.get_song(song).map_or(Vec::new(), |held| held.scenes().to_vec());
        let Some(scene) = scenes.first() else { continue };
        add(words::ADD_SCENE, song, ADDED, added_scene(&data, song, 0, ADDED));
        add(words::COPY_SCENE, song, ADDED, copied_scene(&data, song, 0, ADDED));
        add(words::REMOVE_SCENE, song, "", removed_scene(&data, song, 0));
        if let Some((track, _)) = scene.clip_slots().first() {
            add(words::REMOVE_CLIP, song, track, removed_clip(&data, song, 0, track));
        }
    }
    json(&Data::List(results))
}

/// The name the edits step gives a scene or a track it adds.
const ADDED: &str = words::ADDED;

/// How many of a set's patterns the pattern_edits step edits, and the direction and group it gives them.
const EDITED_PATTERNS: usize = 3;
const EDITED_DIRECTION: &str = file_format::Direction::PENDULUM;
const EDITED_GROUP: &str = words::EDITED;
const DRUM_DEGREE: &str = "C";

/// Each of a set's first patterns after each of the pattern_edits step's edits on a fresh copy, as JSON.
/// The seed every scene's written view is rendered from, so that both programs draw the same random parts.
const SCENE_VIEW_SEED: i64 = 7;

/// Every scene of the first song as Scene View shows it written: its notes, its length, the chord on each beat and the
/// values it plays with.
fn scene_views(setlist: &llamatron_model::objects::setlist::Setlist) -> Vec<Data> {
    use llamatron_tracker::scene_notes::{chord_scale, effective_values, scene_notes};
    let mut results = Vec::new();
    let Some((song_name, _)) = setlist.items(file_format::Section::SONGS).first().cloned() else {
        return results;
    };
    let Some(song) = setlist.get_song(&song_name) else { return results };
    for index in 0..song.scenes().len() {
        let Some(effective) = effective_values(song, index) else { continue };
        let mut clip_scales = effective.clip_scales.clone();
        clip_scales.sort();
        let values = Data::List(vec![
            Data::text(&effective.tempo),
            Data::text(effective.tempo_source),
            Data::text(effective.scale.as_deref().unwrap_or("")),
            Data::text(effective.scale_source),
            Data::text(&effective.groove),
            Data::text(effective.groove_source),
            Data::List(
                clip_scales
                    .iter()
                    .map(|(track, scale)| Data::List(vec![Data::text(track), Data::text(scale)]))
                    .collect(),
            ),
        ]);
        let shown = match scene_notes(setlist, &song_name, index, true, Some(SCENE_VIEW_SEED)) {
            Err(_) => Data::List(vec![Data::text(words::REFUSED), values]),
            Ok(notes) => {
                let scale = effective.scale.as_deref().and_then(|name| chord_scale(setlist, name));
                let heard: Vec<llamatron_tracker::heard_chords::HeardNote> = notes
                    .notes
                    .iter()
                    .map(|note| llamatron_tracker::heard_chords::HeardNote {
                        start: note.start,
                        end: note.end,
                        pitch: note.pitch,
                        drum: note.drum,
                    })
                    .collect();
                let chords = llamatron_tracker::heard_chords::beat_chords(&heard, notes.length, notes.beat, scale.as_ref())
                    .into_iter()
                    .map(|chord| {
                        Data::List(vec![
                            Data::text(&rational_text(chord.start)),
                            Data::text(&chord.name),
                            Data::text(&chord.numeral),
                        ])
                    })
                    .collect();
                let mut rows: Vec<(usize, llamatron_math::Rational, llamatron_math::Rational, i64, bool, bool)> = notes
                    .notes
                    .iter()
                    .map(|note| (note.track, note.start, note.end, note.pitch, note.drum, note.marked))
                    .collect();
                rows.sort_by(|a, b| {
                    (a.0, rational_text(a.1), rational_text(a.2), a.3, a.4, a.5).cmp(&(b.0, rational_text(b.1), rational_text(b.2), b.3, b.4, b.5))
                });
                let shown = rows
                    .into_iter()
                    .map(|(track, start, end, pitch, drum, marked)| {
                        Data::List(vec![
                            Data::Whole(track as i128),
                            Data::text(&rational_text(start)),
                            Data::text(&rational_text(end)),
                            Data::Whole(pitch as i128),
                            Data::Bool(drum),
                            Data::Bool(marked),
                        ])
                    })
                    .collect();
                Data::List(vec![Data::List(shown), Data::text(&rational_text(notes.length)), Data::List(chords), values])
            }
        };
        results.push(Data::List(vec![Data::text(words::SCENE_VIEW), Data::text(&index.to_string()), shown]));
    }
    results
}

/// An exact number as Python's str of a Fraction writes it: a whole number, or a numerator over a denominator.
fn rational_text(value: llamatron_math::Rational) -> String {
    if value.denominator() == 1 {
        value.numerator().to_string()
    } else {
        format!("{}/{}", value.numerator(), value.denominator())
    }
}

fn pattern_edits_of(setlist: &llamatron_model::objects::setlist::Setlist) -> String {
    use llamatron_model::objects::pattern::Pattern;
    let mut results = Vec::new();
    // Every chord's name and numeral, each root with each chord a beat can be heard as, in the set's first scale and in none.
    let first_scale = setlist.items(file_format::Section::SCALES).first().and_then(|(scale, item)| match item {
        llamatron_model::objects::setlist::Item::Scale(held) => {
            llamatron_tracker::chord_text::ChordScale::new(&llamatron_tracker::patterns::scale_root(setlist, scale), held.get_kind().as_str()?)
        }
        _ => None,
    });
    let symbols: Vec<&str> = llamatron_engine::tables::FIXED_CHORDS
        .iter()
        .map(|(symbol, _)| *symbol)
        .filter(|symbol| !llamatron_model::schema::generated::file_format::INTERVAL_CHORDS.contains(symbol))
        .collect();
    for scale in first_scale.into_iter().map(Some).chain([None]) {
        let mut texts = Vec::new();
        for root in 0..12 {
            for symbol in &symbols {
                for bass in [None, Some((root + 4) % 12)] {
                    let (name, numeral) = llamatron_tracker::heard_chords::chord_texts(root, symbol, scale.as_ref(), bass);
                    texts.push(Data::List(vec![Data::text(&name), Data::text(&numeral)]));
                }
            }
        }
        results.push(Data::List(vec![Data::text(words::CHORD_TEXTS), Data::text(""), Data::List(texts)]));
    }
    results.extend(scene_views(setlist));
    for (name, item) in setlist.items(file_format::Section::PATTERNS).iter().take(EDITED_PATTERNS) {
        let llamatron_model::objects::setlist::Item::Pattern(original) = item else {
            continue;
        };
        let steps = original.get_steps() as usize;
        let middle = steps / 2;
        type Edit<'a> = (
            &'a str,
            Box<dyn Fn(&mut Pattern) -> Result<(), llamatron_model::schema::checking::InvalidValue> + 'a>,
        );
        let mut edits: Vec<Edit> = vec![
            (
                words::SET_VALUE,
                Box::new(|pattern| {
                    // A drum pattern's degree is a note letter.
                    let degree = if original.is_drum() { Data::text(DRUM_DEGREE) } else { Data::Whole(3) };
                    pattern.set_value(file_format::Row::DEGREE, 0, Some(degree))
                }),
            ),
            (
                words::SET_VALUE,
                Box::new(move |pattern| pattern.set_value(file_format::TrackSetting::VELOCITY, steps - 1, Some(Data::Whole(EDITED_VELOCITY)))),
            ),
            (words::CLEAR_SOUND, Box::new(|pattern| pattern.clear_sound(0))),
            (words::SET_STEPS, Box::new(move |pattern| pattern.set_steps(steps as i128 + ADDED_STEPS))),
            (words::INSERT_STEP, Box::new(|pattern| pattern.insert_step(0))),
            (words::INSERT_STEP, Box::new(move |pattern| pattern.insert_step(steps))),
            (
                words::SET_GROUP,
                Box::new(|pattern| {
                    pattern.set_group(Some(EDITED_GROUP));
                    Ok(())
                }),
            ),
            (
                words::SET_DIRECTION,
                Box::new(|pattern| {
                    pattern.set_direction(EDITED_DIRECTION);
                    Ok(())
                }),
            ),
            (words::REVERSE, Box::new(|pattern| pattern.reverse())),
            (words::ROLL, Box::new(|pattern| pattern.roll(1))),
            (words::ROLL, Box::new(|pattern| pattern.roll(-1))),
            (words::ROLL_THROUGH, Box::new(move |pattern| pattern.roll_through(middle))),
            (words::ROLL_FROM, Box::new(move |pattern| pattern.roll_from(middle))),
            (words::REVERSE_AFTER, Box::new(|pattern| pattern.reverse_after(0))),
            (words::REVERSE_BEFORE, Box::new(move |pattern| pattern.reverse_before(steps - 1))),
            (words::PIVOT_AROUND, Box::new(move |pattern| pattern.pivot_around(middle).map(|_| ()))),
            (words::REPEAT_AT_END, Box::new(move |pattern| pattern.repeat_at_end(0, steps - 1))),
            (words::REPEAT_AT_START, Box::new(|pattern| pattern.repeat_at_start(0, 0))),
            (
                words::CLEAR_ALL_BUT_PITCH,
                Box::new(|pattern| {
                    pattern.clear_all_but_pitch();
                    Ok(())
                }),
            ),
            (
                words::CLEAR_CHORDS,
                Box::new(|pattern| {
                    pattern.clear_chords();
                    Ok(())
                }),
            ),
            (
                words::CLEAR_STATEMENTS,
                Box::new(|pattern| {
                    pattern.clear_statements();
                    Ok(())
                }),
            ),
            (
                words::SMOOTH_CCS,
                Box::new(|pattern| {
                    pattern.smooth_ccs();
                    Ok(())
                }),
            ),
            (
                words::SMOOTH_VELOCITY,
                Box::new(|pattern| {
                    pattern.smooth_velocity();
                    Ok(())
                }),
            ),
            (words::MIRROR, Box::new(|pattern| pattern.mirror())),
            (words::INTERLEAVE, Box::new(|pattern| pattern.interleave(original))),
            (words::SPLICE, Box::new(|pattern| pattern.splice(original, Some(0)))),
            (words::SPLICE, Box::new(|pattern| pattern.splice(original, None))),
            (
                words::SET_DRUM,
                Box::new(|pattern| {
                    pattern.set_drum(!original.is_drum());
                    Ok(())
                }),
            ),
            (
                words::JOIN_REPEATED_NOTES,
                Box::new(|pattern| {
                    pattern.join_repeated_notes();
                    Ok(())
                }),
            ),
            (
                words::DIVIDE_LONG_NOTES,
                Box::new(|pattern| {
                    let covering = llamatron_tracker::patterns::covering_notes(pattern, llamatron_math::Rational::new(1, DIVIDED_STEP_PARTS));
                    pattern.divide_long_notes(&covering);
                    Ok(())
                }),
            ),
            (
                words::REVERSE_PITCHES,
                Box::new(|pattern| {
                    pattern.reverse_pitches();
                    Ok(())
                }),
            ),
            (words::CLEAR_EVERY, Box::new(|pattern| pattern.clear_every(EVERY_OTHER))),
            (
                words::INVERT_MELODY,
                Box::new(|pattern| pattern.invert_melody(0, INVERTED_SCALE, INVERTED_OCTAVE)),
            ),
        ];
        if steps > 1 {
            edits.push((words::SET_STEPS, Box::new(move |pattern| pattern.set_steps(steps as i128 - 1))));
            edits.push((words::REMOVE_STEP, Box::new(|pattern| pattern.remove_step(0))));
        }
        for (edit, change) in edits {
            let mut pattern = original.clone();
            let outcome = match change(&mut pattern) {
                Ok(()) => pattern.to_data(),
                Err(problem) => Data::text(&format!("refused: {}", problem.message)),
            };
            results.push(Data::List(vec![Data::text(edit), Data::text(name), outcome]));
        }
        // Every step's chord tones, in the set's first scale and with no scale known, as the roll draws them.
        let first_scale = setlist.items(file_format::Section::SCALES).first().and_then(|(scale, item)| match item {
            llamatron_model::objects::setlist::Item::Scale(held) => {
                llamatron_tracker::chord_text::ChordScale::new(&llamatron_tracker::patterns::scale_root(setlist, scale), held.get_kind().as_str()?)
            }
            _ => None,
        });
        let scales: Vec<Option<llamatron_tracker::chord_text::ChordScale>> = first_scale.into_iter().map(Some).chain([None]).collect();
        for scale in scales {
            let tones = (0..steps)
                .map(|step| {
                    let tones = llamatron_tracker::chord_tones::chord_tones(original, step, TONES_OCTAVE, scale.as_ref());
                    Data::List(
                        tones
                            .into_iter()
                            .map(|(degree, octave, accidental)| {
                                Data::List(vec![
                                    Data::Whole(degree as i128),
                                    Data::Whole(octave as i128),
                                    accidental.map_or(Data::Null, |accidental| Data::text(&accidental)),
                                ])
                            })
                            .collect(),
                    )
                })
                .collect();
            results.push(Data::List(vec![Data::text(words::CHORD_TONES), Data::text(name), Data::List(tones)]));
            if let Some(scale) = &scale {
                for octaves in [false, true] {
                    let mut pattern = original.clone();
                    let outcome = match llamatron_tracker::voice_leading::apply_voice_leading(&mut pattern, scale, TONES_OCTAVE, octaves) {
                        Ok(()) => pattern.to_data(),
                        Err(problem) => Data::text(&format!("refused: {}", problem.message)),
                    };
                    results.push(Data::List(vec![Data::text(words::APPLY_VOICE_LEADING), Data::text(name), outcome]));
                }
            }
        }
    }
    json(&Data::List(results))
}

/// The terminal the documents' screenshots show: wider than the 80 by 24 every page fits, so that Arrange shows more tracks
/// and a 16-step pattern fits in one block.
const SHOT_COLUMNS: usize = 112;
const SHOT_ROWS: usize = 32;
/// The name in the picture's title bar, and what the version is written as, so that a version bump alone changes no
/// screenshot.
const SHOT_TITLE: &str = file_format::OctaveLabels::LLAMATRON;
const VERSION_PLACEHOLDER: &str = "$VERSION";
/// The set most shots show, and the others' sets, from the top folder.
const SHOT_SET: &str = "examples/by_genre/electronic/minimal_techno.yml";
const ARP_SET: &str = "examples/learning/15_complex_gifts_chain.yml";
const SWELL_SET: &str = "examples/learning/14_bolero_swell.yml";
const PROGRESSION_SET: &str = "examples/learning/06_chord_progression_generator.yml";
const HOCKET_SET: &str = "examples/learning/17_hocket_shanty.yml";
const DRIFT_SET: &str = "examples/by_genre/rock/volcano.yml";
const DENSITY_SET: &str = "examples/by_genre/electronic/edm_density.yml";
const GLIDE_SET: &str = "examples/learning/12_acid_glide.yml";

/// One screenshot: its file's name, the set it shows, the keys that reach its screen from the main screen, and the place of
/// a settings page the cursor then goes to.
struct Shot {
    name: &'static str,
    set: &'static str,
    keys: Vec<String>,
    reach: Option<Reach>,
}

/// A place of a settings page a shot goes to, by what the page says the cursor is on.
#[derive(Clone, Copy)]
enum Reach {
    /// From the row of tabs, the tab whose first field is the one named.
    Tab(&'static str),
    /// Down the page, the field named.
    Field(&'static str),
}

/// The set of the built-in synths' screenshots: an instrument on each engine, and a lead using every part.
const SYNTH_SET: &str = "src/compare/sets/synths.yml";
/// The most tabs, or fields, a shot tries before it gives up on finding its place.
const MOST_TABS: usize = 16;
const MOST_FIELDS: usize = 40;
/// The first field of an instrument's Oscillators tab, which finds it.
const OSCILLATORS_FIELD: &str = "Osc Type";
/// The first fields of the Envelopes and Filter tabs.
const ENVELOPES_FIELD: &str = "Env 1 Type";
const FILTER_FIELD: &str = "Filter Type";

/// Turn a settings page, its cursor on the row of tabs, to the tab whose first field is the one named: Down goes into the
/// tab under the cursor and the page says which field it reached; Up comes back to the row and Right moves along it.
fn turn_to_tab(tracker: &mut llamatron_tracker::app::Tracker, first_field: &str) -> Result<(), String> {
    let press = |tracker: &mut llamatron_tracker::app::Tracker, key: &str| {
        tracker.press(&llamatron_tracker::keys::pressed_key(key));
        llamatron_tracker::tour::composed(tracker, SHOT_COLUMNS, SHOT_ROWS);
    };
    for _ in 0..MOST_TABS {
        press(tracker, keys::DOWN);
        let place = tracker.top().place_kind(&tracker.app);
        if place.trim() == first_field {
            return Ok(());
        }
        press(tracker, keys::UP);
        press(tracker, keys::RIGHT);
    }
    Err(format!("no tab starting with the field {first_field}"))
}

/// Move a settings page's cursor down until the page says it is on the field named.
fn go_to_field(tracker: &mut llamatron_tracker::app::Tracker, label: &str) -> Result<(), String> {
    for _ in 0..MOST_FIELDS {
        if tracker.top().place_kind(&tracker.app).trim() == label {
            return Ok(());
        }
        tracker.press(&llamatron_tracker::keys::pressed_key(keys::DOWN));
        llamatron_tracker::tour::composed(tracker, SHOT_COLUMNS, SHOT_ROWS);
    }
    Err(format!("no field {label}"))
}

/// Each of the documents' screenshots, as the retired tool took them; the song wizard's wait for the wizard.
fn shots() -> Vec<Shot> {
    let keys = |list: &[&str]| list.iter().map(|key| key.to_string()).collect::<Vec<String>>();
    let repeated = |key: &str, times: usize| vec![key.to_string(); times];
    let joined = |parts: Vec<Vec<String>>| parts.into_iter().flatten().collect::<Vec<String>>();
    // The bass line the pattern editor's shots show, found by the Patterns page's search.
    let to_bass_line = || {
        joined(vec![
            keys(&[words::P, "/"]),
            words::TUMBLE.chars().map(|c| c.to_string()).collect(),
            keys(&[keys::ENTER, keys::ENTER]),
        ])
    };
    // A generator opened from the Generators page by searching for its name, then Down past the names found before it that
    // hold the same text.
    let to_generator = |name: &str, before: usize| {
        joined(vec![
            keys(&[words::G, "/"]),
            name.chars().map(|c| if c == ' ' { keys::SPACE.to_string() } else { c.to_string() }).collect(),
            repeated(keys::DOWN, before),
            keys(&[keys::ENTER, keys::ENTER]),
        ])
    };
    let shot = |name: &'static str, set: &'static str, keys: Vec<String>| Shot { name, set, keys, reach: None };
    // An instrument of the synths' set found by the Instruments page's search and opened, its cursor then taken to the row
    // of tabs, and the tab whose first field is named turned to.
    let to_instrument = |instrument: &str| {
        joined(vec![
            keys(&[words::I, "/"]),
            instrument
                .chars()
                .map(|c| if c == ' ' { keys::SPACE.to_string() } else { c.to_string() })
                .collect(),
            keys(&[keys::ENTER, keys::ENTER]),
        ])
    };
    let synth = |name: &'static str, instrument: &str, first_field: &'static str| Shot {
        name,
        set: SYNTH_SET,
        keys: joined(vec![to_instrument(instrument), keys(&[keys::TAB])]),
        reach: Some(Reach::Tab(first_field)),
    };
    vec![
        shot(words::MAIN, SHOT_SET, vec![]),
        shot(words::FILE, SHOT_SET, keys(&[words::F])),
        shot(file_format::Section::SONGS, SHOT_SET, keys(&[words::S])),
        shot(spec::SONG, SHOT_SET, keys(&[words::S, keys::ENTER])),
        shot(file_format::Section::SCALES, SHOT_SET, keys(&[words::Z])),
        shot(file_format::SongSetting::SCALE, SHOT_SET, keys(&[words::Z, keys::ENTER])),
        shot(file_format::Section::PATTERNS, SHOT_SET, keys(&[words::P])),
        shot(words::PATTERN_EDITOR, SHOT_SET, to_bass_line()),
        shot(words::PATTERN_EDITOR_ROWS, SHOT_SET, joined(vec![to_bass_line(), keys(&[keys::TAB])])),
        // PgDn jumps from heading to heading; Space opens the fifth, Advanced, and Down goes to its first row.
        shot(
            words::PATTERN_EDITOR_ADVANCED,
            SHOT_SET,
            joined(vec![
                to_bass_line(),
                keys(&[keys::TAB]),
                repeated(keys::PAGEDOWN, FOUR_TIMES),
                keys(&[keys::SPACE, keys::DOWN]),
            ]),
        ),
        // The Chord section's Chord row opens the Chord Selector, where Right four times reaches the scales and Down and
        // ENTER open the flyout of Common.
        shot(
            words::CHORD_SELECTOR,
            SHOT_SET,
            joined(vec![
                to_bass_line(),
                keys(&[keys::TAB, keys::PAGEDOWN, keys::PAGEDOWN, keys::SPACE, keys::DOWN, keys::ENTER]),
                repeated(keys::RIGHT, FOUR_TIMES),
                keys(&[keys::DOWN, keys::ENTER]),
            ]),
        ),
        shot(
            words::PATTERN_EDITOR_CC,
            SHOT_SET,
            joined(vec![
                to_bass_line(),
                keys(&[keys::TAB]),
                repeated(keys::PAGEDOWN, FIVE_TIMES),
                keys(&[keys::SPACE, keys::DOWN]),
            ]),
        ),
        // Up from the first scene's name reaches Arrange's corner, and Right the first track's name.
        shot(words::TRACK_EDITOR, SHOT_SET, keys(&[keys::A, keys::UP, keys::RIGHT, keys::ENTER])),
        shot(file_format::FileLayout::GENERATORS, ARP_SET, keys(&[words::G])),
        shot(words::ARP_EDITOR, ARP_SET, to_generator(words::TRILL_IN_THIRDS, 0)),
        // Offsets is the sixth setting of an arpeggiator after its Name.
        shot(
            words::OFFSETS_EDITOR,
            ARP_SET,
            joined(vec![
                to_generator(words::TRILL_IN_THIRDS, 0),
                repeated(keys::DOWN, SIX_TIMES),
                keys(&[keys::ENTER]),
            ]),
        ),
        shot(words::CHAIN_EDITOR, ARP_SET, to_generator(words::SHRED, 1)),
        shot(file_format::Section::GROOVES, SHOT_SET, keys(&[words::V])),
        shot(words::GROOVE_EDITOR, SHOT_SET, keys(&[words::V, keys::DOWN, keys::DOWN, keys::ENTER])),
        shot(words::ARRANGE, SHOT_SET, keys(&[keys::A])),
        shot(words::ARRANGE_DETAILS, DRIFT_SET, keys(&[keys::A, keys::D])),
        shot(
            words::ARRANGE_DETAILS_LOCKED,
            DRIFT_SET,
            keys(&[keys::A, file_format::GateModifier::DOTTED, keys::RIGHT, keys::DOWN, keys::TAB]),
        ),
        shot(words::SCENE_VIEW, DENSITY_SET, keys(&[keys::A, words::P])),
        shot(words::SCENE_VIEW_PLAYED, DENSITY_SET, keys(&[keys::A, words::P, words::V])),
        shot(words::SCENE, SHOT_SET, keys(&[keys::A, keys::ENTER])),
        shot(words::CLIP, SHOT_SET, keys(&[keys::A, keys::RIGHT, keys::ENTER])),
        // The Scene page's Velocity tab, the second, and Shapes, the fourth, gone into with Down.
        shot(words::SCENE_SWELL, SWELL_SET, keys(&[keys::A, keys::ENTER, keys::TAB, keys::RIGHT, keys::DOWN])),
        shot(
            words::SCENE_DENSITY,
            DENSITY_SET,
            keys(&[keys::A, keys::ENTER, keys::TAB, keys::RIGHT, keys::RIGHT, keys::RIGHT, keys::DOWN]),
        ),
        shot(file_format::Section::INSTRUMENTS, SHOT_SET, keys(&[words::I])),
        shot(words::INSTRUMENT_EDITOR, SHOT_SET, keys(&[words::I, keys::ENTER])),
        // The instrument page with the cursor on Engine, the field that chooses a built-in synth.
        Shot {
            name: words::SYNTH_ENGINE_FIELD,
            set: SYNTH_SET,
            keys: to_instrument(file_format::OscillatorType::BASIC),
            reach: Some(Reach::Field("Engine")),
        },
        synth(words::SYNTH_BASIC, file_format::OscillatorType::BASIC, OSCILLATORS_FIELD),
        synth(words::SYNTH_SID, file_format::OscillatorType::SID, OSCILLATORS_FIELD),
        synth(words::SYNTH_POCKET, file_format::OscillatorType::POCKET, OSCILLATORS_FIELD),
        synth(words::SYNTH_OH3, file_format::SoundEngine::OH3, OSCILLATORS_FIELD),
        synth(words::SYNTH_ASHEVILLE, file_format::OscillatorType::ASHEVILLE, OSCILLATORS_FIELD),
        synth(words::SYNTH_MECHADRUM, words::MECHADRUM, OSCILLATORS_FIELD),
        synth(words::SYNTH_OSCILLATORS, "wobble lead", OSCILLATORS_FIELD),
        synth(words::SYNTH_ENVELOPES, "wobble lead", ENVELOPES_FIELD),
        synth(words::ENVELOPE_ADSR, "env adsr", ENVELOPES_FIELD),
        synth(words::ENVELOPE_AR, "env ar", ENVELOPES_FIELD),
        synth(words::ENVELOPE_ASR, "env asr", ENVELOPES_FIELD),
        synth(words::ENVELOPE_SID_ADSR, "env sid adsr", ENVELOPES_FIELD),
        synth(words::ENVELOPE_VACTROL, "env vactrol", ENVELOPES_FIELD),
        synth(words::ENVELOPE_ACID_GATE, "env acid gate", ENVELOPES_FIELD),
        synth(words::ENVELOPE_CHIP_STEPS, "env chip steps", ENVELOPES_FIELD),
        synth(words::FILTER_LADDER, "filter ladder", FILTER_FIELD),
        synth(words::FILTER_MULTIMODE, "filter multimode", FILTER_FIELD),
        synth(words::FILTER_SALLEN_KEY, "filter sallen key", FILTER_FIELD),
        synth(words::FILTER_DIODE, "filter diode", FILTER_FIELD),
        synth(words::FILTER_OTA, "filter ota", FILTER_FIELD),
        synth(words::FILTER_LOW_PASS_GATE, "filter low pass gate", FILTER_FIELD),
        synth(words::SYNTH_LFOS, "wobble lead", "LFO 1 shape"),
        synth(words::SYNTH_FILTER, "wobble lead", FILTER_FIELD),
        synth(words::SYNTH_EFFECTS, "wobble lead", "FX 1"),
        synth(words::SYNTH_MATRIX, "wobble lead", "Slot 1 source"),
        shot(words::CHORDS_GENERATOR, PROGRESSION_SET, to_generator(file_format::NamedProgression::POP, 1)),
        // The fourth setting after the Name opens the chords editor.
        shot(
            words::CHORDS_EDITOR,
            PROGRESSION_SET,
            joined(vec![
                to_generator(file_format::NamedProgression::POP, 1),
                repeated(keys::DOWN, FOUR_TIMES),
                keys(&[keys::ENTER]),
            ]),
        ),
        shot(words::DRIFT_EDITOR, DRIFT_SET, to_generator(words::CLIMB, 0)),
        shot(words::HOCKET_EDITOR, HOCKET_SET, to_generator(words::TRADE, 1)),
        shot(words::SHAPES_EDITOR, SWELL_SET, to_generator(words::HITS, 1)),
        // A clip's Timing tab: the second scene's acid track's clip, the row of tabs, and Right to Timing.
        shot(
            words::TIMING_EDITOR,
            GLIDE_SET,
            joined(vec![
                keys(&[keys::A, keys::DOWN]),
                repeated(keys::RIGHT, FOUR_TIMES),
                keys(&[keys::ENTER, keys::TAB]),
                repeated(keys::RIGHT, FIVE_TIMES),
            ]),
        ),
        shot(
            words::CHAIN_LIST,
            PROGRESSION_SET,
            joined(vec![
                keys(&[keys::A]),
                repeated(keys::DOWN, FIVE_TIMES),
                repeated(keys::RIGHT, FIVE_TIMES),
                keys(&[keys::ENTER, keys::TAB]),
                repeated(keys::RIGHT, FOUR_TIMES),
            ]),
        ),
    ]
}

/// Take the documents' screenshots into a folder, docs/screenshots/ unless another is named: each shot's set opened from the
/// top folder, its keys pressed, and its screen written as an SVG named after the shot.
fn screenshots(folder: Option<&str>) -> ExitCode {
    let folder = std::path::PathBuf::from(folder.unwrap_or("docs/screenshots"));
    llamatron_tracker::realtime::backend::SENDING_ALLOWED.store(false, std::sync::atomic::Ordering::SeqCst);
    for shot in shots() {
        // The set is opened by its whole path, as a person opens one, which the File page shows.
        let path = std::fs::canonicalize(shot.set).unwrap_or_else(|_| std::path::PathBuf::from(shot.set));
        let document = match llamatron_tracker::document::Document::open(&path) {
            Ok(document) => document,
            Err(problem) => {
                eprintln!("{}: {problem}", shot.set);
                return ExitCode::from(1);
            }
        };
        let mut tracker = llamatron_tracker::app::Tracker::new(document);
        tracker.app.fluidsynth_installed = true;
        llamatron_tracker::tour::composed(&tracker, SHOT_COLUMNS, SHOT_ROWS);
        for key in &shot.keys {
            tracker.press(&llamatron_tracker::keys::pressed_key(key));
            llamatron_tracker::tour::composed(&tracker, SHOT_COLUMNS, SHOT_ROWS);
        }
        let reached = match shot.reach {
            Some(Reach::Tab(first_field)) => turn_to_tab(&mut tracker, first_field),
            Some(Reach::Field(label)) => go_to_field(&mut tracker, label),
            None => Ok(()),
        };
        {
            if let Err(problem) = reached {
                eprintln!("{}: {problem}", shot.name);
                return ExitCode::from(1);
            }
        }
        let screen = llamatron_tracker::tour::composed(&tracker, SHOT_COLUMNS, SHOT_ROWS);
        let unique_id = format!("terminal-{}", shot.name);
        let svg = llamatron_tracker::svg::screen_svg(&screen, SHOT_COLUMNS, SHOT_TITLE, &unique_id)
            .replace(llamatron_tracker::version::PROGRAM_VERSION, VERSION_PLACEHOLDER);
        let path = folder.join(format!("{}.svg", shot.name));
        if let Err(problem) = std::fs::write(&path, svg) {
            eprintln!("{}: {problem}", path.display());
            return ExitCode::from(1);
        }
        println!("wrote {}", path.display());
    }
    ExitCode::SUCCESS
}

/// Where a walk of the program keeps its copies of the set.
const EXPLORE_FOLDER: &str = "/tmp/claude/llamatron/explore";
/// The screen a walk of the program draws at.
const EXPLORE_COLUMNS: usize = 80;
const EXPLORE_ROWS: usize = 24;

/// Walk the program on a set from the main screen, pressing every key every page offers at each kind of place, and say how
/// many places it reached, on which pages, and every key that panicked, with the keys that reach it.
fn explore(set: Option<&str>) -> ExitCode {
    let Some(set) = set else {
        eprintln!("usage: llamatron-compare explore SET");
        return ExitCode::from(2);
    };
    // The places on every set named, separated by commas, are reported together.
    let sets: Vec<&str> = set.split(',').collect();
    // The walk's copies of the set go where every working file of the project's tools goes.
    let folder = std::path::PathBuf::from(EXPLORE_FOLDER);
    if let Err(problem) = std::fs::create_dir_all(&folder) {
        eprintln!("{}: {problem}", folder.display());
        return ExitCode::from(1);
    }
    // A panic is a finding the walk records, not a message to print as it happens.
    std::panic::set_hook(Box::new(|_| {}));
    let mut explored = Vec::new();
    for set in sets {
        match llamatron_tracker::tour::explore(std::path::Path::new(set), &folder, EXPLORE_COLUMNS, EXPLORE_ROWS) {
            Ok(places) => explored.extend(places),
            Err(problem) => {
                eprintln!("{set}: {problem}");
                return ExitCode::from(1);
            }
        }
    }
    let mut pages: Vec<(String, usize)> = Vec::new();
    for place in &explored {
        match pages.iter_mut().find(|(page, _)| *page == place.page) {
            Some((_, count)) => *count += 1,
            None => pages.push((place.page.clone(), 1)),
        }
    }
    let panics: Vec<&llamatron_tracker::tour::Explored> = explored.iter().filter(|place| place.panic.is_some()).collect();
    println!("{} places on {} pages, {} panics", explored.len(), pages.len(), panics.len());
    for (page, count) in &pages {
        println!("  {page}: {count}");
    }
    // EXPLORE_SHOW names a page whose places are listed, each with the keys that reach it, to see where a walk goes.
    if let Ok(shown) = std::env::var("EXPLORE_SHOW") {
        for place in explored.iter().filter(|place| place.page == shown) {
            println!("{shown} after {} [{}]", place.keys.join(" "), place.kind);
        }
    }
    for place in &panics {
        println!("panic after {}: {}", place.keys.join(" "), place.panic.clone().unwrap_or_default());
    }
    if panics.is_empty() {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}

/// What KEYMAP.md says of itself above the pages.
const KEYMAP_HEADING: &str = "# Key Map

Written by `internal_tools/key_map.sh` from a walk of llamatron (`llamatron-compare keymap`); never edit it by hand. For
every page and dialog the walk reaches, it says what each key does with the cursor at each kind of place, as the page names
the place. The keys that work everywhere are listed once:

- `Ctrl+S` SAVE
- `Ctrl+O` OPEN
- `Ctrl+X` EXPORT
- `Ctrl+T` SILENCE
- `Ctrl+Z` UNDO
- `Ctrl+Y` REDO
- `F1` HELP
- `F3` ABOUT
- `Ctrl+C` QUIT NOW
";
/// A kind of place and the keys offered there, each the name its legend shows and what it does.
type PlaceKeys = (String, Vec<(String, String)>);
/// What a place is called where its page names no kind of place.
const ANY_PLACE: &str = words::ANYWHERE;

/// Write KEYMAP.md from a walk of the program on the sets named, separated by commas: each page's keys at each kind of place.
fn keymap(sets: Option<&str>, out: Option<&str>) -> ExitCode {
    let (Some(sets), Some(out)) = (sets, out) else {
        eprintln!("usage: llamatron-compare keymap SET,SET OUT.md");
        return ExitCode::from(2);
    };
    let folder = std::path::PathBuf::from(EXPLORE_FOLDER);
    let _ = std::fs::create_dir_all(&folder);
    std::panic::set_hook(Box::new(|_| {}));
    // Each page's kinds of place in the order the walk first reached them, each with the keys it offered there.
    let mut pages: std::collections::BTreeMap<String, Vec<PlaceKeys>> = std::collections::BTreeMap::new();
    for set in sets.split(',') {
        let explored = match llamatron_tracker::tour::explore(std::path::Path::new(set), &folder, EXPLORE_COLUMNS, EXPLORE_ROWS) {
            Ok(explored) => explored,
            Err(problem) => {
                eprintln!("{set}: {problem}");
                return ExitCode::from(1);
            }
        };
        for place in explored.into_iter().filter(|place| !place.offered.is_empty() && place.page != "(not ported)") {
            let kinds = pages.entry(place.page).or_default();
            let kind = if place.kind.trim().is_empty() {
                ANY_PLACE.to_string()
            } else {
                place.kind.trim().to_string()
            };
            if !kinds.iter().any(|(known, _)| *known == kind) {
                kinds.push((kind, place.offered));
            }
        }
    }
    let mut text = String::from(KEYMAP_HEADING);
    for (page, kinds) in &pages {
        let _ = write!(text, "\n\n## {page}\n\n");
        for (kind, keys) in kinds {
            let shown: Vec<String> = keys.iter().map(|(key, what)| format!("`{key}` {what}")).collect();
            let _ = writeln!(text, "- **{kind}**: {}", shown.join(" · "));
        }
    }
    if let Err(problem) = std::fs::write(out, text) {
        eprintln!("{out}: {problem}");
        return ExitCode::from(1);
    }
    println!("wrote {out}: {} pages", pages.len());
    ExitCode::SUCCESS
}
