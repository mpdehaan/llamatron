// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The WAV export (the Python exporters/wave_fluidsynth.py, built_in_wave.py and wave_level.py): the tracks that play through
//! FluidSynth, written as the General MIDI export writes them and played by FluidSynth's program faster than real time, and
//! the tracks on built-in instruments, read back in seconds and rendered by the backend's renderer here, mixed into one 16-bit file,
//! then normalized, its loudest moment 1 dB below full scale, as the demos' WAV files are.

use crate::document::Document;
use crate::instrument_sound::Sound;
use crate::sound_spec::synth_spec;
use llamatron_engine::realizer::Grid;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::{InstrumentSetting, Section, SetlistSetting, TrackSetting, FLUIDSYNTH_DEVICE};
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_names::words;
use llamatron_strings::{errors, named};
use std::path::{Path, PathBuf};
use std::process::Command;

/// Where install_fluidsynth.sh puts FluidSynth, the Apple Silicon Homebrew's and then an Intel Mac's, and its SoundFont.
const HOMEBREW_FLUIDSYNTHS: [&str; 2] = ["/opt/homebrew/bin/fluidsynth", "/usr/local/bin/fluidsynth"];
const FLUIDSYNTH_COMMAND: &str = "fluidsynth";
const SOUNDFONT: &str = "soundfonts/GeneralUser-GS.sf2";
/// What turns FluidSynth off for a computer where it does not work.
const DISABLED_VARIABLE: &str = "NO_FLUIDSYNTH";
const SWITCHED_ON: &str = "1";
/// How FluidSynth's program plays a MIDI file into a WAV file, faster than real time.
const SAMPLE_RATE: u32 = 44100;
const RENDER_OPTIONS: [&str; 6] = ["-n", "-i", "-q", "-r", "44100", "-F"];
/// How long the built-in tracks ring on after the song's end.
const TAIL_SECONDS: f64 = 3.0;
/// What the backend's notes are, by their kind, and the instrument kind that is built in.
const NOTE_ON: i64 = 0;
const NOTE_OFF: i64 = 1;
const ALL_OFF: i64 = 2;
const SCENE_STARTED: i64 = 4;
const CONTROL: i64 = 5;
/// The song's tempo in two parts, coarse then fine, for a built-in instrument's LFOs that follow it (the backend's
/// engine/mod.rs).
const TEMPO_COARSE: i64 = 6;
const TEMPO_FINE: i64 = 7;
/// Playback starting, at the export's start, so that a built-in instrument's modulators run (the backend's PLAY_STARTED).
const PLAY_STARTED: i64 = 8;
const BUILT_IN: &str = "built_in";
/// A 16-bit sample's most, and the level a normalized file peaks at, 1 dB below full scale.
const HIGHEST_SAMPLE: f64 = 32767.0;
const LOWEST_SAMPLE: f64 = -32768.0;
const PEAK_DECIBELS: f64 = -1.0;
const CHANNELS: usize = 2;
/// Half steps a set's octave numbers apart, for the drum tuning note.
const HALF_STEPS_PER_OCTAVE: i64 = 12;

/// Where FluidSynth's program is: the Mac's own Homebrew's, else wherever PATH finds it.
pub fn fluidsynth_path() -> Option<PathBuf> {
    if let Some(found) = HOMEBREW_FLUIDSYNTHS.iter().map(PathBuf::from).find(|path| path.is_file()) {
        return Some(found);
    }
    let path = std::env::var_os("PATH")?;
    std::env::split_paths(&path)
        .map(|folder| folder.join(FLUIDSYNTH_COMMAND))
        .find(|path| path.is_file())
}

/// Where FluidSynth's SoundFont is.
pub fn soundfont_path() -> PathBuf {
    let home = std::env::var_os("HOME").map(PathBuf::from).unwrap_or_default();
    home.join(SOUNDFONT)
}

/// Whether FluidSynth and its SoundFont are both installed and FluidSynth is not turned off.
pub fn fluidsynth_installed() -> bool {
    if std::env::var(DISABLED_VARIABLE).is_ok_and(|value| value == SWITCHED_ON) {
        return false;
    }
    fluidsynth_path().is_some() && soundfont_path().is_file()
}

