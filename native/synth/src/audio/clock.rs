// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The clock notes are timed on: `mach_absolute_time`, in seconds, which is the very clock the tracker's
//! `time.perf_counter` reads on macOS, so that a note's time needs no conversion between the two processes.

use std::sync::OnceLock;

static SCALE: OnceLock<f64> = OnceLock::new();

/// Seconds on the shared monotonic clock.
#[cfg(target_os = "macos")]
// libc marks the mach calls deprecated in favour of another crate; they are the very calls Python's perf_counter makes.
#[allow(deprecated)]
pub fn now() -> f64 {
    let scale = *SCALE.get_or_init(|| {
        let mut info = libc::mach_timebase_info { numer: 0, denom: 0 };
        // SAFETY: mach_timebase_info only writes the two numbers of the struct it is given, which lives on this stack.
        unsafe { libc::mach_timebase_info(&mut info) };
        info.numer as f64 / info.denom as f64 / 1e9
    });
    // SAFETY: mach_absolute_time reads a counter and has no preconditions.
    let ticks = unsafe { libc::mach_absolute_time() };
    ticks as f64 * scale
}

/// Seconds on the shared monotonic clock: elsewhere, CLOCK_MONOTONIC, which Python's perf_counter also reads on Linux.
#[cfg(not(target_os = "macos"))]
pub fn now() -> f64 {
    let _ = &SCALE;
    let mut time = libc::timespec { tv_sec: 0, tv_nsec: 0 };
    // SAFETY: clock_gettime only writes the struct it is given, which lives on this stack.
    unsafe { libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut time) };
    time.tv_sec as f64 + time.tv_nsec as f64 / 1e9
}
