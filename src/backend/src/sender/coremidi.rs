// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A MIDI destination opened through CoreMIDI, macOS's MIDI system, which takes each event ahead of time stamped with the
//! moment it should sound and delivers it then, however late the sender wakes. The stamps are host time, the very ticks
//! the daemon's clock reads (audio/clock.rs), so a moment needs only converting from seconds. What the port holds is
//! taken back by giving the port up and opening another, which drops everything it had scheduled.

use crate::audio::clock;
use coremidi::{Client, Destination, Destinations, OutputPort, PacketBuffer};
use llamatron_names::wire;
use std::sync::Arc;

const NOW: u64 = 0;

/// Why a destination could not be opened.
#[derive(Debug, thiserror::Error)]
pub enum OpenProblem {
    #[error("CoreMIDI would not make its client: status {0}")]
    Client(i32),
    #[error("no MIDI destination is called {0}")]
    NoDestination(String),
    #[error("CoreMIDI would not open a port to {name}: status {status}")]
    Port { name: String, status: i32 },
}

/// The process's one CoreMIDI client.
pub fn client() -> Result<Arc<Client>, OpenProblem> {
    Client::new(wire::LLAMATRON).map(Arc::new).map_err(OpenProblem::Client)
}

/// Every MIDI destination's shown name, as the tracker lists the computer's ports.
pub fn destination_names() -> Vec<String> {
    (0..Destinations::count())
        .filter_map(Destination::from_index)
        .filter_map(|destination| destination.display_name().or_else(|| destination.name()))
        .collect()
}

/// Print every MIDI destination's shown name, a line each, for `llamatron-backend ports`.
pub fn list_destinations() {
    for name in destination_names() {
        println!("{name}");
    }
}

pub struct CoreMidiOutput {
    client: Arc<Client>,
    name: String,
    port: Option<OutputPort>,
    destination: Destination,
}

impl CoreMidiOutput {
    /// Open the destination a name picks as the tracker lists it: the first whose name or shown name is it, or starts with it.
    pub fn open(client: Arc<Client>, name: &str) -> Result<CoreMidiOutput, OpenProblem> {
        let destination = (0..Destinations::count())
            .filter_map(Destination::from_index)
            .find(|destination| {
                [destination.name(), destination.display_name()]
                    .into_iter()
                    .flatten()
                    .any(|found| found == name || found.starts_with(name))
            })
            .ok_or_else(|| OpenProblem::NoDestination(name.to_string()))?;
        let port = client.output_port(name).map_err(|status| OpenProblem::Port {
            name: name.to_string(),
            status,
        })?;
        Ok(CoreMidiOutput {
            client,
            name: name.to_string(),
            port: Some(port),
            destination,
        })
    }

    pub fn send_now(&mut self, data: &[u8]) {
        self.send_stamped(data, NOW);
    }

    /// Hand an event to CoreMIDI now, to be delivered at a reading of the clock, at once when that moment has passed.
    pub fn send_at(&mut self, data: &[u8], at: f64) {
        let stamp = if at <= clock::now() { NOW } else { clock::host_ticks(at) };
        self.send_stamped(data, stamp);
    }

    /// Take back every event held for a moment not yet come, by giving the port up and opening another.
    pub fn flush(&mut self) {
        self.port = None;
        match self.client.output_port(&self.name) {
            Ok(port) => self.port = Some(port),
            Err(status) => log::error!("CoreMIDI would not open a port to {} again: status {status}", self.name),
        }
    }

    fn send_stamped(&mut self, data: &[u8], stamp: u64) {
        let Some(port) = &self.port else { return };
        let packets = PacketBuffer::new(stamp, data);
        if let Err(status) = port.send(&self.destination, &packets) {
            log::warn!("CoreMIDI would not send to {}: status {status}", self.name);
        }
    }
}
