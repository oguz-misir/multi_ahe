#!/usr/bin/env python3
"""Render the paper's .drawio figures to SVG, then to PDF via headless Chrome.

Why this exists: the draw.io desktop CLI is installed on this machine but
segfaults on every export (Electron/GTK: "Schema org.gnome.desktop.interface
does not have key font-antialiasing"), with or without xvfb, --headless,
--no-sandbox or --ozone-platform=headless.  The .drawio file therefore stays
the editable source of truth -- open it in draw.io and it round-trips -- and
this script produces the vector artwork the paper actually includes.

Scope is deliberately narrow: it understands exactly the style vocabulary used
by paper/figure/*.drawio (rounded rectangles, text cells, orthogonal edges with
optional waypoints, and the small HTML label subset draw.io writes: b, i, br,
sub, sup, font colour/size, span style, &nbsp;).  It is not a general
mxGraph renderer and does not try to be.

Usage:
    python3 scripts/drawio_to_svg.py paper/figure/fig1.drawio [out.svg]
"""

from __future__ import annotations

import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LINE_SPACING = 1.34
DEFAULT_FONT = 'Helvetica, Arial, sans-serif'


def parse_style(style: str) -> dict:
    out = {}
    for part in (style or '').split(';'):
        if not part:
            continue
        if '=' in part:
            k, v = part.split('=', 1)
            out[k.strip()] = v.strip()
        else:
            out[part.strip()] = '1'
    return out


class Run:
    __slots__ = ('text', 'bold', 'italic', 'color', 'size', 'shift')

    def __init__(self, text, bold, italic, color, size, shift):
        self.text = text
        self.bold = bold
        self.italic = italic
        self.color = color
        self.size = size
        self.shift = shift          # '', 'sub', 'sup'


def parse_label(label: str, base_size: float, base_color: str):
    """Turn a draw.io HTML label into [[Run, ...], ...] -- one list per line."""
    if not label:
        return []
    tokens = re.split(r'(<[^>]+>)', label)
    lines, cur = [], []
    bold = italic = 0
    colors, sizes, shift = [base_color], [base_size], ''

    for tok in tokens:
        if not tok:
            continue
        if tok.startswith('<'):
            t = tok.lower()
            name = re.match(r'</?\s*([a-z]+)', t)
            name = name.group(1) if name else ''
            closing = t.startswith('</')
            if name == 'br':
                lines.append(cur)
                cur = []
            elif name == 'b' or name == 'strong':
                bold += -1 if closing else 1
            elif name == 'i' or name == 'em':
                italic += -1 if closing else 1
            elif name == 'sub':
                shift = '' if closing else 'sub'
            elif name == 'sup':
                shift = '' if closing else 'sup'
            elif name in ('font', 'span', 'div', 'p'):
                if closing:
                    if len(colors) > 1:
                        colors.pop()
                    if len(sizes) > 1:
                        sizes.pop()
                else:
                    m = re.search(r'color\s*=\s*"([^"]+)"', tok) or \
                        re.search(r'color\s*:\s*([^;"\']+)', tok)
                    colors.append(m.group(1).strip() if m else colors[-1])
                    m = re.search(r'font-size\s*:\s*([\d.]+)\s*px', tok)
                    sizes.append(float(m.group(1)) if m else sizes[-1])
            continue

        text = html.unescape(tok).replace('\xa0', ' ')
        if not text:
            continue
        cur.append(Run(text, bold > 0, italic > 0, colors[-1], sizes[-1], shift))

    lines.append(cur)
    return [ln for ln in lines if ln is not None]


def esc(s: str) -> str:
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def emit_text_block(lines, x, y_first, anchor, default_size):
    """SVG <text> elements, one per label line."""
    out = []
    y = y_first
    for ln in lines:
        if not ln:
            y += default_size * LINE_SPACING
            continue
        size_here = max((r.size for r in ln), default=default_size)
        parts = []
        pending_reset = 0.0
        for r in ln:
            attrs = [f'fill="{r.color}"', f'font-size="{r.size:g}"']
            if r.bold:
                attrs.append('font-weight="bold"')
            if r.italic:
                attrs.append('font-style="italic"')
            dy = 0.0
            if r.shift == 'sub':
                dy = r.size * 0.28
                attrs[1] = f'font-size="{r.size * 0.76:g}"'
            elif r.shift == 'sup':
                dy = -r.size * 0.36
                attrs[1] = f'font-size="{r.size * 0.76:g}"'
            total_dy = dy - pending_reset
            pending_reset = dy
            if abs(total_dy) > 1e-6:
                attrs.append(f'dy="{total_dy:g}"')
            parts.append(f'<tspan {" ".join(attrs)}>{esc(r.text)}</tspan>')
        out.append(
            f'<text x="{x:g}" y="{y:g}" text-anchor="{anchor}" '
            f'font-family="{DEFAULT_FONT}" font-size="{size_here:g}" '
            f'xml:space="preserve">{"".join(parts)}</text>')
        y += size_here * LINE_SPACING
    return out


