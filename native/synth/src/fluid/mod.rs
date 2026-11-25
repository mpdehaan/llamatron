// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! FluidSynth as an engine of the daemon: the General MIDI sampler that plays every demo with no synthesizer, rendered in
//! the daemon's own audio callback, so that it and the built-in synths share one stream and one clock, sample for sample.
//!
//! The library is loaded at run time, from the path the tracker gives (beside the installed `fluidsynth` program), never
//! linked at build time, so that building the daemon never needs FluidSynth; without it the tracker plays FluidSynth as a
//! process of its own, as before. The synth is made and its SoundFont loaded on the reader thread, then handed whole to the
//! audio thread, the only thread that touches it afterwards, which is why FluidSynth's own locking is turned off.

use libloading::Library;
use std::ffi::{c_char, c_double, c_int, c_void, CString};

const SAMPLE_RATE: &str = "synth.sample-rate";
const GAIN: &str = "synth.gain";
const THREAD_SAFE: &str = "synth.threadsafe-api";
const FAILED: c_int = -1;
const NOTE_OFF: u8 = 0x80;
const NOTE_ON: u8 = 0x90;
const CONTROL_CHANGE: u8 = 0xB0;
const PROGRAM_CHANGE: u8 = 0xC0;
const CHANNEL_PRESSURE: u8 = 0xD0;
const PITCH_BEND: u8 = 0xE0;
const KIND_MASK: u8 = 0xF0;
const CHANNEL_MASK: u8 = 0x0F;

/// Why FluidSynth could not be made ready.
#[derive(Debug, thiserror::Error)]
pub enum FluidProblem {
    #[error("the FluidSynth library could not be loaded from {path}: {reason}")]
    Library { path: String, reason: String },
    #[error("the FluidSynth library has no {name}: {reason}")]
    Missing { name: &'static str, reason: String },
    #[error("FluidSynth could not make its synth")]
    NoSynth,
    #[error("FluidSynth could not load the SoundFont {path}")]
    SoundFont { path: String },
}

type NewSettings = unsafe extern "C" fn() -> *mut c_void;
type SetNumber = unsafe extern "C" fn(*mut c_void, *const c_char, c_double) -> c_int;
type SetWhole = unsafe extern "C" fn(*mut c_void, *const c_char, c_int) -> c_int;
type NewSynth = unsafe extern "C" fn(*mut c_void) -> *mut c_void;
type LoadSoundFont = unsafe extern "C" fn(*mut c_void, *const c_char, c_int) -> c_int;
type ThreeWholes = unsafe extern "C" fn(*mut c_void, c_int, c_int, c_int) -> c_int;
type TwoWholes = unsafe extern "C" fn(*mut c_void, c_int, c_int) -> c_int;
type OneWhole = unsafe extern "C" fn(*mut c_void, c_int) -> c_int;
type WriteFloat = unsafe extern "C" fn(*mut c_void, c_int, *mut c_void, c_int, c_int, *mut c_void, c_int, c_int) -> c_int;
type Delete = unsafe extern "C" fn(*mut c_void);

/// The calls the daemon makes, looked up once when the library loads.
struct Calls {
    new_settings: NewSettings,
    set_number: SetNumber,
    set_whole: SetWhole,
    new_synth: NewSynth,
    load_soundfont: LoadSoundFont,
    note_on: ThreeWholes,
    note_off: TwoWholes,
    control_change: ThreeWholes,
    program_change: TwoWholes,
    pitch_bend: TwoWholes,
    channel_pressure: TwoWholes,
    all_sounds_off: OneWhole,
    write_float: WriteFloat,
    delete_synth: Delete,
    delete_settings: Delete,
}

/// A FluidSynth synth with its SoundFont loaded, and the library it came from, which must outlive its calls.
pub struct Fluid {
    calls: Calls,
    settings: *mut c_void,
    synth: *mut c_void,
    _library: Library,
}

// SAFETY: a Fluid is made on the reader thread and then moved, whole, to the audio thread, which alone calls it from then on;
// no two threads ever touch one synth, so its raw pointers may travel between threads.
unsafe impl Send for Fluid {}

/// Look up one call in the library.
fn call<T: Copy>(library: &Library, name: &'static str) -> Result<T, FluidProblem> {
    let symbol = format!("{name}\0");
    // SAFETY: the type each call is read as is the one FluidSynth's public header declares for that name.
    unsafe {
        library
            .get::<T>(symbol.as_bytes())
            .map(|found| *found)
            .map_err(|problem| FluidProblem::Missing {
                name,
                reason: problem.to_string(),
            })
    }
}

fn calls_of(library: &Library) -> Result<Calls, FluidProblem> {
    Ok(Calls {
        new_settings: call(library, "new_fluid_settings")?,
        set_number: call(library, "fluid_settings_setnum")?,
        set_whole: call(library, "fluid_settings_setint")?,
        new_synth: call(library, "new_fluid_synth")?,
        load_soundfont: call(library, "fluid_synth_sfload")?,
        note_on: call(library, "fluid_synth_noteon")?,
        note_off: call(library, "fluid_synth_noteoff")?,
        control_change: call(library, "fluid_synth_cc")?,
        program_change: call(library, "fluid_synth_program_change")?,
        pitch_bend: call(library, "fluid_synth_pitch_bend")?,
        channel_pressure: call(library, "fluid_synth_channel_pressure")?,
        all_sounds_off: call(library, "fluid_synth_all_sounds_off")?,
        write_float: call(library, "fluid_synth_write_float")?,
        delete_synth: call(library, "delete_fluid_synth")?,
        delete_settings: call(library, "delete_fluid_settings")?,
    })
}

fn text(value: &str) -> CString {
    // The names and paths given never hold a zero byte; one that did would be cut there, and the call would fail and say so.
    CString::new(value.replace('\0', "")).unwrap_or_default()
}

impl Fluid {
    /// Load the library, make a synth at a sample rate and gain, and load a SoundFont into it.
    pub fn load(library_path: &str, soundfont: &str, rate: f64, gain: f64) -> Result<Fluid, FluidProblem> {
        // SAFETY: loading a library runs its initializers; FluidSynth's do nothing but set up its own tables.
        let library = unsafe { Library::new(library_path) }.map_err(|problem| FluidProblem::Library {
            path: library_path.to_string(),
            reason: problem.to_string(),
        })?;
        let calls = calls_of(&library)?;
        // SAFETY: every call below is made with the pointers FluidSynth itself returned, checked for null, and with C strings
        // that live until the call returns.
        unsafe {
            let settings = (calls.new_settings)();
            if settings.is_null() {
                return Err(FluidProblem::NoSynth);
            }
            (calls.set_number)(settings, text(SAMPLE_RATE).as_ptr(), rate);
            (calls.set_number)(settings, text(GAIN).as_ptr(), gain);
            (calls.set_whole)(settings, text(THREAD_SAFE).as_ptr(), 0);
            let synth = (calls.new_synth)(settings);
            if synth.is_null() {
                (calls.delete_settings)(settings);
                return Err(FluidProblem::NoSynth);
            }
            let fluid = Fluid {
                calls,
                settings,
                synth,
                _library: library,
            };
            if (fluid.calls.load_soundfont)(synth, text(soundfont).as_ptr(), 1) == FAILED {
                return Err(FluidProblem::SoundFont { path: soundfont.to_string() });
            }
            Ok(fluid)
        }
    }

