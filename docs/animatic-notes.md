# Animatic notes: *The Faithful Friend*, v1

The file in `deliverables/` is a timed storyboard film. It is not the documentary, and nothing in it should be shown as documentary footage.

The request was for the final video. A final film needs material that cannot be produced from a code environment: a crew filming real people in Lisbon and Ílhavo, licensed archive film, a narrator, a composer, and a video-generation model for the two AI shots. None of that exists yet. What can be made honestly is the step that normally comes next in production, an animatic that plays the whole film at the right length with the right cuts, so the script and structure can be judged and changed cheaply.

## What each element is

| Element | In the animatic | In the final film |
| --- | --- | --- |
| Picture, 27 live-action and archive shots | Drawn panels, animated with the planned camera move | Footage filmed on location; licensed archive |
| Picture, 2 AI shots (4 and 20) | Drawn panels | Generated from prompts AI-01 and AI-02, after the accuracy checks in the package |
| Map (shot 5) | Real coastlines from Natural Earth; cod range drawn as a schematic from the EU fisheries observatory's written description | Same data, range checked against a published distribution map |
| Narration | Synthetic voice (Piper, `en_GB-alan-medium`) | A recorded narrator |
| Music | Synthesised plucked strings and drone | Commissioned score for Portuguese guitar and double bass |
| Ambience and effects | Synthesised noise and tones | Sound recorded on location |
| Captions | Placeholders in square brackets for names and archive credits | Real names, with consent; real archive credits |
| On-screen labels | Every frame carries "ANIMATIC" and the shot number and source type | Removed |

No person, interview, quotation or piece of documentary evidence has been invented. The people in the panels are featureless silhouettes standing in for contributors who have not been cast.

## Measured specifications

Measured on the delivered master with `ffprobe` and `ffmpeg`'s EBU R 128 meter.

| Property | Value |
| --- | --- |
| Duration | 120.000 s |
| Frames | 3,000 at 25 fps, progressive |
| Resolution | 3840 × 2160, 16:9 |
| Video | H.264, yuv420p, BT.709 |
| Audio | AAC stereo, 48 kHz, 256 kbit/s |
| Integrated loudness | −23.0 LUFS |
| True peak | −6.2 dBFS |
| Loudness range | 11.8 LU |
| Shots | 30; lengths 3 to 5 s |
| Transitions | 3 dissolves, fade in, fade out, title on black for the last 20 frames |
| Narration | 181 words in 13 cues |
| Subtitles | 21 blocks, separate `.srt` |

Act boundaries fall at 00:12, 00:32, 00:58, 01:28 and 01:52, as the brief requires.

## What the animatic showed

- **The script fits, but Act 4 is tight.** At the synthetic voice's natural pace the two long Act 4 cues overran, so they are sped up by 11 to 13 per cent. A human narrator will need either the same brisk read or a trim of about six words. The likeliest cut is "on long voyages".
- **Four cue times moved** from the script by up to half a second so that no cue runs into the next: 00:58.0, 01:07.5, 01:19.4 and 01:23.2. `animatic/timeline.py` holds the timings used.
- **The two silences hold.** 00:45 to 00:58 and 01:26 to 01:34 play without narration.

## Limits of this version

- The sound was checked by measurement (levels, loudness, cue timing) and by waveform. It was not auditioned by ear. Listen before showing it to anyone; the synthetic pronunciation of *o fiel amigo* in particular is approximate.
- The panels are simple illustrations. They show framing, movement and rhythm. They do not show light, texture, performance or colour grade, so those parts of the quality-control list cannot be assessed yet.
- The mix is a scratch mix, not a professional one.
- Tram bells, shop talk and family voices cannot be synthesised honestly and are absent or reduced to simple cues.
- The six open fact and access checks in section H of the production package are still open. The animatic uses the narration as written, including the two lines flagged there as awaiting confirmation by the Ílhavo museum.

## From here to the final film

1. Watch the animatic and settle the script, especially Act 4.
2. Close the open checks in section H with the Museu Marítimo de Ílhavo.
3. Recce and book the locations in section F; cast the shopkeeper, the former fisherman and the family, with written consent.
4. Shoot three days; record location sound.
5. Locate, date and license the archive.
6. Generate shots 4 and 20 from the prompts in section E, after revising them against museum references. Keep the *Reconstruction* caption.
7. Record the narrator and commission the score.
8. Replace each panel in the timeline with its footage, grade, mix, and run the finished-cut checklist in section H.

## Credits and licences for the animatic

- Coastlines: [Natural Earth](https://www.naturalearthdata.com/) 1:110m land, public domain. Stored at `animatic/data/ne_110m_land.geojson`.
- Voice: [Piper](https://github.com/OHF-Voice/piper1-gpl) text-to-speech with the `en_GB-alan-medium` voice from the [Piper voices collection](https://huggingface.co/rhasspy/piper-voices). The voice file is not stored in this repository. Check its model card for licence terms before distributing the animatic outside the team.
- Fonts in the picture: Liberation Serif and Liberation Sans (SIL Open Font Licence).
- Drawings, music and sound effects: generated by the code in `animatic/`, under this repository's licence.
