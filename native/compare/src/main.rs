// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron-compare: what llamatron2 makes of a set, printed in a form the Python program prints the same way, so that
//! internal_tools/compare_llamatron2.py holds each layer of the port to the Python as it lands.
//!
//! `llamatron-compare load SET` prints the set file's data as JSON, as Python's json.dumps writes what PyYAML loaded;
//! `llamatron-compare layout SET` writes that data back as a set file, as the Python writer lays it out;
//! `llamatron-compare migrate SET` moves the data to today's layout, into the objects' layout and back, and writes it;
//! `llamatron-compare save SET` reads the set into objects and saves it, as the Python program saves a set.

use llamatron_model::file::data::{json_text, load, Data};
use std::process::ExitCode;

/// Data as Python's json.dumps writes it, with its default separators, keys in their order, every key made text.
fn json(data: &Data) -> String {
    match data {
        Data::Null => "null".into(),
        Data::Bool(flag) => if *flag { "true" } else { "false" }.into(),
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
        Data::Bool(flag) => format!("\"{}\"", if *flag { "true" } else { "false" }),
        Data::Whole(whole) => format!("\"{whole}\""),
        Data::Float(float) => format!("\"{}\"", llamatron_math::number::python_float_text(*float)),
        other => json(other),
    }
}

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    let (Some(command), Some(path)) = (arguments.first(), arguments.get(1)) else {
        eprintln!("usage: llamatron-compare load SET");
        return ExitCode::from(2);
    };
    // A MIDI file is read as bytes by the step that imports it.
    let read = if path.ends_with(".mid") {
        Ok(String::new())
    } else {
        std::fs::read_to_string(path)
    };
    let text = match read {
        Ok(text) => text,
        Err(problem) => {
            eprintln!("{path}: {problem}");
            return ExitCode::from(1);
        }
    };
    match command.as_str() {
        "load" => match load(&text) {
            Ok(data) => {
                println!("{}", json(&data));
                ExitCode::SUCCESS
            }
            Err(problem) => {
                eprintln!("{path}: {}", problem.0);
                ExitCode::from(1)
            }
        },
        "layout" => match load(&text) {
            Ok(data) => {
                print!("{}", llamatron_model::file::writing::dump_file_layout(&data));
                ExitCode::SUCCESS
            }
            Err(problem) => {
                eprintln!("{path}: {}", problem.0);
                ExitCode::from(1)
            }
        },
        "migrate" => match load(&text) {
            Ok(data) => {
                let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
                let (moved, _) = llamatron_model::file::migrations::migrated(data, stem);
                match llamatron_model::file::layout::as_object_layout(&moved) {
                    Ok(objects) => {
                        let file = llamatron_model::file::layout::as_file_layout(&objects);
                        print!("{}", llamatron_model::file::writing::dump_file_layout(&file));
                        ExitCode::SUCCESS
                    }
                    Err(problem) => {
                        eprintln!("{path}: {}: {}", problem.section, problem.problem.message);
                        ExitCode::from(1)
                    }
                }
            }
            Err(problem) => {
                eprintln!("{path}: {}", problem.0);
                ExitCode::from(1)
            }
        },
        "pattern_edits" => {
            let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
            match llamatron_model::objects::setlist::Setlist::read_text(&text, stem) {
                Ok(setlist) => {
                    println!("{}", pattern_edits_of(&setlist));
                    ExitCode::SUCCESS
                }
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    ExitCode::from(1)
                }
            }
        }
        "edits" => {
            let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
            match llamatron_model::objects::setlist::Setlist::read_text(&text, stem) {
                Ok(setlist) => {
                    println!("{}", edits_of(&setlist));
                    ExitCode::SUCCESS
                }
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    ExitCode::from(1)
                }
            }
        }
        "save" => {
            let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
            match llamatron_model::objects::setlist::Setlist::read_text(&text, stem) {
                Ok(setlist) => {
                    let file = llamatron_model::file::layout::as_file_layout(&setlist.to_data());
                    print!("{}", llamatron_model::file::writing::dump_file_layout(&file));
                    ExitCode::SUCCESS
                }
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    ExitCode::from(1)
                }
            }
        }
        "import" => match imported(path, &text) {
            Ok(json) => {
                println!("{json}");
                ExitCode::SUCCESS
            }
            Err(problem) => {
                eprintln!("{path}: {problem}");
                ExitCode::from(1)
            }
        },
        "player" => {
            let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text, stem) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    return ExitCode::from(1);
                }
            };
            match players(&setlist) {
                Ok(text) => {
                    println!("{text}");
                    ExitCode::SUCCESS
                }
                Err(llamatron_engine::error::RenderError::NotPorted(what)) => {
                    eprintln!("not ported yet: {what}");
                    ExitCode::from(NOT_PORTED)
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        "timeline" => {
            let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text, stem) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    return ExitCode::from(1);
                }
            };
            match timelines(&setlist) {
                Ok(text) => {
                    println!("{text}");
                    ExitCode::SUCCESS
                }
                Err(llamatron_engine::error::RenderError::NotPorted(what)) => {
                    eprintln!("not ported yet: {what}");
                    ExitCode::from(NOT_PORTED)
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        "live" | "midi" => {
            let stem = std::path::Path::new(path)
                .file_stem()
                .map(|stem| stem.to_string_lossy().to_string())
                .unwrap_or_default();
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text, Some(stem.clone())) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    return ExitCode::from(1);
                }
            };
            let exported = if command == "live" {
                exported_live(&setlist)
            } else {
                exported_midi(&setlist, &stem)
            };
            match exported {
                Ok(text) => {
                    println!("{text}");
                    ExitCode::SUCCESS
                }
                Err(llamatron_engine::error::RenderError::NotPorted(what)) => {
                    eprintln!("not ported yet: {what}");
                    ExitCode::from(NOT_PORTED)
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        "render" => {
            let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text, stem) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    return ExitCode::from(1);
                }
            };
            match rendered_songs(&setlist) {
                Ok(text) => {
                    println!("{text}");
                    ExitCode::SUCCESS
                }
                Err(llamatron_engine::error::RenderError::NotPorted(what)) => {
                    eprintln!("not ported yet: {what}");
                    ExitCode::from(NOT_PORTED)
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        "play" => {
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
        "wav" => {
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
        "screens" => {
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

/// What the tool exits with for a set using a part of the program not ported yet, which the harness counts apart.
const NOT_PORTED: u8 = 3;
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
                keyswitches: true,
                sound: (place % 4 == 0).then(|| "synth".to_string()),
                early: if place % 5 == 0 { 0.01 } else { 0.0 },
            };
            (name.to_string(), route)
        })
        .collect()
}

/// A sender that writes down everything a player hands it, a line each, for the player step.
struct RecordingSender {
    lines: Vec<String>,
}

impl llamatron_tracker::realtime::player::Sender for RecordingSender {
    fn add(&mut self, events: Vec<llamatron_tracker::realtime::timeline::Playing>) {
        for event in events {
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
    player.update_score(&mut sender, now, score_now(&document)?, "asap", &|old| Some(old), &|old| Some(old.to_string()));
    run(&mut player, &mut sender, &mut now, LIVE_EDIT_GAP_SECONDS);
    // Both programs check the edits as a person makes them; a refusal would show as a difference.
    let _ = document.add_scene(0, LIVE_EDIT_SCENE);
    sender.lines.push("edit next_bar".to_string());
    player.update_score(
        &mut sender,
        now,
        score_now(&document)?,
        "next_bar",
        &|old| (old < scenes).then_some(old + 1),
        &|old| Some(old.to_string()),
    );
    run(&mut player, &mut sender, &mut now, LIVE_EDIT_GAP_SECONDS);
    if tracks.len() > 1 {
        let last = tracks[tracks.len() - 1].clone();
        let _ = document.delete_named(Section::TRACKS, &last);
        sender.lines.push("edit clip_restart".to_string());
        let gone = |old: &str| (old != last).then(|| old.to_string());
        player.update_score(&mut sender, now, score_now(&document)?, "clip_restart", &|old| Some(old), &gone);
    }
    run(&mut player, &mut sender, &mut now, LIVE_EDIT_LAST_SECONDS);
    player.stop_all(&mut sender);
    Ok(sender.lines)
}

const LIVE_EDIT_TEMPO: i128 = 150;
const LIVE_EDIT_SCENE: &str = "live_edit";
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
        for event in llamatron_tracker::realtime::timeline::song_timeline(&grid, &routes)? {
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
            Err(other) => return Err(other),
        }
    }
    Ok(lines.join("\n"))
}

/// A new set, as the Python's Setlist.new() makes one.
const NEW_SET: &str = "step_size: 1/16\ndefault_octave: 5\ndefault_drum_octave: 3\noctave_labels: live\n\nscales:\n  - { name: scale-1, root: C, type: major }\n\npatterns:\n  - name: pattern-1\n    steps: 16\n    group: track-1\n    degree: [1, ~, ~, ~, 1, ~, ~, ~, 1, ~, ~, ~, 1, ~, ~, ~]\n\nsongs:\n  - name: untitled\n    tempo: 120\n    scale: scale-1\n\n    tracks:\n      - { name: track-1 }\n\n    scenes:\n      - name: scene-1\n        clips:\n          - { track: track-1, pattern: pattern-1 }\n";

/// Data as JSON, which the harness reads back as YAML.
fn json_written(data: &Data, out: &mut String) {
    match data {
        Data::Null => out.push_str("null"),
        Data::Bool(value) => out.push_str(if *value { "true" } else { "false" }),
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
    let mut names: Vec<String> = holding.items("patterns").iter().map(|(name, _)| name.clone()).collect();
    names.sort();
    tried.push(Data::List(vec![
        Data::text(&again.song.name),
        again.song.song.clone(),
        Data::Whole(again.patterns as i128),
        Data::Whole(again.song.shared as i128),
        Data::List(names.iter().map(|name| Data::text(name)).collect()),
    ]));
    Ok(Data::Map(vec![(Data::text("found"), shown), (Data::text("tried"), Data::List(tried))]))
}

fn imported(path: &str, text: &str) -> Result<String, String> {
    let file = std::path::Path::new(path);
    let stem = file.file_stem().map(|stem| stem.to_string_lossy().to_string()).unwrap_or_default();
    let mut inputs: Vec<(String, Vec<u8>)> = Vec::new();
    if path.ends_with(".mid") {
        inputs.push((stem, std::fs::read(file).map_err(|problem| problem.to_string())?));
    } else {
        let setlist = llamatron_model::objects::setlist::Setlist::read_text(text, Some(stem.clone())).map_err(|problem| problem.message)?;
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
    let new_set = llamatron_model::objects::setlist::Setlist::read_text(NEW_SET, None).map_err(|problem| problem.message)?;
    let mut made = Vec::new();
    let first_input = inputs.first().cloned();
    for (name, bytes) in inputs {
        let entry = match llamatron_importers::import::imported(&bytes, &new_set, &name) {
            Err(_) => Data::Map(vec![(Data::text("refused"), Data::text(&name))]),
            Ok(song) => Data::Map(vec![
                (Data::text("name"), Data::text(&song.name)),
                (Data::text("song"), song.song),
                (
                    Data::text("patterns"),
                    Data::Map(song.patterns.into_iter().map(|(name, data)| (Data::text(&name), data)).collect()),
                ),
                (
                    Data::text("scales"),
                    Data::Map(song.scales.into_iter().map(|(name, data)| (Data::text(&name), data)).collect()),
                ),
                (
                    Data::text("instruments"),
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
        .chain(["chains"])
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
        add("rename", section, first, renamed_in_set(&data, section, first, &format!("{first}{RENAMED}")));
        add("copy", section, first, copied_in_set(&data, section, first, &new));
        add("delete", section, first, removed_from_set(&data, section, first));
        let items = data.get(section).cloned().unwrap_or(Data::Null);
        if held.len() > 1 {
            add("move", section, first, with_section(section, moved_in_section(&items, 0, 1)));
        }
        add("sort", section, first, with_section(section, Some(sorted_section(&items))));
    }
    for song in setlist.song_names() {
        let Some(tracks) = data.get("songs").and_then(|songs| songs.get(song)).and_then(|held| held.get("tracks")).cloned() else {
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
                if let Some((_, Data::Map(songs))) = pairs.iter_mut().find(|(key, _)| key.as_str() == Some("songs")) {
                    if let Some((_, Data::Map(settings))) = songs.iter_mut().find(|(key, _)| key.as_str() == Some(song)) {
                        if let Some(pair) = settings.iter_mut().find(|(key, _)| key.as_str() == Some("tracks")) {
                            pair.1 = items;
                        }
                    }
                }
            }
            edited
        };
        add("rename", song, first, renamed_track(&data, song, first, &format!("{first}{RENAMED}")));
        add("copy", song, first, copied_track(&data, song, first, &new));
        add("delete", song, first, removed_track(&data, song, first));
        if names.len() > 1 {
            add("move", song, first, with_tracks(moved_in_section(&tracks, 0, 1)));
        }
        add("sort", song, first, with_tracks(Some(sorted_section(&tracks))));
        add("add_track", song, ADDED, added_track(&data, song, ADDED, None));
        add("add_track", song, ADDED, added_track(&data, song, ADDED, Some(0)));
        add("fracture", song, "", fractured(&data, song).0);
        let scenes = setlist.get_song(song).map_or(Vec::new(), |held| held.scenes().to_vec());
        let Some(scene) = scenes.first() else { continue };
        add("add_scene", song, ADDED, added_scene(&data, song, 0, ADDED));
        add("copy_scene", song, ADDED, copied_scene(&data, song, 0, ADDED));
        add("remove_scene", song, "", removed_scene(&data, song, 0));
        if let Some((track, _)) = scene.clip_slots().first() {
            add("remove_clip", song, track, removed_clip(&data, song, 0, track));
        }
    }
    json(&Data::List(results))
}

/// The name the edits step gives a scene or a track it adds.
const ADDED: &str = "added";

/// How many of a set's patterns the pattern_edits step edits, and the direction and group it gives them.
const EDITED_PATTERNS: usize = 3;
const EDITED_DIRECTION: &str = "pendulum";
const EDITED_GROUP: &str = "edited";
const DRUM_DEGREE: &str = "C";

/// Each of a set's first patterns after each of the pattern_edits step's edits on a fresh copy, as JSON.
/// The seed every scene's written view is rendered from, so that both programs draw the same random parts.
const SCENE_VIEW_SEED: i64 = 7;

/// Every scene of the first song as Scene View shows it written: its notes, its length, the chord on each beat and the
/// values it plays with.
fn scene_views(setlist: &llamatron_model::objects::setlist::Setlist) -> Vec<Data> {
    use llamatron_tracker::scene_notes::{chord_scale, effective_values, scene_notes};
    let mut results = Vec::new();
    let Some((song_name, _)) = setlist.items("songs").first().cloned() else {
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
            Err(_) => Data::List(vec![Data::text("refused"), values]),
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
        results.push(Data::List(vec![Data::text("scene_view"), Data::text(&index.to_string()), shown]));
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
    let first_scale = setlist.items("scales").first().and_then(|(scale, item)| match item {
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
        results.push(Data::List(vec![Data::text("chord_texts"), Data::text(""), Data::List(texts)]));
    }
    results.extend(scene_views(setlist));
    for (name, item) in setlist.items("patterns").iter().take(EDITED_PATTERNS) {
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
                "set_value",
                Box::new(|pattern| {
                    // A drum pattern's degree is a note letter.
                    let degree = if original.is_drum() { Data::text(DRUM_DEGREE) } else { Data::Whole(3) };
                    pattern.set_value("degree", 0, Some(degree))
                }),
            ),
            (
                "set_value",
                Box::new(move |pattern| pattern.set_value("velocity", steps - 1, Some(Data::Whole(100)))),
            ),
            ("clear_sound", Box::new(|pattern| pattern.clear_sound(0))),
            ("set_steps", Box::new(move |pattern| pattern.set_steps(steps as i128 + 2))),
            ("insert_step", Box::new(|pattern| pattern.insert_step(0))),
            ("insert_step", Box::new(move |pattern| pattern.insert_step(steps))),
            (
                "set_group",
                Box::new(|pattern| {
                    pattern.set_group(Some(EDITED_GROUP));
                    Ok(())
                }),
            ),
            (
                "set_direction",
                Box::new(|pattern| {
                    pattern.set_direction(EDITED_DIRECTION);
                    Ok(())
                }),
            ),
            ("reverse", Box::new(|pattern| pattern.reverse())),
            ("roll", Box::new(|pattern| pattern.roll(1))),
            ("roll", Box::new(|pattern| pattern.roll(-1))),
            ("roll_through", Box::new(move |pattern| pattern.roll_through(middle))),
            ("roll_from", Box::new(move |pattern| pattern.roll_from(middle))),
            ("reverse_after", Box::new(|pattern| pattern.reverse_after(0))),
            ("reverse_before", Box::new(move |pattern| pattern.reverse_before(steps - 1))),
            ("pivot_around", Box::new(move |pattern| pattern.pivot_around(middle).map(|_| ()))),
            ("repeat_at_end", Box::new(move |pattern| pattern.repeat_at_end(0, steps - 1))),
            ("repeat_at_start", Box::new(|pattern| pattern.repeat_at_start(0, 0))),
            (
                "clear_all_but_pitch",
                Box::new(|pattern| {
                    pattern.clear_all_but_pitch();
                    Ok(())
                }),
            ),
            (
                "clear_chords",
                Box::new(|pattern| {
                    pattern.clear_chords();
                    Ok(())
                }),
            ),
            (
                "clear_statements",
                Box::new(|pattern| {
                    pattern.clear_statements();
                    Ok(())
                }),
            ),
            (
                "smooth_ccs",
                Box::new(|pattern| {
                    pattern.smooth_ccs();
                    Ok(())
                }),
            ),
            (
                "smooth_velocity",
                Box::new(|pattern| {
                    pattern.smooth_velocity();
                    Ok(())
                }),
            ),
            ("mirror", Box::new(|pattern| pattern.mirror())),
            ("interleave", Box::new(|pattern| pattern.interleave(original))),
            ("splice", Box::new(|pattern| pattern.splice(original, Some(0)))),
            ("splice", Box::new(|pattern| pattern.splice(original, None))),
            (
                "set_drum",
                Box::new(|pattern| {
                    pattern.set_drum(!original.is_drum());
                    Ok(())
                }),
            ),
            (
                "join_repeated_notes",
                Box::new(|pattern| {
                    pattern.join_repeated_notes();
                    Ok(())
                }),
            ),
            (
                "divide_long_notes",
                Box::new(|pattern| {
                    let covering = llamatron_tracker::patterns::covering_notes(pattern, llamatron_math::Rational::new(1, DIVIDED_STEP_PARTS));
                    pattern.divide_long_notes(&covering);
                    Ok(())
                }),
            ),
            (
                "reverse_pitches",
                Box::new(|pattern| {
                    pattern.reverse_pitches();
                    Ok(())
                }),
            ),
            ("clear_every", Box::new(|pattern| pattern.clear_every(EVERY_OTHER))),
            ("invert_melody", Box::new(|pattern| pattern.invert_melody(0, INVERTED_SCALE, INVERTED_OCTAVE))),
        ];
        if steps > 1 {
            edits.push(("set_steps", Box::new(move |pattern| pattern.set_steps(steps as i128 - 1))));
            edits.push(("remove_step", Box::new(|pattern| pattern.remove_step(0))));
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
        let first_scale = setlist.items("scales").first().and_then(|(scale, item)| match item {
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
            results.push(Data::List(vec![Data::text("chord_tones"), Data::text(name), Data::List(tones)]));
            if let Some(scale) = &scale {
                for octaves in [false, true] {
                    let mut pattern = original.clone();
                    let outcome = match llamatron_tracker::voice_leading::apply_voice_leading(&mut pattern, scale, TONES_OCTAVE, octaves) {
                        Ok(()) => pattern.to_data(),
                        Err(problem) => Data::text(&format!("refused: {}", problem.message)),
                    };
                    results.push(Data::List(vec![Data::text("apply_voice_leading"), Data::text(name), outcome]));
                }
            }
        }
    }
    json(&Data::List(results))
}
