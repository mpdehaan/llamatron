# Recording

This page covers making a video of the tracker playing a set, for YouTube and similar sites, with the sound of your synthesizers or of FluidSynth. One command records a take: the tracker opens on the splash, moves to Arrange, plays the song from the top and quits when the song ends, while the Mac records the terminal window and the sound. The recorder works on a Mac alone, with nothing installed but one audio driver, and builds on the MIDI setup that [MIDI Setup](MIDI_SETUP.md) describes.

## Requirements

The recorder needs a MIDI port, a loopback audio device, a Multi-Output Device, Screen Recording permission and Xcode's command line tools. The installing page [Recording](INSTALLING_RECORDING.md) describes setting each up.

## Takes

Size the terminal window the way the video should look, 16 by 9 for video sites, and run from the project folder:

```
sh user_scripts/record.sh examples/learning/01_hello_world.yml
```

The recorder records the set you name, after asking whether the take shows the clips on Arrange or a visualizer mode over the clip area. `01_hello_world.yml`, three seconds of a C major scale on two tracks, is the best set to record first. Any set, your own or anyone's, can be recorded, with the options described below:

```
sh user_scripts/record.sh examples/learning/12_sailor_arpeggiator.yml
sh user_scripts/record.sh my_set.yml --track-assign 1,1,2
sh user_scripts/record.sh my_set.yml --use-driver "My Synth" --max-seconds 60
```

Then leave the window alone until the tracker quits. After the song, the tracker shows the splash again, for as long as at the start, and holds it five more seconds; the recorder then cuts the last four seconds off the video with the Mac's own `avconvert`, so the video ends on the splash rather than on the terminal the tracker quits back to. Before the take, the recorder prints what it set up:

```
MIDI goes out of (IAC Driver Bus 1)
sound is recorded from (BlackHole 2ch)
  track (lead) plays through (RECORDER 1) on channel 1
  track (bass) plays through (RECORDER 2) on channel 2
recording window 72 for up to 52 s: 6 s of splash, 1 s on Arrange, the song (42 s), 2 s to ring out
wrote recordings/sailor_arpeggiator.mov (18.3 MB)
```

The video is `recordings/<set>.mov` in the project folder, which git ignores, and a second take of the same set replaces the first. The video is an H.264 QuickTime file, which YouTube accepts as it is.

### FluidSynth Takes

Every example plays through FluidSynth as it comes, so a take of an example needs no DAW, no MIDI port and no Live set. With FluidSynth installed, as [FluidSynth](FLUIDSYNTH.md) describes, a FluidSynth take needs only BlackHole, Screen Recording permission and Xcode's command line tools from the [requirements](INSTALLING_RECORDING.md). Run:

```
sh user_scripts/record.sh --sound fluidsynth examples/learning/01_hello_world.yml
```

`record.sh --sound fluidsynth` takes the set and asks for the view as `record.sh` does, and plays the set's own instruments, every instrument whose Device is `*FluidSynth` playing through FluidSynth. FluidSynth's sound goes to your Multi-Output Device of BlackHole and your speakers, as in step 3 of the [requirements](INSTALLING_RECORDING.md), when you have one, so both the recording and you hear the take; otherwise the sound goes straight into BlackHole, which your speakers don't play. `--fluidsynth-output` chooses another output:

```
sh user_scripts/record.sh --sound fluidsynth examples/learning/01_hello_world.yml --fluidsynth-output "Mac Studio Speakers"
```

Only the recorder sends FluidSynth's sound anywhere but the Mac's usual output, through the `LLAMATRON_FLUIDSYNTH_AUDIO_DEVICE` environment variable the recorder sets for the take, so playing a set in the tracker never needs BlackHole.

### Performed Takes

An ordinary take plays the song from the top by itself and ends when the song does. To perform instead, launching scenes and clips, editing as the song plays, and ending when you choose, run:

