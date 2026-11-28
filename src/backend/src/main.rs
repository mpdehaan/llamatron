// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron-backend, llamatron's backend, the daemon that plays the built-in synths and FluidSynth and sends MIDI: the tracker starts it, speaks MessagePack to it
//! over its standard input and output (protocol.rs), and it plays through the sound card or renders into a WAV file.
//!
//! `llamatron-backend play [--block FRAMES] [--device NAME]` plays; `llamatron-backend render --rate HZ` renders;
//! `llamatron-backend send` is the real-time sender, sending the tracker's events through MIDI and the synths alike. The
//! architecture is described for people in docs/BACKEND.md.

use llamatron_backend::protocol::Piped;
use llamatron_backend::{daemon, protocol, sender};
use llamatron_names::wire;
use std::io;
use std::panic;

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
    /// Whether it only lists the computer's MIDI destinations and ends: `llamatron-backend ports`.
    listing: bool,
    block: usize,
    device: Option<String>,
    rate: f64,
}

fn arguments() -> Arguments {
    let mut found = Arguments {
        rendering: false,
        sending: false,
        listing: false,
        block: DEFAULT_BLOCK,
        device: None,
        rate: DEFAULT_RATE,
    };
    let mut given = std::env::args().skip(1);
    while let Some(argument) = given.next() {
        match argument.as_str() {
            wire::RENDER => found.rendering = true,
            wire::SEND => found.sending = true,
            wire::PORTS => found.listing = true,
            wire::PLAY => found.rendering = false,
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
    flexi_logger::Logger::try_with_str(wire::INFO)
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
    let output = daemon::standard_output();
    let mut input = Piped(io::stdin().lock());
    // The output and the input are only read and written here, so a panic leaves nothing half-changed that the loop's
    // answer below would rely on.
    let code = panic::catch_unwind(panic::AssertUnwindSafe(|| {
        if found.listing {
            sender::coremidi::list_destinations();
            0
        } else if found.sending {
            daemon::sending::serve(output.clone(), &mut input)
        } else if found.rendering {
            daemon::render(found.rate, output.clone(), &mut input)
        } else {
            daemon::play(found.block, found.device.as_deref(), output.clone(), &mut input)
        }
    }))
    .unwrap_or_else(|_| {
        daemon::tell(
            &output,
            &protocol::message(
                protocol::FAILED,
                vec![wire::PANIC.into(), "the daemon stopped on an internal error; its log says where".into()],
            ),
        );
        2
    });
    drop(logger);
    std::process::exit(code);
}