    /// Play one MIDI message, its status byte and two data bytes.
    pub fn play(&mut self, status: u8, first: u8, second: u8) {
        let channel = (status & CHANNEL_MASK) as c_int;
        let (first, second) = (first as c_int, second as c_int);
        let calls = &self.calls;
        // SAFETY: the synth is this Fluid's own, alive until it is dropped, and FluidSynth checks every number it is given.
        unsafe {
            match status & KIND_MASK {
                NOTE_ON if second > 0 => (calls.note_on)(self.synth, channel, first, second),
                NOTE_ON | NOTE_OFF => (calls.note_off)(self.synth, channel, first),
                CONTROL_CHANGE => (calls.control_change)(self.synth, channel, first, second),
                PROGRAM_CHANGE => (calls.program_change)(self.synth, channel, first),
                CHANNEL_PRESSURE => (calls.channel_pressure)(self.synth, channel, first),
                PITCH_BEND => (calls.pitch_bend)(self.synth, channel, first | (second << 7)),
                _ => 0,
            };
        }
    }

    /// Stop every sound at once, on every channel.
    pub fn silence(&mut self) {
        // SAFETY: as in play; -1 is FluidSynth's every channel.
        unsafe {
            (self.calls.all_sounds_off)(self.synth, -1);
        }
    }

    /// Add the synth's next samples to the two channels given, which are as long as each other.
    pub fn render(&mut self, left: &mut [f32], right: &mut [f32], scratch: &mut [f32]) {
        let count = left.len().min(right.len()).min(scratch.len() / 2);
        if count == 0 {
            return;
        }
        let (into_left, into_right) = scratch.split_at_mut(scratch.len() / 2);
        // SAFETY: both buffers hold at least count floats, and FluidSynth writes exactly count to each, one apart.
        unsafe {
            (self.calls.write_float)(
                self.synth,
                count as c_int,
                into_left.as_mut_ptr() as *mut c_void,
                0,
                1,
                into_right.as_mut_ptr() as *mut c_void,
                0,
                1,
            );
        }
        for place in 0..count {
            left[place] += into_left[place];
            right[place] += into_right[place];
        }
    }
}

impl Drop for Fluid {
    fn drop(&mut self) {
        // SAFETY: the synth and settings are this Fluid's own and deleted once, synth first, as FluidSynth asks.
        unsafe {
            (self.calls.delete_synth)(self.synth);
            (self.calls.delete_settings)(self.settings);
        }
    }
}
