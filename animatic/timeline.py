"""Single source of truth for the cut: shots, captions, dissolves, narration cues.

Mirrors sections C, D and G of docs/production-package.md.
"""
FPS = 25
TOTAL_FRAMES = 3000          # exactly 120 seconds

# n, duration (s), source, optional caption / AI prompt id
_SHOTS = [
    (1, 4, "real"), (2, 4, "real"), (3, 4, "real", "Ílhavo, Portugal"),
    (4, 5, "ai", None, "AI-01"), (5, 5, "graphic"), (6, 4, "real"), (7, 3, "real"), (8, 3, "real"),
    (9, 4, "real", "[Shopkeeper's name]  ·  [shop], Lisbon"), (10, 3, "real"), (11, 3, "real"), (12, 4, "real"),
    (13, 4, "real"), (14, 3, "real"), (15, 5, "real"),
    (16, 4, "real"), (17, 4, "real"), (18, 5, "archive", "Archive  ·  [year, holder]"),
    (19, 4, "archive", "Archive  ·  [year, holder]"), (20, 4, "ai", "Reconstruction", "AI-02"),
    (21, 4, "real"), (22, 5, "real"),
    (23, 3, "real"), (24, 3, "real"), (25, 4, "real"), (26, 4, "real"), (27, 5, "real"), (28, 5, "real"),
    (29, 4, "real"), (30, 4, "real"),
]

SHOTS = []
_t = 0
for row in _SHOTS:
    SHOTS.append(dict(n=row[0], start=_t, dur=row[1], src=row[2],
                      caption=row[3] if len(row) > 3 else None, ai_id=row[4] if len(row) > 4 else None))
    _t += row[1]
assert _t * FPS == TOTAL_FRAMES, _t

# (from shot index, to shot index, length in frames); indices are zero-based
DISSOLVES = [(3, 4, 12), (14, 15, 10), (28, 29, 16)]

TITLE = dict(text="The Faithful Friend", fade_in_frames=25,
             fade_out_start=2962,      # 01:58.5
             start_frame=2980)         # title on black for the last 20 frames

ACTS = [("The hook", 0, 12), ("Discover the place", 12, 32), ("The human story", 32, 58),
        ("The cultural revelation", 58, 88), ("The visual payoff", 88, 112), ("The closing", 112, 120)]

# Narration cues: (earliest start in seconds, text as subtitled, text as spoken by the synthetic voice)
# The spoken form only differs where the voice needs help with Portuguese.
CUES = [
    (2.0, "On the Portuguese coast, a museum keeps a tank of cold water. The fish inside are a national symbol.", None),
    (None, "And foreigners.", None),                       # follows the previous cue after a one-second beat
    (13.0, "Atlantic cod has never lived in Portuguese seas. Its range ends at the Bay of Biscay.", None),
    (22.0, "Yet in Lisbon's old grocers it is stacked like firewood: split, salted, stiff as a board.", None),
    (33.0, "They call it o fiel amigo, the faithful friend.", "They call it oo fee-ell ah-mee-goo, the faithful friend."),
    (38.0, "It is chosen by weight, sawn into portions, and taken home to soak, the water changed again and again.", None),
    (58.0, "Why a northern fish? Because salted, it keeps. Five centuries ago it fed sailors on long voyages. Then it fed everyone.", None),
    (67.5, "Last century, a dictatorship made it a national cause, sending fleets to Newfoundland and Greenland. "
           "Men fished by line from small open dories, and were gone for half the year.", None),
    (79.4, "The dories are gone. The appetite is not.", None),
    (83.2, "Today the cod comes from Norway and Iceland.", None),
    (94.0, "On Christmas Eve, in many homes, it is simply boiled, with potatoes, cabbage, an egg, and a great deal of olive oil.", None),
    (108.0, "Nothing clever.", None),
    (113.0, "A fish from somewhere else, made entirely their own.", None),
]