```
sh user_scripts/record.sh --interactive examples/learning/01_hello_world.yml
sh user_scripts/record.sh --sound fluidsynth --interactive examples/learning/01_hello_world.yml
```

The interactive scripts take the set, ask for the view, and set up the sound as `record.sh` and `record.sh --sound fluidsynth` do. After the splash, Arrange waits with the cursor on the corner at the top left, where `▶ song` shows, and nothing plays until you press `Space` there. Then perform with anything Arrange does: `Space` on a scene's name or a clip, the arrows, and the rest. To end the take, return to the corner, which now shows `■ song`, and press `Space`, or press `Esc` anywhere on Arrange. What played rings out, the splash shows again, and the tracker quits, so the video ends on the splash as an ordinary take's does. A song whose every clip loops, which an ordinary take refuses, can be performed, since you end the take yourself. The take ends by itself at `--max-seconds`, fifteen minutes unless set otherwise.

### Options

- **`--use-driver TEXT`** picks the MIDI output port: the first whose name holds the text, ignoring
  case. `IAC` is the default. With no port matching, the recorder stops and names the ports the Mac
  has.
- **`--track-assign-auto`**, the default, puts the first track of the song on channel 1, the second
  on channel 2 and so on.
- **`--track-assign 1,1,2`** names a channel for each track, in the song's track order, so that two
  tracks can share a synth. A `-` keeps a track's own instrument from the set, and the count has to
  match the song's tracks. Channels run from 1 to 16.
- **`--audio-device TEXT`** picks the audio input to record the sound from, the first whose name
  holds the text. `BlackHole` is the default. With no device matching, the recorder stops and says
  how to install BlackHole, so a silent take is never made by accident.
- **`--max-seconds N`** is the longest a take may run, fifteen minutes unless set otherwise. The
  tracker quits and the recording ends there, whatever is playing.
- **`--window-id N`** names the window to record when the recorder can't ask the terminal program
  for it. The recorder asks Terminal and iTerm2 itself.
- **`--visualizer NAME`** records that visualizer mode over the clip area instead of the clips,
  and **`--clips`** records the clips, either one without asking.
- **`--plain`** records a visualizer take in the older style, as Visualizer Takes below describes.
- **`--batch`** records a batch video, as Batch Recording below describes.

The recorder uses one MIDI device per take, so tracks can't yet play on different devices in one take.

## Visualizer Takes

A take can show a visualizer mode in place of the clips. [Visualizers](VISUALIZERS.md) describes every mode. When a take starts, the recorder asks whether it shows the clips or a visualizer, and which mode, listing them; `--visualizer NAME` names the mode, and `--clips` the clips, without asking.

A take that shows a visualizer, and isn't performed, is staged like a batch video by default: the video opens on the title on black, shows Arrange with READY, and then the clips and the visualizer take turns filling the screen inside a frame whose pulse changes colour at each scene, ten seconds each with a fade through black between, starting on the clips, recorded from the terminal's cells alone and written as `recordings/<set>_<mode>.mov`. Batch Recording below describes the same staging for every demo at once. `--no-alternate` shows the visualizer alone in the frame, and `--plain` records the older style instead, the visualizer over Arrange's clip area within the window. A take of the clips always records the older style.

To watch a mode without recording, to see it and tune it:

```
internal_tools/preview_visualizer.sh examples/learning/01_hello_world.yml
```

The preview sets up the set you name as the recorder does, with one instrument per channel on the IAC bus, then opens the tracker straight on Arrange with the visualizer showing, plays the song from the top and quits when the song ends. The preview records no video and needs no BlackHole, so the DAW plays through your speakers as usual. The preview asks which mode to show; its options are the recorder's `--use-driver` and `--track-assign`, and `--visualizer NAME` to name the mode without asking:

```
internal_tools/preview_visualizer.sh examples/by_genre/electronic/minimal_techno.yml --visualizer lava_lamp
```

## Batch Recording

