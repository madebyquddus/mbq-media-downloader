"""Dependency-free painted icons (Qt Essentials only).

Every icon is drawn with QPainter so it stays crisp at any DPI and can be
recoloured for the dark and light themes.  Use:

    icons.icon('home', 22, '#a9bfd4', active='#ffffff', filled_active=True)
    icons.pixmap('search', 18, '#8fa5bd')
    icons.draw('close', painter, QRectF(0, 0, 16, 16), QColor('#fff'))
"""
import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QPixmap, QIcon, QBrush

ALIASES = {'download': 'downloads'}


def _poly(points, s, close=False):
    path = QPainterPath(QPointF(points[0][0] * s, points[0][1] * s))
    for x, y in points[1:]:
        path.lineTo(x * s, y * s)
    if close:
        path.closeSubpath()
    return path


def draw(name, p, rect, color, filled=False, weight=1.0):
    """Draw icon `name` inside `rect` (QRectF) using painter `p`."""
    name = ALIASES.get(name, name)
    color = QColor(color)
    s = min(rect.width(), rect.height())
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(rect.center().x() - s / 2, rect.center().y() - s / 2)
    pen = QPen(color, max(1.2, s * 0.075 * weight))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    solid = QBrush(color)
    R = QRectF

    if name == 'home':
        if filled:
            p.setBrush(solid)
            p.drawPath(_poly([(.16, .50), (.50, .19), (.84, .50), (.74, .50), (.74, .82), (.26, .82), (.26, .50)], s, True))
            p.setBrush(Qt.BrushStyle.NoBrush)
        else:
            p.drawPath(_poly([(.16, .50), (.50, .19), (.84, .50)], s))
            p.drawRoundedRect(R(s * .27, s * .45, s * .46, s * .37), 2, 2)
    elif name == 'downloads':
        p.drawLine(QPointF(s * .5, s * .16), QPointF(s * .5, s * .62))
        p.drawPath(_poly([(.32, .46), (.5, .64), (.68, .46)], s))
        p.drawPath(_poly([(.22, .66), (.22, .80), (.78, .80), (.78, .66)], s))
    elif name == 'history':
        p.drawEllipse(R(s * .18, s * .18, s * .64, s * .64))
        p.drawPath(_poly([(.5, .32), (.5, .52), (.65, .61)], s))
    elif name == 'advanced':
        for y, x in [(.30, .36), (.50, .64), (.70, .44)]:
            p.drawLine(QPointF(s * .18, s * y), QPointF(s * .82, s * y))
            p.setBrush(QBrush(QColor(0, 0, 0, 0)) if not filled else solid)
            p.drawEllipse(QPointF(s * x, s * y), s * .07, s * .07)
    elif name == 'engine':
        p.drawRoundedRect(R(s * .29, s * .29, s * .42, s * .42), 3, 3)
        p.drawRect(R(s * .41, s * .41, s * .18, s * .18))
        for t in (.36, .5, .64):
            p.drawLine(QPointF(s * .15, s * t), QPointF(s * .27, s * t))
            p.drawLine(QPointF(s * .73, s * t), QPointF(s * .85, s * t))
            p.drawLine(QPointF(s * t, s * .15), QPointF(s * t, s * .27))
            p.drawLine(QPointF(s * t, s * .73), QPointF(s * t, s * .85))
    elif name == 'settings':
        p.drawEllipse(QPointF(s * .5, s * .5), s * .15, s * .15)
        p.drawEllipse(QPointF(s * .5, s * .5), s * .30, s * .30)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(s * .5 + math.cos(a) * s * .30, s * .5 + math.sin(a) * s * .30),
                       QPointF(s * .5 + math.cos(a) * s * .42, s * .5 + math.sin(a) * s * .42))
    elif name == 'link':
        p.translate(s / 2, s / 2)
        p.rotate(-45)
        p.drawRoundedRect(R(-s * .40, -s * .13, s * .48, s * .26), s * .13, s * .13)
        p.drawRoundedRect(R(-s * .08, -s * .13, s * .48, s * .26), s * .13, s * .13)
    elif name == 'clipboard':
        p.drawRoundedRect(R(s * .24, s * .20, s * .52, s * .64), 3, 3)
        p.setBrush(QColor(0, 0, 0, 0))
        p.drawRoundedRect(R(s * .38, s * .12, s * .24, s * .15), 2, 2)
        p.drawLine(QPointF(s * .36, s * .50), QPointF(s * .64, s * .50))
        p.drawLine(QPointF(s * .36, s * .65), QPointF(s * .56, s * .65))
    elif name == 'trash':
        p.drawLine(QPointF(s * .20, s * .30), QPointF(s * .80, s * .30))
        p.drawPath(_poly([(.40, .30), (.40, .18), (.60, .18), (.60, .30)], s))
        p.drawPath(_poly([(.28, .30), (.32, .84), (.68, .84), (.72, .30)], s))
        p.drawLine(QPointF(s * .43, s * .46), QPointF(s * .43, s * .70))
        p.drawLine(QPointF(s * .57, s * .46), QPointF(s * .57, s * .70))
    elif name == 'search':
        p.drawEllipse(QPointF(s * .45, s * .45), s * .24, s * .24)
        p.drawLine(QPointF(s * .63, s * .63), QPointF(s * .82, s * .82))
    elif name == 'crown':
        p.setBrush(solid)
        p.drawPath(_poly([(.14, .72), (.10, .30), (.33, .50), (.50, .22), (.67, .50), (.90, .30), (.86, .72)], s, True))
        p.drawLine(QPointF(s * .18, s * .82), QPointF(s * .82, s * .82))
    elif name == 'external':
        p.drawPath(_poly([(.44, .22), (.22, .22), (.22, .78), (.78, .78), (.78, .56)], s))
        p.drawLine(QPointF(s * .48, s * .52), QPointF(s * .80, s * .20))
        p.drawPath(_poly([(.58, .20), (.80, .20), (.80, .42)], s))
    elif name == 'dots':
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(solid)
        for y in (.24, .50, .76):
            p.drawEllipse(QPointF(s * .5, s * y), s * .07, s * .07)
    elif name == 'check':
        p.drawPath(_poly([(.22, .52), (.42, .70), (.78, .30)], s))
    elif name == 'play':
        p.setBrush(solid if filled else Qt.BrushStyle.NoBrush)
        p.drawPath(_poly([(.32, .20), (.32, .80), (.80, .50)], s, True))
    elif name == 'music':
        p.drawPath(_poly([(.46, .72), (.46, .22), (.76, .30), (.76, .38)], s))
        p.setBrush(solid)
        p.drawEllipse(QPointF(s * .36, s * .72), s * .11, s * .09)
        p.drawEllipse(QPointF(s * .66, s * .66), s * .11, s * .09)
        p.drawLine(QPointF(s * .76, s * .38), QPointF(s * .76, s * .66))
    elif name == 'stack':
        p.drawPath(_poly([(.50, .16), (.86, .34), (.50, .52), (.14, .34)], s, True))
        p.drawPath(_poly([(.14, .50), (.50, .68), (.86, .50)], s))
        p.drawPath(_poly([(.14, .66), (.50, .84), (.86, .66)], s))
    elif name == 'shorts':
        p.drawRoundedRect(R(s * .30, s * .14, s * .40, s * .72), s * .13, s * .13)
        p.setBrush(solid)
        p.drawPath(_poly([(.43, .40), (.43, .60), (.60, .50)], s, True))
    elif name == 'video':
        p.drawRoundedRect(R(s * .14, s * .24, s * .72, s * .52), 4, 4)
        p.setBrush(solid)
        p.drawPath(_poly([(.43, .38), (.43, .62), (.63, .50)], s, True))
    elif name == 'minimize':
        p.drawLine(QPointF(s * .28, s * .52), QPointF(s * .72, s * .52))
    elif name == 'maximize':
        p.drawRect(R(s * .28, s * .28, s * .44, s * .44))
    elif name == 'restore':
        p.drawRect(R(s * .26, s * .36, s * .38, s * .38))
        p.drawPath(_poly([(.38, .36), (.38, .26), (.74, .26), (.74, .62), (.64, .62)], s))
    elif name == 'close':
        p.drawLine(QPointF(s * .28, s * .28), QPointF(s * .72, s * .72))
        p.drawLine(QPointF(s * .72, s * .28), QPointF(s * .28, s * .72))
    elif name == 'arrow_right':
        p.drawLine(QPointF(s * .20, s * .50), QPointF(s * .80, s * .50))
        p.drawPath(_poly([(.58, .28), (.80, .50), (.58, .72)], s))
    elif name == 'sun':
        p.drawEllipse(QPointF(s * .5, s * .5), s * .17, s * .17)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(s * .5 + math.cos(a) * s * .28, s * .5 + math.sin(a) * s * .28),
                       QPointF(s * .5 + math.cos(a) * s * .38, s * .5 + math.sin(a) * s * .38))
    elif name == 'moon':
        path = QPainterPath()
        path.addEllipse(QPointF(s * .5, s * .5), s * .30, s * .30)
        cut = QPainterPath()
        cut.addEllipse(QPointF(s * .64, s * .40), s * .26, s * .26)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(solid)
        p.drawPath(path.subtracted(cut))
    elif name == 'verified':
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(solid)
        p.drawEllipse(QPointF(s * .5, s * .5), s * .40, s * .40)
        tick = QPen(QColor('#ffffff'), max(1.4, s * .09))
        tick.setCapStyle(Qt.PenCapStyle.RoundCap)
        tick.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(tick)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_poly([(.32, .52), (.45, .65), (.69, .38)], s))
    p.restore()


def pixmap(name, size=22, color='#a9bfd4', filled=False, dpr=2.0, weight=1.0):
    px = QPixmap(int(size * dpr), int(size * dpr))
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    draw(name, p, QRectF(0, 0, size, size), color, filled, weight)
    p.end()
    return px


def icon(name, size=22, color='#a9bfd4', active=None, filled_active=False, hover=None):
    """QIcon with a normal state and (optionally) a Selected/Active state."""
    ico = QIcon()
    normal = pixmap(name, size, color)
    ico.addPixmap(normal, QIcon.Mode.Normal, QIcon.State.Off)
    ico.addPixmap(pixmap(name, size, color, dpr=2.0), QIcon.Mode.Disabled, QIcon.State.Off)
    if hover:
        ico.addPixmap(pixmap(name, size, hover), QIcon.Mode.Active, QIcon.State.Off)
    if active:
        sel = pixmap(name, size, active, filled=filled_active, weight=1.15)
        ico.addPixmap(sel, QIcon.Mode.Selected, QIcon.State.Off)
        ico.addPixmap(sel, QIcon.Mode.Selected, QIcon.State.On)
    return ico
