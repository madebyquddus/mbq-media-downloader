"""Premium native UI surfaces and controls using Qt Essentials only."""

import math
from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QRectF,
    QPointF,
    QTimer,
    QVariantAnimation,
    QEasingCurve,
    Signal,
    QPropertyAnimation,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QFont,
    QLinearGradient,
    QRadialGradient,
    QPainterPath,
    QConicalGradient,
    QBrush,
    QPixmap,
)
from PySide6.QtWidgets import (
    QWidget,
    QAbstractButton,
    QStackedWidget,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
)

from app.ui import icons
from app.ui.ui_config import UI


SIDEBAR_W = UI["sidebar_width"]


def qcolor(value):
    """QColor from '#rrggbb' or the 'rgba(r, g, b, a)' strings used in the theme tokens."""
    value = value.strip()

    if value.startswith("rgba"):
        r, g, b, a = [
            float(x)
            for x in value[value.index("(") + 1:value.rindex(")")].split(",")
        ]
        return QColor(int(r), int(g), int(b), int(a))

    return QColor(value)


class NeonCanvas(QWidget):
    """Restrained premium background with subtle ambient motion."""

    frame = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.phase = 0.0
        self.light = False

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.advance)
        self.timer.start()

    def set_motion(self, enabled):
        self.timer.start() if enabled else self.timer.stop()
        self.update()

    def advance(self):
        if (
            self.isVisible()
            and self.window().isActiveWindow()
            and not self.window().isMinimized()
        ):
            self.phase += 0.010
            self.update()
            self.frame.emit(self.phase)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Cinematic graphite base.  The ambient light is intentionally asymmetric
        # so the shell feels art-directed rather than like a generic blue dashboard.
        if self.light:
            base = QColor("#f4f1ec")
            top = QColor("#faf8f4")
            grid = QColor(40, 48, 58, 14)
            cyan = QColor(24, 170, 195, 24)
            signal = QColor(235, 105, 28, 19)
            frame = QColor("#c9c5bf")
        else:
            base = QColor("#05070a")
            top = QColor("#0a0e13")
            grid = QColor(126, 151, 170, 10)
            cyan = QColor(84, 228, 244, 22)
            signal = QColor(255, 122, 34, 16)
            frame = QColor("#242b33")

        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, top)
        gradient.setColorAt(1, base)
        p.fillRect(self.rect(), gradient)

        # Editorial registration grid: larger cells, lower contrast, offset from
        # the sidebar.  It acts as composition scaffolding rather than decoration.
        p.setPen(QPen(grid, 1))
        major = 96
        minor = 24
        for x in range(SIDEBAR_W, w + major, major):
            p.drawLine(x, 0, x, h)
        for y in range(0, h + major, major):
            p.drawLine(SIDEBAR_W, y, w, y)
        faint = QColor(grid)
        faint.setAlpha(max(3, grid.alpha() // 2))
        p.setPen(QPen(faint, 1))
        for x in range(SIDEBAR_W + minor, w + minor, major):
            p.drawLine(x, 0, x, h)

        sway = math.sin(self.phase * 0.8) * 34
        for x, y, radius, color in [
            (w * 0.74 + sway, -h * 0.04, w * 0.40, cyan),
            (w * 0.42 - sway * 0.45, h * 1.02, w * 0.34, signal),
        ]:
            glow = QRadialGradient(QPointF(x, y), radius)
            glow.setColorAt(0, color)
            fade = QColor(color)
            fade.setAlpha(0)
            glow.setColorAt(1, fade)
            p.fillRect(self.rect(), glow)

        # A long diagonal technical trace is the recurring MBQ editorial motif.
        trace = QLinearGradient(SIDEBAR_W, 0, w, h)
        c0 = QColor(86, 229, 245, 88 if not self.light else 62)
        c1 = QColor(255, 122, 34, 54 if not self.light else 42)
        c2 = QColor(c1)
        c2.setAlpha(0)
        trace.setColorAt(0.0, c0)
        trace.setColorAt(0.68, c1)
        trace.setColorAt(1.0, c2)
        p.setPen(QPen(QBrush(trace), 1))
        p.drawLine(SIDEBAR_W + 90, h, w, 0)

        # Top signal rail.
        accent = QLinearGradient(SIDEBAR_W, 0, w, 0)
        accent.setColorAt(0.0, QColor(84, 229, 245, 130 if not self.light else 95))
        accent.setColorAt(0.72, QColor(84, 229, 245, 25))
        accent.setColorAt(1.0, QColor(255, 122, 34, 105 if not self.light else 80))
        p.setPen(QPen(QBrush(accent), 1))
        p.drawLine(SIDEBAR_W, 0, w, 0)

        if not self.window().isMaximized():
            p.setPen(QPen(frame, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(0.5, 0.5, w - 1, h - 1))


class BrandMark(QWidget):
    """Scalable painted MBQ product mark, no external font/image dependency."""

    def __init__(self, compact=False, parent=None):
        super().__init__(parent)

        self.compact = compact
        self.light = False

        self.setFixedHeight(
            84 if compact else 86
        )

        self.setMinimumWidth(
            190 if compact else 390
        )

        self.setAccessibleName(
            "MBQ MEDIA DOWNLOADER — MadeByQuddus"
        )

        self.sidebar_icon = QPixmap()

        if compact:
            icon_path = (
                Path(__file__).resolve().parents[2]
                / "assets"
                / "icons"
                / "mbq_sidebar_icon.png"
            )

            self.sidebar_icon.load(
                str(icon_path)
            )

    def _logo_path(self, x, y, s):
        path = QPainterPath()

        path.moveTo(
            x,
            y + s * 0.78,
        )

        path.lineTo(
            x,
            y + s * 0.30,
        )

        path.lineTo(
            x + s * 0.26,
            y + s * 0.05,
        )

        path.lineTo(
            x + s * 0.52,
            y + s * 0.28,
        )

        path.lineTo(
            x + s * 0.76,
            y + s * 0.08,
        )

        path.lineTo(
            x + s,
            y + s * 0.31,
        )

        path.lineTo(
            x + s,
            y + s * 0.78,
        )

        path.lineTo(
            x + s * 0.76,
            y + s,
        )

        path.lineTo(
            x + s * 0.50,
            y + s * 0.77,
        )

        path.lineTo(
            x + s * 0.25,
            y + s,
        )

        path.closeSubpath()

        return path

    def paintEvent(self, event):
        p = QPainter(self)

        p.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        p.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform
        )

        logo_size = (
            UI["sidebar_logo_size"]
            if self.compact
            else 54
        )

        logo_x = (
            UI["sidebar_logo_x"]
            if self.compact
            else 6
        )

        logo_y = (
            UI["sidebar_logo_y"]
            if self.compact
            else 14
        )

        if (
            self.compact
            and not self.sidebar_icon.isNull()
        ):
            # Sidebar only: use the supplied PNG symbol.
            # The MBQ text remains unchanged.

            target = QRectF(
                logo_x,
                logo_y,
                logo_size,
                logo_size,
            )

            p.drawPixmap(
                target,
                self.sidebar_icon,
                QRectF(
                    self.sidebar_icon.rect()
                ),
            )

        else:
            # Keep the original painted mark everywhere else.

            path = self._logo_path(
                logo_x,
                logo_y,
                logo_size,
            )

            grad = QLinearGradient(
                logo_x,
                logo_y,
                logo_x + logo_size,
                logo_y + logo_size,
            )

            grad.setColorAt(
                0,
                QColor(
                    "#21e7ff"
                    if not self.light
                    else "#0387b8"
                ),
            )

            grad.setColorAt(
                0.48,
                QColor(
                    "#168cff"
                    if not self.light
                    else "#1b62d6"
                ),
            )

            grad.setColorAt(
                1,
                QColor(
                    "#6159ff"
                    if not self.light
                    else "#4c46c8"
                ),
            )

            if not self.light:
                glow = QRadialGradient(
                    QPointF(
                        logo_x + logo_size / 2,
                        logo_y + logo_size / 2,
                    ),
                    logo_size * 0.9,
                )

                glow.setColorAt(
                    0,
                    QColor(
                        30,
                        180,
                        255,
                        70,
                    ),
                )

                glow.setColorAt(
                    1,
                    QColor(
                        30,
                        180,
                        255,
                        0,
                    ),
                )

                p.setPen(
                    Qt.PenStyle.NoPen
                )

                p.setBrush(
                    glow
                )

                p.drawEllipse(
                    QPointF(
                        logo_x + logo_size / 2,
                        logo_y + logo_size / 2,
                    ),
                    logo_size * 0.9,
                    logo_size * 0.9,
                )

            p.setPen(
                Qt.PenStyle.NoPen
            )

            p.setBrush(
                grad
            )

            p.drawPath(
                path
            )

        text_x = (
            logo_x
            + logo_size
            + 12
        )

        title_y = (
            50
            if self.compact
            else 45
        )

        title = QFont(
            "Segoe UI Variable Display",
            20 if self.compact else 27,
            QFont.Weight.Black,
        )

        if not QFont(title).exactMatch():
            title = QFont(
                "Segoe UI",
                20 if self.compact else 27,
                QFont.Weight.Black,
            )

        p.setFont(
            title
        )

        p.setPen(
            QColor(
                "#f5f8fd"
                if not self.light
                else "#10243d"
            )
        )

        p.drawText(
            QPointF(
                text_x,
                title_y,
            ),
            "MBQ",
        )

        sub = QFont(
            "Segoe UI",
            6 if self.compact else 10,
            QFont.Weight.DemiBold,
        )

        sub.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing,
            1.15 if self.compact else 1.7,
        )

        p.setFont(
            sub
        )

        p.setPen(
            QColor(
                "#8fa9c7"
                if not self.light
                else "#526d8d"
            )
        )

        p.drawText(
            QPointF(
                text_x + 1,
                title_y + (
                    14
                    if self.compact
                    else 18
                ),
            ),
            "MEDIA DOWNLOADER",
        )


class ThemeToggle(QAbstractButton):
    """Compact painted light/dark switch used in the application header."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.light = False
        self.level = 0.0
        self.motion = True

        self.setFixedSize(
            82,
            36,
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setAccessibleName(
            "Toggle light and dark appearance"
        )

        self.anim = QVariantAnimation(
            self
        )

        self.anim.setDuration(
            200
        )

        self.anim.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        self.anim.valueChanged.connect(
            self._animate
        )

    def _animate(self, value):
        self.level = float(value)
        self.update()

    def set_light(self, light):
        target = (
            1.0
            if light
            else 0.0
        )

        if (
            abs(self.level - target) < 0.01
            or not self.motion
        ):
            self.light = light
            self.level = target
            self.update()
            return

        self.light = light

        self.anim.stop()

        self.anim.setStartValue(
            self.level
        )

        self.anim.setEndValue(
            target
        )

        self.anim.start()

    def paintEvent(self, event):
        p = QPainter(self)

        p.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        r = QRectF(
            1,
            2,
            self.width() - 2,
            self.height() - 4,
        )

        bg = QColor(
            "#e8f1fb"
            if self.light
            else "#0b192a"
        )

        border = QColor(
            "#a8c0d9"
            if self.light
            else "#2a4a66"
        )

        p.setBrush(bg)
        p.setPen(
            QPen(
                border,
                1,
            )
        )

        p.drawRoundedRect(
            r,
            16,
            16,
        )

        icons.draw(
            "sun",
            p,
            QRectF(
                8,
                8,
                20,
                20,
            ),
            QColor(
                "#667e98"
                if self.light
                else "#8fa9c1"
            ),
            weight=0.9,
        )

        icons.draw(
            "moon",
            p,
            QRectF(
                54,
                8,
                20,
                20,
            ),
            QColor(
                "#91a9c0"
                if self.light
                else "#8fb7d8"
            ),
        )

        x = (
            44
            - self.level * 42
        )

        knob = QRectF(
            x,
            5,
            26,
            26,
        )

        glow = QColor(
            30,
            200,
            255,
            70,
        )

        p.setPen(
            Qt.PenStyle.NoPen
        )

        p.setBrush(
            glow
        )

        p.drawEllipse(
            knob.adjusted(
                -3,
                -3,
                3,
                3,
            )
        )

        knob_grad = QLinearGradient(
            knob.topLeft(),
            knob.bottomRight(),
        )

        knob_grad.setColorAt(
            0,
            QColor("#27e5ff"),
        )

        knob_grad.setColorAt(
            1,
            QColor("#187cff"),
        )

        p.setBrush(
            knob_grad
        )

        p.setPen(
            QPen(
                QColor(
                    92,
                    231,
                    255,
                    150,
                ),
                1,
            )
        )

        p.drawEllipse(
            knob
        )

        icons.draw(
            "moon"
            if not self.light
            else "sun",
            p,
            knob.adjusted(
                5,
                5,
                -5,
                -5,
            ),
            QColor("#04202e"),
            weight=0.9,
        )


class WindowButton(QAbstractButton):
    """Painted minimise / maximise / close button for the frameless title bar."""

    def __init__(self, kind, parent=None):
        super().__init__(parent)

        self.kind = kind
        self.maximized = False
        self.level = 0.0
        self.motion = True

        self.fg = QColor(
            "#c9d7e5"
        )

        self.hover_bg = QColor(
            255,
            255,
            255,
            24,
        )

        self.close_bg = QColor(
            "#e5384f"
        )

        self.setFixedSize(
            46,
            34,
        )

        self.setCursor(
            Qt.CursorShape.ArrowCursor
        )

        names = {
            "min": "Minimize",
            "max": "Maximize",
            "close": "Close",
        }

        self.setAccessibleName(
            names[kind]
        )

        self.setToolTip(
            names[kind]
        )

        self.anim = QVariantAnimation(
            self
        )

        self.anim.setDuration(
            120
        )

        self.anim.valueChanged.connect(
            self._level
        )

    def _level(self, value):
        self.level = float(value)
        self.update()

    def set_theme(self, tokens):
        self.fg = qcolor(
            tokens["text_btn"]
        )

        self.hover_bg = qcolor(
            tokens["win_hover"]
        )

        self.close_bg = qcolor(
            tokens["win_close"]
        )

        self.update()

    def set_maximized(self, value):
        self.maximized = value

        if self.kind == "max":
            self.setToolTip(
                "Restore"
                if value
                else "Maximize"
            )

            self.setAccessibleName(
                "Restore"
                if value
                else "Maximize"
            )

        self.update()

    def _fade(self, end):
        self.anim.stop()

        if not self.motion:
            self.level = end
            self.update()
            return

        self.anim.setStartValue(
            self.level
        )

        self.anim.setEndValue(
            end
        )

        self.anim.start()

    def enterEvent(self, event):
        self._fade(
            1.0
        )

        super().enterEvent(
            event
        )

    def leaveEvent(self, event):
        self._fade(
            0.0
        )

        super().leaveEvent(
            event
        )

    def paintEvent(self, event):
        p = QPainter(self)

        p.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        pressed = self.isDown()

        if self.kind == "close":
            bg = QColor(
                self.close_bg
            )

            bg.setAlpha(
                int(
                    255
                    * self.level
                    * (
                        0.8
                        if pressed
                        else 1
                    )
                )
            )

        else:
            bg = QColor(
                self.hover_bg
            )

            bg.setAlpha(
                int(
                    bg.alpha()
                    * self.level
                    * (
                        1.6
                        if pressed
                        else 1
                    )
                )
            )

        p.fillRect(
            self.rect(),
            bg,
        )

        fg = (
            QColor("#ffffff")
            if (
                self.kind == "close"
                and self.level > 0.5
            )
            else self.fg
        )

        name = (
            "restore"
            if (
                self.kind == "max"
                and self.maximized
            )
            else {
                "min": "minimize",
                "max": "maximize",
                "close": "close",
            }[self.kind]
        )

        icons.draw(
            name,
            p,
            QRectF(
                self.width() / 2 - 9,
                self.height() / 2 - 9,
                18,
                18,
            ),
            fg,
            weight=0.85,
        )


class HeaderBar(QWidget):
    """
    Frameless title bar: page title on the left,
    theme switch + window controls on the right.

    Dragging the empty area moves the window;
    double-click maximises.
    """

    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()

    TAGLINE = (
        "SIGNAL ACQUISITION  /  QUEUE CONTROL  /  LOCAL OUTPUT"
    )

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName(
            "headerBar"
        )

        self.setFixedHeight(
            UI["header_height"]
        )

        self.tokens = {
            "text_strong": "#ffffff",
            "accent": "#19d3ff",
            "text2": "#9bb3cc",
            "text_btn": "#c9d7e5",
            "win_hover": "rgba(255,255,255,24)",
            "win_close": "#e5384f",
        }

        self._page = (
            "MBQ MEDIA DOWNLOADER",
            "",
            True,
        )

        root = QHBoxLayout(
            self
        )

        root.setContentsMargins(
            28,
            0,
            0,
            0,
        )

        root.setSpacing(
            0
        )

        text = QVBoxLayout()

        text.setContentsMargins(
            0,
            10,
            0,
            0,
        )

        text.setSpacing(
            0
        )

        self.title = QLabel()

        self.title.setObjectName(
            "headerTitle"
        )

        self.title.setTextFormat(
            Qt.TextFormat.RichText
        )

        self.sub = QLabel()

        self.sub.setObjectName(
            "headerSub"
        )

        self.sub.setWordWrap(
            True
        )

        text.addWidget(
            self.title
        )

        text.addWidget(
            self.sub
        )

        text.addStretch()

        root.addLayout(
            text,
            1,
        )

        right = QVBoxLayout()

        right.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        right.setSpacing(
            0
        )

        row = QHBoxLayout()

        row.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        row.setSpacing(
            0
        )

        self.theme_toggle = ThemeToggle()

        toggle_box = QVBoxLayout()

        toggle_box.setContentsMargins(
            0,
            8,
            0,
            0,
        )

        toggle_box.addWidget(
            self.theme_toggle
        )

        row.addLayout(
            toggle_box
        )

        row.addSpacing(
            18
        )

        self.btn_min = WindowButton(
            "min"
        )

        self.btn_max = WindowButton(
            "max"
        )

        self.btn_close = WindowButton(
            "close"
        )

        self.btn_min.clicked.connect(
            self.minimize_clicked
        )

        self.btn_max.clicked.connect(
            self.maximize_clicked
        )

        self.btn_close.clicked.connect(
            self.close_clicked
        )

        for b in (
            self.btn_min,
            self.btn_max,
            self.btn_close,
        ):
            row.addWidget(
                b,
                0,
                Qt.AlignmentFlag.AlignTop,
            )

        right.addLayout(
            row
        )

        right.addStretch()

        root.addLayout(
            right
        )

        self.render_page()

    def set_page(
        self,
        title,
        subtitle,
        home=False,
    ):
        self._page = (
            title,
            subtitle,
            home,
        )

        self.render_page()

    def set_theme(
        self,
        tokens,
    ):
        self.tokens = tokens

        for b in (
            self.btn_min,
            self.btn_max,
            self.btn_close,
        ):
            b.set_theme(
                tokens
            )

        self.render_page()

    def set_motion(
        self,
        enabled,
    ):
        self.theme_toggle.motion = enabled

        for b in (
            self.btn_min,
            self.btn_max,
            self.btn_close,
        ):
            b.motion = enabled

    def set_maximized(
        self,
        value,
    ):
        self.btn_max.set_maximized(
            value
        )

    def render_page(self):
        title, subtitle, home = (
            self._page
        )

        t = self.tokens

        if home:
            signal = t.get("signal", t["accent"])
            self.title.setText(
                (
                    f'<span style="font-size:14pt; font-weight:900; color:{t["text_strong"]};">MBQ</span>'
                    f'<span style="font-size:14pt; font-weight:800; color:{signal};"> / MEDIA CONSOLE</span>'
                )
            )
            self.sub.setText(self.TAGLINE)

        else:
            self.title.setText(
                (
                    f'<span style="font-size:21pt; '
                    f'font-weight:800; '
                    f'color:{t["text_strong"]};">'
                    f"{title}"
                    f"</span>"
                )
            )

            self.sub.setText(
                subtitle
            )

    def mousePressEvent(self, event):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            handle = (
                self.window().windowHandle()
            )

            if (
                handle is not None
                and not self.window().isMaximized()
            ):
                handle.startSystemMove()
                event.accept()
                return

        super().mousePressEvent(
            event
        )

    def mouseDoubleClickEvent(self, event):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.maximize_clicked.emit()
            event.accept()
            return

        super().mouseDoubleClickEvent(
            event
        )


class NavHighlight(QWidget):
    """Soft gradient pill that glides behind the active sidebar item."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        self.c1 = QColor(84, 229, 245, 42)
        self.c2 = QColor(255, 122, 34, 16)
        self.edge = QColor(84, 229, 245, 90)

        self.motion = True

        self.anim = QPropertyAnimation(
            self,
            b"geometry",
            self,
        )

        self.anim.setDuration(
            240
        )

        self.anim.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

    def set_theme(self, light):
        if light:
            self.c1 = QColor(24, 154, 180, 32)
            self.c2 = QColor(235, 105, 28, 15)
            self.edge = QColor(24, 154, 180, 90)
        else:
            self.c1 = QColor(84, 229, 245, 42)
            self.c2 = QColor(255, 122, 34, 16)
            self.edge = QColor(84, 229, 245, 90)
        self.update()

    def move_to(
        self,
        rect,
        animate=True,
    ):
        if (
            self.anim.state()
            == QPropertyAnimation.State.Running
        ):
            self.anim.stop()

        if (
            not animate
            or not self.motion
            or not self.isVisible()
            or self.geometry().isEmpty()
        ):
            self.setGeometry(
                rect
            )
            return

        self.anim.setStartValue(
            self.geometry()
        )

        self.anim.setEndValue(
            rect
        )

        self.anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        g = QLinearGradient(r.topLeft(), r.topRight())
        g.setColorAt(0, self.c1)
        g.setColorAt(0.66, self.c2)
        transparent = QColor(self.c2)
        transparent.setAlpha(0)
        g.setColorAt(1, transparent)
        p.setBrush(g)
        p.setPen(QPen(self.edge, 1))
        p.drawRoundedRect(r, 4, 4)

        # Sharp signal rail: the selected page reads as a location marker, not a pill.
        p.setPen(QPen(self.edge, 3))
        p.drawLine(QPointF(r.left() + 1.5, r.top() + 7), QPointF(r.left() + 1.5, r.bottom() - 7))


class EdgeGrip(QWidget):
    """Invisible resize handle placed on a window edge or corner."""

    def __init__(
        self,
        edges,
        parent,
    ):
        super().__init__(
            parent
        )

        self.edges = edges

        L = Qt.Edge.LeftEdge
        R = Qt.Edge.RightEdge
        T = Qt.Edge.TopEdge
        B = Qt.Edge.BottomEdge

        shape = Qt.CursorShape

        if edges in (
            L,
            R,
        ):
            self.setCursor(
                shape.SizeHorCursor
            )

        elif edges in (
            T,
            B,
        ):
            self.setCursor(
                shape.SizeVerCursor
            )

        elif edges in (
            L | T,
            R | B,
        ):
            self.setCursor(
                shape.SizeFDiagCursor
            )

        else:
            self.setCursor(
                shape.SizeBDiagCursor
            )

    def mousePressEvent(
        self,
        event,
    ):
        handle = (
            self.window().windowHandle()
        )

        if (
            event.button()
            == Qt.MouseButton.LeftButton
            and handle is not None
        ):
            handle.startSystemResize(
                self.edges
            )

            event.accept()


class FormatCard(QAbstractButton):

    def __init__(
        self,
        title,
        badge,
        detail,
        accent="#00cfff",
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.title = title
        self.badge = badge
        self.detail = detail

        self.accent = QColor(
            accent
        )

        self.level = 0.0
        self.motion = True
        self.light = False

        self.best = (
            title
            in (
                "Best Available",
                "BEST",
            )
        )

        self.phase = 0.0

        self.setCheckable(
            True
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setMinimumSize(
            100,
            108,
        )

        self.setMaximumHeight(
            112
        )

        self.setAccessibleName(
            f"{title} {badge}. {detail}"
        )

        self.anim = QVariantAnimation(
            self
        )

        self.anim.setDuration(
            170
        )

        self.anim.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        self.anim.valueChanged.connect(
            self.animate
        )

        self.toggled.connect(
            self.update
        )

    def advance(
        self,
        phase,
    ):
        if (
            self.best
            and self.motion
            and self.isVisible()
        ):
            self.phase = phase
            self.update()

    def set_motion(
        self,
        enabled,
    ):
        self.motion = enabled

        if not enabled:
            self.anim.stop()
            self.phase = 0.0

        self.update()

    def animate(
        self,
        value,
    ):
        self.level = float(
            value
        )

        self.update()

    def hover(
        self,
        end,
    ):
        self.anim.stop()

        if not self.motion:
            self.level = end
            self.update()
            return

        self.anim.setStartValue(
            self.level
        )

        self.anim.setEndValue(
            end
        )

        self.anim.start()

    def enterEvent(
        self,
        event,
    ):
        self.hover(
            1.0
        )

        super().enterEvent(
            event
        )

    def leaveEvent(
        self,
        event,
    ):
        self.hover(
            0.0
        )

        super().leaveEvent(
            event
        )

    def paintEvent(
        self,
        event,
    ):
        p = QPainter(
            self
        )

        p.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        selected = (
            self.isChecked()
        )

        strength = (
            1.0
            if selected
            else self.level
        )

        r = QRectF(
            5,
            7 - self.level * 2,
            self.width() - 10,
            self.height() - 12,
        )

        if (
            selected
            or self.level > 0.15
        ):
            halo = QColor(
                self.accent
            )

            halo.setAlpha(
                int(
                    20
                    + strength * 42
                )
            )

            p.setBrush(
                Qt.BrushStyle.NoBrush
            )

            p.setPen(
                QPen(
                    halo,
                    5,
                )
            )

            p.drawRoundedRect(
                r,
                12,
                12,
            )

        bg = QLinearGradient(
            r.topLeft(),
            r.bottomRight(),
        )

        bg.setColorAt(
            0,
            QColor(
                "#ffffff"
                if self.light
                else "#102236"
            ),
        )

        bg.setColorAt(
            1,
            QColor(
                "#edf4fb"
                if self.light
                else "#091522"
            ),
        )

        p.setBrush(
            bg
        )

        p.setPen(
            QPen(
                (
                    self.accent
                    if selected
                    else QColor(
                        "#b6c8dd"
                        if self.light
                        else "#29445f"
                    )
                ),
                (
                    1.5
                    if selected
                    else 1
                ),
            )
        )

        p.drawRoundedRect(
            r,
            12,
            12,
        )

        if (
            self.best
            and self.motion
            and selected
        ):
            ring = QConicalGradient(
                r.center(),
                -self.phase * 75,
            )

            for position, alpha in [
                (0, 0),
                (0.7, 0),
                (0.88, 90),
                (0.96, 210),
                (1, 0),
            ]:
                color = QColor(
                    "#057da9"
                    if self.light
                    else "#8eefff"
                )

                color.setAlpha(
                    alpha
                )

                ring.setColorAt(
                    position,
                    color,
                )

            p.setBrush(
                Qt.BrushStyle.NoBrush
            )

            p.setPen(
                QPen(
                    QBrush(ring),
                    2,
                )
            )

            p.drawRoundedRect(
                r,
                12,
                12,
            )

        p.setOpacity(
            1
            if self.isEnabled()
            else 0.4
        )

        display_title = (
            "BEST"
            if (
                self.best
                or self.title == "BEST"
            )
            else self.title.replace(
                " Video",
                "",
            ).upper()
        )

        title_font = QFont(
            "Segoe UI",
            10,
            QFont.Weight.Bold,
        )

        p.setFont(
            title_font
        )

        p.setPen(
            QColor(
                "#13283f"
                if self.light
                else "#f4f8ff"
            )
        )

        p.drawText(
            r.adjusted(
                11,
                12,
                -8,
                -8,
            ),
            (
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignTop
            ),
            display_title,
        )

        badge_font = QFont(
            "Segoe UI",
            8,
            QFont.Weight.DemiBold,
        )

        p.setFont(
            badge_font
        )

        p.setPen(
            self.accent
        )

        p.drawText(
            r.adjusted(
                11,
                35,
                -8,
                -8,
            ),
            (
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignTop
            ),
            self.badge,
        )

        detail_font = QFont(
            "Segoe UI",
            7,
        )

        p.setFont(
            detail_font
        )

        p.setPen(
            QColor(
                "#60748c"
                if self.light
                else "#8ca8c4"
            )
        )

        detail = self.detail.replace(
            "Source resolution",
            "Best source",
        )

        # Resolution/FPS is deliberately allowed two compact
        # lines so nothing is clipped.
        if "  •  " in detail:
            detail = detail.replace(
                "  •  ",
                "\n",
                1,
            )

        elif " • " in detail:
            detail = detail.replace(
                " • ",
                "\n",
                1,
            )

        p.drawText(
            r.adjusted(
                11,
                57,
                -8,
                -5,
            ),
            (
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignTop
                | Qt.TextFlag.TextWordWrap
            ),
            detail,
        )

        if selected:
            p.setPen(
                Qt.PenStyle.NoPen
            )

            p.setBrush(
                self.accent
            )

            p.drawEllipse(
                QPointF(
                    r.right() - 14,
                    r.top() + 14,
                ),
                4.5,
                4.5,
            )

        if self.hasFocus():
            p.setBrush(
                Qt.BrushStyle.NoBrush
            )

            p.setPen(
                QPen(
                    QColor(
                        "#173057"
                        if self.light
                        else "white"
                    ),
                    1,
                    Qt.PenStyle.DotLine,
                )
            )

            p.drawRoundedRect(
                r.adjusted(
                    3,
                    3,
                    -3,
                    -3,
                ),
                9,
                9,
            )


class PageStack(QStackedWidget):

    def __init__(self, parent=None):
        super().__init__(
            parent
        )

        self.motion = True

        self.fade = QVariantAnimation(
            self
        )

        self.fade.setDuration(
            180
        )

        self.fade.valueChanged.connect(
            self.fade_value
        )

        self.effect = None
        self.effect_widget = None

        self.fade.finished.connect(
            self.clear_effect
        )

        self.currentChanged.connect(
            self.transition
        )

    def transition(
        self,
        index,
    ):
        self.fade.stop()

        self.clear_effect()

        if (
            not self.motion
            or not self.isVisible()
        ):
            return

        self.effect = QGraphicsOpacityEffect(
            self.currentWidget()
        )

        self.effect_widget = (
            self.currentWidget()
        )

        self.currentWidget().setGraphicsEffect(
            self.effect
        )

        self.fade.setStartValue(
            0.72
        )

        self.fade.setEndValue(
            1.0
        )

        self.fade.start()

    def clear_effect(self):
        if self.effect_widget is not None:
            self.effect_widget.setGraphicsEffect(
                None
            )

        self.effect_widget = None
        self.effect = None

    def set_motion(
        self,
        enabled,
    ):
        self.motion = enabled

        if not enabled:
            self.fade.stop()
            self.clear_effect()

    def fade_value(
        self,
        value,
    ):
        if self.effect:
            self.effect.setOpacity(
                float(value)
            )


def nav_icon(
    kind,
    size=23,
    color="#a9bfd4",
    active=None,
    filled_active=False,
):
    """Sidebar icon with a normal and a selected state."""

    return icons.icon(
        kind,
        size,
        color,
        active=active,
        filled_active=filled_active,
    )