/// Write the current song's WAV file at a path: its FluidSynth tracks and its built-in tracks, mixed and normalized.
pub fn export(document: &Document, grid: &Grid, path: &Path) -> Result<(), String> {
    let setlist = document.get_setlist();
    let song = document.song();
    let instrument_of = |track: &str| -> Option<&llamatron_model::objects::setlist::Instrument> {
        let name = song.get_track(track)?.get_written(TrackSetting::INSTRUMENT)?.as_str()?.to_string();
        match setlist.get_item(Section::INSTRUMENTS, &name) {
            Some(Item::Instrument(instrument)) => Some(instrument),
            _ => None,
        }
    };
    let sounding: Vec<&str> = grid.columns.iter().filter(|column| !column.mute).map(|column| column.name.as_str()).collect();
    let on_fluidsynth: Vec<String> = sounding
        .iter()
        .filter(|track| {
            instrument_of(track)
                .and_then(|held| held.get_written(InstrumentSetting::DEVICE))
                .and_then(Data::as_str)
                == Some(FLUIDSYNTH_DEVICE)
        })
        .map(|track| track.to_string())
        .collect();
    let drums_from = setlist
        .get_written(SetlistSetting::DEFAULT_DRUM_OCTAVE)
        .and_then(Data::as_whole)
        .map_or(3, |octave| octave as i64)
        * HALF_STEPS_PER_OCTAVE;
    let mut built_in = Vec::new();
    for track in &sounding {
        let Some(instrument) = instrument_of(track) else { continue };
        if instrument.get_written(InstrumentSetting::KIND).and_then(Data::as_str) != Some(BUILT_IN) {
            continue;
        }
        let spec = synth_spec(&Sound::of(instrument), drums_from);
        if let Some(timed) = llamatron_exporters::midi::timed_track(grid, track).map_err(refusal)? {
            built_in.push((spec, timed));
        }
    }
    if on_fluidsynth.is_empty() && built_in.is_empty() {
        return Err(errors::ERR_NO_FLUIDSYNTH_TRACKS.to_string());
    }
    if !on_fluidsynth.is_empty() && !fluidsynth_installed() {
        return Err(errors::ERR_WAV_NEEDS_FLUIDSYNTH.to_string());
    }

    let scratch = Scratch::new()?;
    let mut parts = Vec::new();
    if !on_fluidsynth.is_empty() {
        let kept = |column: &llamatron_engine::realizer::GridColumn| on_fluidsynth.contains(&column.name);
        let (_, midi) = llamatron_exporters::midi::song_file_of(grid, &document.export_name(), true, &kept).map_err(refusal)?;
        parts.push(read_wave(&render_fluidsynth(&scratch.folder, &midi)?)?);
    }
    if !built_in.is_empty() {
        let seconds = llamatron_exporters::midi::song_seconds(grid).map_err(refusal)? + TAIL_SECONDS;
        let rendered = scratch.folder.join("built_in.wav");
        render_built_in(&built_in, seconds, &rendered)?;
        parts.push(read_wave(&rendered)?);
    }
    write_mix(path, &parts)
}

/// A refused render's reason.
fn refusal(error: llamatron_engine::error::RenderError) -> String {
    match error {
        llamatron_engine::error::RenderError::Refused(problem) => problem,
    }
}

/// A folder of the export's own for its passing files, removed when the export is done.
struct Scratch {
    folder: PathBuf,
}

impl Scratch {
    /// A new, empty folder in the computer's temporary folder.
    fn new() -> Result<Scratch, String> {
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |since| since.as_nanos());
        let folder = std::env::temp_dir().join(format!("llamatron-wav-{}-{stamp}", std::process::id()));
        std::fs::create_dir_all(&folder).map_err(|error| error.to_string())?;
        Ok(Scratch { folder })
    }
}

impl Drop for Scratch {
    /// Remove the folder and what is left in it.
    fn drop(&mut self) {
        // Nothing is left to report a failure to on the way out; the folder is the temporary folder's to clear.
        let _ = std::fs::remove_dir_all(&self.folder);
    }
}

