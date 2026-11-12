"""Central UI metrics for MBQ Media Downloader.

Production builds always use DEFAULT_UI.
When running from source with MBQ_UI_DEV=1, devtools/ui_config.json is
overlaid on top. Frozen/release builds ignore developer overrides.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


DEFAULT_UI = {
    # Main window
    "window_width": 1460,
    "window_height": 920,
    "window_min_width": 1020,
    "window_min_height": 700,

    # Sidebar
    "sidebar_width": 214,
    "sidebar_logo_size": 44,
    "sidebar_logo_x": 6,
    "sidebar_logo_y": 20,
    "sidebar_margin_left": 10,
    "sidebar_margin_top": 5,
    "sidebar_margin_right": 10,
    "sidebar_margin_bottom": 14,
    "sidebar_spacing": 8,
    "nav_icon_size": 22,

    # Header
    "header_height": 78,

    # Main pages
    "page_margin_left": 22,
    "page_margin_top": 4,
    "page_margin_right": 22,
    "page_margin_bottom": 16,
    "page_spacing": 12,

    # Home
    "home_spacing": 12,
    "home_scroll_right_margin": 8,
    "hero_min_height": 300,
    "hero_core_min_width": 430,
    "hero_gap": 18,
    "hero_margin_x": 22,
    "hero_margin_y": 18,
    "live_strip_min_height": 66,
    "media_thumbnail_width": 250,
    "media_thumbnail_height": 142,

    # Analyzer
    "analyzer_margin_x": 20,
    "analyzer_margin_top": 14,
    "analyzer_margin_bottom": 14,
    "analyzer_spacing": 10,
    "url_input_height": 48,
    "analyze_button_height": 48,
    "analyze_button_min_width": 164,

    # Media profile
    "media_margin_x": 20,
    "media_margin_top": 14,
    "media_margin_bottom": 16,
    "media_spacing": 12,

    # Extractor
    "extractor_margin_x": 18,
    "extractor_margin_y": 14,
    "extractor_spacing": 10,
    "channel_avatar_size": 92,

    # Footer / queue
    "download_footer_min_height": 86,
    "queue_scroll_min_height": 360,
    "queue_card_min_height": 90,
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _dev_enabled() -> bool:
    if _is_frozen():
        return False
    return os.environ.get("MBQ_UI_DEV", "").strip().lower() in {"1", "true", "yes", "on"}


def _load_overlay() -> dict:
    if not _dev_enabled():
        return {}
    path = _project_root() / "devtools" / "ui_config.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        key: value
        for key, value in data.items()
        if key in DEFAULT_UI and isinstance(value, (int, float))
    }


UI = dict(DEFAULT_UI)
UI.update(_load_overlay())
