"""Builds the editable PowerPoint version of the five-slide pitch.

Every element is a native PowerPoint shape or text box, placed at the same coordinates as film.html
(a 1920 x 1080 canvas). Each slide plays a staged fade-in sequence on its own and then advances.

Usage:  python build_pptx.py            ->  out/rashmi-singh-pitch.pptx
"""
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

PX = 6350                                   # 1920 px across a 13.333 inch slide
INK, PAPER, MINT, MUTED = "0F1F1C", "FBFCFB", "62D2B0", "9FB5AD"
SANS, SERIF = "Instrument Sans", "Instrument Serif"


def rgb(h): return RGBColor.from_string(h)
def E(px): return Emu(int(round(px * PX)))
def pt(px): return Pt(px * 0.5)             # 1 px on this canvas = 0.5 pt


class Slide:
    def __init__(self, prs, n, seconds, notes):
        self.s = prs.slides.add_slide(prs.slide_layouts[6])
        bg = self.s.background.fill
        bg.solid(); bg.fore_color.rgb = rgb(INK)
        self.steps = []                     # [(delay_ms_after_previous_step, [shape ids])]
        self.seconds = seconds
        self.s.notes_slide.notes_text_frame.text = notes
        self.text(120, 60, 500, 40, "RASHMI SINGH", 22, MUTED, bold=True, spc=4)
        self.text(1400, 60, 400, 40, f"0{n} — 05", 22, MUTED, bold=True, spc=4, align="r")

    # ---- shapes ----
    def _style(self, shp, fill, stroke, w, dash=False):
        if fill: shp.fill.solid(); shp.fill.fore_color.rgb = rgb(fill)
        else: shp.fill.background()
        if stroke:
            shp.line.color.rgb = rgb(stroke); shp.line.width = Emu(int(w * PX))
            if dash: shp.line.dash_style = MSO_LINE.ROUND_DOT
        else: shp.line.fill.background()
        shp.shadow.inherit = False
        return shp

    def circle(self, cx, cy, r, fill=None, stroke=None, w=4, dash=False, name="Circle"):
        shp = self.s.shapes.add_shape(MSO_SHAPE.OVAL, E(cx - r), E(cy - r), E(2 * r), E(2 * r))
        shp.name = name
        return self._style(shp, fill, stroke, w, dash)

    def rect(self, x, y, w, h, fill, radius=None, name="Bar"):
        kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        shp = self.s.shapes.add_shape(kind, E(x), E(y), E(w), E(h))
        if radius: shp.adjustments[0] = min(0.5, radius / min(w, h))
        shp.name = name
        return self._style(shp, fill, None, 0)

    def line(self, x1, y1, x2, y2, color=MINT, w=4, name="Connection"):
        shp = self.s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
        shp.line.color.rgb = rgb(color); shp.line.width = Emu(int(w * PX)); shp.name = name
        return shp

    def check(self, pts, color=INK, w=14, name="Tick"):
        fb = self.s.shapes.build_freeform(E(pts[0][0]), E(pts[0][1]))
        fb.add_line_segments([(E(x), E(y)) for x, y in pts[1:]], close=False)
        shp = fb.convert_to_shape(); shp.name = name
        shp.fill.background(); shp.line.color.rgb = rgb(color); shp.line.width = Emu(int(w * PX))
        ln = shp.line._get_or_add_ln(); ln.set("cap", "rnd")
        shp.shadow.inherit = False
        return shp

    def text(self, x, y, w, h, runs, size, color=PAPER, bold=False, italic=False, font=SANS, spc=0,
             align="l", anchor="t", line=1.0, name="Text"):
        """runs: a string, or a list of paragraphs, each a string or (string, colour, size, font, italic, bold)."""
        tb = self.s.shapes.add_textbox(E(x), E(y), E(w), E(h)); tb.name = name
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
        paras = runs if isinstance(runs, list) else [runs]
        for i, para in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = {"l": PP_ALIGN.LEFT, "r": PP_ALIGN.RIGHT, "c": PP_ALIGN.CENTER}[align]
            p.line_spacing = line
            t, c, sz, f, it, b = (para, color, size, font, italic, bold) if isinstance(para, str) else para
            r = p.add_run(); r.text = t
            r.font.size = pt(sz); r.font.bold = b; r.font.italic = it; r.font.name = f
            r.font.color.rgb = rgb(c)
            rpr = r._r.get_or_add_rPr()
            if spc: rpr.set("spc", str(int(spc * 50)))          # px -> hundredths of a point
            for tag in ("a:ea", "a:cs"):                         # same face for all scripts
                el = etree.SubElement(rpr, qn(tag)); el.set("typeface", f)
        return tb

    def label(self, cx, y, s, color=PAPER, name=None):
        return self.text(cx - 220, y - 22, 440, 34, s, 22, color, bold=True, spc=4, align="c", name=name or f"Label {s.title()}")

    def headline(self, lines, bottom=112):
        h = 100 * len(lines) + 8
        paras = [(t, MINT if i == len(lines) - 1 else PAPER, 100, SANS, False, True) for i, t in enumerate(lines)]
        return self.text(120, 1080 - bottom - h, 1150, h, paras, 100, spc=-2, line=0.92, anchor="b", name="Headline")

    def side(self, say, src=None, width=640, bottom=120):
        paras = [(say, PAPER, 46, SERIF, True, False)]
        if src: paras += [(s, MUTED, 22, SANS, False, False) for s in src]
        return self.text(1920 - 120 - width, 1080 - bottom - 260, width, 260, paras, 46, align="r", anchor="b", line=1.05, name="Supporting line")

    # ---- animation ----
    def step(self, delay_ms, *shapes, exit=False):
        self.steps.append((delay_ms, [s.shape_id for s in shapes], exit))

    def evidence(self, fig, what, src):
        """The evidence block, bottom right on scenes 2 to 4: tag, figure, what it measures, source."""
        x, w = 1200, 600
        tag = self.text(x, 668, w, 30, "——  EVIDENCE", 22, MINT, bold=True, spc=4, align="r", name="Evidence tag")
        f = self.text(x - 200, 704, w + 200, 140, fig, 132, MINT, bold=True, spc=-4, align="r", anchor="b", line=0.9, name="Evidence figure")
        wt = self.text(x, 852, w, 74, what, 30, PAPER, bold=True, align="r", anchor="b", line=1.1, name="Evidence: what it measures")
        sr = self.text(x, 934, w, 30, src, 22, MUTED, align="r", name="Evidence source")
        return tag, f, wt, sr

    def finish(self):
        """Write the fade-in sequence and the automatic fade transition into the slide XML."""
        P = "http://schemas.openxmlformats.org/presentationml/2006/main"
        ids = iter(range(3, 100000))
        groups, at = [], 0
        for delay, spids, is_exit in self.steps:
            at += delay
            effects = ""
            for k, spid in enumerate(spids):
                node = "afterEffect" if k == 0 else "withEffect"
                if is_exit:
                    effects += (
                        f'<p:par><p:cTn id="{next(ids)}" presetID="10" presetClass="exit" presetSubtype="0" fill="hold" nodeType="{node}">'
                        f'<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                        f'<p:animEffect transition="out" filter="fade"><p:cBhvr><p:cTn id="{next(ids)}" dur="500"/>'
                        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
                        f'<p:set><p:cBhvr><p:cTn id="{next(ids)}" dur="1" fill="hold"><p:stCondLst><p:cond delay="499"/></p:stCondLst></p:cTn>'
                        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
                        f'<p:to><p:strVal val="hidden"/></p:to></p:set>'
                        f'</p:childTnLst></p:cTn></p:par>')
                    continue
                effects += (
                    f'<p:par><p:cTn id="{next(ids)}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" nodeType="{node}">'
                    f'<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                    f'<p:set><p:cBhvr><p:cTn id="{next(ids)}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                    f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
                    f'<p:to><p:strVal val="visible"/></p:to></p:set>'
                    f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{next(ids)}" dur="600"/>'
                    f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
                    f'</p:childTnLst></p:cTn></p:par>')
            groups.append(f'<p:par><p:cTn id="{next(ids)}" fill="hold"><p:stCondLst><p:cond delay="{at}"/></p:stCondLst>'
                          f'<p:childTnLst>{effects}</p:childTnLst></p:cTn></p:par>')
        timing = (
            f'<p:timing xmlns:p="{P}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            f'<p:par><p:cTn id="{next(ids)}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
            f'<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>{"".join(groups)}</p:childTnLst></p:cTn></p:par>'
            f'</p:childTnLst></p:cTn>'
            f'<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            f'<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
            f'</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')
        transition = f'<p:transition xmlns:p="{P}" spd="med" advTm="{int(self.seconds * 1000)}"><p:fade/></p:transition>'
        sld = self.s._element
        for old in sld.findall(qn("p:transition")) + sld.findall(qn("p:timing")): sld.remove(old)
        sld.append(etree.fromstring(transition)); sld.append(etree.fromstring(timing))


