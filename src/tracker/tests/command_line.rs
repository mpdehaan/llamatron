// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The command line's export, run as a person runs it: `llamatron SET --to KIND`.

use std::path::{Path, PathBuf};
use std::process::Command;

/// A set of one song, the learning demo of scales, from the top folder.
fn scale_set() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../examples/learning/04_scale.yml")
}

/// Where the project's tools keep their working files.
const WORKING_FOLDER: &str = "/tmp/claude/llamatron/command_line_tests";

/// A fresh folder for one test's exports, under the project's folder for working files, emptied first.
fn fresh_folder(name: &str) -> PathBuf {
    let folder = Path::new(WORKING_FOLDER).join(name);
    let _ = std::fs::remove_dir_all(&folder);
    folder
}

/// The --out folder is made where it doesn't exist, and --song finds its song without regard to case.
#[test]
fn an_export_makes_its_out_folder_and_finds_its_song_by_any_case() {
    let folder = fresh_folder("out_and_song").join("not_made_yet");
    let song_in_capitals = "SCALE";
    let run = Command::new(env!("CARGO_BIN_EXE_llamatron"))
        .arg(scale_set())
        .args(["--to", "midi", "--song", song_in_capitals, "--out"])
        .arg(&folder)
        .output()
        .expect("llamatron runs");
    assert!(run.status.success(), "{}", String::from_utf8_lossy(&run.stderr));
    let written: Vec<PathBuf> = std::fs::read_dir(&folder)
        .expect("the folder was made")
        .map(|entry| entry.expect("an entry").path())
        .collect();
    assert_eq!(written.len(), 1, "{written:?}");
}

/// What the program says on its error stream for some arguments, and whether it succeeded.
fn ran(arguments: &[&str]) -> (bool, String) {
    let run = Command::new(env!("CARGO_BIN_EXE_llamatron")).args(arguments).output().expect("llamatron runs");
    (run.status.success(), String::from_utf8_lossy(&run.stderr).to_string())
}

/// A visualizer the program has no mode for is refused, naming the modes it has; a launch option with --to is refused.
#[test]
fn launch_options_are_checked_before_anything_opens() {
    let set = scale_set();
    let set = set.to_str().expect("a path of text");
    let (worked, said) = ran(&[set, "--visualizer", "no_such_mode"]);
    assert!(!worked && said.contains("lava_lamp"), "{said}");
    let (worked, said) = ran(&[set, "--to", "midi", "--autoplay"]);
    assert!(!worked && said.contains("--autoplay"), "{said}");
}

/// A set of two FluidSynth pianos, the first panned to 20%, the second never panned.
fn panned_set() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/panned_fluidsynth.yml")
}

/// The General MIDI file places a panned instrument's track with CC 10 at its start, 20% as 25 of 127, on its own
/// channel; a track whose instrument never set its Pan sends no CC 10.
#[test]
fn a_general_midi_export_sends_each_panned_instruments_pan() {
    let folder = fresh_folder("panned_gm");
    let run = Command::new(env!("CARGO_BIN_EXE_llamatron"))
        .arg(panned_set())
        .args(["--to", "gm", "--out"])
        .arg(&folder)
        .output()
        .expect("llamatron runs");
    assert!(run.status.success(), "{}", String::from_utf8_lossy(&run.stderr));
    let file = std::fs::read_dir(&folder)
        .expect("the folder was made")
        .map(|entry| entry.expect("an entry").path())
        .find(|path| path.extension().is_some_and(|extension| extension == "mid"))
        .expect("a MIDI file");
    let bytes = std::fs::read(file).expect("the MIDI file reads back");
    let control_change = 0xb0u8;
    let pan_control = 10u8;
    let (left_channel, middle_channel) = (0u8, 1u8);
    let twenty_percent = 25u8;
    let sends = |channel: u8| bytes.windows(2).any(|pair| pair == [control_change | channel, pan_control]);
    assert!(bytes
        .windows(3)
        .any(|three| three == [control_change | left_channel, pan_control, twenty_percent]));
    assert!(!sends(middle_channel));
}

