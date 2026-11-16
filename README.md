# I connect two worlds: a five-slide animated hiring pitch

A 45-second visual pitch for Rashmi Singh, delivered in two matching formats.

| File | What it is |
|---|---|
| `out/rashmi-singh-pitch.mp4` | The film: 1920 x 1080, 30 frames per second, 45 seconds, no sound |
| `out/rashmi-singh-pitch.pptx` | The editable PowerPoint: five slides, native shapes and text, staged animations |
| `film.html` | The source animation. Open it in any browser to watch it |

## The message

**I connect business understanding, structured execution and emerging technology.**

| # | Headline | The one idea | Proof on screen |
|---|---|---|---|
| 1 | I connect two worlds. | Two separate worlds, business and technology, join through one point | |
| 2 | I understand what business needs. | People, priorities and needs come together into one outcome | 5 cities, about 100,000 students: one programme owned end to end (DMart Foundation, 2022–24) |
| 3 | I turn complexity into action. | Scattered points become Challenge → Structure → People → Action | 200+ educators recruited and trained every year (DMart Foundation) |
| 4 | I turn curiosity into capability. | Business problem → AI workflow → human oversight | A working prototype, built and tested: 8 of 8 sample requests completed |
| 5 | The bridge between business and technology. | The two worlds return, now joined by a bridge carrying needs, action and capability | Closing statement and contact details |

Every figure comes from the CV or from the prototype's test report. The pitch does not present Rashmi as an AI engineer. The speaker notes for slide 4 say that she defined the requirements, tools, approval rules and tests, and that the prototype was built with an AI coding assistant.

## Design system

| Element | Rule |
|---|---|
| Colour | Four colours only: ink `#0F1F1C` (ground), paper `#FBFCFB`, mint `#62D2B0`, muted `#9FB5AD` |
| Display type | Instrument Sans Bold, capitals, 100 px, tight spacing. The last line of every headline is mint |
| Supporting type | Instrument Serif Italic, 46 px. One line per slide, bottom right |
| Labels | Instrument Sans Bold, 22 px, wide letter spacing |
| Shapes | Solid paper circle = business. Mint ring = technology. Mint line = the connection. Nothing else |
| Layout | 120 px margins. Visual in the upper two thirds, headline bottom left, supporting line bottom right |
| Furniture | Name top left and slide count top right, on every slide |
| Motion | Elements fade, rise or draw in once, in reading order. Nothing loops, bounces or spins. Scenes cross-fade |

## Timing

| Scene | Starts | Length |
|---|---|---|
| 1 | 0.0 s | 7.5 s |
| 2 | 7.5 s | 8.5 s |
| 3 | 16.0 s | 8.5 s |
| 4 | 24.5 s | 9.5 s |
| 5 | 34.0 s | 11 s, final frame held about 4 seconds |

## How the two formats differ

They share the layout, text, colours, order and reveal sequence. The motion is richer in the film.

| | Film | PowerPoint |
|---|---|---|
| Two worlds moving together | Yes | Shapes fade in at their final positions |
| Lines drawing themselves | Yes | Lines fade in |
| Scattered dots gathering (slide 3) | Yes | The ordered process builds step by step |
| AI lines tidying (slide 4) | Yes | The tidy lines fade in |
| Plays by itself | Always | Yes: each slide animates and advances automatically. Clicking also advances |

The PowerPoint was checked by converting it with LibreOffice, which confirmed the layout. Its animations and automatic timings were written to the PowerPoint standard but have not been played in PowerPoint itself, so run the slide show once before using it.

## Fonts

The PowerPoint uses Instrument Sans and Instrument Serif. Both are free under the SIL Open Font License. Install the four files in `fonts/ttf/` on the computer that presents, or PowerPoint will substitute another font. The film needs no fonts installed.

## Changing it

- **Text or layout in PowerPoint:** edit the file directly. Every element is a normal shape or text box with a readable name in the Selection Pane.
- **Text in both formats:** change it in `film.html` and in `build_pptx.py`, then rebuild.

Rebuild the film (needs Node.js with Playwright, and ffmpeg):

```bash
node render.cjs 30 45
```

```bash
ffmpeg -y -framerate 30 -i out/frames/f%05d.png -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -movflags +faststart out/rashmi-singh-pitch.mp4
```

Rebuild the PowerPoint (needs Python with `python-pptx`):

```bash
python build_pptx.py
```