def rel_point(geo, fx, fy):
    return (geo[0] + geo[2] * fx, geo[1] + geo[3] * fy)


def orthogonalise(pts):
    """Insert elbows so every segment is axis-aligned."""
    out = [pts[0]]
    for p in pts[1:]:
        a = out[-1]
        if abs(a[0] - p[0]) > 0.5 and abs(a[1] - p[1]) > 0.5:
            out.append((p[0], a[1]))
        out.append(p)
    return out


def arrow_head(p_prev, p_end, color, size=9.0):
    dx, dy = p_end[0] - p_prev[0], p_end[1] - p_prev[1]
    n = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    b = (p_end[0] - ux * size, p_end[1] - uy * size)
    w = size * 0.40
    p1 = (b[0] + px * w, b[1] + py * w)
    p2 = (b[0] - px * w, b[1] - py * w)
    return (f'<path d="M {p_end[0]:g} {p_end[1]:g} L {p1[0]:g} {p1[1]:g} '
            f'L {p2[0]:g} {p2[1]:g} Z" fill="{color}" stroke="none"/>')


def convert(path: Path) -> str:
    model = ET.parse(path).getroot()
    if model.tag != 'mxGraphModel':
        model = model.find('.//mxGraphModel')
    root = model.find('root')

    W = float(model.get('pageWidth', 1280))
    H = float(model.get('pageHeight', 660))

    geo, cells = {}, []
    for c in root.findall('mxCell'):
        g = c.find('mxGeometry')
        if g is not None and g.get('width'):
            geo[c.get('id')] = (float(g.get('x', 0)), float(g.get('y', 0)),
                                float(g.get('width')), float(g.get('height')))
        cells.append(c)

    body = []
    edges = []
    seen = []          # every drawn point, so the viewBox can cover overflow

    for c in cells:
        st = parse_style(c.get('style', ''))
        cid = c.get('id')

        if c.get('edge') == '1':
            s, t = geo.get(c.get('source')), geo.get(c.get('target'))
            if not s or not t:
                continue
            p0 = rel_point(s, float(st.get('exitX', 0.5)),
                           float(st.get('exitY', 0.5)))
            p1 = rel_point(t, float(st.get('entryX', 0.5)),
                           float(st.get('entryY', 0.5)))
            way = []
            g = c.find('mxGeometry')
            if g is not None:
                arr = g.find("Array[@as='points']")
                if arr is not None:
                    way = [(float(p.get('x')), float(p.get('y')))
                           for p in arr.findall('mxPoint')]
            pts = orthogonalise([p0] + way + [p1])
            seen.extend(pts)
            color = st.get('strokeColor', '#000000')
            sw = float(st.get('strokeWidth', 1))
            dash = ''
            if st.get('dashed') == '1':
                dp = st.get('dashPattern', '6 4').split()
                dash = f' stroke-dasharray="{float(dp[0])*sw:g} {float(dp[1])*sw:g}"'
            d = 'M ' + ' L '.join(f'{x:g} {y:g}' for x, y in pts)
            shortened = list(pts)
            edges.append(f'<path d="{d}" fill="none" stroke="{color}" '
                         f'stroke-width="{sw:g}"{dash} stroke-linejoin="miter"/>')
            if st.get('endArrow', 'block') != 'none':
                edges.append(arrow_head(shortened[-2], shortened[-1], color))
            continue

        if cid in ('0', '1') or cid not in geo:
            continue
        x, y, w, h = geo[cid]
        seen.extend([(x, y), (x + w, y + h)])
        is_text = 'text' in st

        if not is_text:
            fill = st.get('fillColor', '#FFFFFF')
            stroke = st.get('strokeColor', '#000000')
            sw = float(st.get('strokeWidth', 1))
            rx = 0.0
            if st.get('rounded') == '1':
                rx = float(st.get('arcSize', 6))
            dash = ''
            if st.get('dashed') == '1':
                dp = st.get('dashPattern', '6 4').split()
                dash = f' stroke-dasharray="{float(dp[0])*sw:g} {float(dp[1])*sw:g}"'
            body.append(
                f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                f'rx="{rx:g}" ry="{rx:g}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw:g}"{dash}/>')

        base_size = float(st.get('fontSize', 11))
        lines = parse_label(c.get('value', ''), base_size,
                            st.get('fontColor', '#1A1A1A'))
        if not lines or not any(lines):
            continue

        align = st.get('align', 'center')
        anchor = {'left': 'start', 'center': 'middle', 'right': 'end'}[align]
        if anchor == 'start':
            tx = x + float(st.get('spacingLeft', 0))
        elif anchor == 'end':
            tx = x + w - float(st.get('spacingRight', 0))
        else:
            tx = x + w / 2.0

        heights = [max((r.size for r in ln), default=base_size) * LINE_SPACING
                   for ln in lines]
        total = sum(heights)
        valign = st.get('verticalAlign', 'middle')
        if valign == 'top':
            y0 = y + float(st.get('spacingTop', 0)) + heights[0] * 0.78
        elif valign == 'bottom':
            y0 = y + h - total + heights[0] * 0.78
        else:
            y0 = y + (h - total) / 2.0 + heights[0] * 0.78

        if st.get('labelBackgroundColor'):
            body.append(
                f'<rect x="{x:g}" y="{y0 - heights[0]:g}" width="{w:g}" '
                f'height="{total + 4:g}" fill="{st["labelBackgroundColor"]}" '
                f'stroke="none"/>')

        body.extend(emit_text_block(lines, tx, y0, anchor, base_size))

    # draw.io lets content sit outside the declared page (the feedback wire is
    # routed at x=-30).  Grow the viewBox to whatever is actually drawn, or it
    # gets silently clipped on the left.
    pad = 8.0
    x0 = min([0.0] + [p[0] for p in seen]) - pad
    y0 = min([0.0] + [p[1] for p in seen]) - pad
    x1 = max([W] + [p[0] for p in seen]) + pad
    y1 = max([H] + [p[1] for p in seen]) + pad
    vw, vh = x1 - x0, y1 - y0

    bg = (f'<rect x="{x0:g}" y="{y0:g}" width="{vw:g}" height="{vh:g}" '
          f'fill="#FFFFFF"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{vw:g}" height="{vh:g}" '
            f'viewBox="{x0:g} {y0:g} {vw:g} {vh:g}">\n'
            + '\n'.join([bg] + body + edges) + '\n</svg>\n')


