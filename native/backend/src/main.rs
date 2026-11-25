// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron-backend, llamatron's backend, the daemon that plays the built-in synths and FluidSynth and sends MIDI: the tracker starts it, speaks MessagePack to it
//! over its standard input and output (protocol.rs), and it plays through the sound card or renders into a WAV file.
//!
//! `llamatron-backend play [--block FRAMES] [--device NAME]` plays; `llamatron-backend render --rate HZ` renders;
//! `llamatron-backend send` is the real-time sender, sending the tracker's events through MIDI and the synths alike. The
//! architecture is described for people in docs/BACKEND.md.

mod audio;
mod daemon;
mod drums;
mod dsp;
mod engine;
mod fluid;
mod protocol;
mod sender;
mod voice;

use std::io;
use std::panic;
use std::sync::{Arc, Mutex};

const DEFAULT_BLOCK: usize = 128;
const DEFAULT_RATE: f64 = 44100.0;
const LOG_FOLDER: &str = ".llamatron";
const LOG_NAME: &str = "llamatron-backend";
const LOG_FILE_BYTES: u64 = 1 << 20;
const LOG_FILES_KEPT: usize = 10;

/// What the command line asks for.
struct Arguments {
    rendering: bool,
    sending: bool,
    block: usize,
    device: Option<String>,
    rate: f64,
}

fn arguments() -> Arguments {
    let mut found = Arguments {
        rendering: false,
        sending: false,
        block: DEFAULT_BLOCK,
        device: None,
        rate: DEFAULT_RATE,
    };
    let mut given = std::env::args().skip(1);
    while let Some(argument) = given.next() {
        match argument.as_str() {
            "render" => found.rendering = true,
            "send" => found.sending = true,
            "play" => found.rendering = false,
            "--block" => found.block = given.next().and_then(|value| value.parse().ok()).unwrap_or(DEFAULT_BLOCK),
            "--device" => found.device = given.next(),
            "--rate" => found.rate = given.next().and_then(|value| value.parse().ok()).unwrap_or(DEFAULT_RATE),
            other => eprintln!("llamatron-backend: an argument it does not know: {other}"),
        }
    }
    found
}

/// Log to rotating files in ~/.llamatron/, appended to at each start and rotated by size alone, ten small files kept, so that the daemon's start-ups and problems can be read
/// afterwards; it logs nothing of the music. Without a home folder it logs nowhere.
fn start_logging() -> Option<flexi_logger::LoggerHandle> {
    let home = std::env::var_os("HOME")?;
    let folder = std::path::Path::new(&home).join(LOG_FOLDER);
    let file = flexi_logger::FileSpec::default().directory(folder).basename(LOG_NAME).suppress_timestamp();
    flexi_logger::Logger::try_with_str("info")
        .ok()?
        .log_to_file(file)
        .append()
        .rotate(
            flexi_logger::Criterion::Size(LOG_FILE_BYTES),
            flexi_logger::Naming::Numbers,
            flexi_logger::Cleanup::KeepLogFiles(LOG_FILES_KEPT),
        )
        .format(flexi_logger::detailed_format)
        .start()
        .ok()
}

fn main() {
    let logger = start_logging();
    panic::set_hook(Box::new(|information| log::error!("panic: {information}")));
    let found = arguments();
    log::info!("started, version {}, process {}", env!("CARGO_PKG_VERSION"), std::process::id());
    daemon::watch_parent();
    let output = Arc::new(Mutex::new(io::stdout()));
    let code = panic::catch_unwind(|| {
        if found.sending {
            daemon::sending::serve(output.clone())
        } else if found.rendering {
            daemon::render(found.rate, output.clone())
        } else {
            daemon::play(found.block, found.device.as_deref(), output.clone())
        }
    })
    .unwrap_or_else(|_| {
        daemon::tell(
            &output,
            &protocol::message(
                protocol::FAILED,
                vec!["panic".into(), "the daemon stopped on an internal error; its log says where".into()],
            ),
        );
        2
    });
    drop(logger);
    std::process::exit(code);
}
