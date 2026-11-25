# Building the Synth Engine

llamatron's built-in synths are played by a small program of their own, the
synth engine, called `llamatron-synth`. It is written in Rust, a language that
compiles to fast native code, so that many instruments can play at once with
steady timing. llamatron starts it, sends it the notes, and closes it again;
nobody runs it by hand.

The engine is built from its source on your computer, once, by one script.
No knowledge of Rust is needed: the script checks what building needs, offers
to install whatever is missing, and installs nothing unless you say yes.

```
sh internal_tools/build_synth.sh
```

`sh user_scripts/setup.sh` runs the same script at the end of setting up, so
on a fresh copy of llamatron the engine is usually built already. Until it is
built, the built-in synths play on llamatron's older Python engine, which is
slower and runs out of room with many instruments.

## What Building Needs

The script looks for each of these in turn and stops at the first that is
missing, saying what to do.

| What | Why | How the script helps |
| --- | --- | --- |
| Apple's command line tools (Mac) | The compiler and linker every program on a Mac is built with. | Offers to start Apple's installer, `xcode-select --install`. |
| The ALSA headers and pkg-config (Linux) | The sound library the engine plays through on Linux. | Names the packages, such as `libasound2-dev` and `pkg-config`, since installing them needs your system's package manager and your password. |
| Rust | The language the engine is written in, with its build tool, cargo. | Offers to install it with rustup, the Rust project's own installer. |

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

The script builds `native/synth/` into one file,
`native/synth/target/release/llamatron-synth`, where llamatron finds it. The
first build downloads the engine's libraries and takes a minute or so;
running the script again rebuilds only what changed, in seconds. The
`native/synth/target/` folder holds everything the build makes and is never
committed.

Setting `LLAMATRON_SYNTH_DAEMON` to a path makes llamatron use the engine
there instead.

## Choosing the Python Engine

While the Python engine is still part of llamatron, starting llamatron with
`LLAMATRON_PYTHON_SYNTH=1` plays the built-in synths on it instead, for
comparing the two:

```
LLAMATRON_PYTHON_SYNTH=1 ./llamatron.sh examples/synth/duck_blur.yml
```

## Logs

The engine writes what it did when it started and stopped, and any problem it
met, to small files in `~/.llamatron/`, keeping the newest few. They never hold
the music. If the built-in synths stop or will not start, the newest file there
says why.

## Problems

| What happens | What to do |
| --- | --- |
| The script says Rust builds Intel programs. | Run the two `rustup` commands above, then the script again. |
| `linker 'cc' not found` | Apple's command line tools (Mac) or your system's compiler are missing: run the script again and say yes, or install `build-essential` on Linux. |
| `alsa` not found on Linux | Install your system's ALSA development package and `pkg-config`. |
| The built-in synths say the engine is not built. | Run `sh internal_tools/build_synth.sh`. |

[Synth Engine](SYNTH_ENGINE.md) explains how the engine works inside, for
anyone changing it.
