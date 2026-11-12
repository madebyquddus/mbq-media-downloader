"""Signature cinematic visual system for MBQ Media Downloader.

This module is UI-only.  It never starts, stops, pauses or mutates downloads.
It paints the MBQ signal core used by the Home console and reacts to state
updates supplied by the main window.
"""

import math

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget, QSizePolicy


class MBQCore(QWidget):
    """Animated editorial signal core used as MBQ's visual signature."""

    STATE_LABELS = {
        "idle": "READY",
        "scanning": "RESOLVING",
        "locked": "SIGNAL LOCKED",
        "downloading": "PULLING MEDIA",
        "processing": "FINALIZING",
        "complete": "MEDIA ACQUIRED",
        "error": "SIGNAL LOST",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mbqCore")
        self.setMinimumSize(360, 250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self.phase = 0.0
        self.progress = 0
        self.state = "idle"
        self.source = "LOCAL"
        self.title = "MBQ MEDIA CONSOLE"
        self.creator = "WAITING FOR SOURCE"
        self.artwork = QPixmap()
        self.motion = True
        self.light = False
        self.cursor_norm = QPointF(0.5, 0.5)

        self.tokens = {
            "bg": "#05070a",
            "card": "#0c1118",
            "text_strong": "#f5f7fb",
            "text2": "#a4acb9",
            "text3": "#687384",
            "accent": "#62e5f5",
            "accent2": "#2b8cff",
            "signal": "#ff7b22",
            "border": "#222b36",
        }

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._advance)
        self.timer.start()

    def set_motion(self, enabled):
        self.motion = bool(enabled)
        if self.motion:
            self.timer.start()
        else:
            self.timer.stop()
        self.update()

    def set_theme(self, tokens):
        if tokens:
            self.tokens.update(tokens)
            bg = QColor(self.tokens.get("bg", "#05070a"))
            self.light = bg.lightness() > 145
        self.update()

    def set_state(self, state, label=None):
        state = state if state in self.STATE_LABELS else "idle"
        self.state = state
        if label:
            self.STATE_LABELS[state] = str(label).upper()
        if state in ("idle", "locked"):
            self.progress = 0 if state == "idle" else self.progress
        elif state == "complete":
            self.progress = 100
        self.update()

    def set_progress(self, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = 0
        self.progress = max(0, min(100, value))
        if self.progress and self.state not in ("scanning", "processing", "complete"):
            self.state = "downloading"
        self.update()

    def set_media(self, title="", creator="", source=""):
        if title:
            self.title = str(title)
        if creator:
            self.creator = str(creator)
        if source:
            self.source = str(source).upper()
        self.update()

    def set_source(self, source):
        if source:
            self.source = str(source).upper()
        self.update()

    def set_artwork(self, pixmap):
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            self.artwork = QPixmap(pixmap)
        else:
            self.artwork = QPixmap()
        self.update()

    def clear_artwork(self):
        self.artwork = QPixmap()
        self.update()

    def _advance(self):
        if self.motion and self.isVisible() and self.window().isActiveWindow():
            speed = 0.020 if self.state in ("scanning", "downloading", "processing") else 0.008
            self.phase = (self.phase + speed) % (math.tau * 100)
            self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self.width() and self.height():
            self.cursor_norm = QPointF(
                max(0.0, min(1.0, pos.x() / self.width())),
                max(0.0, min(1.0, pos.y() / self.height())),
            )
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.cursor_norm = QPointF(0.5, 0.5)
        self.update()
        super().leaveEvent(event)

    @staticmethod
    def _fit(text, max_chars):
        text = str(text or "")
        return text if len(text) <= max_chars else text[: max(1, max_chars - 1)].rstrip() + "…"

    def _source_colors(self):
        source = self.source.lower()
        if "youtube" in source:
            return QColor("#ff4054"), QColor("#ff8b45")
        if "tiktok" in source:
            return QColor("#23f0e9"), QColor("#ff3e75")
        if "instagram" in source:
            return QColor("#ff6b72"), QColor("#c75dff")
        if "facebook" in source:
            return QColor("#55a8ff"), QColor("#6de0ff")
        return QColor(self.tokens.get("accent", "#62e5f5")), QColor(self.tokens.get("signal", "#ff7b22"))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w = float(self.width())
        h = float(self.height())
        r = QRectF(0.5, 0.5, max(1.0, w - 1.0), max(1.0, h - 1.0))
        t = self.tokens
        cyan, signal = self._source_colors()

        base = QColor("#f7f9fc" if self.light else "#080b10")
        base2 = QColor("#edf2f7" if self.light else "#0c1219")
        border = QColor(t.get("border", "#222b36"))
        text = QColor(t.get("text_strong", "#f5f7fb"))
        text2 = QColor(t.get("text2", "#a4acb9"))
        text3 = QColor(t.get("text3", "#687384"))

        # Cinematic deck surface.
        deck = QLinearGradient(r.topLeft(), r.bottomRight())
        deck.setColorAt(0.0, base2)
        deck.setColorAt(0.65, base)
        deck.setColorAt(1.0, QColor("#e8eef4" if self.light else "#07090d"))
        p.setPen(QPen(border, 1))
        p.setBrush(deck)
        p.drawRoundedRect(r, 8, 8)

        # Artwork becomes a very restrained atmospheric layer.
        if not self.artwork.isNull():
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(r.adjusted(1, 1, -1, -1), 7, 7)
            p.setClipPath(clip)
            target = QRectF(w * 0.38, 0, w * 0.62, h)
            scaled = self.artwork.scaled(
                int(max(1, target.width())), int(max(1, target.height())),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            sx = max(0, int((scaled.width() - target.width()) / 2))
            sy = max(0, int((scaled.height() - target.height()) / 2))
            source_rect = QRectF(sx, sy, target.width(), target.height())
            p.setOpacity(0.13 if not self.light else 0.09)
            p.drawPixmap(target, scaled, source_rect)
            overlay = QLinearGradient(target.left(), 0, target.right(), 0)
            fade0 = QColor(base)
            fade0.setAlpha(255)
            fade1 = QColor(base)
            fade1.setAlpha(30)
            overlay.setColorAt(0.0, fade0)
            overlay.setColorAt(0.72, fade1)
            p.setOpacity(1.0)
            p.fillRect(target, overlay)
            p.restore()

        # Editorial grid and registration marks.
        grid = QColor(text3)
        grid.setAlpha(26 if not self.light else 24)
        p.setPen(QPen(grid, 1))
        for x in range(24, int(w), 48):
            p.drawLine(x, 0, x, int(h))
        for y in range(24, int(h), 48):
            p.drawLine(0, y, int(w), y)

        # Mouse parallax moves only atmospheric geometry.
        px = (self.cursor_norm.x() - 0.5) * 16.0
        py = (self.cursor_norm.y() - 0.5) * 10.0
        center = QPointF(w * 0.69 + px, h * 0.51 + py)
        radius = min(w, h) * 0.29

        glow = QRadialGradient(center, radius * 1.8)
        c0 = QColor(cyan)
        c0.setAlpha(48 if not self.light else 28)
        c1 = QColor(signal)
        c1.setAlpha(20 if not self.light else 14)
        clear = QColor(cyan)
        clear.setAlpha(0)
        glow.setColorAt(0.0, c0)
        glow.setColorAt(0.52, c1)
        glow.setColorAt(1.0, clear)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(center, radius * 1.85, radius * 1.85)

        # Ghost MBQ typography anchors the composition.
        ghost = QColor(text)
        ghost.setAlpha(13 if not self.light else 10)
        p.setPen(ghost)
        ghost_font = QFont("Segoe UI Variable Display", max(32, int(h * 0.28)), QFont.Weight.Black)
        p.setFont(ghost_font)
        p.drawText(QRectF(w * 0.32, h * 0.05, w * 0.66, h * 0.46), Qt.AlignmentFlag.AlignCenter, "MBQ")

        # Signal rings.
        active = self.state in ("scanning", "downloading", "processing")
        spin = self.phase * (2.4 if active else 0.7)
        for idx, scale in enumerate((1.0, 0.76, 0.52)):
            rr = QRectF(
                center.x() - radius * scale,
                center.y() - radius * scale,
                radius * scale * 2,
                radius * scale * 2,
            )
            ring = QColor(cyan if idx != 1 else signal)
            ring.setAlpha((120 - idx * 25) if active else (72 - idx * 14))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ring, 1.2 if idx else 1.6))
            start = int((spin * 45 + idx * 70) * 16)
            span = int((215 - idx * 25) * 16)
            p.drawArc(rr, start, span)

        # Rotating scan spokes.
        spoke_color = QColor(signal if active else cyan)
        spoke_color.setAlpha(160 if active else 80)
        p.setPen(QPen(spoke_color, 1))
        for i in range(3):
            a = spin + i * (math.tau / 3)
            inner = QPointF(center.x() + math.cos(a) * radius * 0.38, center.y() + math.sin(a) * radius * 0.38)
            outer = QPointF(center.x() + math.cos(a) * radius * 1.02, center.y() + math.sin(a) * radius * 1.02)
            p.drawLine(inner, outer)

        # Node labels around the ring.
        node_font = QFont("Consolas", 7, QFont.Weight.DemiBold)
        p.setFont(node_font)
        nodes = (("VIDEO", -0.58), ("AUDIO", 0.15), ("META", 0.78))
        for label, fraction in nodes:
            a = spin * 0.18 + fraction * math.tau
            pos = QPointF(center.x() + math.cos(a) * radius * 1.17, center.y() + math.sin(a) * radius * 1.17)
            dot = QColor(signal if label == "META" else cyan)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot)
            p.drawEllipse(pos, 2.5, 2.5)
            p.setPen(text3)
            p.drawText(QRectF(pos.x() + 6, pos.y() - 7, 52, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

        # Progress / core status.
        state_text = self.STATE_LABELS.get(self.state, "READY")
        value_text = f"{self.progress:02d}%" if self.state in ("downloading", "processing", "complete") else "MBQ"
        value_font = QFont("Segoe UI Variable Display", max(19, int(radius * 0.22)), QFont.Weight.Black)
        p.setFont(value_font)
        p.setPen(text)
        p.drawText(QRectF(center.x() - radius * 0.7, center.y() - 18, radius * 1.4, 38), Qt.AlignmentFlag.AlignCenter, value_text)

        state_font = QFont("Consolas", 7, QFont.Weight.Bold)
        state_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        p.setFont(state_font)
        p.setPen(cyan if self.state != "error" else QColor("#ff5c6c"))
        p.drawText(QRectF(center.x() - radius, center.y() + 18, radius * 2, 22), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, state_text)

        # Editorial information block.
        left = 22.0
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.setPen(signal)
        p.drawText(QRectF(left, 18, w * 0.42, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "MBQ / SIGNAL CORE")

        p.setFont(QFont("Segoe UI Variable Display", 12, QFont.Weight.Bold))
        p.setPen(text)
        p.drawText(
            QRectF(left, h - 92, w * 0.43, 42),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
            self._fit(self.title, 44),
        )
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(text2)
        p.drawText(QRectF(left, h - 49, w * 0.43, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._fit(self.creator, 46))

        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.setPen(cyan)
        p.drawText(QRectF(left, h - 28, w * 0.43, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"SOURCE / {self._fit(self.source, 24)}")

        # Corner registration marks: deliberately sharp, unlike generic rounded cards.
        mark = QColor(signal)
        mark.setAlpha(185)
        p.setPen(QPen(mark, 1.4))
        m = 13
        d = 14
        for x, y, sx, sy in ((m, m, 1, 1), (w - m, m, -1, 1), (m, h - m, 1, -1), (w - m, h - m, -1, -1)):
            p.drawLine(QPointF(x, y), QPointF(x + sx * d, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + sy * d))

        # State rail at the bottom.
        rail = QRectF(22, h - 8, max(40, w - 44), 2)
        p.setPen(Qt.PenStyle.NoPen)
        rail_bg = QColor(text3)
        rail_bg.setAlpha(55)
        p.setBrush(rail_bg)
        p.drawRect(rail)
        if self.state in ("scanning", "downloading", "processing", "complete"):
            amount = self.progress / 100.0 if self.progress else (0.28 + (math.sin(self.phase * 3) + 1) * 0.18)
            amount = max(0.03, min(1.0, amount))
            rail_grad = QLinearGradient(rail.left(), 0, rail.right(), 0)
            rail_grad.setColorAt(0.0, cyan)
            rail_grad.setColorAt(1.0, signal)
            p.setBrush(rail_grad)
            p.drawRect(QRectF(rail.left(), rail.top(), rail.width() * amount, rail.height()))