/// Play the FluidSynth tracks' MIDI file into a WAV file in the scratch folder, and return its path.
fn render_fluidsynth(folder: &Path, midi: &[u8]) -> Result<PathBuf, String> {
    let program = fluidsynth_path().ok_or_else(|| errors::ERR_WAV_NEEDS_FLUIDSYNTH.to_string())?;
    let file = folder.join("song.mid");
    let played = folder.join("fluidsynth.wav");
    std::fs::write(&file, midi).map_err(|error| error.to_string())?;
    let finished = Command::new(program)
        .args(RENDER_OPTIONS)
        .arg(&played)
        .arg(soundfont_path())
        .arg(&file)
        .output()
        .map_err(|error| named(errors::ERR_FLUIDSYNTH_RENDER_FAILED, &[(fill::PROBLEM, error.to_string().as_str().into())]))?;
    if !finished.status.success() || !played.is_file() {
        let said = if finished.stderr.is_empty() { &finished.stdout } else { &finished.stderr };
        let problem = String::from_utf8_lossy(said).trim().to_string();
        return Err(named(errors::ERR_FLUIDSYNTH_RENDER_FAILED, &[(fill::PROBLEM, problem.as_str().into())]));
    }
    Ok(played)
}

/// Render the built-in tracks through the backend's renderer, run here on this thread, into a WAV file of floats, as
/// fast as it can.
fn render_built_in(tracks: &[(Data, llamatron_exporters::midi::TimedTrack)], seconds: f64, path: &Path) -> Result<(), String> {
    let failed = |answer: &str| named(errors::ERR_SYNTH_DAEMON_RENDER_FAILED, &[(fill::ANSWER, answer.into())]);
    let (to_renderer, mut inbox) = std::sync::mpsc::channel::<rmpv::Value>();
    let message = |items: Vec<Data>| crate::msgpack::value_of(&Data::List(items));
    for (number, (spec, timed)) in tracks.iter().enumerate() {
        let number = Data::Whole(number as i128);
        let _ = to_renderer.send(message(vec![Data::text(file_format::TrackSetting::INSTRUMENT), number.clone(), spec.clone()]));
        let _ = to_renderer.send(message(vec![
            Data::text(file_format::SetlistSetting::NOTES),
            Data::List(offline_notes(&number, timed)),
        ]));
    }
    let _ = to_renderer.send(message(vec![
        Data::text(words::RENDER),
        Data::text(&path.display().to_string()),
        Data::Float(seconds),
    ]));
    let _ = to_renderer.send(message(vec![Data::text(words::CLOSE)]));
    drop(to_renderer);
    let answers = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));
    let kept = answers.clone();
    let output: llamatron_backend::daemon::Output = std::sync::Arc::new(move |answer: &rmpv::Value| {
        if let Ok(mut kept) = kept.lock() {
            kept.push(answer.clone());
        }
    });
    llamatron_backend::daemon::render(SAMPLE_RATE as f64, output, &mut inbox);
    let answers = answers.lock().map(|held| held.clone()).unwrap_or_default();
    let rendered = answers
        .iter()
        .any(|answer| answer.as_array().and_then(|items| items.first()).and_then(rmpv::Value::as_str) == Some(words::RENDERED));
    if !rendered {
        let said = answers.last().map(ToString::to_string).unwrap_or_default();
        return Err(failed(&said));
    }
    Ok(())
}

/// A track's clip starts, notes and endings as the backend takes notes: seconds, kind, instrument, pitch and velocity.
fn offline_notes(number: &Data, timed: &llamatron_exporters::midi::TimedTrack) -> Vec<Data> {
    let note = |when: f64, kind: i64, pitch: i64, velocity: i64| {
        Data::List(vec![
            Data::Float(when),
            Data::Whole(kind as i128),
            number.clone(),
            Data::Whole(pitch as i128),
            Data::Whole(velocity as i128),
        ])
    };
    let song_start = 0.0;
    let mut notes = vec![note(song_start, PLAY_STARTED, 0, 0)];
    notes.extend(timed.scene_starts.iter().map(|when| note(*when, SCENE_STARTED, 0, 0)));
    for (when, pitch, velocity) in &timed.notes {
        let kind = if *velocity == 0 { NOTE_OFF } else { NOTE_ON };
        notes.push(note(*when, kind, *pitch, *velocity));
    }
    notes.extend(timed.endings.iter().map(|when| note(*when, ALL_OFF, 0, 0)));
    notes.extend(timed.controls.iter().map(|(when, number, value)| note(*when, CONTROL, *number, *value)));
    for (when, tempo) in &timed.tempos {
        let (coarse, fine) = crate::realtime::timeline::tempo_parts(*tempo);
        notes.push(note(*when, TEMPO_COARSE, 0, coarse));
        notes.push(note(*when, TEMPO_FINE, 0, fine));
    }
    notes
}