def build(path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = E(1920), E(1080)
    prs.core_properties.title = "Rashmi Singh: I connect two worlds"
    prs.core_properties.author = "Rashmi Singh"

    # 1 · the hook (7.5 s)
    s = Slide(prs, 1, 7.5, "I connect two worlds. I bring business understanding together with an emerging technology perspective.")
    b = s.circle(640, 360, 200, fill=PAPER, name="World: Business"); bl = s.label(640, 364, "BUSINESS", INK)
    t = s.circle(1280, 360, 200, stroke=MINT, name="World: Technology"); t2 = s.circle(1280, 360, 170, stroke=MINT, w=2, dash=True, name="Technology inner ring")
    tl = s.label(1280, 364, "TECHNOLOGY", MINT)
    ln = s.line(840, 360, 1080, 360); dot = s.circle(960, 360, 18, fill=MINT, name="Connection point")
    hl = s.headline(["I CONNECT", "TWO WORLDS."]); sd = s.side("Business understanding, meeting emerging technology.")
    s.step(300, b, bl); s.step(600, t, t2, tl); s.step(900, ln); s.step(500, dot, hl); s.step(900, sd); s.finish()

    # 2 · business understanding (9 s)
    s = Slide(prs, 2, 9, "I understand what business needs. Projects start with people, priorities and needs. Evidence: at DMart Foundation I owned one programme across 5 cities that reached about 100,000 students.")
    hl = s.headline(["I UNDERSTAND WHAT", "BUSINESS NEEDS."])
    small = []
    for cx, word in ((560, "PEOPLE"), (960, "PRIORITIES"), (1360, "NEEDS")):
        small.append((s.circle(cx, 340, 100, stroke=PAPER, w=3, name=f"Need: {word.title()}"), s.label(cx, 344, word)))
    big = s.circle(960, 340, 180, fill=PAPER, name="Outcome")
    n1 = s.text(780, 300, 360, 44, "ONE PROGRAMME", 30, INK, bold=True, align="c", name="Outcome title")
    n2 = s.text(780, 350, 360, 34, "5 CITIES", 24, INK, bold=True, spc=4, align="c", name="Outcome detail")
    ev = s.evidence("~100,000", "students reached by one programme I owned end to end", "DMart Foundation · 2022–24")
    s.step(300, hl)
    for pair in small: s.step(600, *pair)
    s.step(1000, big, n1, n2); s.step(900, *ev); s.finish()

    # 3 · execution (9 s)
    s = Slide(prs, 3, 9, "I turn complexity into action: challenge, structure, people, action. Evidence: I led the recruitment and training of more than 200 educators a year.")
    hl = s.headline(["I TURN COMPLEXITY", "INTO ACTION."])
    xs = [420, 780, 1140, 1500]; words = ["CHALLENGE", "STRUCTURE", "PEOPLE", "ACTION"]
    nodes, labels, lines = [], [], []
    for i, (x, wd) in enumerate(zip(xs, words)):
        last = i == 3
        nodes.append(s.circle(x, 340, 38 if last else 30, fill=MINT if last else None, stroke=None if last else PAPER, name=f"Step: {wd.title()}"))
        labels.append(s.label(x, 420, wd, MINT if last else PAPER))
    for a, b_ in ((450, 750), (810, 1110), (1170, 1462)): lines.append(s.line(a, 340, b_, 340))
    ev = s.evidence("200+", "educators recruited and trained a year", "DMart Foundation · 2022–24")
    s.step(300, hl); s.step(900, nodes[0], labels[0])
    for i in (1, 2, 3): s.step(600, lines[i - 1], nodes[i], labels[i])
    s.step(800, *ev); s.finish()

    # 4 · technology and AI (11.5 s): the workflow as a compact row, the real prototype below it
    s = Slide(prs, 4, 11.5, "I turn curiosity into capability. My Intelligent Business Operations Assistant: a business request goes in, an AI workflow organises it, and a person approves every item. The screenshot is the real review screen: one AI-suggested task edited by the reviewer, one rejected. Evidence: all 8 sample requests completed. I defined the requirements, tools, approval rules and tests; it was built with an AI coding assistant.")
    hl = s.headline(["I TURN CURIOSITY", "INTO CAPABILITY."])
    card = s.rect(466, 158, 108, 72, PAPER, radius=10, name="Request")
    c1 = s.rect(482, 176, 64, 8, INK, radius=4, name="Request line 1")
    c2 = s.rect(482, 192, 76, 8, "A9B2AF", radius=4, name="Request line 2")
    c3 = s.rect(482, 208, 50, 8, "A9B2AF", radius=4, name="Request line 3")
    l1 = s.label(520, 266, "BUSINESS PROBLEM")
    a1 = s.line(590, 194, 890, 194)
    ring = s.circle(960, 194, 58, stroke=MINT, name="AI workflow")
    r1 = s.rect(932, 176, 56, 8, MINT, radius=4, name="Organised line 1"); r2 = s.rect(932, 190, 56, 8, MINT, radius=4, name="Organised line 2"); r3 = s.rect(932, 204, 40, 8, MINT, radius=4, name="Organised line 3")
    l2 = s.label(960, 266, "AI WORKFLOW", MINT)
    a2 = s.line(1030, 194, 1330, 194)
    halo = s.circle(1400, 194, 58, stroke=MINT, name="Approval ring"); human = s.circle(1400, 194, 48, fill=PAPER, name="Human reviewer")
    tick = s.check([(1379, 195), (1394, 210), (1423, 179)], w=8)
    l3 = s.label(1400, 266, "HUMAN OVERSIGHT")
    shot = s.s.shapes.add_picture("prototype-review.png", E(606), E(306), E(708), E(300))
    shot.name = "Prototype review screen"
    shot.line.color.rgb = rgb(MINT); shot.line.width = Emu(int(3 * PX))
    cap = s.text(360, 622, 1200, 30, "THE REAL PROTOTYPE · EVERY AI SUGGESTION WAITS FOR A PERSON", 22, MUTED, bold=True, spc=4, align="c", name="Screenshot caption")
    ev = s.evidence("8 of 8", "sample requests completed by my working AI prototype", "Intelligent Business Operations Assistant · 2026")
    s.step(300, hl); s.step(600, card, c1, c2, c3, l1); s.step(700, a1, ring, l2); s.step(500, r1, r2, r3)
    s.step(700, a2, human, l3); s.step(500, tick, halo)
    s.step(900, shot, cap); s.step(1000, *ev); s.finish()

    # 5 · the close (13 s)
    s = Slide(prs, 5, 13, "The bridge between business and technology. Needs, action and capability, each with its evidence: about 100,000 students reached, 200+ educators a year, 8 of 8 prototype test requests. I connect business needs with the people, processes and technology that move them forward. Hold this slide and invite the conversation.")
    b = s.circle(330, 330, 150, fill=PAPER, name="World: Business"); bl = s.label(330, 334, "BUSINESS", INK)
    t = s.circle(1590, 330, 150, stroke=MINT, name="World: Technology"); t2 = s.circle(1590, 330, 124, stroke=MINT, w=2, dash=True, name="Technology inner ring")
    tl = s.label(1590, 334, "TECHNOLOGY", MINT)
    bridge = s.line(480, 330, 1440, 330, name="Bridge")
    pillars = []
    for x, w, fig, under in ((690, "NEEDS", "~100,000", "STUDENTS"), (960, "ACTION", "200+", "EDUCATORS / YEAR"), (1230, "CAPABILITY", "8 of 8", "AI TEST REQUESTS")):
        pt_ = s.circle(x, 330, 18, fill=MINT, name=f"Bridge point: {w.title()}")
        lab = s.label(x, 278, w)
        f = s.text(x - 135, 376, 270, 60, fig, 52, MINT, bold=True, spc=-1, align="c", name=f"Evidence: {w.title()}")
        u = s.text(x - 135, 440, 270, 28, under, 19, PAPER, bold=True, spc=2, align="c", name=f"Evidence label: {w.title()}")
        pillars.append((pt_, lab, f, u))
    hl = s.headline(["THE BRIDGE", "BETWEEN BUSINESS", "AND TECHNOLOGY."], bottom=128)
    sd = s.side("I connect business needs with the people, processes and technology that move them forward.", width=700, bottom=136)
    contact = s.text(120, 1000, 1680, 36, "Rashmi Singh · rashmissingh97@gmail.com · linkedin.com/in/-rashmi-singh- · rashmi-singh.rashmissingh97.workers.dev", 22, MUTED, name="Contact")
    s.step(300, b, bl, t, t2, tl); s.step(900, bridge)
    for p_ in pillars: s.step(400, *p_)
    s.step(800, hl); s.step(1100, sd); s.step(900, contact); s.finish()

    prs.save(path)
    return path


if __name__ == "__main__":
    import os
    os.makedirs("out", exist_ok=True)
    print(build("out/rashmi-singh-pitch.pptx"))