/// A soloed track plays alone, in an export as in real time: the multitrack MIDI file of a song whose left track is
/// soloed holds the tempo track and that one track, where the same song unsoloed holds both.
#[test]
fn a_soloed_track_is_exported_alone() {
    let tracks_in = |set: &str, folder: &str| {
        let folder = fresh_folder(folder);
        let run = Command::new(env!("CARGO_BIN_EXE_llamatron"))
            .arg(Path::new(env!("CARGO_MANIFEST_DIR")).join(set))
            .args(["--to", "midi", "--out"])
            .arg(&folder)
            .output()
            .expect("llamatron runs");
        assert!(run.status.success(), "{}", String::from_utf8_lossy(&run.stderr));
        let file = std::fs::read_dir(&folder)
            .expect("the folder")
            .next()
            .expect("a file")
            .expect("an entry")
            .path();
        let bytes = std::fs::read(file).expect("the MIDI file reads back");
        bytes.windows(4).filter(|four| four == b"MTrk").count()
    };
    let (tempo_and_one, tempo_and_two) = (2, 3);
    assert_eq!(tracks_in("tests/data/soloed_fluidsynth.yml", "soloed"), tempo_and_one);
    assert_eq!(tracks_in("tests/data/panned_fluidsynth.yml", "unsoloed"), tempo_and_two);
}

/// A track's Lowest and Highest octave, which only guide the piano roll, never stop its song from exporting.
#[test]
fn a_tracks_octave_range_exports() {
    let folder = fresh_folder("octave_range");
    let run = Command::new(env!("CARGO_BIN_EXE_llamatron"))
        .arg(Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/octave_range_track.yml"))
        .args(["--to", "midi", "--out"])
        .arg(&folder)
        .output()
        .expect("llamatron runs");
    assert!(run.status.success(), "{}", String::from_utf8_lossy(&run.stderr));
}

/// A set holding a value that cannot be used is refused for export, the change it would make listed, until --force
/// exports it with the nearest allowed value in its place; the set file is not changed.
#[test]
fn a_set_with_a_value_out_of_range_exports_only_with_force() {
    let folder = fresh_folder("force");
    let set = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/velocity_too_loud.yml");
    let before = std::fs::read_to_string(&set).expect("the set reads");
    let export = |force: bool| {
        let mut command = Command::new(env!("CARGO_BIN_EXE_llamatron"));
        command.arg(&set).args(["--to", "midi", "--replace", "--out"]).arg(&folder);
        if force {
            command.arg("--force");
        }
        command.output().expect("llamatron runs")
    };
    let refused = export(false);
    assert!(!refused.status.success());
    let said = String::from_utf8_lossy(&refused.stderr);
    let would = llamatron_strings::cli::MSG_CLI_WOULD_CHANGE.split('{').next().expect("the line's start");
    assert!(said.contains(would) && said.contains("--force"), "{said}");
    let forced = export(true);
    assert!(forced.status.success(), "{}", String::from_utf8_lossy(&forced.stderr));
    assert_eq!(std::fs::read_to_string(&set).expect("the set reads"), before);
}

/// --template builds the Ableton Live set from the Live set named, and a template that cannot be read is refused,
/// naming it.
#[test]
fn template_builds_the_live_set_from_the_set_named() {
    let folder = fresh_folder("template");
    let set = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/clip_of_two_patterns.yml");
    let template = Path::new(env!("CARGO_MANIFEST_DIR")).join("../exporters/templates/live12.als");
    let export = |template: &Path| {
        Command::new(env!("CARGO_BIN_EXE_llamatron"))
            .arg(&set)
            .args(["--to", "ableton", "--replace", "--out"])
            .arg(&folder)
            .arg("--template")
            .arg(template)
            .output()
            .expect("llamatron runs")
    };
    let built = export(&template);
    assert!(built.status.success(), "{}", String::from_utf8_lossy(&built.stderr));
    let missing = folder.join("no_such_template.als");
    let refused = export(&missing);
    assert!(!refused.status.success());
    assert!(String::from_utf8_lossy(&refused.stderr).contains("no_such_template.als"));
}