def to_pdf(svg_text: str, out_pdf: Path) -> None:
    """SVG -> vector PDF through headless Chrome, page sized to the artwork."""
    import re as _re
    import subprocess
    import tempfile

    m = _re.search(r'width="([\d.]+)"\s+height="([\d.]+)"', svg_text)
    w, h = float(m.group(1)), float(m.group(2))
    with tempfile.TemporaryDirectory() as td:
        page = Path(td) / 'page.html'
        page.write_text(
            '<!doctype html><html><head><meta charset="utf-8"><style>'
            f'@page {{ size: {w:g}px {h:g}px; margin: 0; }}'
            'html,body{margin:0;padding:0;background:#fff}svg{display:block}'
            '</style></head><body>\n' + svg_text + '\n</body></html>')
        subprocess.run(
            ['google-chrome', '--headless', '--disable-gpu', '--no-sandbox',
             '--no-pdf-header-footer', f'--print-to-pdf={out_pdf}', str(page)],
            check=True, capture_output=True, timeout=180)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src = Path(args[0])
    dst = Path(args[1]) if len(args) > 1 else src.with_suffix('.svg')
    svg = convert(src)
    dst.write_text(svg)
    print(f'OK  {dst}')
    if '--pdf' in sys.argv:
        pdf = dst.with_suffix('.pdf') if dst.suffix == '.svg' else \
            Path(str(dst) + '.pdf')
        to_pdf(svg, pdf)
        print(f'OK  {pdf}')


if __name__ == '__main__':
    main()
