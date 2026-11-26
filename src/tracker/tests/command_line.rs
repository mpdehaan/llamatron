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