`sh user_scripts/record_all.sh` records a video of every example through FluidSynth, shortest first,
each with the visualizer mode `internal_tools/visualizer_pairings.yml` gives it. A video opens on the title on black,
shows Arrange with READY, and then the clips and the visualizer take turns inside a frame whose pulse changes colour at each
scene, as Visualizer Takes above describes. The batch records the terminal's cells alone, with no window around them, as `recordings/<set>_<mode>.mov`. A demo
whose video is already in `recordings/` is left out, so running it again records only what is missing; delete a
video to record it again. Set up as for `record.sh --sound fluidsynth` above, and turn on Do Not Disturb, since anything
that appears over the window is recorded. `LLAMATRON_BATCH_RECORD_MAX=2` records only the two shortest, to try it
first.

## Recorder Changes to the Set

The recorder changes nothing on disk. The set is read, and in memory the set gains one instrument per channel used, named `RECORDER 1`, `RECORDER 2` and so on, on the driver's port. Each track is given the instrument of its channel, the set's Real Time switch is turned on, and the tracker is launched for recording on that set. The set's own instruments are set aside for the take, unless a `-` in `--track-assign` keeps one. A FluidSynth take keeps the set's own instruments. The file is never written, which is why the header shows no save mark during a take.

## Tracker Launch Options

The recorder runs the tracker with options of the `llamatron` command that make the tracker play a set by itself. You can use them yourself; none works with `--to`.

- **`--autoplay`** opens on Arrange and plays the song from the top, as `Space` on the `▶ song` corner does. The set needs instruments on its tracks and the Real Time switch on.
- **`--autoplay-quit-when-finished`** does the same and quits two seconds after the song's last note.
- **`--launch-for-recording`** opens on the splash for six seconds, shows the splash again for six seconds once the song has ended, leaves the save mark off the header, and refuses a song with a scene whose every clip loops. Real-time playback waits on such a scene for you to move on, so a recording of the song would never end; turn Loop off on one clip of the scene to record it. A looping clip beside one that ends is fine, since the scene below cuts the loop.
- **`--max-seconds N`** quits after that many seconds, whatever is playing.
- **`--visualizer NAME`** opens on Arrange with that visualizer mode over the clip area and plays the song from the top, as `--autoplay` does. [Visualizers](VISUALIZERS.md) lists the modes' names.
- **`--batch-video`**, with `--visualizer`, plays the batch video that Batch Recording describes.

`internal_tools/demo_splash_screen.sh` shows the splash alone, to look at it.

## Tutorial Videos

`internal_tools/tutorial.sh examples/learning/01_hello_world.yml` records a different kind of video: the tracker building that set from a new one, key by key, with a box of narration over the screen, then playing the set into the DAW and quitting. The tutorial needs the same setup as a take, and writes
`recordings/<set>_tutorial.mov`, the name of the set with `_tutorial` after it. The video starts on
the splash and ends the moment the tracker quits. `--no-play` builds the set without playing it,
and the video has no sound; `--no-video` runs the tutorial in the terminal without recording.

## Troubleshooting

- **No sound in the video, though Live played**: Live's output isn't the Multi-Output Device, or
  BlackHole isn't in it. Check the DAW's audio preferences and Audio MIDI Setup.
- **No picture, or a picture of the wrong window**: the recorder records the front window of the
  terminal program it runs in. Run it from the window you want recorded, and pass `--window-id`
  if the terminal program isn't Terminal or iTerm2.
- **The take stops at once with "bad value(s) in fds_to_keep" or a permission dialog**: Screen
  Recording permission was just granted; quit and reopen the terminal.
- **The tracker shows a dialog instead of playing**: the dialog gives the reason, usually that no
  track has an instrument, which `--track-assign-auto` provides, or that the driver's port isn't
  connected.
- **Asking Claude about a take**: save the recorder's output to a file and name the file in your
  question, with what you saw and heard:

  ```
  sh user_scripts/record.sh examples/learning/01_hello_world.yml > /tmp/record.txt 2>&1
  ```
