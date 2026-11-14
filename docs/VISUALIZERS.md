# Visualizers

While a song plays in real time, Arrange can show a visualizer in place of its clips: a moving picture in full colour, drawn in the terminal from the notes being played. The track names and scene names stay where they are, so the song's shape stays visible around the picture. This page covers showing a visualizer, every mode, and recording a visualizer.

[A video of the visualizers playing a song](https://www.youtube.com/watch?v=yt9NffJ1HF4) is on YouTube.

## Visualizer Controls

Visualizers need real-time playback, so the set's Real Time switch has to be on; `T` on the main screen turns it on, and every example has it on. On Arrange, these keys control the visualizer:

| Key | What it does |
| --- | --- |
| `Z` | Show the first visualizer mode over the clip area, and each press after that the next mode, and after the last, the clips again. |
| `Esc` | Bring the clips back, staying on Arrange. |

A visualizer can show while nothing plays, and follows the music once the song starts with `Space` on the corner. When the mode changes, the mode's name shows near the bottom for eight seconds, steady, and then goes away.

A visualizer hears the notes as they are played, with their tracks, pitches and velocities, and the song's beat. It never hears the sound itself, so a visualizer works the same through FluidSynth, a hardware synthesizer or a DAW, and never knows a note before the note plays.

## Modes

| Mode | What it shows |
| --- | --- |
| Lava lamp | A blob of colour for each track, drifting on a path of its own; every note splashes a ripple into it, held notes keep pushing, and the whole picture turns and breathes with the beat. Dark in silence. |
| Spectrum | A bar for each band of pitches, low at the left, lifted by each note's velocity, its neighbours a little, falling back steadily, with caps that hang and drop, green to yellow to red. |
| MilkDrop | A feedback picture in the spirit of the classic: each frame the last one warped, zoomed, turned and swirled, with notes splashed in on a slowly turning circle. |
| Llamas | An ASCII llama for each track that plays, strolling, turning at the edges, bobbing with the beat and hopping on its notes, growing and glowing as its track gets busier. |
| Hypercube | A tesseract turning in four dimensions, faster with the tempo, its edges shared out among the tracks' colours and glowing, pulsing with the beat. Bright even in silence. |
| Fireworks | A rocket for each note, bursting into sparks that fall and fade. |
| WarpZone | A ball for each track bouncing at the song's tempo, sending out slow rings. |
| Pipes | The old screensaver's pipes, one for each track, laid as its notes play. |
| Plasma | Waves of colour blended from the playing tracks' colours. |
| Maze | A maze carved on screen, with a walker for each track. |
| Mystify | The old screensaver's polygons with trails, over a field of stars, their corners following the held notes. |
| Laser Llama | A neon sunset over a perspective grid, and a llama firing beams on the notes. |
| Mandelbrot | The Mandelbrot set turning about a point on its edge, breathing in and out, coloured from the tracks' hues. |
| Life | Conway's Game of Life over a drifting gradient of the tracks' colours, stepping on the beat, with notes seeding new cells. |
| Digital rain | Green streams of ones and zeros falling down the screen, a stream for each note in the column of its pitch, as bright as the note is loud, the green brightening as more plays. |
| Cycle | Each mode above in turn, a new one every fifteen seconds. |

Every track has a colour of its own, which each mode leans by pitch and brightens by octave, so a track looks the same across modes.

## Eye Safety

No mode strobes or flashes, since some people are sensitive to flashing light. Brightness rises and falls gently, a limiter holds the whole picture down as more plays, and nothing jumps to white.

## Terminal Support

A visualizer draws in full colour where the terminal supports it, and in the nearest of 256 or 16 colours otherwise. A bigger window shows more detail, and every mode fits the window's size, starting again when the window is resized.

## Launching and Recording

A set can open straight onto a visualizer, playing, from the command line:

```
llamatron examples/by_genre/electronic/edm_density.yml --visualizer lava_lamp
```

The mode names on the command line are `lava_lamp`, `spectrum`, `milkdrop`, `llamas`, `hypercube`,
`fireworks`, `warpzone`, `pipes`, `plasma`, `maze`, `mystify`, `laser_llama`, `mandelbrot`, `life`,
`digital_rain` and `cycle`.

Every visualizer can be recorded into a video with its sound, as [Recording](RECORDING.md) describes.
