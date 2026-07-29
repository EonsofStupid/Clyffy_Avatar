#!/usr/bin/env python3
"""clyffy-overlay — a lightweight, click-through screen annotation layer.

A fullscreen transparent always-on-top window that paints markers read from a JSON
file. It is INPUT-TRANSPARENT: every click, scroll and keystroke passes straight
through to whatever is underneath, so it can sit over Blender (or anything) without
interfering.

Run it once, leave it running:

    python3 tools/overlay.py [markers.json]

Then write markers to the JSON file and they appear within ~150 ms. Write `[]` to clear.

Marker schema — a JSON list of objects:
    {"x":960, "y":540, "n":1, "label":"click here", "color":"#ff3b30", "r":34}
      x,y    screen pixels, origin top-left      (required)
      n      step number drawn in the ring        (optional)
      label  text drawn beside the marker         (optional)
      color  hex, default #ff3b30                 (optional)
      r      ring radius in px, default 30        (optional)
      kind   "ring" (default) | "box" | "arrow"   (optional)
      w,h    box size when kind="box"
      x2,y2  arrow endpoint when kind="arrow"

Ordered steps are drawn ring 1 -> 2 -> 3 with a faint connecting line, so a sequence
reads at a glance.
"""
import gi, json, os, sys, math
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import cairo

PATH = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else \
    os.path.expanduser("~/.clyffy-overlay.json")


def hex_rgb(h, default=(1.0, 0.23, 0.19)):
    try:
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    except Exception:
        return default


class Overlay(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.markers = []
        self.mtime = 0

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.move(0, 0)
        self.set_default_size(screen.get_width(), screen.get_height())

        self.connect("draw", self.on_draw)
        self.connect("destroy", Gtk.main_quit)
        self.show_all()

        # make the whole window click-through
        self.get_window().input_shape_combine_region(
            cairo.Region(), 0, 0)

        GLib.timeout_add(150, self.poll)

    def poll(self):
        try:
            m = os.path.getmtime(PATH)
            if m != self.mtime:
                self.mtime = m
                with open(PATH) as f:
                    self.markers = json.load(f)
                self.queue_draw()
        except FileNotFoundError:
            if self.markers:
                self.markers = []
                self.queue_draw()
        except Exception as e:
            print("overlay: bad markers file:", e, file=sys.stderr)
        return True

    def on_draw(self, _w, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        pts = [(m.get("x", 0), m.get("y", 0))
               for m in self.markers if m.get("n") is not None]
        if len(pts) > 1:                       # faint path through the numbered steps
            cr.set_source_rgba(1, 1, 1, 0.35)
            cr.set_line_width(2)
            cr.set_dash([7, 6])
            cr.move_to(*pts[0])
            for p in pts[1:]:
                cr.line_to(*p)
            cr.stroke()
            cr.set_dash([])

        for m in self.markers:
            x, y = m.get("x", 0), m.get("y", 0)
            r = m.get("r", 30)
            col = hex_rgb(m.get("color", "#ff3b30"))
            kind = m.get("kind", "ring")

            cr.set_line_width(4)
            if kind == "box":
                w, h = m.get("w", 120), m.get("h", 60)
                cr.set_source_rgba(*col, 0.16)
                cr.rectangle(x, y, w, h); cr.fill()
                cr.set_source_rgba(*col, 0.95)
                cr.rectangle(x, y, w, h); cr.stroke()
                tx, ty = x, y - 10
            elif kind == "arrow":
                x2, y2 = m.get("x2", x + 80), m.get("y2", y + 80)
                cr.set_source_rgba(*col, 0.95)
                cr.move_to(x, y); cr.line_to(x2, y2); cr.stroke()
                ang = math.atan2(y2 - y, x2 - x)
                for s in (2.6, -2.6):
                    cr.move_to(x2, y2)
                    cr.line_to(x2 + 18 * math.cos(ang + s),
                               y2 + 18 * math.sin(ang + s))
                cr.stroke()
                tx, ty = x2 + 12, y2
            else:
                cr.set_source_rgba(*col, 0.14)
                cr.arc(x, y, r, 0, 2 * math.pi); cr.fill()
                cr.set_source_rgba(*col, 0.98)
                cr.arc(x, y, r, 0, 2 * math.pi); cr.stroke()
                cr.set_source_rgba(*col, 0.55)
                cr.arc(x, y, r * 0.45, 0, 2 * math.pi); cr.stroke()
                tx, ty = x + r + 12, y + 6

            n = m.get("n")
            if n is not None and kind == "ring":
                cr.select_font_face("sans", cairo.FONT_SLANT_NORMAL,
                                    cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(r * 0.95)
                t = str(n)
                ext = cr.text_extents(t)
                cr.set_source_rgba(0, 0, 0, 0.75)
                cr.move_to(x - ext.width / 2 - ext.x_bearing + 1.5,
                           y + ext.height / 2 + 1.5)
                cr.show_text(t)
                cr.set_source_rgba(1, 1, 1, 1)
                cr.move_to(x - ext.width / 2 - ext.x_bearing,
                           y + ext.height / 2)
                cr.show_text(t)

            label = m.get("label")
            if label:
                cr.select_font_face("sans", cairo.FONT_SLANT_NORMAL,
                                    cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(19)
                ext = cr.text_extents(label)
                cr.set_source_rgba(0, 0, 0, 0.72)
                cr.rectangle(tx - 8, ty - ext.height - 8,
                             ext.width + 16, ext.height + 16)
                cr.fill()
                cr.set_source_rgba(1, 1, 1, 1)
                cr.move_to(tx, ty)
                cr.show_text(label)
        return False


if __name__ == "__main__":
    print(f"clyffy-overlay reading {PATH}")
    Overlay()
    Gtk.main()
