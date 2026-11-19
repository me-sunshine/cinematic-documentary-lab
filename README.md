# I connect two worlds: a five-slide animated hiring pitch

A 50-second visual pitch for Rashmi Singh, in two matching formats.

| File | What it is |
|---|---|
| `out/rashmi-singh-pitch.mp4` | The film: 1920 x 1080, 30 frames per second, 50 seconds, with an original music score |
| `out/rashmi-singh-pitch.pptx` | The editable PowerPoint: five slides, native shapes and text, staged animations, no sound |
| `film.html` | The source animation. Open it in a browser to watch it (silent) |
| `music.py` | The source of the score |

## The message

**I connect business understanding, structured execution and emerging technology.**

Each slide pairs a claim with its proof. The claim is the headline, bottom left. The proof is the evidence block, bottom right: a mint "EVIDENCE" tag, a figure that counts up in the film, what it measures and where it comes from.

| # | Claim | Visual | Evidence |
|---|---|---|---|
| 1 | I connect two worlds. | Business and technology move together and join | |
| 2 | I understand what business needs. | People, priorities and needs merge into one programme across 5 cities | ~100,000 students reached by one programme owned end to end. DMart Foundation, 2022–24 |
| 3 | I turn complexity into action. | Scattered dots become Challenge → Structure → People → Action | 200+ educators recruited and trained a year. DMart Foundation, 2022–24 |
| 4 | I turn curiosity into capability. | Business problem → AI workflow → human oversight, then the real prototype's review screen | 8 of 8 sample requests completed by the working AI prototype, 2026 |
| 5 | The bridge between business and technology. | The worlds rejoin; the bridge carries needs, action and capability, each with its evidence | All three figures together, the closing line and contact details |

Every figure comes from the CV or the prototype's test report. The screenshot on slide 4 is the prototype's actual review screen, showing one AI-suggested task edited by a reviewer and one rejected. The pitch does not present Rashmi as an AI engineer, and it claims no time saving because none has been measured.

## Music

An original score written in code (`music.py`), so there is no licence to clear and nothing can be taken down. It follows the story:

| Scene | What the music does |
|---|---|
| 1 | A held chord that resolves as the two worlds connect |
| 2 | A quiet plucked pattern enters |
| 3 | A soft pulse joins as the scattered dots become a process |
| 4 | The pulse lifts; a swell leads into the close |
| 5 | The pulse falls away and the harmony resolves home, then rings out |

A soft bell marks each headline and each evidence figure as it lands. The film's sound is normalised to −16 LUFS, the usual level for online video, with peaks below −1.5 dB. It was checked by measurement (levels, balance, no clipping), not by ear, so listen once before you send it.

## Design system

| Element | Rule |
|---|---|
| Colour | Ink `#0F1F1C` (ground), paper `#FBFCFB`, mint `#62D2B0`, muted `#9FB5AD` |
| Display type | Instrument Sans Bold, capitals, 100 px. The last line of every headline is mint |
| Supporting type | Instrument Serif Italic, on the first and last slides only |
| Evidence | Same block, same place on slides 2 to 4: tag, mint figure at 132 px, what it measures, source |
| Shapes | Solid paper circle = business. Mint ring = technology. Mint line = the connection |
| Layout | 120 px margins. Visual in the upper half, claim bottom left, evidence bottom right |
| Motion | Elements fade, rise, draw or count in once, in reading order. Nothing loops or bounces |

## Timing

| Scene | Starts | Length |
|---|---|---|
| 1 | 0.0 s | 7.5 s |
| 2 | 7.5 s | 9 s |
| 3 | 16.5 s | 9 s |
| 4 | 25.5 s | 11.5 s |
| 5 | 37.0 s | 13 s, the last frame held about 6 seconds |

## How the two formats differ

Same text, colours, evidence, order and reveal sequence.

| | Film | PowerPoint |
|---|---|---|
| Music | Yes | No |
| Figures counting up | Yes | Shown at their final value |
| Shapes moving together, lines drawing, dots gathering | Yes | Elements fade in step by step |
| Slide 4 | Large workflow, which then gives way to the screenshot | Compact workflow row above the screenshot, so the slide also reads correctly when edited or exported to PDF |
| Plays by itself | Always | Yes: each slide animates and advances automatically. Clicking also advances |

The PowerPoint layout was checked by converting it with LibreOffice. Its animations and automatic timings follow the PowerPoint file standard but have not been played in PowerPoint itself, so run the slide show once before using it.

## Fonts

Instrument Sans and Instrument Serif, both free under the SIL Open Font License. Install the four files in `fonts/ttf/` on the computer that presents the PowerPoint, or it will substitute another font. The film needs nothing installed.

## Rebuilding

Needs Node.js with Playwright, Python with `numpy` and `python-pptx`, and ffmpeg.

```bash
node render.cjs 30 50
```

```bash
python music.py
```

```bash
ffmpeg -y -framerate 30 -i out/frames/f%05d.png -i out/score.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart out/rashmi-singh-pitch.mp4
```

```bash
python build_pptx.py
```

To change wording, edit both `film.html` and `build_pptx.py`. If you change scene lengths, change the times in `music.py` as well so the music still lands on the reveals.
