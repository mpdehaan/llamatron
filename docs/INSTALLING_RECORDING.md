# Recording

This page covers installing and setting up what the demo recorder needs before its first take. [Recording](RECORDING.md), the chapter on making videos, covers the takes themselves.

## Requirements

1. **A MIDI port the DAW listens on.** This is the IAC bus, as [MIDI Setup](MIDI_SETUP.md) describes,
   with a Live set holding a MIDI track for each channel used. The first track of a set plays on
   channel 1, the second on channel 2 and so on, so a Live set with a track listening to
   `IAC Driver Bus 1` on each of channels 1 to 4 covers a demo with four tracks. Each Live track's
   Monitor switch must be set to **In**. A take through FluidSynth needs none of this.
2. **A loopback audio device.** A Mac can't record what comes out of its speakers by itself, so the
   recorder records from BlackHole 2ch, a free, open-source loopback device. Install it from the
   project folder:

   ```
   sh user_scripts/install_blackhole.sh
   ```

   The script uses Homebrew, offering to install it first, and asks before installing BlackHole, an
   audio driver, for which macOS asks your password and restarts the audio; it does nothing when
   BlackHole is installed already, and ends by saying how to make the Multi-Output Device below.
   BlackHole can also be installed by hand from https://existential.audio/blackhole/, the 2-channel
   build. After installing, macOS may ask you to allow the driver in System Settings under Privacy
   & Security.
3. **A Multi-Output Device**, so that you hear the DAW while the take is recorded. In Audio MIDI Setup,
   press `+` at the bottom left, choose **Create Multi-Output Device**, and tick your speakers or
   headphones and **BlackHole 2ch**. Tick **Drift Correction** on BlackHole. In the DAW's audio
   preferences, choose that Multi-Output Device as the output. The DAW now plays into your speakers
   and into BlackHole at once, and the recorder reads BlackHole.
4. **Screen Recording permission** for your terminal program. The first take asks for it; after
   allowing it in System Settings under Privacy & Security, quit and reopen the terminal, since the
   permission reaches new processes only.
5. **Xcode's command line tools**, which most Macs that build software already have, for the
   `swift` command the recorder uses once per take to find BlackHole's id:

   ```
   xcode-select --install
   ```
