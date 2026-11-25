# Building the Backend

llamatron's backend is a small program of its own, `llamatron-backend`,
which plays the built-in synths and FluidSynth and sends every MIDI event on
time. It is written in Rust, a language that compiles to fast native code, so
that many instruments can play at once with steady timing. llamatron starts
it, sends it the notes, and closes it again; nobody runs it by hand.

The backend is built from its source on your computer, once, by one script.
No knowledge of Rust is needed: the script checks what building needs, offers
to install whatever is missing, and installs nothing unless you say yes.

```
sh internal_tools/build_backend.sh
```

`sh user_scripts/setup.sh` runs the same script at the end of setting up, so
on a fresh copy of llamatron the backend is usually built already. Until it is
built, llamatron plays through its older Python processes, which are slower
and run out of room with many instruments.

## What Building Needs

The script looks for each of these in turn and stops at the first that is
missing, saying what to do.

| What | Why | How the script helps |
| --- | --- | --- |
| Apple's command line tools (Mac) | The compiler and linker every program on a Mac is built with. | Offers to start Apple's installer, `xcode-select --install`. |
| The ALSA headers and pkg-config (Linux) | The sound library the backend plays through on Linux. | Names the packages, such as `libasound2-dev` and `pkg-config`, since installing them needs your system's package manager and your password. |
| Rust | The language the backend is written in, with its build tool, cargo. | Offers to install it with rustup, the Rust project's own installer. |

rustup installs Rust into two folders in your home folder, `~/.cargo` and
`~/.rustup`. It needs no password and touches nothing else, and
`rustup self uninstall` removes it again.

On an Apple Silicon Mac, the script checks that Rust builds Apple Silicon
programs. A Rust installed for Intel Macs builds a program that runs slowly
under Rosetta; the script says how to switch it:

```
rustup set default-host aarch64-apple-darwin
rustup toolchain install stable
```

## What Building Makes

The script builds `native/backend/` into one file,
`native/backend/target/release/llamatron-backend`, where llamatron finds it. The
first build downloads the backend's libraries and takes a minute or so;
running the script again rebuilds only what changed, in seconds. The
`native/backend/target/` folder holds everything the build makes and is never
committed.

Setting `LLAMATRON_BACKEND` to a path makes llamatron use the backend
there instead.

## Choosing the Python Processes

While llamatron's Python processes are still part of it, starting llamatron
with `LLAMATRON_PYTHON_SYNTH=1` plays the built-in synths on the Python engine,
`LLAMATRON_PYTHON_SENDER=1` sends MIDI through the Python sender, and
`LLAMATRON_FLUIDSYNTH_PROCESS=1` plays FluidSynth as its own program, for
comparing them:

```
LLAMATRON_PYTHON_SYNTH=1 ./llamatron.sh examples/synth/duck_blur.yml
```

## Logs

The backend writes what it did when it started and stopped, and any problem it
met, to small files in `~/.llamatron/`, keeping the newest few. They never hold
the music. If the sound stops or will not start, the newest file there says why.

## Problems

| What happens | What to do |
| --- | --- |
| The script says Rust builds Intel programs. | Run the two `rustup` commands above, then the script again. |
| `linker 'cc' not found` | Apple's command line tools (Mac) or your system's compiler are missing: run the script again and say yes, or install `build-essential` on Linux. |
| `alsa` not found on Linux | Install your system's ALSA development package and `pkg-config`. |
| llamatron says the backend is not built. | Run `sh internal_tools/build_backend.sh`. |

[Backend](BACKEND.md) explains how the backend works inside, for
anyone changing it.
