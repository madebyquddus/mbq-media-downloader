"""MBQ UI Studio 2.1 — visual live component inspector."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QDoubleSpinBox, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QTreeWidgetItemIterator, QVBoxLayout, QWidget
)

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS_PATH = ROOT / "devtools" / "ui_components.json"
SELECTED_PATH = ROOT / "devtools" / "selected_component.json"
SCENE_PATH = ROOT / "devtools" / "ui_scene.json"
PREVIEW_PATH = ROOT / "devtools" / "live_preview.png"
METRICS_PATH = ROOT / "devtools" / "ui_config.json"
APP_CONFIG = ROOT / "app" / "ui" / "ui_config.py"


CATALOG = OrderedDict({
    "Shell": [
        ("shell.sidebar", "Sidebar"),
        ("shell.sidebar.brand", "MBQ Sidebar Brand"),
        ("shell.sidebar.nav", "Navigation"),
        ("shell.sidebar.about", "MadeByQuddus / Version"),
        ("shell.header", "Header"),
        ("shell.theme_toggle", "Theme Toggle"),
    ],
    "Home / Analyzer": [
        ("home.analyzer.card", "Analyzer Card"),
        ("home.analyzer.eyebrow", "Paste & Analyze Heading"),
        ("home.analyzer.url_input", "URL Input"),
        ("home.analyzer.analyze_button", "Analyze Button"),
        ("home.analyzer.paste_button", "Paste Clipboard Button"),
        ("home.analyzer.clear_button", "Clear Button"),
        ("home.analyzer.cancel_button", "Cancel Analysis Button"),
    ],
    "Home / Media Profile": [
        ("home.media.card", "Media Profile Card"),
        ("home.media.eyebrow", "Media Profile Heading"),
        ("home.media.thumbnail", "Media Thumbnail"),
        ("home.media.title", "Media Title"),
        ("home.media.creator", "Creator Label"),
        ("home.media.meta", "Media Metadata"),
        ("home.media.video_tab", "Video Mode Button"),
        ("home.media.audio_tab", "Audio Mode Button"),
        ("home.media.container.mp4", "MP4 Button"),
        ("home.media.container.mkv", "MKV Button"),
        ("home.media.container.webm", "WebM Button"),
    ],
    "Home / Playlist": [
        ("home.playlist.panel", "Playlist Panel"),
        ("home.playlist.label", "Playlist Label"),
        ("home.playlist.table", "Media Table"),
    ],
    "Home / Extractor": [
        ("home.extractor.card", "Channel / Profile Extractor"),
        ("home.extractor.heading", "Extractor Heading"),
        ("home.extractor.avatar", "Channel Avatar"),
        ("home.extractor.name", "Channel Name"),
        ("home.extractor.meta", "Channel Metadata"),
        ("home.extractor.search", "Extractor Search"),
        ("home.extractor.open_button", "Open Channel / Profile"),
        ("home.extractor.videos_table", "Videos Table"),
        ("home.extractor.shorts_table", "Shorts Table"),
    ],
    "Home / Footer": [
        ("home.footer.bar", "Download Footer"),
        ("home.footer.summary", "Selection Summary"),
        ("home.footer.download_button", "Download Selected Button"),
        ("home.footer.bulk_button", "Bulk Download Button"),
    ],
    "Downloads": [
        ("downloads.queue_scroll", "Queue Scroll Area"),
        ("downloads.start_button", "Start Queue Button"),
        ("downloads.pause_button", "Pause Queue Button"),
        ("downloads.resume_button", "Resume Queue Button"),
        ("downloads.stop_button", "Stop After Current Button"),
    ],
    "History": [("history.search", "History Search")],
    "Advanced": [
        ("advanced.format_table", "Formats Table"),
        ("advanced.exact", "Exact Format Selection"),
        ("advanced.custom", "Advanced Arguments"),
    ],
    "Engine": [
        ("engine.status", "Engine Status"),
        ("engine.check_button", "Check Engine Button"),
        ("engine.update_button", "Update yt-dlp Button"),
    ],
    "Settings": [("settings.folder", "Download Folder")],
})


METRIC_SECTIONS = OrderedDict({
    "Main Window": [
        ("window_width", "Window width", 800, 3840),
        ("window_height", "Window height", 600, 2160),
        ("window_min_width", "Minimum window width", 700, 2400),
        ("window_min_height", "Minimum window height", 500, 1600),
    ],
    "Sidebar": [
        ("sidebar_width", "Sidebar width", 160, 420),
        ("sidebar_logo_size", "Sidebar logo size", 24, 120),
        ("sidebar_logo_x", "Sidebar logo X", 0, 100),
        ("sidebar_logo_y", "Sidebar logo Y", 0, 100),
        ("sidebar_margin_left", "Left margin", 0, 80),
        ("sidebar_margin_top", "Top margin", 0, 80),
        ("sidebar_margin_right", "Right margin", 0, 80),
        ("sidebar_margin_bottom", "Bottom margin", 0, 80),
        ("sidebar_spacing", "Sidebar spacing", 0, 40),
        ("nav_icon_size", "Navigation icon size", 14, 48),
    ],
    "Header": [("header_height", "Header height", 56, 180)],
    "Pages": [
        ("page_margin_left", "Left margin", 0, 100),
        ("page_margin_top", "Top margin", 0, 100),
        ("page_margin_right", "Right margin", 0, 100),
        ("page_margin_bottom", "Bottom margin", 0, 100),
        ("page_spacing", "Page spacing", 0, 50),
    ],
    "Home": [
        ("home_spacing", "Home spacing", 0, 50),
        ("home_scroll_right_margin", "Scroll right margin", 0, 60),
    ],
    "Analyzer": [
        ("analyzer_margin_x", "Horizontal margin", 0, 80),
        ("analyzer_margin_top", "Top margin", 0, 80),
        ("analyzer_margin_bottom", "Bottom margin", 0, 80),
        ("analyzer_spacing", "Analyzer spacing", 0, 50),
        ("url_input_height", "URL input height", 32, 120),
        ("analyze_button_height", "Analyze button height", 32, 120),
        ("analyze_button_min_width", "Analyze button min width", 80, 360),
    ],
    "Media": [
        ("media_margin_x", "Horizontal margin", 0, 80),
        ("media_margin_top", "Top margin", 0, 80),
        ("media_margin_bottom", "Bottom margin", 0, 80),
        ("media_spacing", "Media spacing", 0, 50),
    ],
    "Extractor": [
        ("extractor_margin_x", "Horizontal margin", 0, 80),
        ("extractor_margin_y", "Vertical margin", 0, 80),
        ("extractor_spacing", "Extractor spacing", 0, 50),
        ("channel_avatar_size", "Channel avatar size", 48, 180),
    ],
    "Downloads": [
        ("download_footer_min_height", "Footer min height", 56, 180),
        ("queue_scroll_min_height", "Queue min height", 180, 900),
        ("queue_card_min_height", "Queue card min height", 64, 220),
    ],
})


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_defaults():
    namespace = {"__file__": str(APP_CONFIG)}
    exec(compile(APP_CONFIG.read_text(encoding="utf-8"), str(APP_CONFIG), "exec"), namespace)
    return dict(namespace["DEFAULT_UI"])


class ColorField(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("inherit theme")
        self.edit.textEdited.connect(self.changed)
        row.addWidget(self.edit, 1)

        pick = QPushButton("●")
        pick.setFixedWidth(36)
        pick.clicked.connect(self.pick)
        row.addWidget(pick)

        clear = QPushButton("×")
        clear.setFixedWidth(36)
        clear.clicked.connect(self.clear)
        row.addWidget(clear)

    def pick(self):
        start = QColor(self.edit.text()) if self.edit.text() else QColor("#19d3ff")
        color = QColorDialog.getColor(start, self, "Choose color")
        if color.isValid():
            self.edit.setText(color.name())
            self.changed.emit()

    def clear(self):
        self.edit.clear()
        self.changed.emit()

    def text(self):
        return self.edit.text().strip()

    def setText(self, value):
        self.edit.setText(str(value or ""))


class PreviewLabel(QLabel):
    componentClicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = {}
        self.source_size = (1, 1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(420, 320)
        self.setObjectName("preview")
        self.setText("Waiting for MBQ live preview…")

    def set_scene(self, scene):
        self.scene = scene or {}
        self.source_size = (
            max(1, int(self.scene.get("window_width", 1))),
            max(1, int(self.scene.get("window_height", 1))),
        )

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.pixmap():
            return super().mousePressEvent(event)

        pix = self.pixmap()
        shown_w = pix.width()
        shown_h = pix.height()
        x0 = (self.width() - shown_w) / 2
        y0 = (self.height() - shown_h) / 2

        x = event.position().x() - x0
        y = event.position().y() - y0
        if x < 0 or y < 0 or x > shown_w or y > shown_h:
            return

        src_w, src_h = self.source_size
        sx = x * src_w / max(1, shown_w)
        sy = y * src_h / max(1, shown_h)

        candidates = []
        for cid, info in self.scene.get("components", {}).items():
            rx = info.get("x", 0)
            ry = info.get("y", 0)
            rw = info.get("width", 0)
            rh = info.get("height", 0)
            if rx <= sx <= rx + rw and ry <= sy <= ry + rh:
                candidates.append((rw * rh, cid))

        if candidates:
            candidates.sort()
            self.componentClicked.emit(candidates[0][1])


class PropertyInspector(QWidget):
    def __init__(self, on_change, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        self.loading = False
        self.component_id = ""
        self.snapshot = {}
        self.editors = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        self.title = QLabel("No component selected")
        self.title.setObjectName("inspectorTitle")
        self.sub = QLabel("Click the real MBQ window or the Live Preview.")
        self.sub.setObjectName("muted")
        self.sub.setWordWrap(True)
        outer.addWidget(self.title)
        outer.addWidget(self.sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        self.form = QFormLayout(panel)
        self.form.setContentsMargins(4, 6, 8, 12)
        self.form.setSpacing(8)

        self._line("text", "Text")
        self._line("placeholder", "Placeholder")
        self._spin("width", "Width", 0, 2000, " px")
        self._spin("height", "Height", 0, 1200, " px")
        self._spin("min_width", "Minimum width", 0, 2000, " px")
        self._spin("min_height", "Minimum height", 0, 1200, " px")
        self._spin("offset_x", "Position offset X", -300, 300, " px")
        self._spin("offset_y", "Position offset Y", -300, 300, " px")
        self._line("font_family", "Font family")
        self._double("font_size", "Font size", 5, 72, " pt")
        self._spin("font_weight", "Font weight", 100, 900)

        self._color("background", "Background")
        self._color("text_color", "Text color")
        self._color("border_color", "Border color")
        self._spin("border_width", "Border width", 0, 12, " px")
        self._spin("border_radius", "Border radius", 0, 80, " px")
        self._spin("padding_x", "Padding X", 0, 80, " px")
        self._spin("padding_y", "Padding Y", 0, 80, " px")
        self._color("hover_background", "Hover background")
        self._color("hover_text_color", "Hover text")
        self._color("hover_border_color", "Hover border")
        self._color("pressed_background", "Pressed background")
        self._color("pressed_text_color", "Pressed text")
        self._color("disabled_background", "Disabled background")
        self._color("disabled_text_color", "Disabled text")

        scroll.setWidget(panel)
        outer.addWidget(scroll, 1)

        row = QHBoxLayout()
        reset = QPushButton("Reset Component")
        reset.clicked.connect(self.reset_component)
        row.addWidget(reset)
        row.addStretch()
        outer.addLayout(row)

    def _line(self, key, label):
        e = QLineEdit()
        e.textEdited.connect(self.changed)
        self.editors[key] = e
        self.form.addRow(label, e)

    def _spin(self, key, label, minimum, maximum, suffix=""):
        e = QSpinBox()
        e.setRange(minimum, maximum)
        e.setSuffix(suffix)
        e.valueChanged.connect(self.changed)
        self.editors[key] = e
        self.form.addRow(label, e)

    def _double(self, key, label, minimum, maximum, suffix=""):
        e = QDoubleSpinBox()
        e.setRange(minimum, maximum)
        e.setDecimals(1)
        e.setSuffix(suffix)
        e.valueChanged.connect(self.changed)
        self.editors[key] = e
        self.form.addRow(label, e)

    def _color(self, key, label):
        e = ColorField()
        e.changed.connect(self.changed)
        self.editors[key] = e
        self.form.addRow(label, e)

    def changed(self, *_):
        if not self.loading and self.component_id:
            self.on_change(self.component_id, self.values())

    def values(self):
        data = {}
        for key, editor in self.editors.items():
            if isinstance(editor, QLineEdit):
                value = editor.text()
                if value:
                    data[key] = value
            elif isinstance(editor, ColorField):
                value = editor.text()
                if value:
                    data[key] = value
            elif isinstance(editor, QDoubleSpinBox):
                data[key] = editor.value()
            elif isinstance(editor, QSpinBox):
                data[key] = editor.value()
        return data

    def load_component(self, component_id, label, snapshot, override):
        self.loading = True
        self.component_id = component_id
        self.snapshot = snapshot or {}
        self.title.setText(label)
        self.sub.setText(
            f"{component_id}\n"
            f"{snapshot.get('class_name', 'Not connected')} • "
            f"{snapshot.get('width', '?')}×{snapshot.get('height', '?')} px • "
            f"X {snapshot.get('x', '?')} / Y {snapshot.get('y', '?')}"
        )

        defaults = {
            "text": snapshot.get("text", ""),
            "placeholder": snapshot.get("placeholder", ""),
            "width": snapshot.get("width", 0),
            "height": snapshot.get("height", 0),
            "min_width": snapshot.get("min_width", 0),
            "min_height": snapshot.get("min_height", 0),
            "offset_x": 0,
            "offset_y": 0,
            "font_family": snapshot.get("font_family", ""),
            "font_size": snapshot.get("font_size", 10),
            "font_weight": snapshot.get("font_weight", 400),
            "border_width": 0,
            "border_radius": 0,
            "padding_x": 0,
            "padding_y": 0,
        }

        for key, editor in self.editors.items():
            value = override.get(key, defaults.get(key, ""))
            if isinstance(editor, QLineEdit):
                editor.setText(str(value or ""))
            elif isinstance(editor, ColorField):
                editor.setText(value)
            elif isinstance(editor, QDoubleSpinBox):
                editor.setValue(float(value or defaults.get(key, 10)))
            elif isinstance(editor, QSpinBox):
                try:
                    editor.setValue(int(value))
                except Exception:
                    editor.setValue(int(defaults.get(key, 0) or 0))

        self.loading = False

    def reset_component(self):
        if self.component_id:
            self.on_change(self.component_id, None)


class GlobalMetrics(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.defaults = load_defaults()
        self.overlay = read_json(METRICS_PATH, {})
        self.controls = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        stack = QVBoxLayout(content)
        stack.setSpacing(12)

        for section, fields in METRIC_SECTIONS.items():
            card = QFrame()
            card.setObjectName("metricCard")
            box = QVBoxLayout(card)
            title = QLabel(section)
            title.setObjectName("sectionTitle")
            box.addWidget(title)
            form = QFormLayout()
            form.setSpacing(9)
            for key, label, minimum, maximum in fields:
                spin = QSpinBox()
                spin.setRange(minimum, maximum)
                spin.setValue(int(self.overlay.get(key, self.defaults[key])))
                spin.setSuffix(" px")
                self.controls[key] = spin
                form.addRow(label, spin)
            box.addLayout(form)
            stack.addWidget(card)

        stack.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        row = QHBoxLayout()
        reset = QPushButton("Reset Metrics")
        reset.clicked.connect(self.reset)
        save = QPushButton("Save Metrics")
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        row.addWidget(reset)
        row.addStretch()
        row.addWidget(save)
        outer.addLayout(row)

    def save(self):
        values = {k: w.value() for k, w in self.controls.items()}
        overlay = {k: v for k, v in values.items() if v != self.defaults.get(k)}
        write_json(METRICS_PATH, overlay)
        QMessageBox.information(self, "Saved", "Global metrics saved. Relaunch MBQ to apply them.")

    def reset(self):
        for key, widget in self.controls.items():
            widget.setValue(int(self.defaults[key]))


class Studio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MBQ UI Studio 2.1 — Live Visual Inspector")
        self.resize(1550, 920)
        self.setMinimumSize(1100, 700)

        self.overrides = read_json(COMPONENTS_PATH, {})
        self.scene = {}
        self.selected_mtime = -1
        self.preview_mtime = -1
        self.scene_mtime = -1
        self.current_component = ""

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(9)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("MBQ UI Studio 2.1")
        title.setObjectName("title")
        subtitle = QLabel("Live visual preview + click-to-select + real component property editing.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top.addLayout(title_box, 1)

        self.bring_btn = QPushButton("Bring MBQ to Front")
        self.bring_btn.clicked.connect(self.bring_mbq_hint)
        top.addWidget(self.bring_btn)

        launch = QPushButton("▶  Launch MBQ Inspect Mode")
        launch.setObjectName("primary")
        launch.clicked.connect(self.launch_mbq)
        top.addWidget(launch)
        outer.addLayout(top)

        self.status = QLabel("Not connected. Launch MBQ Inspect Mode.")
        self.status.setObjectName("notice")
        outer.addWidget(self.status)

        tabs = QTabWidget()
        outer.addWidget(tabs, 1)

        page = QWidget()
        tabs.addTab(page, "Visual Inspector")
        main = QHBoxLayout(page)
        main.setContentsMargins(0, 8, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(splitter)

        # Left
        left = QFrame()
        left.setObjectName("panel")
        left_box = QVBoxLayout(left)
        h = QLabel("COMPONENT TREE")
        h.setObjectName("sectionTitle")
        left_box.addWidget(h)
        hint = QLabel("Click the tree, the real MBQ window, or directly on the live preview.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        left_box.addWidget(hint)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.tree_selected)
        left_box.addWidget(self.tree, 1)
        splitter.addWidget(left)

        # Center live preview
        center = QFrame()
        center.setObjectName("panel")
        center_box = QVBoxLayout(center)
        center_head = QHBoxLayout()
        label = QLabel("LIVE MBQ PREVIEW")
        label.setObjectName("sectionTitle")
        center_head.addWidget(label)
        center_head.addStretch()
        self.preview_state = QLabel("OFFLINE")
        self.preview_state.setObjectName("state")
        center_head.addWidget(self.preview_state)
        center_box.addLayout(center_head)

        self.preview = PreviewLabel()
        self.preview.componentClicked.connect(self.preview_clicked)
        center_box.addWidget(self.preview, 1)

        self.live_info = QLabel("Launch Inspect Mode. The actual MBQ window will be mirrored here.")
        self.live_info.setObjectName("muted")
        self.live_info.setWordWrap(True)
        center_box.addWidget(self.live_info)

        reset_all = QPushButton("Reset ALL Component Overrides")
        reset_all.clicked.connect(self.reset_all)
        center_box.addWidget(reset_all)
        splitter.addWidget(center)

        # Right
        self.inspector = PropertyInspector(self.update_component)
        self.inspector.setObjectName("panel")
        splitter.addWidget(self.inspector)
        splitter.setSizes([300, 650, 520])

        self.populate_tree()

        tabs.addTab(GlobalMetrics(), "Global Metrics")

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #07111f; color: #e9f3ff;
                font-family: "Segoe UI"; font-size: 10pt;
            }
            QLabel#title { font-size: 23pt; font-weight: 850; color: white; }
            QLabel#muted { color: #8da9c4; }
            QLabel#notice {
                background: #0b1c2f; border: 1px solid #1d4260;
                border-radius: 9px; padding: 9px 11px; color: #9bc7e5;
            }
            QLabel#sectionTitle { font-weight: 800; font-size: 11pt; color: white; }
            QLabel#inspectorTitle { font-weight: 850; font-size: 15pt; color: white; }
            QLabel#state {
                color: #70e5ff; background: #0b2840; border: 1px solid #1c5b7f;
                border-radius: 7px; padding: 4px 8px; font-weight: 800;
            }
            QLabel#preview {
                background: #040a12; border: 1px solid #173852;
                border-radius: 8px; color: #6f8ba3;
            }
            QFrame#panel, QFrame#metricCard {
                background: #0a1727; border: 1px solid #173852; border-radius: 11px;
            }
            QTreeWidget, QLineEdit, QSpinBox, QDoubleSpinBox, QScrollArea {
                background: #07111f; color: #e9f3ff;
                border: 1px solid #234761; border-radius: 7px;
            }
            QTreeWidget { padding: 6px; }
            QTreeWidget::item { min-height: 29px; padding: 2px 5px; }
            QTreeWidget::item:selected { background: #14577e; color: white; }
            QLineEdit, QSpinBox, QDoubleSpinBox { min-height: 31px; padding: 0 7px; }
            QPushButton {
                min-height: 34px; padding: 0 13px; background: #10253a;
                color: #ddecf9; border: 1px solid #28516d;
                border-radius: 8px; font-weight: 650;
            }
            QPushButton:hover { background: #16344f; border-color: #2a9cca; }
            QPushButton#primary {
                background: #087fca; border-color: #28d8ff;
                color: white; font-weight: 800; min-height: 40px;
            }
            QTabWidget::pane { border: 1px solid #173852; border-radius: 8px; }
            QTabBar::tab {
                background: #0b1a2c; color: #92acc4; padding: 9px 16px;
                border: 1px solid #173852;
            }
            QTabBar::tab:selected { background: #12304a; color: white; }
        """)

        self.poller = QTimer(self)
        self.poller.setInterval(200)
        self.poller.timeout.connect(self.poll_files)
        self.poller.start()

    def populate_tree(self):
        self.tree.clear()
        for group, components in CATALOG.items():
            parent = QTreeWidgetItem([group])
            parent.setData(0, Qt.ItemDataRole.UserRole, "")
            self.tree.addTopLevelItem(parent)
            for cid, label in components:
                item = QTreeWidgetItem([label])
                item.setData(0, Qt.ItemDataRole.UserRole, cid)
                parent.addChild(item)
            parent.setExpanded(group.startswith("Home"))

    def launch_mbq(self):
        main_py = ROOT / "main.py"
        if not main_py.is_file():
            QMessageBox.critical(self, "main.py not found", str(main_py))
            return

        env = os.environ.copy()
        env["MBQ_UI_DEV"] = "1"
        env["MBQ_UI_DEV_INSPECT"] = "1"

        try:
            subprocess.Popen([sys.executable, str(main_py)], cwd=str(ROOT), env=env)
        except OSError as exc:
            QMessageBox.critical(self, "Launch failed", str(exc))
            return

        self.status.setText(
            "INSPECT MODE STARTED • Wait 1–2 seconds. The MBQ window should open separately and its live preview will appear below."
        )

    def bring_mbq_hint(self):
        QMessageBox.information(
            self,
            "Bring MBQ to Front",
            "Use Alt+Tab and choose MBQ MEDIA DOWNLOADER.\n\n"
            "The live preview in the center is also clickable, so you do not have to keep switching windows."
        )

    def poll_files(self):
        self.poll_scene()
        self.poll_preview()
        self.poll_selection()

    def poll_scene(self):
        try:
            m = SCENE_PATH.stat().st_mtime_ns
        except OSError:
            return
        if m == self.scene_mtime:
            return
        self.scene_mtime = m
        scene = read_json(SCENE_PATH, {})
        if isinstance(scene, dict):
            self.scene = scene
            self.preview.set_scene(scene)
            self.preview_state.setText("LIVE")
            self.status.setText("CONNECTED • Click a component in the preview or in the actual MBQ window.")

    def poll_preview(self):
        try:
            m = PREVIEW_PATH.stat().st_mtime_ns
        except OSError:
            return
        if m == self.preview_mtime:
            return
        self.preview_mtime = m

        pix = QPixmap(str(PREVIEW_PATH))
        if pix.isNull():
            return

        scaled = pix.scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview.setPixmap(scaled)

    def poll_selection(self):
        try:
            m = SELECTED_PATH.stat().st_mtime_ns
        except OSError:
            return
        if m == self.selected_mtime:
            return
        self.selected_mtime = m
        data = read_json(SELECTED_PATH, {})
        cid = data.get("component_id") if isinstance(data, dict) else None
        if cid:
            self.select_component(cid, data)

    def preview_clicked(self, cid):
        info = self.scene.get("components", {}).get(cid, {})
        snapshot = dict(info)
        snapshot["component_id"] = cid
        self.select_component(cid, snapshot)

    def tree_selected(self, item, column):
        cid = item.data(0, Qt.ItemDataRole.UserRole)
        if cid:
            info = self.scene.get("components", {}).get(cid, {})
            snapshot = dict(info)
            snapshot["component_id"] = cid
            self.select_component(cid, snapshot)

    def label_for(self, cid):
        for group, comps in CATALOG.items():
            for item_id, label in comps:
                if item_id == cid:
                    return label
        return cid

    def select_component(self, cid, snapshot):
        self.current_component = cid
        label = snapshot.get("label") or self.label_for(cid)
        self.inspector.load_component(cid, label, snapshot, self.overrides.get(cid, {}))
        self.live_info.setText(
            f"{label} • {cid}\n"
            f"{snapshot.get('class_name', 'Not connected')} • "
            f"{snapshot.get('width', '?')}×{snapshot.get('height', '?')} px"
        )
        self.select_tree_id(cid)

    def select_tree_id(self, cid):
        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == cid:
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                break
            it += 1

    def update_component(self, cid, values):
        if values is None:
            self.overrides.pop(cid, None)
        else:
            self.overrides[cid] = {k: v for k, v in values.items() if v not in (None, "")}
        write_json(COMPONENTS_PATH, self.overrides)
        self.status.setText(f"LIVE APPLY • {self.label_for(cid)}")

    def reset_all(self):
        if QMessageBox.question(
            self, "Reset all overrides", "Remove every component-level override?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.overrides = {}
        write_json(COMPONENTS_PATH, {})
        self.status.setText("All component overrides cleared.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MBQ UI Studio 2.1")
    app.setFont(QFont("Segoe UI", 10))
    window = Studio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