/// A WAV file's rate and samples as floats from -1 to 1, two to a frame: 16-bit PCM, as FluidSynth writes, or 32-bit
/// float, as llamatron-backend writes.
fn read_wave(path: &Path) -> Result<(u32, Vec<f64>), String> {
    let data = std::fs::read(path).map_err(|error| format!("{}: {error}", path.display()))?;
    let find = |tag: &[u8]| data.windows(4).position(|window| window == tag);
    let (Some(format), Some(body)) = (find(b"fmt "), find(b"data")) else {
        return Err(format!("{}: not a WAV file", path.display()));
    };
    let read_u16 = |at: usize| u16::from_le_bytes([data[at], data[at + 1]]);
    let channels = read_u16(format + 10) as usize;
    let rate = u32::from_le_bytes([data[format + 12], data[format + 13], data[format + 14], data[format + 15]]);
    let bits = read_u16(format + 22);
    let samples: Vec<f64> = match bits {
        32 => data[body + 8..]
            .as_chunks::<4>()
            .0
            .iter()
            .map(|bytes| f32::from_le_bytes(*bytes) as f64)
            .collect(),
        16 => data[body + 8..]
            .as_chunks::<2>()
            .0
            .iter()
            .map(|bytes| i16::from_le_bytes(*bytes) as f64 / HIGHEST_SAMPLE)
            .collect(),
        _ => {
            let words = [("path", path.display().to_string().as_str().into()), ("bits", (bits as i64).into())];
            return Err(named(errors::ERR_NOT_16_BIT_WAVE, &words));
        }
    };
    // A mono file is spread to both sides, so that every part mixes as two channels.
    let samples = if channels == 1 {
        samples.iter().flat_map(|sample| [*sample, *sample]).collect()
    } else {
        samples
    };
    Ok((rate, samples))
}

/// Write the parts' mix as a 16-bit stereo WAV file at full level, then normalize it so that its loudest moment is 1 dB below
/// full scale: the whole file moves by one amount, so that its quiet and loud parts keep their difference.
fn write_mix(path: &Path, parts: &[(u32, Vec<f64>)]) -> Result<(), String> {
    let rate = parts.first().map_or(SAMPLE_RATE, |(rate, _)| *rate);
    let length = parts.iter().map(|(_, samples)| samples.len()).max().unwrap_or(0);
    let mut mix = vec![0.0; length - length % CHANNELS];
    for (_, samples) in parts {
        for (place, sample) in samples.iter().enumerate().take(mix.len()) {
            mix[place] += sample;
        }
    }
    let loudest = mix.iter().fold(0.0f64, |most, sample| most.max(sample.abs()));
    if loudest > 1.0 {
        mix.iter_mut().for_each(|sample| *sample /= loudest);
    }
    let whole: Vec<i16> = mix.iter().map(|sample| (sample * HIGHEST_SAMPLE).round_ties_even() as i16).collect();
    let peak = whole.iter().map(|sample| (*sample as i32).abs()).max().unwrap_or(0);
    let normalized: Vec<i16> = if peak == 0 {
        whole
    } else {
        let factor = HIGHEST_SAMPLE * 10f64.powf(PEAK_DECIBELS / 20.0) / peak as f64;
        whole
            .iter()
            .map(|sample| (*sample as f64 * factor).round_ties_even().clamp(LOWEST_SAMPLE, HIGHEST_SAMPLE) as i16)
            .collect()
    };
    let mut bytes = Vec::with_capacity(44 + normalized.len() * 2);
    let body = (normalized.len() * 2) as u32;
    bytes.extend(b"RIFF");
    bytes.extend((36 + body).to_le_bytes());
    bytes.extend(b"WAVEfmt ");
    bytes.extend(16u32.to_le_bytes());
    bytes.extend(1u16.to_le_bytes());
    bytes.extend((CHANNELS as u16).to_le_bytes());
    bytes.extend(rate.to_le_bytes());
    bytes.extend((rate * CHANNELS as u32 * 2).to_le_bytes());
    bytes.extend((CHANNELS as u16 * 2).to_le_bytes());
    bytes.extend(16u16.to_le_bytes());
    bytes.extend(b"data");
    bytes.extend(body.to_le_bytes());
    for sample in normalized {
        bytes.extend(sample.to_le_bytes());
    }
    let partial = path.with_extension("wav.part");
    std::fs::write(&partial, bytes).map_err(|error| format!("{}: {error}", partial.display()))?;
    std::fs::rename(&partial, path).map_err(|error| format!("{}: {error}", path.display()))
}
