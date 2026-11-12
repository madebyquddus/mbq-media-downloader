"""Runtime bridge for MBQ UI Studio 2.1.

Developer only. Loaded only when MBQ_UI_DEV_INSPECT=1 and never in frozen builds.
Provides:
- click-to-select on the real MBQ window
- live component snapshots
- live screenshot preview
- live component rectangle map
- hot-reload of component overrides
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QEvent, QTimer, Qt, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractButton, QComboBox, QLabel, QLineEdit, QPlainTextEdit,
    QProgressBar, QTableWidget, QWidget
)

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS_PATH = ROOT / "devtools" / "ui_components.json"
SELECTED_PATH = ROOT / "devtools" / "selected_component.json"
SCENE_PATH = ROOT / "devtools" / "ui_scene.json"
PREVIEW_PATH = ROOT / "devtools" / "live_preview.png"


def inspector_enabled() -> bool:
    if getattr(sys, "frozen", False):
        return False
    return os.environ.get("MBQ_UI_DEV_INSPECT", "").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _read_json(path: Path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


class UIStudioRuntime(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.widgets = {}
        self.last_component_mtime = -1.0
        self.overrides = {}
        self._filtered = set()

        self._register_components()
        self._install_filters()

        self.override_timer = QTimer(self)
        self.override_timer.setInterval(180)
        self.override_timer.timeout.connect(self.reload_overrides_if_changed)
        self.override_timer.start()

        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(350)
        self.preview_timer.timeout.connect(self.publish_live_scene)
        self.preview_timer.start()

        self.filter_timer = QTimer(self)
        self.filter_timer.setInterval(1000)
        self.filter_timer.timeout.connect(self._install_filters)
        self.filter_timer.start()

        self.reload_overrides_if_changed(force=True)
        QTimer.singleShot(300, self.publish_live_scene)

    def _add(self, component_id, widget, label, group):
        if not isinstance(widget, QWidget):
            return
        widget.setProperty("mbq_component_id", component_id)
        widget.setProperty("mbq_component_label", label)
        widget.setProperty("mbq_component_group", group)
        self.widgets[component_id] = widget

    def _register_components(self):
        w = self.window

        # Shell
        self._add("shell.sidebar", getattr(w, "sidebar", None), "Sidebar", "Shell")
        self._add("shell.sidebar.brand", getattr(w, "sidebar_brand", None), "MBQ Sidebar Brand", "Shell")
        self._add("shell.sidebar.nav", getattr(w, "nav", None), "Navigation", "Shell")
        self._add("shell.sidebar.about", getattr(w, "about_button", None), "MadeByQuddus / Version", "Shell")
        self._add("shell.header", getattr(w, "header", None), "Header", "Shell")
        self._add("shell.theme_toggle", getattr(w, "theme_toggle", None), "Theme Toggle", "Shell")

        # Home / Analyzer
        self._add("home.analyzer.card", getattr(w, "analyze_card", None), "Analyzer Card", "Home / Analyzer")
        self._add("home.analyzer.eyebrow", getattr(w, "analyzer_eyebrow", None), "Paste & Analyze Heading", "Home / Analyzer")
        self._add("home.analyzer.url_input", getattr(w, "url_input", None), "URL Input", "Home / Analyzer")
        self._add("home.analyzer.analyze_button", getattr(w, "analyze_button", None), "Analyze Button", "Home / Analyzer")
        self._add("home.analyzer.paste_button", getattr(w, "paste_button", None), "Paste Clipboard Button", "Home / Analyzer")
        self._add("home.analyzer.clear_button", getattr(w, "clear_button", None), "Clear Button", "Home / Analyzer")
        self._add("home.analyzer.cancel_button", getattr(w, "cancel_analysis_button", None), "Cancel Analysis Button", "Home / Analyzer")

        # Home / Media
        self._add("home.media.card", getattr(w, "media_card", None), "Media Profile Card", "Home / Media Profile")
        self._add("home.media.eyebrow", getattr(w, "media_eyebrow", None), "Media Profile Heading", "Home / Media Profile")
        self._add("home.media.thumbnail", getattr(w, "thumbnail", None), "Media Thumbnail", "Home / Media Profile")
        self._add("home.media.title", getattr(w, "media_title_label", None), "Media Title", "Home / Media Profile")
        self._add("home.media.creator", getattr(w, "media_creator_label", None), "Creator Label", "Home / Media Profile")
        self._add("home.media.meta", getattr(w, "media_meta_label", None), "Media Metadata", "Home / Media Profile")
        self._add("home.media.video_tab", getattr(w, "video_mode_button", None), "Video Mode Button", "Home / Media Profile")
        self._add("home.media.audio_tab", getattr(w, "audio_mode_button", None), "Audio Mode Button", "Home / Media Profile")
        self._add("home.media.container.mp4", getattr(w, "mp4_button", None), "MP4 Button", "Home / Media Profile")
        self._add("home.media.container.mkv", getattr(w, "mkv_button", None), "MKV Button", "Home / Media Profile")
        self._add("home.media.container.webm", getattr(w, "webm_button", None), "WebM Button", "Home / Media Profile")

        # Home / Playlist
        self._add("home.playlist.panel", getattr(w, "playlist_panel", None), "Playlist Panel", "Home / Playlist")
        self._add("home.playlist.label", getattr(w, "playlist_label", None), "Playlist Label", "Home / Playlist")
        self._add("home.playlist.table", getattr(w, "media_table", None), "Media Table", "Home / Playlist")

        # Home / Extractor
        self._add("home.extractor.card", getattr(w, "channel_section", None), "Channel / Profile Extractor", "Home / Extractor")
        self._add("home.extractor.heading", getattr(w, "channel_eyebrow", None), "Extractor Heading", "Home / Extractor")
        self._add("home.extractor.avatar", getattr(w, "channel_avatar", None), "Channel Avatar", "Home / Extractor")
        self._add("home.extractor.name", getattr(w, "channel_name_label", None), "Channel Name", "Home / Extractor")
        self._add("home.extractor.meta", getattr(w, "channel_meta_label", None), "Channel Metadata", "Home / Extractor")
        self._add("home.extractor.search", getattr(w, "channel_search", None), "Extractor Search", "Home / Extractor")
        self._add("home.extractor.open_button", getattr(w, "channel_open_button", None), "Open Channel / Profile", "Home / Extractor")
        self._add("home.extractor.videos_table", getattr(w, "channel_videos_table", None), "Videos Table", "Home / Extractor")
        self._add("home.extractor.shorts_table", getattr(w, "channel_shorts_table", None), "Shorts Table", "Home / Extractor")

        # Home / Footer
        self._add("home.footer.bar", getattr(w, "download_footer", None), "Download Footer", "Home / Footer")
        self._add("home.footer.summary", getattr(w, "selection_summary", None), "Selection Summary", "Home / Footer")
        self._add("home.footer.download_button", getattr(w, "download_button", None), "Download Selected Button", "Home / Footer")
        self._add("home.footer.bulk_button", getattr(w, "channel_download_button", None), "Bulk Download Button", "Home / Footer")

        # Other pages
        self._add("downloads.queue_scroll", getattr(w, "queue_scroll", None), "Queue Scroll Area", "Downloads")
        self._add("downloads.start_button", getattr(w, "queue_start_button", None), "Start Queue Button", "Downloads")
        self._add("downloads.pause_button", getattr(w, "queue_pause_button", None), "Pause Queue Button", "Downloads")
        self._add("downloads.resume_button", getattr(w, "queue_resume_button", None), "Resume Queue Button", "Downloads")
        self._add("downloads.stop_button", getattr(w, "queue_stop_button", None), "Stop After Current Button", "Downloads")
        self._add("history.search", getattr(w, "search", None), "History Search", "History")
        self._add("advanced.format_table", getattr(w, "formats_table", None), "Formats Table", "Advanced")
        self._add("advanced.exact", getattr(w, "exact", None), "Exact Format Selection", "Advanced")
        self._add("advanced.custom", getattr(w, "custom", None), "Advanced Arguments", "Advanced")
        self._add("engine.status", getattr(w, "engine_status", None), "Engine Status", "Engine")
        self._add("engine.check_button", getattr(w, "check_button", None), "Check Engine Button", "Engine")
        self._add("engine.update_button", getattr(w, "update_button", None), "Update yt-dlp Button", "Engine")
        self._add("settings.folder", getattr(w, "folder", None), "Download Folder", "Settings")

    def _install_filters(self):
        # Re-scan because queue cards and other dynamic widgets can appear later.
        for widget in self.window.findChildren(QWidget):
            marker = id(widget)
            if marker in self._filtered:
                continue
            widget.installEventFilter(self)
            self._filtered.add(marker)

    def _component_for_widget(self, widget):
        current = widget
        while isinstance(current, QWidget):
            cid = current.property("mbq_component_id")
            if cid:
                return current
            current = current.parentWidget()
        return None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            target = self._component_for_widget(obj)
            if target is not None:
                self.select_widget(target)
                # Click means "select" in inspect mode.
                return True
        return super().eventFilter(obj, event)

    def snapshot(self, widget):
        text = ""
        placeholder = ""

        if hasattr(widget, "text") and callable(widget.text):
            try:
                text = widget.text()
            except Exception:
                pass

        if hasattr(widget, "placeholderText") and callable(widget.placeholderText):
            try:
                placeholder = widget.placeholderText()
            except Exception:
                pass

        font = widget.font()
        g = widget.geometry()
        p = widget.mapTo(self.window, QPoint(0, 0))

        return {
            "class_name": widget.__class__.__name__,
            "object_name": widget.objectName(),
            "text": text,
            "placeholder": placeholder,
            "x": p.x(),
            "y": p.y(),
            "width": g.width(),
            "height": g.height(),
            "min_width": widget.minimumWidth(),
            "min_height": widget.minimumHeight(),
            "max_width": widget.maximumWidth(),
            "max_height": widget.maximumHeight(),
            "font_family": font.family(),
            "font_size": round(font.pointSizeF(), 2),
            "font_weight": int(font.weight()),
            "enabled": widget.isEnabled(),
            "visible": widget.isVisible(),
        }

    def select_widget(self, widget):
        cid = str(widget.property("mbq_component_id") or "")
        if not cid:
            return
        payload = self.snapshot(widget)
        payload.update({
            "component_id": cid,
            "label": str(widget.property("mbq_component_label") or cid),
            "group": str(widget.property("mbq_component_group") or ""),
            "override": self.overrides.get(cid, {}),
            "timestamp": time.time(),
        })
        _write_json(SELECTED_PATH, payload)

    def publish_live_scene(self):
        if not self.window.isVisible():
            return

        # Screenshot of the actual running MBQ window.
        try:
            pix = self.window.grab()
            tmp = PREVIEW_PATH.with_suffix(".tmp.png")
            if pix.save(str(tmp), "PNG"):
                tmp.replace(PREVIEW_PATH)
        except Exception:
            pass

        # Rectangle map used for click-selection directly on Studio preview.
        scene = {
            "window_width": self.window.width(),
            "window_height": self.window.height(),
            "components": {},
            "timestamp": time.time(),
        }

        for cid, widget in self.widgets.items():
            if not widget.isVisible():
                continue
            snap = self.snapshot(widget)
            scene["components"][cid] = {
                "label": str(widget.property("mbq_component_label") or cid),
                "group": str(widget.property("mbq_component_group") or ""),
                "x": snap["x"],
                "y": snap["y"],
                "width": snap["width"],
                "height": snap["height"],
                "class_name": snap["class_name"],
                "object_name": snap["object_name"],
                "text": snap["text"],
                "placeholder": snap["placeholder"],
                "font_family": snap["font_family"],
                "font_size": snap["font_size"],
                "font_weight": snap["font_weight"],
                "min_width": snap["min_width"],
                "min_height": snap["min_height"],
            }

        _write_json(SCENE_PATH, scene)

    def reload_overrides_if_changed(self, force=False):
        try:
            mtime = COMPONENTS_PATH.stat().st_mtime_ns
        except OSError:
            mtime = 0

        if not force and mtime == self.last_component_mtime:
            return

        self.last_component_mtime = mtime
        data = _read_json(COMPONENTS_PATH, {})
        self.overrides = data if isinstance(data, dict) else {}

        for cid, widget in self.widgets.items():
            self.apply_component(widget, self.overrides.get(cid, {}))

        self.publish_live_scene()

    def apply_component(self, widget, props):
        if not isinstance(props, dict):
            return

        # Content
        if "text" in props:
            value = str(props["text"])
            if isinstance(widget, (QAbstractButton, QLabel)):
                widget.setText(value)

        if "placeholder" in props:
            value = str(props["placeholder"])
            if isinstance(widget, (QLineEdit, QPlainTextEdit)):
                widget.setPlaceholderText(value)

        # Geometry — only when explicitly overridden.
        if "width" in props and int(props["width"]) > 0:
            widget.setFixedWidth(int(props["width"]))
        if "height" in props and int(props["height"]) > 0:
            widget.setFixedHeight(int(props["height"]))
        if "min_width" in props:
            widget.setMinimumWidth(max(0, int(props["min_width"])))
        if "min_height" in props:
            widget.setMinimumHeight(max(0, int(props["min_height"])))

        # Typography
        font = widget.font()
        changed_font = False
        if props.get("font_family"):
            font.setFamily(str(props["font_family"]))
            changed_font = True
        if props.get("font_size"):
            font.setPointSizeF(float(props["font_size"]))
            changed_font = True
        if props.get("font_weight"):
            try:
                font.setWeight(QFont.Weight(int(props["font_weight"])))
                changed_font = True
            except Exception:
                pass
        if changed_font:
            widget.setFont(font)

        # Local style override.
        selector = self._selector(widget)
        base, hover, pressed, disabled = [], [], [], []

        def add(prop, key, target=base, suffix=""):
            value = props.get(key)
            if value not in (None, ""):
                target.append(f"{prop}: {value}{suffix};")

        add("background", "background")
        add("color", "text_color")
        add("border-color", "border_color")
        add("border-width", "border_width", suffix="px")
        if props.get("border_width") not in (None, ""):
            base.append("border-style: solid;")
        add("border-radius", "border_radius", suffix="px")
        add("padding-left", "padding_x", suffix="px")
        add("padding-right", "padding_x", suffix="px")
        add("padding-top", "padding_y", suffix="px")
        add("padding-bottom", "padding_y", suffix="px")
        add("margin-left", "offset_x", suffix="px")
        add("margin-top", "offset_y", suffix="px")

        add("background", "hover_background", hover)
        add("color", "hover_text_color", hover)
        add("border-color", "hover_border_color", hover)

        add("background", "pressed_background", pressed)
        add("color", "pressed_text_color", pressed)

        add("background", "disabled_background", disabled)
        add("color", "disabled_text_color", disabled)

        blocks = []
        if base:
            blocks.append(f"{selector} {{ {' '.join(base)} }}")
        if hover:
            blocks.append(f"{selector}:hover {{ {' '.join(hover)} }}")
        if pressed:
            blocks.append(f"{selector}:pressed {{ {' '.join(pressed)} }}")
        if disabled:
            blocks.append(f"{selector}:disabled {{ {' '.join(disabled)} }}")

        widget.setStyleSheet("\n".join(blocks))

    def _selector(self, widget):
        if isinstance(widget, QAbstractButton):
            return "QPushButton"
        if isinstance(widget, QPlainTextEdit):
            return "QPlainTextEdit"
        if isinstance(widget, QLineEdit):
            return "QLineEdit"
        if isinstance(widget, QComboBox):
            return "QComboBox"
        if isinstance(widget, QTableWidget):
            return "QTableWidget"
        if isinstance(widget, QProgressBar):
            return "QProgressBar"
        if isinstance(widget, QLabel):
            return "QLabel"
        return "QWidget"


def install(window):
    if not inspector_enabled():
        return None
    return UIStudioRuntime(window)
