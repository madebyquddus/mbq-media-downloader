import copy
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from PySide6.QtCore import Qt, QTimer, QUrl, QSettings, QSize, QRect, QEvent
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap, QPainter, QPainterPath
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QLabel, QPushButton, QLineEdit, QPlainTextEdit, QListWidget, QStackedWidget,
    QComboBox, QCheckBox, QSpinBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QMessageBox, QDialog, QScrollArea, QGridLayout, QButtonGroup)
from app.core.storage import Store
from app.core.options import QUALITIES, available_qualities, custom_args, urls, validate_template
from app.core.engine import check_engine, update_engine, find_tool
from app.workers.tasks import FunctionWorker, ProcessWorker
from app.ui import icons
from app.ui.neon_theme import STYLE, stylesheet, palette
from app.ui.neon import (NeonCanvas, FormatCard, PageStack, BrandMark, HeaderBar, NavHighlight,
                         EdgeGrip, SIDEBAR_W)
from app.ui.ui_config import UI
from app.ui.mbq_core import MBQCore

def duration(value):
    if value is None:
        return '—'
    seconds = int(value)
    return f'{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}' if seconds >= 3600 else f'{seconds // 60}:{seconds % 60:02d}'

def size(value):
    if not isinstance(value, (float, int)):
        return '—'
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if value < 1024:
            return f'{value:.1f} {unit}'
        value /= 1024
    return f'{value:.1f} PiB'

def button(text, fn, primary=False):
    item = QPushButton(text)
    if primary:
        item.setObjectName('primary')
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    item.clicked.connect(fn)
    return item

def table(headers):
    item = QTableWidget(0, len(headers))
    item.setHorizontalHeaderLabels(headers)
    item.setAlternatingRowColors(True)
    item.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    item.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    item.verticalHeader().hide()
    item.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    item.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    return item

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = Store()
        self.ui_settings = QSettings('MadeByQuddus', 'MBQDownloader')  # legacy settings key kept for upgrade compatibility
        self.log_path = self.store.root / 'mbq.log'
        handler = RotatingFileHandler(self.log_path, maxBytes=4_000_000, backupCount=3, encoding='utf-8')
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[handler], force=True)
        self.setWindowTitle('MBQ MEDIA DOWNLOADER')
        self.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.NoDropShadowWindowHint
        | Qt.WindowType.WindowSystemMenuHint
        | Qt.WindowType.WindowMinimizeButtonHint
        | Qt.WindowType.WindowMaximizeButtonHint
        )  # fully client-drawn frame
        self.resize(UI["window_width"], UI["window_height"])
        self.setMinimumSize(UI["window_min_width"], UI["window_min_height"])
        self.setStyleSheet(STYLE)
        self.page_meta = []
        self.workers = set()
        self.active = {}
        self.jobs = []
        self.media = []
        self.current_info = None
        self.analysis_pending = []
        self.analysis_worker = None
        self.analysis_progress_value = 0
        self.analysis_progress_timer = QTimer(self)
        self.analysis_progress_timer.setInterval(70)
        self.analysis_progress_timer.timeout.connect(self.advance_analysis_progress)

        # Visual-only channel/profile extraction progress.
        # This never controls extraction; it only reflects that scanning is active.
        self.channel_progress_value = 0
        self.channel_progress_timer = QTimer(self)
        self.channel_progress_timer.setInterval(80)
        self.channel_progress_timer.timeout.connect(self.advance_channel_progress)

        self.channel_workers = set()
        self.channel_profile_worker = None
        self.channel_items = {'videos': [], 'shorts': []}
        self.channel_title = ''
        self.channel_base_url = ''
        self.channel_platform = 'youtube'
        self.last_error = ''
        self.thumbs = {}
        self.thumb_pending = []
        self.thumb_loading = set()
        self.running = False
        self.stop_after_current = False
        self.paused_job_status = {}
        self.force_stopped_job_ids = set()
        self.engine_updating = False
        self.closing = False
        central = NeonCanvas()
        self.canvas = central
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = sidebar = QWidget()
        sidebar.setFixedWidth(SIDEBAR_W)
        sidebar.setObjectName("sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(UI["sidebar_margin_left"], UI["sidebar_margin_top"], UI["sidebar_margin_right"], UI["sidebar_margin_bottom"])
        side.setSpacing(UI["sidebar_spacing"])
        self.sidebar_brand = BrandMark(compact=True)
        side.addWidget(self.sidebar_brand)
        side.addSpacing(10)
        self.nav_highlight = NavHighlight(sidebar)   # glides behind the active item
        self.nav = QListWidget()
        self.nav.setObjectName('nav')
        self.nav.setIconSize(QSize(UI["nav_icon_size"], UI["nav_icon_size"]))
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_names = ['home', 'downloads', 'history', 'advanced', 'engine', 'settings']
        for label in ('Home', 'Downloads', 'History', 'Advanced', 'Engine', 'Settings'):
            self.nav.addItem(label)
        side.addWidget(self.nav, 1)
        self.nav_highlight.stackUnder(self.nav)
        about_button = QPushButton('MadeByQuddus\nVersion 1.2')
        about_button.setObjectName('sidebarAbout')
        about_button.setToolTip('About MBQ MEDIA DOWNLOADER')
        about_button.setCursor(Qt.CursorShape.PointingHandCursor)
        about_button.clicked.connect(self.about)
        side.addWidget(about_button)
        layout.addWidget(sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.header = HeaderBar()
        self.header.minimize_clicked.connect(self.showMinimized)
        self.header.maximize_clicked.connect(self.toggle_maximized)
        self.header.close_clicked.connect(self.close)
        self.theme_toggle = self.header.theme_toggle
        self.theme_toggle.clicked.connect(self.toggle_theme)
        right_layout.addWidget(self.header)
        self.pages = PageStack()
        right_layout.addWidget(self.pages, 1)
        layout.addWidget(right, 1)

        E = Qt.Edge
        self.grips = [EdgeGrip(edges, self) for edges in (
            E.LeftEdge, E.RightEdge, E.TopEdge, E.BottomEdge,
            E.LeftEdge | E.TopEdge, E.RightEdge | E.TopEdge,
            E.LeftEdge | E.BottomEdge, E.RightEdge | E.BottomEdge)]
        self.build_home()
        self.build_downloads()
        self.build_history()
        self.build_advanced()
        self.build_engine()
        self.build_settings()
        self.nav.currentRowChanged.connect(self.on_nav_changed)
        self.nav.currentRowChanged.connect(lambda row: self.refresh_history() if row == 2 else None)
        self.nav.setCurrentRow(0)
        self.apply_theme()
        self.apply_motion()
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().showMessage('Ready • Paste a URL to begin')
        self.restore_queue()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.schedule)
        self.timer.start(400)
        QTimer.singleShot(100, self.check_engine_ui)

    def page(self, title, description):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(UI["page_margin_left"], UI["page_margin_top"], UI["page_margin_right"], UI["page_margin_bottom"])
        layout.setSpacing(UI["page_spacing"])
        self.page_meta.append((title, description))   # shown by the shared HeaderBar
        self.pages.addWidget(widget)
        return layout

    def build_home(self):
        outer = self.page(
            'MBQ / MEDIA CONSOLE',
            'Source acquisition, format control and local transfer in one cinematic workspace.'
        )

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, UI["home_scroll_right_margin"], 0)
        layout.setSpacing(UI["home_spacing"])
        area.setWidget(content)
        outer.addWidget(area, 1)

        # ------------------------------------------------------------------
        # HERO / IDLE ATTRACTION STATE
        # ------------------------------------------------------------------
        hero = QWidget()
        hero.setObjectName('heroDeck')
        hero.setMinimumHeight(UI.get('hero_min_height', 300))
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(
            UI.get('hero_margin_x', 22), UI.get('hero_margin_y', 18),
            UI.get('hero_margin_x', 22), UI.get('hero_margin_y', 18)
        )
        hero_layout.setSpacing(UI.get('hero_gap', 18))

        copy_pane = QWidget()
        copy_pane.setObjectName('heroCopyPane')
        copy_layout = QVBoxLayout(copy_pane)
        copy_layout.setContentsMargins(0, 0, 0, 0)
        copy_layout.setSpacing(8)

        identity_row = QHBoxLayout()
        hero_kicker = QLabel('MBQ / CINEMATIC MEDIA CONSOLE')
        hero_kicker.setObjectName('heroKicker')
        identity_row.addWidget(hero_kicker)
        identity_row.addStretch()
        hero_index = QLabel('LOCAL  //  01')
        hero_index.setObjectName('heroIndex')
        identity_row.addWidget(hero_index)
        copy_layout.addLayout(identity_row)

        hero_title = QLabel('DOWNLOAD\nWITHOUT THE NOISE.')
        hero_title.setObjectName('heroTitle')
        hero_title.setWordWrap(True)
        copy_layout.addWidget(hero_title)

        hero_body = QLabel(
            'Resolve a link, playlist or creator feed into a clean local media queue. '
            'The interface reacts to the source, the transfer and the final file — without hiding the controls.'
        )
        hero_body.setObjectName('heroBody')
        hero_body.setWordWrap(True)
        hero_body.setMaximumWidth(650)
        copy_layout.addWidget(hero_body)

        state_row = QHBoxLayout()
        state_row.setSpacing(12)
        self.hero_state_label = QLabel('READY / WAITING FOR SOURCE')
        self.hero_state_label.setObjectName('heroState')
        state_row.addWidget(self.hero_state_label)
        state_row.addStretch()
        self.hero_source_label = QLabel('SOURCE / UNRESOLVED')
        self.hero_source_label.setObjectName('heroIndex')
        state_row.addWidget(self.hero_source_label)
        copy_layout.addLayout(state_row)

        source_command = QWidget()
        source_command.setObjectName('sourceCommand')
        command_layout = QVBoxLayout(source_command)
        command_layout.setContentsMargins(12, 8, 8, 8)
        command_layout.setSpacing(5)
        source_label = QLabel('PASTE A LINK, PLAYLIST OR CREATOR')
        source_label.setObjectName('heroIndex')
        command_layout.addWidget(source_label)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_input = QPlainTextEdit()
        self.url_input.setObjectName('urlInput')
        self.url_input.setPlaceholderText('https://…')
        self.url_input.setFixedHeight(UI["url_input_height"])
        url_row.addWidget(self.url_input, 1)
        self.analyze_button = button('LOCK SOURCE  →', self.analyze, True)
        self.analyze_button.setObjectName('analyzePrimary')
        self.analyze_button.setMinimumWidth(UI["analyze_button_min_width"])
        self.analyze_button.setFixedHeight(UI["analyze_button_height"])
        url_row.addWidget(self.analyze_button)
        command_layout.addLayout(url_row)
        copy_layout.addWidget(source_command)

        action_row = QHBoxLayout()
        action_row.setSpacing(7)
        paste_btn = button('▣  Paste clipboard', lambda: self.url_input.setPlainText(QApplication.clipboard().text()))
        paste_btn.setObjectName('chip')
        clear_btn = button('×  Clear', lambda: self.url_input.clear())
        clear_btn.setObjectName('ghost')
        cancel_btn = button('Cancel scan', self.cancel_analysis)
        cancel_btn.setObjectName('ghost')
        action_row.addWidget(paste_btn)
        action_row.addWidget(clear_btn)
        action_row.addWidget(cancel_btn)
        action_row.addStretch()
        copy_layout.addLayout(action_row)

        self.analysis_progress_wrap = QWidget()
        self.analysis_progress_wrap.setObjectName('analysisProgressWrap')
        extraction_layout = QVBoxLayout(self.analysis_progress_wrap)
        extraction_layout.setContentsMargins(0, 3, 0, 0)
        extraction_layout.setSpacing(5)
        self.analysis_progress_label = QLabel('RESOLVING SOURCE  •  0%')
        self.analysis_progress_label.setObjectName('heroState')
        extraction_layout.addWidget(self.analysis_progress_label)
        self.analysis_progress = QProgressBar()
        self.analysis_progress.setObjectName('analysisProgress')
        self.analysis_progress.setRange(0, 100)
        self.analysis_progress.setValue(0)
        self.analysis_progress.setTextVisible(True)
        self.analysis_progress.setFormat('%p%')
        self.analysis_progress.setFixedHeight(14)
        extraction_layout.addWidget(self.analysis_progress)
        self.analysis_progress_wrap.hide()
        copy_layout.addWidget(self.analysis_progress_wrap)
        copy_layout.addStretch()

        hero_layout.addWidget(copy_pane, 6)
        self.mbq_core = MBQCore()
        self.mbq_core.setMinimumWidth(UI.get('hero_core_min_width', 430))
        self.mbq_core.set_media('MBQ MEDIA CONSOLE', 'WAITING FOR SOURCE', 'LOCAL')
        hero_layout.addWidget(self.mbq_core, 5)
        layout.addWidget(hero)

        # Live instrumentation — data, not dashboard decoration.
        live_strip = QWidget()
        live_strip.setObjectName('liveStrip')
        live_strip.setMinimumHeight(UI.get('live_strip_min_height', 66))
        live_row = QHBoxLayout(live_strip)
        live_row.setContentsMargins(4, 0, 4, 0)
        live_row.setSpacing(0)
        self.home_stat_values = {}

        def live_cell(key, caption, value, signal=False):
            cell = QWidget()
            cell.setObjectName('liveCell')
            box = QVBoxLayout(cell)
            box.setContentsMargins(15, 8, 15, 8)
            box.setSpacing(1)
            label = QLabel(caption)
            label.setObjectName('liveCaption')
            data = QLabel(value)
            data.setObjectName('liveValueSignal' if signal else 'liveValue')
            box.addWidget(label)
            box.addWidget(data)
            self.home_stat_values[key] = data
            live_row.addWidget(cell, 1)

        live_cell('source', 'SOURCE', 'UNRESOLVED', True)
        live_cell('queue', 'QUEUE', '0')
        live_cell('active', 'ACTIVE', '0')
        live_cell('completed', 'COMPLETED', '0')
        live_cell('mode', 'OUTPUT MODE', 'VIDEO / AUTO')
        layout.addWidget(live_strip)

        # ------------------------------------------------------------------
        # MEDIA LOCK / FORMAT WORKSTATION
        # ------------------------------------------------------------------
        media_card = QWidget()
        media_card.setObjectName('mediaProfileCard')
        media_layout = QVBoxLayout(media_card)
        media_layout.setContentsMargins(
            UI["media_margin_x"], UI["media_margin_top"],
            UI["media_margin_x"], UI["media_margin_bottom"]
        )
        media_layout.setSpacing(UI["media_spacing"])

        media_header = QHBoxLayout()
        media_kicker = QLabel('SOURCE LOCK / MEDIA PROFILE')
        media_kicker.setObjectName('mediaDeckKicker')
        media_header.addWidget(media_kicker)
        media_header.addStretch()
        media_state = QLabel('SELECT OUTPUT / QUALITY')
        media_state.setObjectName('heroIndex')
        media_header.addWidget(media_state)
        media_layout.addLayout(media_header)

        media_body = QHBoxLayout()
        media_body.setSpacing(18)

        self.thumbnail = QLabel('NO SIGNAL')
        self.thumbnail.setObjectName('mediaThumbnail')
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setFixedSize(
            UI.get('media_thumbnail_width', 250),
            UI.get('media_thumbnail_height', 142)
        )
        media_body.addWidget(self.thumbnail, 0, Qt.AlignmentFlag.AlignTop)

        info_col = QVBoxLayout()
        info_col.setSpacing(5)
        self.media_title_label = QLabel('No source locked')
        self.media_title_label.setObjectName('mediaTitle')
        self.media_title_label.setTextFormat(Qt.TextFormat.PlainText)
        self.media_title_label.setWordWrap(True)
        self.media_title_label.setMinimumWidth(250)
        info_col.addWidget(self.media_title_label)
        self.media_creator_label = QLabel('Paste a source above to resolve its media profile.')
        self.media_creator_label.setObjectName('mediaCreator')
        self.media_creator_label.setTextFormat(Qt.TextFormat.PlainText)
        info_col.addWidget(self.media_creator_label)
        self.media_meta_label = QLabel('DURATION / —    SOURCE / —')
        self.media_meta_label.setObjectName('mediaMeta')
        self.media_meta_label.setTextFormat(Qt.TextFormat.PlainText)
        info_col.addWidget(self.media_meta_label)
        info_col.addStretch()
        media_body.addLayout(info_col, 2)

        format_panel = QVBoxLayout()
        format_panel.setSpacing(10)
        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)
        selector_row.addStretch()

        self.mode = QComboBox()
        self.mode.addItems(['Video', 'Audio'])
        self.mode.hide()
        self.mode_group = QButtonGroup(self)
        self.mode_buttons = {}
        for name in ('Video', 'Audio'):
            tab = button(('▷  ' if name == 'Video' else '♫  ') + name.upper(),
                         lambda checked=False, value=name: self.mode.setCurrentText(value))
            tab.setObjectName('segment')
            tab.setCheckable(True)
            tab.setChecked(name == 'Video')
            self.mode_group.addButton(tab)
            self.mode_buttons[name] = tab
            selector_row.addWidget(tab)

        self.output = QComboBox()
        self.output.addItems(['MP4', 'MKV', 'WebM'])
        self.output.setCurrentText(self.store.settings['container'])
        self.output.hide()
        self.container_tabs = QWidget()
        self.container_tabs.setObjectName('segmentGroup')
        tabs = QHBoxLayout(self.container_tabs)
        tabs.setContentsMargins(4, 3, 4, 3)
        tabs.setSpacing(4)
        self.container_group = QButtonGroup(self)
        self.container_buttons = {}
        for name in ('MP4', 'MKV', 'WebM'):
            tab = button(name.upper(), lambda checked=False, value=name: self.output.setCurrentText(value))
            tab.setObjectName('segment')
            tab.setCheckable(True)
            tab.setChecked(name == self.output.currentText())
            self.container_group.addButton(tab)
            self.container_buttons[name] = tab
            tabs.addWidget(tab)
        selector_row.addSpacing(8)
        selector_row.addWidget(self.container_tabs)
        format_panel.addLayout(selector_row)

        self.quality = QComboBox()
        self.quality.addItem('Best Available')
        self.quality.hide()
        self.mode.currentTextChanged.connect(self.change_mode)
        self.output.currentTextChanged.connect(self.refresh_format_cards)
        self.quality.currentTextChanged.connect(self.sync_card_selection)

        self.cards_grid = QGridLayout()
        self.cards_grid.setHorizontalSpacing(7)
        self.cards_grid.setVerticalSpacing(7)
        self.format_cards = []
        self.card_group = QButtonGroup(self)
        self.card_group.setExclusive(True)
        format_panel.addLayout(self.cards_grid)

        self.format_help = QLabel('Lock a source to reveal its available resolution envelope.')
        self.format_help.setObjectName('formatHint')
        self.format_help.setWordWrap(True)
        format_panel.addWidget(self.format_help)
        media_body.addLayout(format_panel, 3)
        media_layout.addLayout(media_body)
        layout.addWidget(media_card)

        # Media stack — playlist and multi-URL detail without becoming the hero.
        playlist_panel = QWidget()
        playlist_panel.setObjectName('playlistPanel')
        playlist_layout = QVBoxLayout(playlist_panel)
        playlist_layout.setContentsMargins(12, 9, 12, 10)
        playlist_layout.setSpacing(7)
        stack_header = QHBoxLayout()
        stack_kicker = QLabel('MEDIA STACK / RESOLVED ITEMS')
        stack_kicker.setObjectName('stackKicker')
        stack_header.addWidget(stack_kicker)
        stack_header.addStretch()
        self.playlist_label = QLabel('Single media / multiple URLs')
        self.playlist_label.setTextFormat(Qt.TextFormat.PlainText)
        self.playlist_label.setObjectName('muted')
        stack_header.addWidget(self.playlist_label)
        playlist_layout.addLayout(stack_header)

        self.media_table = table(['Media / playlist entry', 'Duration', 'Source', 'Status'])
        self.media_table.setMinimumHeight(82)
        self.media_table.setMaximumHeight(132)
        self.media_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.media_table.setWordWrap(False)
        header = self.media_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.media_table.setColumnWidth(1, 84)
        self.media_table.setColumnWidth(2, 112)
        self.media_table.setColumnWidth(3, 166)
        self.media_table.itemSelectionChanged.connect(self.select_media)
        playlist_layout.addWidget(self.media_table)

        row = QHBoxLayout()
        row.setSpacing(7)
        for text_value, fn in [
            ('Select all', lambda: self.check_media(True)),
            ('Deselect all', lambda: self.check_media(False)),
            ('Inspect formats', self.analyze_selected),
            ('Download options', lambda: self.nav.setCurrentRow(5)),
        ]:
            control = button(text_value, fn)
            control.setObjectName('ghost')
            row.addWidget(control)
        row.addStretch()
        playlist_layout.addLayout(row)
        layout.addWidget(playlist_panel)

        # ------------------------------------------------------------------
        # CREATOR SIGNAL / CHANNEL + PROFILE EXTRACTION
        # ------------------------------------------------------------------
        self.channel_section = QWidget()
        self.channel_section.setObjectName('extractorCard')
        channel_layout = QVBoxLayout(self.channel_section)
        channel_layout.setContentsMargins(
            UI["extractor_margin_x"], UI["extractor_margin_y"],
            UI["extractor_margin_x"], UI["extractor_margin_y"]
        )
        channel_layout.setSpacing(UI["extractor_spacing"])

        channel_head = QHBoxLayout()
        self.channel_eyebrow = QLabel('CREATOR SIGNAL / YOUTUBE')
        self.channel_eyebrow.setObjectName('channelDeckKicker')
        channel_head.addWidget(self.channel_eyebrow)
        channel_head.addStretch()
        channel_index = QLabel('LIVE ENUMERATION')
        channel_index.setObjectName('heroIndex')
        channel_head.addWidget(channel_index)
        channel_layout.addLayout(channel_head)

        profile_card = QWidget()
        profile_card.setObjectName('extractorProfile')
        profile_row = QHBoxLayout(profile_card)
        profile_row.setContentsMargins(14, 12, 14, 12)
        profile_row.setSpacing(14)

        self.channel_avatar = QLabel('YT')
        self.channel_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.channel_avatar.setFixedSize(UI["channel_avatar_size"], UI["channel_avatar_size"])
        self.channel_avatar.setObjectName('channelAvatar')
        profile_row.addWidget(self.channel_avatar)

        profile_text = QVBoxLayout()
        profile_text.setSpacing(2)
        self.channel_name_label = QLabel('YouTube Channel')
        self.channel_name_label.setTextFormat(Qt.TextFormat.PlainText)
        self.channel_name_label.setObjectName('channelName')
        self.channel_name_label.setWordWrap(True)
        profile_text.addWidget(self.channel_name_label)
        self.channel_meta_label = QLabel('Creator profile will appear here')
        self.channel_meta_label.setObjectName('channelMeta')
        self.channel_meta_label.setTextFormat(Qt.TextFormat.PlainText)
        profile_text.addWidget(self.channel_meta_label)
        self.channel_label = QLabel('Waiting for a creator signal')
        self.channel_label.setObjectName('channelScanText')
        self.channel_label.setWordWrap(True)
        profile_text.addWidget(self.channel_label)
        profile_row.addLayout(profile_text, 2)

        def stat_card(title, initial='0'):
            card = QWidget()
            card.setObjectName('statCard')
            box = QVBoxLayout(card)
            box.setContentsMargins(14, 9, 14, 9)
            box.setSpacing(1)
            label = QLabel(title)
            label.setObjectName('statLabel')
            value = QLabel(initial)
            value.setObjectName('statValue')
            box.addWidget(label)
            box.addWidget(value)
            return card, value

        videos_stat, self.channel_videos_stat_value = stat_card('VIDEOS')
        shorts_stat, self.channel_shorts_stat_value = stat_card('SHORTS')
        selected_stat, self.channel_selected_stat_value = stat_card('SELECTED')
        self.channel_shorts_stat_card = shorts_stat
        profile_row.addWidget(videos_stat)
        profile_row.addWidget(shorts_stat)
        profile_row.addWidget(selected_stat)

        self.channel_open_button = button('OPEN CREATOR  ↗', self.open_channel)
        self.channel_open_button.setObjectName('outlineAction')
        self.channel_open_button.setEnabled(False)
        profile_row.addWidget(self.channel_open_button, 0, Qt.AlignmentFlag.AlignVCenter)
        channel_layout.addWidget(profile_card)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.channel_progress = QProgressBar()
        self.channel_progress.setObjectName('channelProgress')
        self.channel_progress.setRange(0, 100)
        self.channel_progress.setValue(0)
        self.channel_progress.setTextVisible(True)
        self.channel_progress.setFormat('%p%')
        self.channel_progress.setFixedHeight(14)
        self.channel_progress.setVisible(False)
        progress_row.addWidget(self.channel_progress, 1)
        self.channel_progress_hint = QLabel('')
        self.channel_progress_hint.setObjectName('progressHint')
        progress_row.addWidget(self.channel_progress_hint)
        channel_layout.addLayout(progress_row)

        extractor_tools = QHBoxLayout()
        extractor_tools.setSpacing(7)
        self.channel_search = QLineEdit()
        self.channel_search.setObjectName('channelSearch')
        self.channel_search.setPlaceholderText('Search resolved creator media…')
        self.channel_search.textChanged.connect(self.filter_channel_media)
        extractor_tools.addWidget(self.channel_search, 1)
        self.channel_select_videos_button = button('✓  Select Videos', lambda: self.check_channel_kind('videos', True))
        self.channel_select_videos_button.setObjectName('chip')
        self.channel_clear_videos_button = button('Clear Videos', lambda: self.check_channel_kind('videos', False))
        self.channel_clear_videos_button.setObjectName('ghost')
        self.channel_select_shorts_button = button('✓  Select Shorts', lambda: self.check_channel_kind('shorts', True))
        self.channel_select_shorts_button.setObjectName('chip')
        self.channel_clear_shorts_button = button('Clear Shorts', lambda: self.check_channel_kind('shorts', False))
        self.channel_clear_shorts_button.setObjectName('ghost')
        extractor_tools.addWidget(self.channel_select_videos_button)
        extractor_tools.addWidget(self.channel_select_shorts_button)
        clear_selection = button('Clear Selection', lambda: self.check_channel_media(False))
        clear_selection.setObjectName('ghost')
        extractor_tools.addWidget(clear_selection)
        channel_layout.addLayout(extractor_tools)

        channel_columns = QHBoxLayout()
        channel_columns.setSpacing(10)
        self.channel_videos_column = QWidget()
        self.channel_videos_column.setObjectName('extractorListPanel')
        videos_box = QVBoxLayout(self.channel_videos_column)
        videos_box.setContentsMargins(10, 9, 10, 10)
        videos_box.setSpacing(7)
        self.channel_videos_label = QLabel('VIDEOS  •  0')
        self.channel_videos_label.setObjectName('listSectionTitle')
        videos_box.addWidget(self.channel_videos_label)
        self.channel_videos_table = table(['Video', 'Duration', 'URL'])
        self.channel_videos_table.setObjectName('extractorTable')
        self.channel_videos_table.setMinimumHeight(270)
        self.channel_videos_table.itemChanged.connect(self.update_channel_selection)
        videos_box.addWidget(self.channel_videos_table)
        channel_columns.addWidget(self.channel_videos_column, 1)

        self.channel_shorts_column = QWidget()
        self.channel_shorts_column.setObjectName('extractorListPanel')
        shorts_box = QVBoxLayout(self.channel_shorts_column)
        shorts_box.setContentsMargins(10, 9, 10, 10)
        shorts_box.setSpacing(7)
        self.channel_shorts_label = QLabel('SHORTS  •  0')
        self.channel_shorts_label.setObjectName('listSectionTitle')
        shorts_box.addWidget(self.channel_shorts_label)
        self.channel_shorts_table = table(['Short', 'Duration', 'URL'])
        self.channel_shorts_table.setObjectName('extractorTable')
        self.channel_shorts_table.setMinimumHeight(270)
        self.channel_shorts_table.itemChanged.connect(self.update_channel_selection)
        shorts_box.addWidget(self.channel_shorts_table)
        channel_columns.addWidget(self.channel_shorts_column, 1)
        channel_layout.addLayout(channel_columns)

        self.channel_section.setVisible(False)
        layout.addWidget(self.channel_section)

        # Persistent command rail stays outside the scrolling content.
        self.download_footer = QWidget()
        self.download_footer.setObjectName('downloadFooter')
        self.download_footer.setMinimumHeight(UI["download_footer_min_height"])
        footer = QHBoxLayout(self.download_footer)
        footer.setContentsMargins(18, 10, 12, 10)
        footer.setSpacing(12)
        self.selection_summary = QLabel('READY / CHOOSE A FORMAT')
        self.selection_summary.setWordWrap(True)
        self.selection_summary.setObjectName('footerSummary')
        footer.addWidget(self.selection_summary, 1)
        self.channel_selected_label = QLabel('0 items selected')
        self.channel_selected_label.setObjectName('footerChannelSummary')
        self.channel_selected_label.setWordWrap(True)
        self.channel_selected_label.setVisible(False)
        footer.addWidget(self.channel_selected_label, 1)
        self.footer_divider = QWidget()
        self.footer_divider.setObjectName('footerDivider')
        self.footer_divider.setFixedWidth(1)
        self.footer_divider.setFixedHeight(48)
        self.footer_divider.setVisible(False)
        footer.addWidget(self.footer_divider)

        self.channel_footer_controls = QWidget()
        self.channel_footer_controls.setObjectName('footerControls')
        footer_controls = QHBoxLayout(self.channel_footer_controls)
        footer_controls.setContentsMargins(0, 0, 0, 0)
        footer_controls.setSpacing(8)
        quality_label = QLabel('BULK QUALITY')
        quality_label.setObjectName('footerControlLabel')
        footer_controls.addWidget(quality_label)
        self.channel_quality = QComboBox()
        self.channel_quality.setObjectName('bulkQuality')
        self.channel_quality.addItems([q[0] for q in QUALITIES] + ['Audio Only'])
        default_quality = self.ui_settings.value('channel_bulk_quality', self.store.settings.get('quality', 'Best Available'))
        self.channel_quality.setCurrentText(default_quality if self.channel_quality.findText(default_quality) >= 0 else 'Best Available')
        self.channel_quality.currentTextChanged.connect(self.remember_channel_quality)
        footer_controls.addWidget(self.channel_quality)
        copy_button = button('Copy Links', self.copy_channel_links)
        copy_button.setObjectName('ghost')
        footer_controls.addWidget(copy_button)
        self.channel_footer_controls.setVisible(False)
        footer.addWidget(self.channel_footer_controls)

        self.download_button = button('↓   ACQUIRE SELECTED MEDIA', self.enqueue, True)
        self.download_button.setObjectName('footerPrimary')
        self.download_button.setMinimumWidth(270)
        self.download_button.setMinimumHeight(48)
        self.download_button.setEnabled(False)
        footer.addWidget(self.download_button)
        self.channel_download_button = button('↓   ACQUIRE 0 ITEMS', self.enqueue_channel, True)
        self.channel_download_button.setObjectName('footerPrimary')
        self.channel_download_button.setMinimumWidth(270)
        self.channel_download_button.setMinimumHeight(48)
        self.channel_download_button.setVisible(False)
        footer.addWidget(self.channel_download_button)

        outer.addWidget(self.download_footer)
        layout.addStretch()

    def update_home_signal(self, core_state=None, status=None, source=None, progress=None, title=None, creator=None):
        """UI-only bridge between existing app state and the cinematic Home console."""
        if status and hasattr(self, 'hero_state_label'):
            self.hero_state_label.setText(str(status).upper())
        if source:
            clean_source = str(source).upper()
            if hasattr(self, 'hero_source_label'):
                self.hero_source_label.setText(f'SOURCE / {clean_source}')
            if hasattr(self, 'home_stat_values') and 'source' in self.home_stat_values:
                self.home_stat_values['source'].setText(clean_source)
        if hasattr(self, 'mbq_core'):
            if title or creator or source:
                self.mbq_core.set_media(title or self.mbq_core.title, creator or self.mbq_core.creator, source or self.mbq_core.source)
            if progress is not None:
                self.mbq_core.set_progress(progress)
            if core_state:
                self.mbq_core.set_state(core_state)

    def refresh_format_cards(self, *_):
        if not hasattr(self, 'cards_grid'):
            return
        self.container_tabs.setVisible(self.mode.currentText() == 'Video')
        for name, tab in self.mode_buttons.items():
            tab.setChecked(name == self.mode.currentText())
        for name, tab in self.container_buttons.items():
            tab.setChecked(name == self.output.currentText())
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                self.card_group.removeButton(item.widget())
                item.widget().deleteLater()
        self.format_cards = []
        info = self.current_info or {}
        formats = [f for f in info.get('formats', []) if not f.get('has_drm') and f.get('url')]
        choices = []
        if not formats:
            self.format_help.setText(
    'Real source resolutions detected for this media • Exact codec and size details are in Advanced.'
)
        elif self.mode.currentText() == 'Audio':
            choices = [(name, 'AUDIO', detail, {'MP3':'#c159ff','M4A':'#389aff','Opus':'#00ce9e','WAV':'#ffb32d'}[name]) for name, detail in [
                ('MP3', 'High-quality VBR encoding'), ('M4A', 'AAC / M4A output'),
                ('Opus', 'Efficient Opus encoding'), ('WAV', 'Uncompressed output')]]
            self.format_help.setText('Audio conversion uses the best source audio. Higher output bitrate cannot restore missing source detail.')
        else:
            choices = []
            for quality in available_qualities(info):
                height = dict(QUALITIES)[quality]
                candidates = [f for f in formats if f.get('vcodec') not in (None, 'none') and (height is None or f.get('height', 0) <= height)]
                candidates.sort(key=lambda f: (f.get('height') or 0, f.get('fps') or 0, f.get('tbr') or 0), reverse=True)
                f = candidates[0] if candidates else {}
                resolution = f"{f.get('width', '?')} × {f.get('height', '?')}" if f.get('height') else 'Source resolution'
                fps = f"  •  {f['fps']:g} fps" if f.get('fps') else ''
                accent = {'Best Available':'#00dcff','8K':'#ed4cff','4K':'#b45aff','1440p':'#6474ff',
                          '1080p':'#329aff','720p':'#00d7a0','480p':'#ffb32d','360p':'#ff6d80'}[quality]
                choices.append((quality, self.output.currentText(), resolution + fps, accent))
            self.format_help.setText('Available source resolutions • Cards select a quality ceiling; exact codec and size details are in Advanced.')
        for index, (name, badge, detail, accent) in enumerate(choices):
            title = name if self.mode.currentText() == 'Audio' else ('BEST' if name == 'Best Available' else name.upper())
            card = FormatCard(title, badge, detail, accent)
            card.set_motion(self.store.settings.get('motion', True))
            card.light = self.store.settings.get('theme') == 'Light'
            card.dark_accent = accent
            if card.light:
                from PySide6.QtGui import QColor
                card.accent = QColor(accent).darker(155)
            if card.best:
                self.canvas.frame.connect(card.advance)
            card.choice = name
            self.card_group.addButton(card)
            card.clicked.connect(lambda checked=False, value=name: self.choose_card(value))
            columns = self.format_card_columns()
            self.cards_grid.addWidget(card, index // columns, index % columns)
            self.format_cards.append(card)
        self.sync_card_selection()

    def format_card_columns(self):
        """Keep the quality grid inside the media profile at common desktop widths."""
        width = self.width()
        if width >= 1600:
            return 6
        if width >= 1360:
            return 5
        if width >= 1160:
            return 4
        if width >= 1020:
            return 3
        return 2

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_grips()
        QTimer.singleShot(0, lambda: self.sync_nav_highlight(False))
        if hasattr(self, 'format_cards'):
            columns = self.format_card_columns()
            for index, card in enumerate(self.format_cards):
                self.cards_grid.removeWidget(card)
                self.cards_grid.addWidget(card, index//columns, index%columns)

    def choose_card(self, value):
        self.exact.clear()
        if self.mode.currentText() == 'Audio':
            self.output.setCurrentText(value)
        else:
            self.quality.setCurrentText(value)
        self.sync_card_selection()

    def sync_card_selection(self, *_):
        if not hasattr(self, 'format_cards'):
            return
        selected = self.output.currentText() if self.mode.currentText() == 'Audio' else self.quality.currentText()
        for card in self.format_cards:
            card.setChecked(card.choice == selected)
        if hasattr(self, 'selection_summary'):
            exact = self.exact.text() if hasattr(self, 'exact') else ''
            self.selection_summary.setText(f"{self.mode.currentText()}  •  {self.output.currentText()}  •  {exact or selected}\nSave to: {self.store.settings['folder']}")
        if hasattr(self, 'home_stat_values') and 'mode' in self.home_stat_values:
            self.home_stat_values['mode'].setText(f"{self.mode.currentText().upper()} / {self.output.currentText().upper()}")

    def apply_motion(self):
        enabled = self.store.settings.get('motion', True)
        self.canvas.set_motion(enabled)
        self.pages.set_motion(enabled)
        self.header.set_motion(enabled)
        self.nav_highlight.motion = enabled
        if hasattr(self, 'mbq_core'):
            self.mbq_core.set_motion(enabled)
        for card in self.format_cards:
            card.set_motion(enabled)

    def apply_theme(self):
        theme = self.store.settings.get('theme', 'Dark')
        light = theme == 'Light'
        self.setStyleSheet(stylesheet(theme))
        self.canvas.light = light
        self.canvas.update()
        tokens = palette(theme)
        self.header.set_theme(tokens)
        if hasattr(self, 'mbq_core'):
            self.mbq_core.set_theme(tokens)
        self.nav_highlight.set_theme(light)
        self.refresh_nav_icons(tokens)
        self.sidebar_brand.light = light
        self.sidebar_brand.update()
        if hasattr(self.theme_toggle, 'set_light'):
            self.theme_toggle.set_light(light)
        else:
            self.theme_toggle.setText('Switch to Dark' if light else 'Switch to Light')
        if hasattr(self, 'settings_widgets') and 'theme' in self.settings_widgets:
            combo = self.settings_widgets['theme']
            combo.blockSignals(True)
            combo.setCurrentText(theme)
            combo.blockSignals(False)
        for card in self.format_cards:
            from PySide6.QtGui import QColor
            card.light = light
            card.accent = QColor(card.dark_accent).darker(155) if light else QColor(card.dark_accent)
            card.update()
        self.thumbnail.setStyleSheet('')

    def toggle_theme(self):
        self.set_theme('Light' if self.store.settings.get('theme') != 'Light' else 'Dark')

    def set_theme(self, theme):
        self.store.save_settings({'theme':theme})
        self.apply_theme()

    # ---- frameless shell helpers ------------------------------------------
    def toggle_maximized(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, 'grips'):
            maximized = self.isMaximized()
            self.header.set_maximized(maximized)
            for grip in self.grips:
                grip.setVisible(not maximized)
            self.canvas.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.layout_grips()
        QTimer.singleShot(0, lambda: self.sync_nav_highlight(False))

    def layout_grips(self):
        if not hasattr(self, 'grips'):
            return
        w, h, e, c = self.width(), self.height(), 6, 12
        rects = [QRect(0, c, e, h - 2 * c), QRect(w - e, c, e, h - 2 * c),
                 QRect(c, 0, w - 2 * c, e), QRect(c, h - e, w - 2 * c, e),
                 QRect(0, 0, c, c), QRect(w - c, 0, c, c),
                 QRect(0, h - c, c, c), QRect(w - c, h - c, c, c)]
        for grip, rect in zip(self.grips, rects):
            grip.setGeometry(rect)
            grip.raise_()

    def on_nav_changed(self, row):
        if row < 0:
            return
        self.pages.setCurrentIndex(row)
        title, description = self.page_meta[row]
        self.header.set_page(title, description, home=(row == 0))
        self.sync_nav_highlight(True)

    def sync_nav_highlight(self, animate=True):
        item = self.nav.currentItem()
        if item is None:
            return
        r = self.nav.visualItemRect(item)
        top_left = self.nav.viewport().mapTo(self.sidebar, r.topLeft())
        self.nav_highlight.show()
        self.nav_highlight.move_to(QRect(top_left, r.size()).adjusted(0, 3, 0, -3), animate)

    def refresh_nav_icons(self, tokens):
        active = tokens['text_strong']
        for index, name in enumerate(self.nav_names):
            self.nav.item(index).setIcon(icons.icon(name, UI["nav_icon_size"], tokens['text2'], active=active,
                                                    filled_active=(name == 'home')))

    def about(self):
        QMessageBox.about(
        self,
        'About MBQ Media Downloader',
        'MBQ Media Downloader 1.2\n\n'
        'Modern desktop media downloader with support for quality selection, playlists, '
        'channel extraction, batch processing and download queue management.\n\n'
        'Built with Python and PySide6.\n\n'
        'Developed by @madebyquddus\n'
        'madebyquddus.com\n\n'
        '© 2026 MadeByQuddus'
    )
    def build_downloads(self):
        layout = self.page(
            'Transfer Deck',
            'Live queue control, throughput state and file hand-off.'
        )
        layout.setSpacing(10)

        control_card = QWidget()
        control_card.setObjectName('queueControlCard')
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(18, 14, 16, 14)
        control_layout.setSpacing(20)

        state_col = QVBoxLayout()
        state_col.setSpacing(2)
        kicker = QLabel('MBQ / TRANSFER DECK')
        kicker.setObjectName('queueDeckKicker')
        state_col.addWidget(kicker)
        self.queue_state_word = QLabel('IDLE')
        self.queue_state_word.setObjectName('queueStateWord')
        state_col.addWidget(self.queue_state_word)
        self.queue_summary = QLabel('Queue ready')
        self.queue_summary.setObjectName('queueSummary')
        self.queue_summary.setWordWrap(True)
        state_col.addWidget(self.queue_summary)
        control_layout.addLayout(state_col, 1)

        control_buttons = QVBoxLayout()
        control_buttons.setSpacing(7)
        top = QHBoxLayout()
        top.setSpacing(7)
        self.queue_start_button = button('▶  START / RESUME', self.start_or_resume_queue, True)
        self.queue_pause_button = button('Ⅱ  PAUSE', self.pause_queue)
        self.queue_stop_button = button('■  STOP AFTER CURRENT', self.stop_queue_after_current)
        self.queue_force_stop_button = button('■  FORCE STOP', self.force_stop_queue)
        self.queue_force_stop_button.setObjectName('ghost')
        for widget in (
            self.queue_start_button, self.queue_pause_button,
            self.queue_stop_button, self.queue_force_stop_button,
        ):
            widget.setMinimumHeight(38)
            top.addWidget(widget)
        control_buttons.addLayout(top)
        deck_note = QLabel('ACTIVE TRANSFERS / PROCESS TREE CONTROL / LOCAL FILE OUTPUT')
        deck_note.setObjectName('heroIndex')
        deck_note.setAlignment(Qt.AlignmentFlag.AlignRight)
        control_buttons.addWidget(deck_note)
        control_layout.addLayout(control_buttons, 2)
        layout.addWidget(control_card)

        stats = QHBoxLayout()
        stats.setSpacing(8)
        self.queue_stat_labels = {}
        for key, caption in [
            ('active', 'ACTIVE'), ('waiting', 'WAITING'),
            ('completed', 'COMPLETED'), ('failed', 'FAILED'),
        ]:
            tile = QWidget()
            tile.setObjectName('queueStat')
            box = QVBoxLayout(tile)
            box.setContentsMargins(14, 9, 14, 9)
            box.setSpacing(0)
            value = QLabel('0')
            value.setObjectName('queueStatValue')
            label = QLabel(caption)
            label.setObjectName('queueStatLabel')
            box.addWidget(value)
            box.addWidget(label)
            self.queue_stat_labels[key] = value
            stats.addWidget(tile, 1)
        layout.addLayout(stats)

        selection_bar = QWidget()
        selection_bar.setObjectName('queueToolbar')
        selection_layout = QHBoxLayout(selection_bar)
        selection_layout.setContentsMargins(10, 7, 10, 7)
        selection_layout.setSpacing(7)
        self.queue_select_all = QCheckBox('Select All')
        self.queue_select_all.setObjectName('queueSelectAll')
        self.queue_select_all.toggled.connect(self.select_all_queue_items)
        selection_layout.addWidget(self.queue_select_all)
        self.queue_deselect_button = button('Deselect All', self.deselect_all_queue_items)
        self.queue_deselect_button.setObjectName('ghost')
        selection_layout.addWidget(self.queue_deselect_button)
        self.queue_selection_label = QLabel('0 selected')
        self.queue_selection_label.setObjectName('sectionHint')
        selection_layout.addWidget(self.queue_selection_label)
        selection_layout.addStretch()
        self.queue_delete_selected_button = button('DELETE SELECTED', self.delete_selected_queue_items)
        self.queue_delete_selected_button.setObjectName('ghost')
        selection_layout.addWidget(self.queue_delete_selected_button)
        self.queue_clear_button = button('CLEAR QUEUE', self.clear_queue)
        self.queue_clear_button.setObjectName('ghost')
        selection_layout.addWidget(self.queue_clear_button)
        layout.addWidget(selection_bar)

        filters = QWidget()
        filters.setObjectName('queueToolbar')
        filter_layout = QHBoxLayout(filters)
        filter_layout.setContentsMargins(10, 7, 10, 7)
        filter_layout.setSpacing(6)
        filter_label = QLabel('VIEW /')
        filter_label.setObjectName('heroIndex')
        filter_layout.addWidget(filter_label)
        self.queue_filter_group = QButtonGroup(self)
        self.queue_filter_group.setExclusive(True)
        self.queue_filter_buttons = {}
        for name in ('All', 'Active', 'Waiting', 'Completed', 'Failed'):
            tab = QPushButton(name.upper())
            tab.setObjectName('queueFilter')
            tab.setCheckable(True)
            tab.setChecked(name == 'All')
            tab.clicked.connect(lambda checked=False, value=name: self.set_queue_filter(value))
            self.queue_filter_group.addButton(tab)
            self.queue_filter_buttons[name] = tab
            filter_layout.addWidget(tab)
        filter_layout.addStretch()
        self.queue_open_file_button = button('Open File', self.open_job)
        self.queue_open_file_button.setObjectName('ghost')
        self.queue_open_folder_button = button('Open Folder', lambda: self.open_job(True))
        self.queue_open_folder_button.setObjectName('ghost')
        filter_layout.addWidget(self.queue_open_file_button)
        filter_layout.addWidget(self.queue_open_folder_button)
        layout.addWidget(filters)

        self.queue_filter = 'All'
        self.queue_selected_ids = set()
        self.queue_checks = {}
        self.queue_cards = {}
        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setObjectName('queueScroll')
        self.queue_scroll.setMinimumHeight(UI["queue_scroll_min_height"])
        self.queue_list_widget = QWidget()
        self.queue_list_widget.setObjectName('queueList')
        self.queue_list = QVBoxLayout(self.queue_list_widget)
        self.queue_list.setContentsMargins(0, 0, 0, 0)
        self.queue_list.setSpacing(7)
        self.queue_list.addStretch()
        self.queue_scroll.setWidget(self.queue_list_widget)
        layout.addWidget(self.queue_scroll, 1)

    def set_queue_filter(self, value):
        self.queue_filter = value
        self.render_queue()

    def queue_job_visible(self, job):
        status = job.get('status', 'Waiting')
        if self.queue_filter == 'All':
            return True
        if self.queue_filter == 'Active':
            return job.get('id') in self.active or status in ('Analyzing', 'Downloading', 'Merging', 'Processing')
        return status == self.queue_filter

    def remember_queue_selection(self):
        if not hasattr(self, 'queue_checks'):
            return
        for job_id, check in self.queue_checks.items():
            if check.isChecked():
                self.queue_selected_ids.add(job_id)
            else:
                self.queue_selected_ids.discard(job_id)

    def toggle_queue_job(self, job_id, checked):
        if checked:
            self.queue_selected_ids.add(job_id)
        else:
            self.queue_selected_ids.discard(job_id)

        self.update_queue_selection_ui()

    def update_queue_selection_ui(self):
        if not hasattr(self, 'queue_selection_label'):
            return

        valid_ids = {job.get('id') for job in self.jobs}
        self.queue_selected_ids.intersection_update(valid_ids)

        count = len(self.queue_selected_ids)
        total = len(self.jobs)
        self.queue_selection_label.setText(f'{count} selected')
        self.queue_delete_selected_button.setEnabled(count > 0)
        self.queue_deselect_button.setEnabled(count > 0)
        self.queue_clear_button.setEnabled(total > 0)

        self.queue_select_all.blockSignals(True)
        self.queue_select_all.setChecked(total > 0 and count == total)
        self.queue_select_all.blockSignals(False)

        selected = [job for job in self.jobs if job.get('id') in self.queue_selected_ids]
        has_output = len(selected) == 1 and bool(selected[0].get('file'))
        self.queue_open_file_button.setEnabled(has_output)
        self.queue_open_folder_button.setEnabled(has_output)

    def select_all_queue_items(self, checked=True):
        if checked:
            self.queue_selected_ids = {job.get('id') for job in self.jobs if job.get('id')}
        else:
            self.queue_selected_ids.clear()

        for job_id, checkbox in self.queue_checks.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(job_id in self.queue_selected_ids)
            checkbox.blockSignals(False)

        self.update_queue_selection_ui()

    def deselect_all_queue_items(self):
        self.select_all_queue_items(False)

    def delete_selected_queue_items(self):
        self.remember_queue_selection()
        selected = [job for job in self.jobs if job.get('id') in self.queue_selected_ids]
        if not selected:
            self.statusBar().showMessage('Select one or more queue items first.')
            return

        answer = QMessageBox.question(
            self,
            'Delete selected queue items',
            f'Remove {len(selected)} selected item(s) from the MBQ download queue?\n\n'
            'Downloaded media files on your computer will NOT be deleted.\n'
            'Any selected active download will be cancelled first.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        ids = {job.get('id') for job in selected}
        remaining = []
        cancelling = 0

        for job in self.jobs:
            job_id = job.get('id')
            if job_id not in ids:
                remaining.append(job)
                continue

            worker = self.active.get(job_id)
            if worker is not None:
                job['_remove_after_cancel'] = True
                worker.cancel()
                remaining.append(job)
                cancelling += 1

        self.jobs = remaining
        self.queue_selected_ids.difference_update(ids)
        self.persist_queue()
        self.render_queue()

        if cancelling:
            self.statusBar().showMessage(
                f'Removing selected queue items • cancelling {cancelling} active download(s)…'
            )
        else:
            self.statusBar().showMessage('Selected queue items removed.')

    def clear_queue(self):
        if not self.jobs:
            return

        answer = QMessageBox.question(
            self,
            'Clear download queue',
            f'Clear all {len(self.jobs)} item(s) from the download queue?\n\n'
            'Downloaded media files will NOT be deleted.\n'
            'Any active downloads will be cancelled first.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        active_ids = set(self.active)
        remaining = []

        for job in self.jobs:
            job_id = job.get('id')
            if job_id in active_ids:
                job['_remove_after_cancel'] = True
                worker = self.active.get(job_id)
                if worker is not None:
                    worker.cancel()
                remaining.append(job)

        self.jobs = remaining
        self.queue_selected_ids.clear()
        self.running = False
        self.stop_after_current = False
        self.persist_queue()
        self.render_queue()

        if active_ids:
            self.statusBar().showMessage('Queue cleared • cancelling active download(s)…')
        else:
            self.statusBar().showMessage('Download queue cleared.')

    def build_history(self):
        layout = self.page('History', 'Your completed-download archive, searchable and ready to reopen at any time.')
        layout.setSpacing(12)

        toolbar = QWidget()
        toolbar.setObjectName('sectionCard')
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(14, 12, 14, 12)
        bar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setObjectName('historySearch')
        self.search.setPlaceholderText('Search title, source or URL...')
        self.search.textChanged.connect(self.refresh_history)
        bar.addWidget(self.search, 1)
        self.history_count_label = QLabel('0 downloads')
        self.history_count_label.setObjectName('sectionHint')
        bar.addWidget(self.history_count_label)
        for text, fn in [
            ('Open file', self.open_history),
            ('Open folder', lambda: self.open_history(True)),
            ('Clear history', self.clear_history),
        ]:
            action = button(text, fn)
            action.setObjectName('ghost')
            bar.addWidget(action)
        layout.addWidget(toolbar)

        archive = QWidget()
        archive.setObjectName('sectionCard')
        archive_box = QVBoxLayout(archive)
        archive_box.setContentsMargins(14, 14, 14, 14)
        archive_box.setSpacing(10)
        title_row = QHBoxLayout()
        title = QLabel('DOWNLOAD ARCHIVE')
        title.setObjectName('sectionTitle')
        title_row.addWidget(title)
        title_row.addStretch()
        hint = QLabel('Double-clicking is not required — select a row and use the actions above.')
        hint.setObjectName('sectionHint')
        title_row.addWidget(hint)
        archive_box.addLayout(title_row)
        self.history_table = table(['Title', 'URL', 'Source', 'Date (UTC)', 'Output file', 'Quality', 'Status'])
        self.history_table.setObjectName('premiumTable')
        archive_box.addWidget(self.history_table, 1)
        layout.addWidget(archive, 1)

    def build_advanced(self):
        layout = self.page('Advanced formats', 'Inspect the real source streams and override the simple quality presets only when you need exact control.')
        layout.setSpacing(12)

        header = QWidget()
        header.setObjectName('sectionCard')
        header_box = QVBoxLayout(header)
        header_box.setContentsMargins(14, 12, 14, 12)
        header_box.setSpacing(4)
        label = QLabel('CURRENT MEDIA')
        label.setObjectName('sectionTitle')
        header_box.addWidget(label)
        self.format_label = QLabel('Select media on Home and analyze its formats.')
        self.format_label.setObjectName('advancedMediaLabel')
        self.format_label.setWordWrap(True)
        header_box.addWidget(self.format_label)
        layout.addWidget(header)

        formats_card = QWidget()
        formats_card.setObjectName('sectionCard')
        formats_box = QVBoxLayout(formats_card)
        formats_box.setContentsMargins(14, 14, 14, 14)
        formats_box.setSpacing(10)
        top = QHBoxLayout()
        title = QLabel('AVAILABLE SOURCE STREAMS')
        title.setObjectName('sectionTitle')
        top.addWidget(title)
        top.addStretch()
        note = QLabel('Select one combined stream, or one video-only + one audio-only stream.')
        note.setObjectName('sectionHint')
        top.addWidget(note)
        formats_box.addLayout(top)
        self.formats_table = table(['Resolution', 'ID', 'Container', 'Video codec', 'Audio codec', 'FPS', 'Bitrate (kbps)', 'Size / approximate'])
        self.formats_table.setObjectName('premiumTable')
        self.formats_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        formats_box.addWidget(self.formats_table, 1)
        layout.addWidget(formats_card, 1)

        exact_card = QWidget()
        exact_card.setObjectName('sectionCard')
        exact_box = QVBoxLayout(exact_card)
        exact_box.setContentsMargins(14, 12, 14, 12)
        exact_box.setSpacing(8)
        exact_title = QLabel('EXACT FORMAT SELECTION')
        exact_title.setObjectName('sectionTitle')
        exact_box.addWidget(exact_title)
        exact_row = QHBoxLayout()
        self.exact = QLineEdit()
        self.exact.setReadOnly(True)
        self.exact.setPlaceholderText('Using simple quality preset')
        exact_row.addWidget(self.exact, 1)
        use_ids = button('Use selected IDs', self.use_formats, True)
        use_preset = button('Use preset', lambda: self.exact.clear())
        use_preset.setObjectName('ghost')
        exact_row.addWidget(use_ids)
        exact_row.addWidget(use_preset)
        exact_box.addLayout(exact_row)
        layout.addWidget(exact_card)

        custom_card = QWidget()
        custom_card.setObjectName('sectionCard')
        custom_box = QVBoxLayout(custom_card)
        custom_box.setContentsMargins(14, 12, 14, 12)
        custom_box.setSpacing(8)
        custom_title = QLabel('ADVANCED yt-dlp OPTIONS')
        custom_title.setObjectName('sectionTitle')
        custom_box.addWidget(custom_title)
        custom_hint = QLabel('Optional power-user arguments. Unsafe config, plugin, command and arbitrary output-path options remain blocked.')
        custom_hint.setObjectName('sectionHint')
        custom_hint.setWordWrap(True)
        custom_box.addWidget(custom_hint)
        custom_row = QHBoxLayout()
        self.custom = QLineEdit()
        self.custom.setPlaceholderText('Example: --limit-rate 5M --retries 10')
        custom_row.addWidget(self.custom, 1)
        validate = button('Validate arguments', self.validate_custom)
        validate.setObjectName('ghost')
        custom_row.addWidget(validate)
        custom_box.addLayout(custom_row)
        info = QLabel('Allowed: --limit-rate, --retries, --fragment-retries, --socket-timeout, --concurrent-fragments, --proxy, --user-agent, --referer.')
        info.setWordWrap(True)
        info.setObjectName('sectionHint')
        custom_box.addWidget(info)
        layout.addWidget(custom_card)

    def build_engine(self):
        layout = self.page('Engine', 'Keep the extraction stack healthy without rebuilding the application.')
        layout.setSpacing(12)

        status_card = QWidget()
        status_card.setObjectName('engineCard')
        status_box = QVBoxLayout(status_card)
        status_box.setContentsMargins(16, 14, 16, 14)
        status_box.setSpacing(10)
        top = QHBoxLayout()
        title = QLabel('ENGINE HEALTH')
        title.setObjectName('sectionTitle')
        top.addWidget(title)
        top.addStretch()
        badge = QLabel('yt-dlp + FFmpeg + JS runtime')
        badge.setObjectName('engineBadge')
        top.addWidget(badge)
        status_box.addLayout(top)
        self.engine_status = QPlainTextEdit()
        self.engine_status.setObjectName('engineStatus')
        self.engine_status.setReadOnly(True)
        self.engine_status.setMinimumHeight(220)
        status_box.addWidget(self.engine_status)
        controls = QHBoxLayout()
        self.check_button = button('CHECK ENGINE', self.check_engine_ui)
        self.update_button = button('UPDATE yt-dlp', self.update_engine_ui, True)
        view_log = button('VIEW LOG', self.view_log)
        view_log.setObjectName('ghost')
        controls.addWidget(self.check_button)
        controls.addWidget(self.update_button)
        controls.addWidget(view_log)
        controls.addStretch()
        status_box.addLayout(controls)
        layout.addWidget(status_card, 1)

        tools_card = QWidget()
        tools_card.setObjectName('sectionCard')
        tools_box = QVBoxLayout(tools_card)
        tools_box.setContentsMargins(16, 14, 16, 14)
        tools_box.setSpacing(8)
        tools_title = QLabel('LOCAL MEDIA TOOLCHAIN')
        tools_title.setObjectName('sectionTitle')
        tools_box.addWidget(tools_title)
        explanation = QLabel('FFmpeg and ffprobe handle merging, remuxing and conversion. A supported JavaScript runtime improves YouTube compatibility. Browser sessions remain local when authentication is enabled in Settings.')
        explanation.setWordWrap(True)
        explanation.setObjectName('sectionHint')
        tools_box.addWidget(explanation)
        actions = QHBoxLayout()
        ffmpeg_page = button('FFmpeg download page', lambda: QDesktopServices.openUrl(QUrl('https://ffmpeg.org/download.html')))
        ffmpeg_page.setObjectName('ghost')
        install = button('Install local FFmpeg files', self.install_ffmpeg)
        actions.addWidget(install)
        actions.addWidget(ffmpeg_page)
        actions.addStretch()
        tools_box.addLayout(actions)
        layout.addWidget(tools_card)

    def build_settings(self):
        layout = self.page('Settings', 'Configure defaults once; every new download inherits these preferences.')
        layout.setSpacing(10)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setObjectName('settingsScroll')
        widget = QWidget()
        stack = QVBoxLayout(widget)
        stack.setContentsMargins(0, 0, 8, 0)
        stack.setSpacing(10)
        self.settings_widgets = {}
        s = self.store.settings

        destination = QWidget()
        destination.setObjectName('settingsCard')
        destination_form = QFormLayout(destination)
        destination_form.setContentsMargins(16, 14, 16, 14)
        destination_form.setSpacing(11)
        destination_title = QLabel('DESTINATION & DEFAULT FORMAT')
        destination_title.setObjectName('sectionTitle')
        destination_form.addRow(destination_title)
        folder_row = QHBoxLayout()
        self.folder = QLineEdit(s['folder'])
        folder_row.addWidget(self.folder, 1)
        browse = button('Browse', self.browse_folder)
        browse.setObjectName('ghost')
        folder_row.addWidget(browse)
        destination_form.addRow('Download folder', folder_row)
        for key, label, choices in [
            ('quality', 'Default quality', [q[0] for q in QUALITIES]),
            ('container', 'Preferred container', ['MP4', 'MKV', 'WebM']),
            ('audio', 'Audio format', ['MP3', 'M4A', 'Opus', 'WAV']),
        ]:
            item = QComboBox()
            item.addItems(choices)
            item.setCurrentText(s[key])
            self.settings_widgets[key] = item
            destination_form.addRow(label, item)
        stack.addWidget(destination)

        experience = QWidget()
        experience.setObjectName('settingsCard')
        experience_form = QFormLayout(experience)
        experience_form.setContentsMargins(16, 14, 16, 14)
        experience_form.setSpacing(11)
        experience_title = QLabel('APPLICATION & QUEUE')
        experience_title.setObjectName('sectionTitle')
        experience_form.addRow(experience_title)
        theme = QComboBox()
        theme.addItems(['Dark', 'Light'])
        theme.setCurrentText(s['theme'])
        self.settings_widgets['theme'] = theme
        theme.currentTextChanged.connect(self.set_theme)
        experience_form.addRow('Appearance', theme)
        concurrency = QSpinBox()
        concurrency.setRange(1, 10)
        concurrency.setValue(s['concurrency'])
        self.settings_widgets['concurrency'] = concurrency
        experience_form.addRow('Concurrent downloads', concurrency)
        for key, label in [
            ('motion', 'Enable interface animations'),
            ('playlist_folders', 'Organize playlists in named folders'),
            ('skip', 'Skip previously downloaded media'),
        ]:
            item = QCheckBox(label)
            item.setChecked(s[key])
            self.settings_widgets[key] = item
            experience_form.addRow('', item)
        stack.addWidget(experience)

        metadata = QWidget()
        metadata.setObjectName('settingsCard')
        metadata_form = QFormLayout(metadata)
        metadata_form.setContentsMargins(16, 14, 16, 14)
        metadata_form.setSpacing(11)
        metadata_title = QLabel('METADATA, SUBTITLES & NAMING')
        metadata_title.setObjectName('sectionTitle')
        metadata_form.addRow(metadata_title)
        for key, label in [('languages', 'Subtitle languages (en,ur or all)'), ('template', 'Filename template')]:
            item = QLineEdit(s[key])
            self.settings_widgets[key] = item
            metadata_form.addRow(label, item)
        for key, label in [
            ('metadata', 'Embed metadata'),
            ('thumbnail', 'Embed thumbnail'),
            ('embed_subs', 'Embed subtitles'),
            ('write_subs', 'Download subtitles separately'),
            ('auto_subs', 'Include automatic captions'),
            ('chapters', 'Preserve chapters'),
        ]:
            item = QCheckBox(label)
            item.setChecked(s[key])
            self.settings_widgets[key] = item
            metadata_form.addRow('', item)
        stack.addWidget(metadata)

        auth = QWidget()
        auth.setObjectName('settingsCard')
        auth_form = QFormLayout(auth)
        auth_form.setContentsMargins(16, 14, 16, 14)
        auth_form.setSpacing(11)
        auth_title = QLabel('AUTHENTICATION')
        auth_title.setObjectName('sectionTitle')
        auth_form.addRow(auth_title)
        browser = QComboBox()
        browser.addItems(['None', 'Chrome', 'Edge', 'Firefox', 'Brave'])
        browser.setCurrentText(s['browser'])
        self.settings_widgets['browser'] = browser
        auth_form.addRow('Use existing browser login session', browser)
        warning = QLabel('Browser sessions remain on this computer. MBQ never asks for account passwords. Only use an account that is legitimately allowed to access the media.')
        warning.setWordWrap(True)
        warning.setObjectName('sectionHint')
        auth_form.addRow(warning)
        stack.addWidget(auth)

        maintenance = QWidget()
        maintenance.setObjectName('settingsCard')
        maintenance_layout = QVBoxLayout(maintenance)
        maintenance_layout.setContentsMargins(16, 14, 16, 14)
        maintenance_layout.setSpacing(10)

        maintenance_title = QLabel('MAINTENANCE & RESET')
        maintenance_title.setObjectName('sectionTitle')
        maintenance_layout.addWidget(maintenance_title)

        maintenance_hint = QLabel(
            'Clear disposable app data or restore MBQ to its defaults. '
            'Downloaded media files are never deleted by these controls.'
        )
        maintenance_hint.setWordWrap(True)
        maintenance_hint.setObjectName('sectionHint')
        maintenance_layout.addWidget(maintenance_hint)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.clear_cache_button = button('CLEAR CACHE', self.clear_app_cache)
        self.clear_cache_button.setObjectName('ghost')
        actions.addWidget(self.clear_cache_button)

        self.reset_defaults_button = button('RESET APP DEFAULTS', self.reset_application_defaults)
        self.reset_defaults_button.setObjectName('ghost')
        actions.addWidget(self.reset_defaults_button)

        self.reset_everything_button = button('RESET EVERYTHING', self.reset_everything)
        self.reset_everything_button.setObjectName('ghost')
        actions.addWidget(self.reset_everything_button)
        actions.addStretch()
        maintenance_layout.addLayout(actions)

        note = QLabel(
            'Reset App Defaults keeps queue and history.  •  '
            'Reset Everything clears settings, queue, history/archive and cache.  •  '
            'Downloaded files always remain untouched.'
        )
        note.setWordWrap(True)
        note.setObjectName('sectionHint')
        maintenance_layout.addWidget(note)

        stack.addWidget(maintenance)
        stack.addStretch()

        area.setWidget(widget)
        layout.addWidget(area, 1)

        save_bar = QWidget()
        save_bar.setObjectName('settingsSaveBar')
        save_row = QHBoxLayout(save_bar)
        save_row.setContentsMargins(14, 10, 14, 10)
        save_hint = QLabel('Changes apply to new downloads and are remembered between launches.')
        save_hint.setObjectName('sectionHint')
        save_row.addWidget(save_hint, 1)
        save = button('SAVE SETTINGS', self.save_settings, True)
        save.setMinimumWidth(180)
        save_row.addWidget(save)
        layout.addWidget(save_bar)

    def track(self, worker):
        self.workers.add(worker)
        worker.finished.connect(lambda: self.workers.discard(worker))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def error(self, message, details=''):
        self.last_error = message + '\n\n' + details
        box = QMessageBox(self)
        box.setWindowTitle('MBQ MEDIA DOWNLOADER')
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(message)
        box.setDetailedText(details)
        copy_button = box.addButton('Copy Error Details', QMessageBox.ButtonRole.ActionRole)
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.last_error))
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()

    def start_analysis_progress(self):
        if not hasattr(self, 'analysis_progress'):
            return
        self.analysis_progress_timer.stop()
        self.analysis_progress_timer.setInterval(70)
        self.analysis_progress_value = 0
        self.analysis_progress.setValue(0)
        self.analysis_progress_label.setText('RESOLVING SOURCE  •  0%')
        self.analysis_progress_wrap.show()
        self.update_home_signal('scanning', 'RESOLVING SOURCE', progress=0)
        self.analysis_progress_timer.start()

    def advance_analysis_progress(self):
        if not hasattr(self, 'analysis_progress_wrap') or not self.analysis_progress_wrap.isVisible():
            self.analysis_progress_timer.stop()
            return
        value = self.analysis_progress_value
        if value < 55:
            step, interval = 2, 70
        elif value < 82:
            step, interval = 1, 120
        elif value < 94:
            step, interval = 1, 240
        elif value < 97:
            step, interval = 1, 420
        else:
            return
        self.analysis_progress_timer.setInterval(interval)
        value = min(97, value + step)
        self.analysis_progress_value = value
        self.analysis_progress.setValue(value)
        self.analysis_progress_label.setText(f'RESOLVING SOURCE  •  {value}%')
        if hasattr(self, 'mbq_core'):
            self.mbq_core.set_progress(value)
            self.mbq_core.set_state('scanning')

    def finish_analysis_progress(self):
        if not hasattr(self, 'analysis_progress'):
            return
        self.analysis_progress_timer.stop()
        self.analysis_progress_value = 100
        self.analysis_progress.setValue(100)
        self.analysis_progress_label.setText('SOURCE RESOLVED  •  100%')
        if not self.channel_workers:
            self.update_home_signal('locked', 'SOURCE RESOLVED', progress=100)
        QTimer.singleShot(900, self.hide_analysis_progress)

    def hide_analysis_progress(self):
        if not hasattr(self, 'analysis_progress_wrap'):
            return
        if self.analysis_worker is None and not self.analysis_pending:
            self.analysis_progress_wrap.hide()
            self.analysis_progress.setValue(0)
            self.analysis_progress_value = 0

    def cancel_analysis_progress(self):
        if not hasattr(self, 'analysis_progress'):
            return
        self.analysis_progress_timer.stop()
        self.analysis_progress_value = 0
        self.analysis_progress.setValue(0)
        self.analysis_progress_label.setText('SCAN CANCELLED')
        self.update_home_signal('idle', 'READY / SCAN CANCELLED', progress=0)
        QTimer.singleShot(500, self.analysis_progress_wrap.hide)

    def analyze(self):
        if self.analysis_worker or self.engine_updating:
            return
        try:
            self.analysis_pending = urls(self.url_input.toPlainText())
        except ValueError as exc:
            self.error(str(exc))
            return
        self.media.clear()
        self.media_table.setRowCount(0)
        self.reset_channel_media(cancel_workers=True)
        self.exact.clear()
        self.download_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.start_analysis_progress()
        self.next_analysis()

    def next_analysis(self):
        if not self.analysis_pending:
            self.analyze_button.setEnabled(True)
            self.analyze_button.setText('LOCK SOURCE  →')
            self.download_button.setText('↓   ACQUIRE SELECTED MEDIA')
            self.download_button.setEnabled(bool(self.media))
            self.statusBar().showMessage(f'Analysis complete • {len(self.media)} media entries')
            return
        url = self.analysis_pending.pop(0)
        self.analyze_button.setText('RESOLVING…')
        self.download_button.setText('RESOLVING…')
        self.statusBar().showMessage('Analyzing ' + url)
        if self.is_tiktok_profile_url(url):
            self.start_direct_tiktok_profile(url)
            self.finish_analysis_progress()
            QTimer.singleShot(0, self.next_analysis)
            return
        worker = ProcessWorker('analyze', {'url': url, 'browser': self.store.settings['browser']}, self)
        self.analysis_worker = worker
        worker.result.connect(lambda info: self.add_media(info, url))
        worker.error.connect(self.error)
        worker.finished.connect(self.analysis_finished)
        self.track(worker)

    def analysis_finished(self):
        self.analysis_worker = None
        if not self.closing:
            if not self.analysis_pending:
                self.finish_analysis_progress()
            self.next_analysis()

    def cancel_analysis(self):
        self.analysis_pending.clear()
        if self.analysis_worker:
            self.analysis_worker.cancel()
        for worker in list(self.channel_workers):
            worker.cancel()
        self.cancel_analysis_progress()
        self.statusBar().showMessage('Analysis cancelled')

    def reset_channel_media(self, cancel_workers=False):
        if cancel_workers:
            for worker in list(self.channel_workers):
                worker.cancel()
            self.channel_workers.clear()
            if self.channel_profile_worker:
                self.channel_profile_worker.cancel()
                self.channel_profile_worker = None
        self.channel_items = {'videos': [], 'shorts': []}
        self.channel_title = ''
        self.channel_base_url = ''
        self.channel_platform = 'youtube'
        if hasattr(self, 'channel_videos_table'):
            self.channel_videos_table.setRowCount(0)
            self.channel_shorts_table.setRowCount(0)
            self.channel_videos_label.setText('VIDEOS  •  0')
            self.channel_shorts_label.setText('SHORTS  •  0')
            self.channel_selected_label.setText('0 items selected')
            if hasattr(self, 'channel_videos_stat_value'):
                self.channel_videos_stat_value.setText('0')
                self.channel_shorts_stat_value.setText('0')
                self.channel_selected_stat_value.setText('0')
                self.channel_shorts_stat_card.setVisible(True)
            self.channel_download_button.setVisible(False)
            if hasattr(self, 'channel_footer_controls'):
                self.channel_footer_controls.setVisible(False)
                self.channel_selected_label.setVisible(False)
                self.footer_divider.setVisible(False)
                self.selection_summary.setVisible(True)
                self.download_button.setVisible(True)
                self.sync_card_selection()
            self.channel_search.clear()
            self.reset_channel_progress()
            self.channel_section.setVisible(False)
            self.channel_avatar.clear()
            self.channel_avatar.setText('YT')
            self.channel_eyebrow.setText('CREATOR SIGNAL / YOUTUBE')
            self.channel_name_label.setText('YouTube Creator')
            self.channel_shorts_column.setVisible(True)
            self.channel_videos_label.setText('VIDEOS • 0')
            self.channel_select_videos_button.setText('Select Videos')
            self.channel_clear_videos_button.setText('Clear Videos')
            self.channel_meta_label.setText('Creator profile will appear here')
            self.channel_open_button.setEnabled(False)

    def youtube_channel_base(self, info):
        for key in ('channel_url', 'uploader_url'):
            value = info.get(key)
            if isinstance(value, str) and value.startswith(('http://', 'https://')) and 'youtube.com' in value:
                return value.rstrip('/')
        channel_id = info.get('channel_id') or info.get('uploader_id')
        if channel_id and str(channel_id).startswith('UC'):
            return 'https://www.youtube.com/channel/' + str(channel_id)
        return ''

    def tiktok_profile_base(self, info=None, original_url=''):
        info = info or {}
        candidates = [
            info.get('uploader_url'), info.get('channel_url'), info.get('webpage_url'),
            original_url,
        ]
        for value in candidates:
            if not isinstance(value, str) or not value.startswith(('http://', 'https://')):
                continue
            parsed = urlparse(value)
            host = (parsed.hostname or '').lower()
            if 'tiktok.com' not in host:
                continue
            parts = [part for part in parsed.path.split('/') if part]
            for part in parts:
                if part.startswith('@') and len(part) > 1:
                    return f'https://www.tiktok.com/{part}'
        handle = info.get('uploader_id')
        if handle:
            handle = str(handle).strip()
            if handle and not handle.isdigit():
                if not handle.startswith('@'):
                    handle = '@' + handle
                return 'https://www.tiktok.com/' + handle
        return ''

    def is_tiktok_profile_url(self, url):
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        host = (parsed.hostname or '').lower()
        if 'tiktok.com' not in host:
            return False
        parts = [part for part in parsed.path.split('/') if part]
        return len(parts) == 1 and parts[0].startswith('@')

    def start_direct_tiktok_profile(self, url):
        parts = [part for part in urlparse(url).path.split('/') if part]
        handle = parts[0] if parts else '@TikTok'
        self.start_channel_analysis({
            'uploader': handle.lstrip('@'),
            'uploader_id': handle,
            'uploader_url': url.rstrip('/'),
            'extractor_key': 'TikTokUser',
        }, url)

    def start_channel_progress(self):
        if not hasattr(self, 'channel_progress'):
            return
        self.channel_progress_timer.stop()
        self.channel_progress_timer.setInterval(85)
        self.channel_progress_value = 0
        self.channel_progress.setRange(0, 100)
        self.channel_progress.setValue(0)
        self.channel_progress.setFormat('%p%')
        self.channel_progress.setTextVisible(True)
        self.channel_progress.setVisible(True)
        if hasattr(self, 'channel_progress_hint'):
            self.channel_progress_hint.setText('MAPPING FEED  •  0%')
        self.update_home_signal('scanning', 'MAPPING CREATOR FEED', progress=0)
        self.channel_progress_timer.start()

    def advance_channel_progress(self):
        if not hasattr(self, 'channel_progress') or not self.channel_progress.isVisible():
            self.channel_progress_timer.stop()
            return
        value = self.channel_progress_value
        if value < 50:
            step, interval = 2, 85
        elif value < 80:
            step, interval = 1, 145
        elif value < 93:
            step, interval = 1, 260
        elif value < 97:
            step, interval = 1, 440
        else:
            return
        self.channel_progress_timer.setInterval(interval)
        value = min(97, value + step)
        self.channel_progress_value = value
        self.channel_progress.setValue(value)
        if hasattr(self, 'channel_progress_hint'):
            self.channel_progress_hint.setText(f'MAPPING FEED  •  {value}%')
        if hasattr(self, 'mbq_core'):
            self.mbq_core.set_progress(value)
            self.mbq_core.set_state('scanning')

    def finish_channel_progress(self):
        if not hasattr(self, 'channel_progress'):
            return
        self.channel_progress_timer.stop()
        self.channel_progress_value = 100
        self.channel_progress.setValue(100)
        if hasattr(self, 'channel_progress_hint'):
            self.channel_progress_hint.setText('FEED LOCKED  •  100%')
        self.update_home_signal('locked', 'CREATOR FEED LOCKED', progress=100)

    def reset_channel_progress(self):
        if hasattr(self, 'channel_progress_timer'):
            self.channel_progress_timer.stop()
        self.channel_progress_value = 0
        if hasattr(self, 'channel_progress'):
            self.channel_progress.setValue(0)
            self.channel_progress.setVisible(False)
        if hasattr(self, 'channel_progress_hint'):
            self.channel_progress_hint.setText('')

    def start_channel_analysis(self, info, original_url=''):
        host = (urlparse(original_url or str(info.get('webpage_url') or '')).hostname or '').lower()
        extractor = str(info.get('extractor_key') or info.get('extractor') or '').lower()

        if 'tiktok.com' in host or 'tiktok' in extractor:
            platform = 'tiktok'
            base = self.tiktok_profile_base(info, original_url)
        elif 'youtube.com' in host or host.endswith('youtu.be') or 'youtube' in extractor:
            platform = 'youtube'
            base = self.youtube_channel_base(info)
        else:
            return

        if not base or self.channel_workers or self.closing:
            return

        self.channel_platform = platform
        self.update_home_signal('scanning', 'MAPPING CREATOR FEED', source=platform)

        if platform == 'tiktok':
            self.channel_title = info.get('uploader') or info.get('channel') or info.get('uploader_id') or 'TikTok creator'
            self.channel_eyebrow.setText('CREATOR SIGNAL / TIKTOK')
            self.channel_avatar.clear()
            self.channel_avatar.setText('TT')
            self.channel_avatar.setStyleSheet('border-radius: 43px; background: #151923; color: #25F4EE; border: 2px solid #FE2C55; font-size: 18pt; font-weight: 900;')
            self.channel_search.setPlaceholderText('Search this TikTok profile…')
            self.channel_open_button.setText('OPEN CREATOR  ↗')
            self.channel_shorts_column.setVisible(False)
            self.channel_shorts_stat_card.setVisible(False)
            self.channel_select_shorts_button.setVisible(False)
            self.channel_videos_label.setText('VIDEOS  •  0 loading')
            self.channel_videos_stat_value.setText('0')
            self.channel_select_videos_button.setText('Select Videos')
            self.channel_clear_videos_button.setText('Clear Videos')
            scan_targets = [('videos', base)]
            profile_url = base
            scan_text = 'Scanning public TikTok videos…'

        else:
            self.channel_title = info.get('channel') or info.get('uploader') or 'YouTube channel'
            self.channel_eyebrow.setText('CREATOR SIGNAL / YOUTUBE')
            self.channel_avatar.clear()
            self.channel_avatar.setText('YT')
            self.channel_avatar.setStyleSheet('border-radius: 43px; background: #16284b; color: #ff4d61; border: 2px solid #ff4d61; font-size: 18pt; font-weight: 900;')
            self.channel_search.setPlaceholderText('Search this channel…')
            self.channel_open_button.setText('OPEN CREATOR  ↗')
            self.channel_shorts_column.setVisible(True)
            self.channel_shorts_stat_card.setVisible(True)
            self.channel_select_shorts_button.setVisible(True)
            self.channel_videos_label.setText('VIDEOS  •  0 loading')
            self.channel_shorts_label.setText('SHORTS  •  0 loading')
            self.channel_videos_stat_value.setText('0')
            self.channel_shorts_stat_value.setText('0')
            self.channel_select_videos_button.setText('Select Videos')
            self.channel_clear_videos_button.setText('Clear Videos')
            scan_targets = [('videos', base + '/videos'), ('shorts', base + '/shorts')]
            profile_url = base + '/videos'
            scan_text = 'Scanning public Videos and Shorts…'

        self.channel_base_url = base
        self.channel_section.setVisible(True)
        self.start_channel_progress()
        self.channel_name_label.setText(self.channel_title)
        self.channel_meta_label.setText(self.channel_profile_meta(info))
        self.channel_label.setText(scan_text)
        self.channel_open_button.setEnabled(True)

        profile_worker = ProcessWorker('channel_profile', {
            'url': profile_url,
            'browser': self.store.settings['browser']
        }, self)
        self.channel_profile_worker = profile_worker
        profile_worker.result.connect(lambda profile, source=info: self.apply_channel_profile(profile, source))
        profile_worker.error.connect(lambda message, details: logging.warning('Profile extraction failed: %s\n%s', message, details))
        profile_worker.finished.connect(self.channel_profile_finished)
        self.track(profile_worker)

        for kind, scan_url in scan_targets:
            worker = ProcessWorker('channel', {
                'url': scan_url,
                'browser': self.store.settings['browser']
            }, self)
            self.channel_workers.add(worker)
            worker.event.connect(lambda event, media_kind=kind: self.channel_event(media_kind, event))
            worker.result.connect(lambda data, media_kind=kind: self.channel_stream_complete(media_kind, data))
            worker.error.connect(lambda message, details, media_kind=kind: self.channel_error(media_kind, message, details))
            worker.finished.connect(lambda w=worker: self.channel_worker_finished(w))
            self.track(worker)

    def compact_number(self, value):
        try:
            number = int(value)
        except (TypeError, ValueError):
            return ''
        for divisor, suffix in ((1_000_000_000, 'B'), (1_000_000, 'M'), (1_000, 'K')):
            if number >= divisor:
                amount = number / divisor
                text = f'{amount:.1f}'.rstrip('0').rstrip('.')
                return text + suffix
        return f'{number:,}'

    def channel_profile_meta(self, info):
        handle = info.get('uploader_id') or info.get('channel_id') or ''
        if handle and not str(handle).startswith('@') and not str(handle).startswith('UC'):
            handle = '@' + str(handle)
        elif str(handle).startswith('UC'):
            handle = ''
        followers = self.compact_number(
            info.get('channel_follower_count') or info.get('uploader_follower_count') or info.get('follower_count')
        )
        pieces = []
        if handle:
            pieces.append(str(handle))
        if self.channel_platform == 'youtube':
            pieces.append((followers + ' subscribers') if followers else 'Subscriber count unavailable')
        else:
            pieces.append((followers + ' followers') if followers else 'Follower count unavailable')
        return '  •  '.join(pieces)

    def channel_avatar_url(self, info):
        thumbnails = info.get('thumbnails') or []
        avatar = [t for t in thumbnails if 'avatar' in str(t.get('id', '')).lower() and t.get('url')]
        if avatar:
            return avatar[-1]['url']
        square = []
        for thumb in thumbnails:
            url = thumb.get('url')
            width = thumb.get('width') or 0
            height = thumb.get('height') or 0
            if url and width and height:
                square.append((abs(width - height), -(width * height), url))
        if square:
            square.sort()
            return square[0][2]
        return ''

    def apply_channel_profile(self, profile, source_info):
        if not isinstance(profile, dict):
            return
        merged = dict(source_info or {})
        for key, value in profile.items():
            if value not in (None, '', [], {}):
                merged[key] = value
        name = merged.get('channel') or merged.get('uploader') or merged.get('title') or self.channel_title
        if name:
            self.channel_title = str(name).replace(' - Videos', '').strip()
            self.channel_name_label.setText(self.channel_title)
        self.channel_meta_label.setText(self.channel_profile_meta(merged))
        avatar_url = self.channel_avatar_url(profile)
        if avatar_url:
            self.load_channel_avatar(avatar_url)

    def channel_profile_finished(self):
        self.channel_profile_worker = None

    def load_channel_avatar(self, url):
        if not isinstance(url, str) or not url.startswith(('https://', 'http://')):
            return
        def fetch():
            with urlopen(Request(url, headers={'User-Agent': 'MBQ-Media-Downloader/1.2'}), timeout=15) as response:
                return response.read(3_000_000)
        def display(data):
            pix = QPixmap()
            if not pix.loadFromData(data):
                return
            size_px = 82
            scaled = pix.scaled(size_px, size_px, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = max(0, (scaled.width() - size_px) // 2)
            y = max(0, (scaled.height() - size_px) // 2)
            cropped = scaled.copy(x, y, size_px, size_px)
            rounded = QPixmap(size_px, size_px)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            path = QPainterPath()
            path.addEllipse(0, 0, size_px, size_px)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, cropped)
            painter.end()
            self.channel_avatar.setText('')
            self.channel_avatar.setPixmap(rounded)
        worker = FunctionWorker(fetch, self)
        worker.result.connect(display)
        self.track(worker)

    def open_channel(self):
        if self.channel_base_url:
            QDesktopServices.openUrl(QUrl(self.channel_base_url))

    def channel_event(self, kind, event):
        if not isinstance(event, dict):
            return
        if event.get('status') == 'Channel item' and isinstance(event.get('entry'), dict):
            self.add_channel_entry(kind, event['entry'])

    def channel_stream_complete(self, kind, data):
        # The worker streams entries in real time. The result only marks that
        # one channel tab reached the end successfully.
        count = len(self.channel_items[kind])
        label = self.channel_videos_label if kind == 'videos' else self.channel_shorts_label
        if kind == 'shorts':
            name = 'SHORTS'
        else:
            name = 'VIDEOS'
        label.setText(f'{name}  •  {count} loaded')
        if kind == 'videos':
            self.channel_videos_stat_value.setText(f'{count:,}')
        else:
            self.channel_shorts_stat_value.setText(f'{count:,}')

    def channel_worker_finished(self, worker):
        self.channel_workers.discard(worker)
        if not self.channel_workers and not self.closing:
            self.dedupe_channel_items()
            self.populate_channel_table('videos')
            self.populate_channel_table('shorts')
            self.filter_channel_media()
            total = len(self.channel_items['videos']) + len(self.channel_items['shorts'])
            self.finish_channel_progress()
            self.channel_videos_stat_value.setText(f'{len(self.channel_items["videos"]):,}')
            self.channel_shorts_stat_value.setText(f'{len(self.channel_items["shorts"]):,}')
            platform_name = {
                'tiktok': 'TikTok videos',
                'youtube': 'YouTube items',
            }.get(self.channel_platform, 'media items')
            self.channel_label.setText(f'{total} unique public {platform_name} loaded • extraction complete')
            self.update_home_signal('locked', f'{total} MEDIA ITEMS LOCKED', source=self.channel_platform)
            self.update_channel_selection()

    def channel_error(self, kind, message, details):
        logging.warning('Channel %s extraction failed: %s\n%s', kind, message, details)
        if kind == 'videos':
            self.channel_videos_label.setText(f'VIDEOS  •  {len(self.channel_items["videos"])} loaded • error')
        else:
            self.channel_shorts_label.setText(f'SHORTS  •  {len(self.channel_items["shorts"])} loaded • error')

    def channel_entry_url(self, entry, kind):
        video_id = str(entry.get('id') or '')
        url = entry.get('webpage_url') or entry.get('url') or ''
        if isinstance(url, str) and url.startswith(('http://', 'https://')):
            return url
        if self.channel_platform == 'tiktok' and video_id:
            handle = (urlparse(self.channel_base_url).path or '').strip('/')
            if handle.startswith('@'):
                return f'https://www.tiktok.com/{handle}/video/{video_id}'
        if video_id:
            if kind == 'shorts':
                return 'https://www.youtube.com/shorts/' + video_id
            return 'https://www.youtube.com/watch?v=' + video_id
        return ''

    def channel_record_key(self, record):
        info = record.get('info') or {}
        video_id = str(info.get('id') or '').strip()
        if video_id:
            return 'id:' + video_id
        url = str(record.get('url') or '').strip().lower()
        return 'url:' + url

    def dedupe_channel_items(self):
        # Shorts can also appear in YouTube's normal Videos tab. Prefer the
        # Shorts classification and remove duplicate IDs/URLs from Videos.
        unique_shorts = []
        short_keys = set()
        for record in self.channel_items['shorts']:
            key = self.channel_record_key(record)
            if key in short_keys:
                continue
            short_keys.add(key)
            unique_shorts.append(record)

        unique_videos = []
        video_keys = set()
        for record in self.channel_items['videos']:
            key = self.channel_record_key(record)
            if key in short_keys or key in video_keys:
                continue
            video_keys.add(key)
            unique_videos.append(record)

        self.channel_items['shorts'] = unique_shorts
        self.channel_items['videos'] = unique_videos

    def populate_channel_table(self, kind):
        records = self.channel_items[kind]
        table_widget = self.channel_shorts_table if kind == 'shorts' else self.channel_videos_table
        table_widget.blockSignals(True)
        table_widget.setRowCount(0)
        for record in records:
            self.append_channel_table_row(kind, record, table_widget)
        table_widget.blockSignals(False)

    def append_channel_table_row(self, kind, record, table_widget=None):
        table_widget = table_widget or (self.channel_shorts_table if kind == 'shorts' else self.channel_videos_table)
        entry = record['info']
        row = table_widget.rowCount()
        table_widget.insertRow(row)
        title = QTableWidgetItem(entry.get('title') or entry.get('id') or record['url'])
        title.setFlags(title.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        title.setCheckState(Qt.CheckState.Unchecked)
        table_widget.setItem(row, 0, title)
        table_widget.setItem(row, 1, QTableWidgetItem(duration(entry.get('duration'))))
        table_widget.setItem(row, 2, QTableWidgetItem(record['url']))

    def add_channel_entry(self, kind, entry):
        if not entry:
            return
        url = self.channel_entry_url(entry, kind)
        if not url:
            return

        record = {
            'info': entry,
            'url': url,
            'playlist': self.channel_title + (
                (' - Shorts' if kind == 'shorts' else ' - Videos')
                if self.channel_platform == 'youtube'
                else {'tiktok': ' - TikTok'}.get(self.channel_platform, ' - Media')
            ),
            'index': entry.get('playlist_index') or (len(self.channel_items[kind]) + 1),
            'kind': kind
        }
        key = self.channel_record_key(record)
        if any(self.channel_record_key(existing) == key for existing in self.channel_items[kind]):
            return

        self.channel_items[kind].append(record)
        table_widget = self.channel_shorts_table if kind == 'shorts' else self.channel_videos_table
        table_widget.blockSignals(True)
        self.append_channel_table_row(kind, record, table_widget)
        table_widget.blockSignals(False)

        count = len(self.channel_items[kind])
        if kind == 'shorts':
            name = 'SHORTS'
        else:
            name = 'VIDEOS'
        label = self.channel_videos_label if kind == 'videos' else self.channel_shorts_label
        label.setText(f'{name}  •  {count} loading')
        if kind == 'videos':
            self.channel_videos_stat_value.setText(f'{count:,}')
        else:
            self.channel_shorts_stat_value.setText(f'{count:,}')
        total = len(self.channel_items['videos']) + len(self.channel_items['shorts'])
        self.channel_label.setText(f'{self.channel_title} • scanning… {total} links found')

        # Keep search filtering live while rows stream in.
        query = self.channel_search.text().strip().lower()
        if query:
            row = table_widget.rowCount() - 1
            title = table_widget.item(row, 0).text().lower() if table_widget.item(row, 0) else ''
            length = table_widget.item(row, 1).text().lower() if table_widget.item(row, 1) else ''
            link = table_widget.item(row, 2).text().lower() if table_widget.item(row, 2) else ''
            table_widget.setRowHidden(row, query not in title and query not in length and query not in link)

    def remember_channel_quality(self, value):
        self.ui_settings.setValue('channel_bulk_quality', value)

    def clear_channel_search(self):
        self.channel_search.clear()
        self.channel_search.setFocus()

    def filter_channel_media(self, *_):
        if not hasattr(self, 'channel_search'):
            return
        query = self.channel_search.text().strip().lower()
        for kind, table_widget, label in (
            ('videos', self.channel_videos_table, self.channel_videos_label),
            ('shorts', self.channel_shorts_table, self.channel_shorts_label),
        ):
            visible = 0
            for row in range(table_widget.rowCount()):
                title = table_widget.item(row, 0).text().lower() if table_widget.item(row, 0) else ''
                length = table_widget.item(row, 1).text().lower() if table_widget.item(row, 1) else ''
                url = table_widget.item(row, 2).text().lower() if table_widget.item(row, 2) else ''
                hidden = bool(query and query not in title and query not in length and query not in url)
                table_widget.setRowHidden(row, hidden)
                if not hidden:
                    visible += 1
            total = len(self.channel_items[kind])
            if kind == 'shorts':
                name = 'SHORTS'
            else:
                name = 'VIDEOS'
            label.setText(f'{name}  •  {visible} shown / {total}' if query else f'{name}  •  {total}')

    def channel_selected_records(self):
        selected = []
        seen = set()
        for kind, table_widget in (('videos', self.channel_videos_table), ('shorts', self.channel_shorts_table)):
            records = self.channel_items[kind]
            for row in range(min(table_widget.rowCount(), len(records))):
                item = table_widget.item(row, 0)
                if item and item.checkState() == Qt.CheckState.Checked:
                    record = records[row]
                    key = self.channel_record_key(record)
                    if key in seen:
                        continue
                    seen.add(key)
                    selected.append((record, table_widget, row))
        return selected

    def update_channel_selection(self, *_):
        if not hasattr(self, 'channel_download_button'):
            return
        selected = self.channel_selected_records()
        videos = sum(1 for record, _, _ in selected if record.get('kind') == 'videos')
        shorts = sum(1 for record, _, _ in selected if record.get('kind') == 'shorts')
        count = len(selected)
        detail = []
        if videos:
            detail.append(f'{videos} videos')
        if shorts:
            detail.append(f'{shorts} Shorts')
        if detail:
            self.channel_selected_label.setText(f"{count} items selected\n" + '  •  '.join(detail))
        else:
            self.channel_selected_label.setText('0 items selected')
        self.channel_selected_stat_value.setText(f'{count:,}')
        self.channel_download_button.setText(f'↓   ACQUIRE {count} ITEMS')
        channel_mode = count > 0
        self.channel_selected_label.setVisible(channel_mode)
        self.channel_footer_controls.setVisible(channel_mode)
        self.footer_divider.setVisible(channel_mode)
        self.channel_download_button.setVisible(channel_mode)
        self.channel_download_button.setEnabled(channel_mode and not self.engine_updating)
        self.selection_summary.setVisible(not channel_mode)
        self.download_button.setVisible(not channel_mode)
        if not channel_mode:
            self.sync_card_selection()

    def check_channel_kind(self, kind, checked):
        table_widget = self.channel_shorts_table if kind == 'shorts' else self.channel_videos_table
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        table_widget.blockSignals(True)
        for row in range(table_widget.rowCount()):
            item = table_widget.item(row, 0)
            if item:
                item.setCheckState(state)
        table_widget.blockSignals(False)
        self.update_channel_selection()

    def check_channel_media(self, checked):
        self.check_channel_kind('videos', checked)
        self.check_channel_kind('shorts', checked)

    def copy_channel_links(self):
        selected = self.channel_selected_records()
        links = [record['url'] for record, _, _ in selected]
        if not links:
            for kind, table_widget in (('videos', self.channel_videos_table), ('shorts', self.channel_shorts_table)):
                for row, record in enumerate(self.channel_items[kind]):
                    if row < table_widget.rowCount() and not table_widget.isRowHidden(row):
                        links.append(record['url'])
        if not links:
            self.statusBar().showMessage('No profile/channel links to copy.')
            return
        QApplication.clipboard().setText('\n'.join(links))
        self.statusBar().showMessage(f'Copied {len(links)} media links')

    def enqueue_channel(self):
        if self.engine_updating:
            self.statusBar().showMessage('Wait for the engine update to finish before adding downloads.')
            return
        selected = self.channel_selected_records()
        if not selected:
            return
        try:
            custom_args(self.custom.text())
            validate_template(self.store.settings['template'])
            if not find_tool('ffmpeg') or not find_tool('ffprobe'):
                self.nav.setCurrentRow(4)
                self.error('FFmpeg and ffprobe are required. Install both using Engine before downloading.')
                return
            choice = self.channel_quality.currentText()
            mode = 'Audio' if choice == 'Audio Only' else 'Video'
            quality = 'Best Available' if mode == 'Audio' else choice
            count = skipped = duplicates = 0
            queued_urls = {str(job.get('url') or '') for job in self.jobs}
            for record, table_widget, row in selected:
                info = record['info']
                if record['url'] in queued_urls:
                    duplicates += 1
                    continue
                if self.store.settings['skip'] and self.store.downloaded(info):
                    skipped += 1
                    continue
                settings = self.store.settings.copy()
                minimal = {k: info[k] for k in ('id', 'title', 'extractor', 'extractor_key', 'ie_key', 'webpage_url') if k in info}
                self.jobs.append(dict(
                    id=uuid.uuid4().hex,
                    info=minimal,
                    url=record['url'],
                    title=info.get('title') or record['url'],
                    playlist=record['playlist'],
                    index=record['index'],
                    thumb_url='',
                    quality=quality,
                    mode=mode,
                    exact='',
                    custom=self.custom.text(),
                    settings=settings,
                    status='Waiting',
                    percent=0,
                    file='',
                    details=''
                ))
                queued_urls.add(record['url'])
                count += 1
            self.persist_queue()
            self.render_queue()
            if count:
                self.start_queue()
                self.nav.setCurrentRow(1)
            self.statusBar().showMessage(f'Queued {count} channel items • Skipped {skipped} downloaded • Ignored {duplicates} duplicate queue links')
        except (ValueError, OSError) as exc:
            self.error(str(exc))

    def add_media(self, info, original_url):
        playlist = info.get('_type') in ('playlist', 'multi_video') or 'entries' in info
        entries = info.get('entries', []) if playlist else [info]
        self.playlist_label.setText(f"{info.get('title', 'Media')} • {len(entries)} entries" if playlist else 'Single media / multiple URLs')
        for index, entry in enumerate(entries, 1):
            if not entry:
                continue
            url = entry.get('webpage_url') or entry.get('url') or original_url
            if not url.startswith(('http://', 'https://')):
                if str(entry.get('ie_key', '')).lower() == 'youtube':
                    url = 'https://www.youtube.com/watch?v=' + str(entry['id'])
                else:
                    continue
            record = dict(info=entry, url=url, playlist=info.get('title', 'Playlist') if playlist else '', index=entry.get('playlist_index') or index)
            self.media.append(record)
            row = self.media_table.rowCount()
            self.media_table.insertRow(row)
            item = QTableWidgetItem(entry.get('title') or entry.get('id') or url)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.media_table.setItem(row, 0, item)
            self.media_table.setItem(row, 1, QTableWidgetItem(duration(entry.get('duration'))))
            self.media_table.setItem(row, 2, QTableWidgetItem(entry.get('extractor_key') or entry.get('ie_key') or urlparse(url).hostname or ''))
            self.media_table.setItem(row, 3, QTableWidgetItem('Formats ready' if entry.get('formats') else 'Select → analyze formats'))
        if self.media:
            self.media_table.selectRow(0)
        host = (urlparse(original_url).hostname or '').lower()
        if not playlist and (
            'youtube.com' in host or host.endswith('youtu.be') or 'tiktok.com' in host
        ):
            self.start_channel_analysis(info, original_url)

    def select_media(self):
        row = self.media_table.currentRow()
        if not 0 <= row < len(self.media):
            return
        info = self.media[row]['info']
        self.current_info = info
        self.exact.clear()
        title = info.get('title', 'Untitled')
        creator = info.get('uploader') or info.get('channel') or 'Unknown uploader'
        source = info.get('extractor_key') or info.get('ie_key') or urlparse(self.media[row]['url']).hostname or 'Unknown source'
        self.media_title_label.setText(title)
        self.media_creator_label.setText(str(creator))
        self.media_meta_label.setText(f"DURATION / {duration(info.get('duration'))}    SOURCE / {source}")
        self.update_home_signal('locked', 'SIGNAL LOCKED', source=source, title=title, creator=str(creator))
        previous = self.quality.currentText()
        self.quality.clear()
        self.quality.addItems(available_qualities(info) if info.get('formats') else ['Best Available'])
        self.quality.setCurrentText(previous if self.quality.findText(previous) >= 0 else 'Best Available')
        self.show_formats(info)
        self.refresh_format_cards()
        self.thumbnail.clear()
        self.thumbnail.setText('VIDEO')
        image_url = info.get('thumbnail')
        if not image_url and info.get('thumbnails'):
            image_url = info['thumbnails'][-1].get('url')
        if image_url:
            self.load_thumbnail(image_url, row)

    def load_thumbnail(self, url, row):
        if not url.startswith(('https://', 'http://')):
            return
        def fetch():
            with urlopen(Request(url, headers={'User-Agent': 'MBQ-Media-Downloader/1.2'}), timeout=15) as response:
                return response.read(5_000_000)
        def display(data):
            pix = QPixmap()
            if pix.loadFromData(data):
                self.thumbs[url] = pix
                if self.media_table.currentRow() == row:
                    self.thumbnail.setPixmap(pix.scaled(self.thumbnail.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    if hasattr(self, 'mbq_core'):
                        self.mbq_core.set_artwork(pix)
                if row < len(self.media):
                    self.media[row]['thumb_url'] = url
        if url in self.thumbs:
            self.media[row]['thumb_url'] = url
            self.thumbnail.setPixmap(self.thumbs[url].scaled(self.thumbnail.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            if hasattr(self, 'mbq_core'):
                self.mbq_core.set_artwork(self.thumbs[url])
            return
        worker = FunctionWorker(fetch, self)
        worker.result.connect(display)
        self.track(worker)

    def analyze_selected(self):
        row = self.media_table.currentRow()
        if not 0 <= row < len(self.media) or self.analysis_worker or self.engine_updating:
            return
        record = self.media[row]
        self.statusBar().showMessage('Analyzing selected video formats...')
        worker = ProcessWorker('analyze', {'url': record['url'], 'browser': self.store.settings['browser']}, self)
        self.analysis_worker = worker
        self.analyze_button.setEnabled(False)
        def done(info):
            if 'entries' in info:
                self.error('Select a single video to inspect exact formats.')
                return
            record['info'] = info
            self.media_table.item(row, 0).setText(info.get('title', record['url']))
            self.media_table.item(row, 1).setText(duration(info.get('duration')))
            self.media_table.item(row, 3).setText('Formats ready')
            self.media_table.selectRow(row)
            self.select_media()
            self.nav.setCurrentRow(3)
        worker.result.connect(done)
        worker.error.connect(self.error)
        worker.finished.connect(self.analysis_finished)
        self.track(worker)

    def show_formats(self, info):
        self.formats_table.setRowCount(0)
        self.format_label.setText(info.get('title', 'Unknown media') + (' • Formats not analyzed yet' if not info.get('formats') else ''))
        for f in info.get('formats', []):
            if f.get('has_drm') or not f.get('url'):
                continue
            row = self.formats_table.rowCount()
            self.formats_table.insertRow(row)
            values = [f.get('resolution') or (f"{f.get('width', '?')}x{f.get('height', '?')}" if f.get('height') else 'audio'),
                f.get('format_id'), f.get('ext'), f.get('vcodec'), f.get('acodec'), f.get('fps'),
                f.get('tbr'), size(f.get('filesize') or f.get('filesize_approx')) + (' ≈' if not f.get('filesize') and f.get('filesize_approx') else '')]
            for col, value in enumerate(values):
                self.formats_table.setItem(row, col, QTableWidgetItem(str(value) if value is not None else '—'))

    def use_formats(self):
        rows = sorted({index.row() for index in self.formats_table.selectedIndexes()})
        if not 1 <= len(rows) <= 2:
            self.error('Select one format, or a video-only format and an audio-only format.')
            return
        ids = [self.formats_table.item(row, 1).text() for row in rows]
        formats = {str(f['format_id']): f for f in self.current_info.get('formats', [])}
        if len(ids) == 2:
            videos = [i for i in ids if formats[i].get('vcodec') != 'none' and formats[i].get('acodec') == 'none']
            audios = [i for i in ids if formats[i].get('vcodec') == 'none' and formats[i].get('acodec') != 'none']
            if len(videos) != 1 or len(audios) != 1:
                self.error('The pair must be one video-only and one audio-only format.')
                return
            ids = videos + audios
        self.exact.setText('+'.join(ids))
        self.sync_card_selection()
        self.statusBar().showMessage('Exact selection applied to the currently selected media.')

    def validate_custom(self):
        try:
            custom_args(self.custom.text())
            self.statusBar().showMessage('Advanced arguments are valid.')
        except ValueError as exc:
            self.error(str(exc))

    def check_media(self, checked):
        for row in range(self.media_table.rowCount()):
            self.media_table.item(row, 0).setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def change_mode(self, mode):
        self.output.clear()
        self.output.addItems(['MP4', 'MKV', 'WebM'] if mode == 'Video' else ['MP3', 'M4A', 'Opus', 'WAV'])
        self.output.setCurrentText(self.store.settings['container' if mode == 'Video' else 'audio'])
        self.quality.setEnabled(mode == 'Video')
        self.refresh_format_cards()

    def enqueue(self):
        if self.engine_updating:
            self.statusBar().showMessage('Wait for the engine update to finish before adding downloads.')
            return
        try:
            custom_args(self.custom.text())
            validate_template(self.store.settings['template'])
            if not find_tool('ffmpeg') or not find_tool('ffprobe'):
                self.nav.setCurrentRow(4)
                self.error('FFmpeg and ffprobe are required. Install both using Engine before downloading.')
                return
            selected = self.media_table.currentRow()
            count = skipped = 0
            for row, record in enumerate(self.media):
                if self.media_table.item(row, 0).checkState() != Qt.CheckState.Checked:
                    continue
                if self.store.settings['skip'] and self.store.downloaded(record['info']):
                    self.media_table.item(row, 3).setText('Skipped • in archive')
                    skipped += 1
                    continue
                settings = self.store.settings.copy()
                settings['container' if self.mode.currentText() == 'Video' else 'audio'] = self.output.currentText()
                info = record['info']
                minimal = {k: info[k] for k in ('id', 'title', 'extractor', 'extractor_key', 'ie_key', 'webpage_url') if k in info}
                self.jobs.append(dict(id=uuid.uuid4().hex, info=minimal, url=record['url'],
                    title=info.get('title') or record['url'], playlist=record['playlist'], index=record['index'],
                    thumb_url=record.get('thumb_url') or info.get('thumbnail') or (info.get('thumbnails') or [{}])[-1].get('url', ''), quality=self.quality.currentText(), mode=self.mode.currentText(),
                    exact=self.exact.text() if row == selected else '', custom=self.custom.text(), settings=settings,
                    status='Waiting', percent=0, file='', details=''))
                self.media_table.item(row, 3).setText('Waiting')
                count += 1
            self.persist_queue()
            self.render_queue()
            self.load_queue_thumbnails()
            if count:
                self.start_queue()
                self.nav.setCurrentRow(1)
            self.statusBar().showMessage(f'Queued {count} • Skipped {skipped} previously downloaded')
        except (ValueError, OSError) as exc:
            self.error(str(exc))

    def start_or_resume_queue(self):
        """Start waiting jobs and resume any downloads that were paused in-place."""
        resumed = 0
        for job_id, worker in list(self.active.items()):
            if job_id not in self.paused_job_status:
                continue
            if worker.resume():
                resumed += 1
            previous = self.paused_job_status.pop(job_id, 'Downloading')
            job = next((item for item in self.jobs if item.get('id') == job_id), None)
            if job is not None:
                job['status'] = previous if previous != 'Paused' else 'Downloading'

        self.stop_after_current = False
        self.running = True
        self.statusBar().showMessage(
            f'Queue resumed • {resumed} paused download(s) continued'
            if resumed else
            'Queue started'
        )
        self.render_queue()
        self.schedule()
        self.update_queue_summary()

    def start_queue(self):
        # Compatibility with existing internal calls.
        self.start_or_resume_queue()

    def resume_queue(self):
        # Compatibility with older UI/actions.
        self.start_or_resume_queue()

    def pause_queue(self):
        """Pause active downloads immediately and prevent new jobs from starting."""
        self.running = False
        self.stop_after_current = False
        paused = 0

        for job_id, worker in list(self.active.items()):
            job = next((item for item in self.jobs if item.get('id') == job_id), None)
            if job is None or job_id in self.force_stopped_job_ids:
                continue

            if job_id not in self.paused_job_status:
                self.paused_job_status[job_id] = job.get('status', 'Downloading')

            if worker.pause():
                paused += 1
            job['status'] = 'Paused'

        self.persist_queue()
        self.render_queue()
        if paused:
            self.statusBar().showMessage(
                f'Paused {paused} active download(s) • waiting queue is paused'
            )
        else:
            self.statusBar().showMessage('Queue paused')
        self.update_queue_summary()

    def stop_queue_after_current(self):
        """Let currently active downloads finish, but do not start another job."""
        # A paused download must be resumed if the user asks it to finish.
        for job_id, worker in list(self.active.items()):
            if job_id in self.paused_job_status:
                worker.resume()
                previous = self.paused_job_status.pop(job_id, 'Downloading')
                job = next((item for item in self.jobs if item.get('id') == job_id), None)
                if job is not None:
                    job['status'] = previous if previous != 'Paused' else 'Downloading'

        self.stop_after_current = True
        self.running = True
        self.render_queue()
        self.statusBar().showMessage(
            'Stop after current enabled • active downloads will finish, then the queue stops'
        )
        self.update_queue_summary()

    def force_stop_queue(self):
        """Immediately terminate active downloads and stop the queue.

        Force-stopped jobs are returned to Waiting so Start / Resume can continue
        them later. yt-dlp can reuse its partial .part file when available.
        """
        self.running = False
        self.stop_after_current = False

        active_ids = list(self.active)
        if not active_ids:
            self.statusBar().showMessage('Queue stopped • no active downloads')
            self.update_queue_summary()
            return

        for job_id in active_ids:
            self.force_stopped_job_ids.add(job_id)
            self.paused_job_status.pop(job_id, None)

            job = next((item for item in self.jobs if item.get('id') == job_id), None)
            if job is not None:
                job['status'] = 'Stopping'
                job['speed'] = '—'
                job['eta'] = '—'

            worker = self.active.get(job_id)
            if worker is not None:
                worker.cancel()

        self.persist_queue()
        self.render_queue()
        self.statusBar().showMessage(
            f'Force stopping {len(active_ids)} active download(s)…'
        )
        self.update_queue_summary()

    def schedule(self):
        if not self.running or self.closing or self.engine_updating:
            return

        if self.stop_after_current:
            if not self.active:
                self.running = False
                self.stop_after_current = False
                self.statusBar().showMessage('Queue stopped after current downloads completed')
                self.update_queue_summary()
            return

        for job in self.jobs:
            if len(self.active) >= self.store.settings['concurrency']:
                break
            if job['status'] != 'Waiting' or job['id'] in self.active:
                continue
            worker = ProcessWorker('download', job, self)
            self.active[job['id']] = worker
            job['status'] = 'Analyzing'
            worker.event.connect(lambda event, j=job: self.job_event(j, event))
            worker.result.connect(lambda path, j=job: self.job_done(j, path))
            worker.error.connect(lambda msg, details, j=job: self.job_failed(j, msg, details))
            worker.finished.connect(lambda j=job: self.job_finished(j))
            self.track(worker)
            self.render_queue()

        if not self.active and not any(j['status'] == 'Waiting' for j in self.jobs):
            self.running = False
            self.stop_after_current = False
            self.update_queue_summary()

    def job_event(self, job, event):
        job_id = job.get('id')
        if job_id in self.force_stopped_job_ids:
            # Keep the temporary STOPPING state until the worker has fully exited.
            pass
        elif job_id in self.paused_job_status and event.get('status') != 'Cancelled':
            # Progress output already buffered by the subprocess must not visually
            # unpause a download.
            job['status'] = 'Paused'
        else:
            job['status'] = event['status']
        self.update_media_status(job)
        if event.get('progress'):
            p = event['progress']
            total = p.get('total_bytes') or p.get('total_bytes_estimate') or 0
            downloaded = p.get('downloaded_bytes') or 0
            job['percent'] = min(100, round(downloaded / total * 100)) if total else 0
            job['bytes'] = size(downloaded) + ' / ' + size(total or None)
            job['speed'] = size(p.get('speed')) + '/s' if p.get('speed') else '—'
            job['eta'] = duration(p.get('eta'))
            self.update_home_signal('downloading', 'PULLING MEDIA', progress=job['percent'], title=job.get('title', 'Media'))
        elif event.get('status') in ('Merging', 'Processing'):
            self.update_home_signal('processing', str(event.get('status')).upper(), title=job.get('title', 'Media'))
        self.render_queue()

    def job_done(self, job, path):
        job.update(status='Completed', file=path, percent=100, speed='—', eta='—')
        self.update_home_signal('complete', 'MEDIA ACQUIRED', progress=100, title=job.get('title', 'Media'))
        self.update_media_status(job)
        self.store.record(job)
        self.persist_queue()
        self.render_queue()

    def job_failed(self, job, message, details):
        job.update(status='Failed', details=message + '\n\n' + details)
        self.update_home_signal('error', 'SIGNAL LOST', title=job.get('title', 'Media'))
        self.update_media_status(job)
        self.last_error = job['details']
        self.store.record(job)
        self.persist_queue()
        self.render_queue()
        self.statusBar().showMessage(message)

    def job_finished(self, job):
        job_id = job.get('id')
        self.active.pop(job_id, None)
        self.paused_job_status.pop(job_id, None)

        remove_after_cancel = bool(job.pop('_remove_after_cancel', False))
        force_stopped = job_id in self.force_stopped_job_ids
        if force_stopped:
            self.force_stopped_job_ids.discard(job_id)
            job.update(status='Waiting', speed='—', eta='—')
            self.update_media_status(job)
        elif remove_after_cancel:
            self.jobs = [item for item in self.jobs if item.get('id') != job_id]
            self.queue_selected_ids.discard(job_id)
        elif job['status'] == 'Cancelled':
            self.store.record(job)

        self.persist_queue()
        self.render_queue()
        self.update_queue_summary()
        if not self.closing:
            self.schedule()

    def update_media_status(self, job):
        for row, record in enumerate(self.media):
            if record['url'] == job['url']:
                self.media_table.item(row, 3).setText(job['status'])

    def selected_jobs(self):
        self.remember_queue_selection()
        return [j for j in self.jobs if j['id'] in self.queue_selected_ids]

    def cancel_jobs(self):
        for job in self.selected_jobs():
            if job['id'] in self.active:
                self.active[job['id']].cancel()
            elif job['status'] == 'Waiting':
                job['status'] = 'Cancelled'
                self.store.record(job)
        self.persist_queue()
        self.render_queue()

    def retry_jobs(self):
        for job in self.selected_jobs():
            if job['id'] not in self.active and job['status'] in ('Failed', 'Cancelled'):
                job.update(status='Waiting', percent=0, details='')
        self.persist_queue()
        self.render_queue()
        self.start_queue()

    def retry_failed_jobs(self):
        count = 0
        for job in self.jobs:
            if job['id'] not in self.active and job['status'] == 'Failed':
                job.update(status='Waiting', percent=0, details='', bytes='—', speed='—', eta='—')
                count += 1
        self.persist_queue()
        self.render_queue()
        if count:
            self.statusBar().showMessage(f'Retrying {count} failed download(s)')
            self.start_queue()
        else:
            self.statusBar().showMessage('No failed downloads to retry')

    def move_jobs_to_top(self):
        selected_ids = {j['id'] for j in self.selected_jobs() if j['id'] not in self.active}
        if not selected_ids:
            self.statusBar().showMessage('Select one or more waiting/finished jobs to move')
            return
        selected_jobs = [j for j in self.jobs if j['id'] in selected_ids]
        remaining = [j for j in self.jobs if j['id'] not in selected_ids]
        # Keep active jobs at the very front so their live rows do not jump around.
        active_jobs = [j for j in remaining if j['id'] in self.active]
        other_jobs = [j for j in remaining if j['id'] not in self.active]
        self.jobs = active_jobs + selected_jobs + other_jobs
        self.persist_queue()
        self.render_queue()
        self.statusBar().showMessage(f'Moved {len(selected_jobs)} job(s) to the top of the waiting queue')

    def update_queue_summary(self):
        if not hasattr(self, 'queue_summary'):
            return
        counts = {}
        for job in self.jobs:
            counts[job.get('status', 'Unknown')] = counts.get(job.get('status', 'Unknown'), 0) + 1
        active = len(self.active)
        waiting = counts.get('Waiting', 0)
        completed = counts.get('Completed', 0)
        failed = counts.get('Failed', 0)
        cancelled = counts.get('Cancelled', 0)
        paused = sum(1 for job_id in self.active if job_id in self.paused_job_status)
        stopping = sum(1 for job_id in self.active if job_id in self.force_stopped_job_ids)
        if stopping:
            state = 'FORCE STOPPING'
        elif paused:
            state = 'PAUSED'
        elif self.stop_after_current:
            state = 'STOPPING AFTER CURRENT'
        elif self.running:
            state = 'RUNNING'
        elif active:
            state = 'ACTIVE'
        else:
            state = 'PAUSED' if waiting else 'IDLE'
        self.queue_summary.setText(
            f'{state}   •   {active} active   •   {waiting} waiting   •   '
            f'{completed} completed   •   {failed} failed'
            + (f'   •   {cancelled} cancelled' if cancelled else '')
        )
        if hasattr(self, 'queue_stat_labels'):
            self.queue_stat_labels['active'].setText(str(active))
            self.queue_stat_labels['waiting'].setText(str(waiting))
            self.queue_stat_labels['completed'].setText(str(completed))
            self.queue_stat_labels['failed'].setText(str(failed))
        if hasattr(self, 'queue_state_word'):
            self.queue_state_word.setText(state)
        if hasattr(self, 'home_stat_values'):
            if 'queue' in self.home_stat_values:
                self.home_stat_values['queue'].setText(str(len(self.jobs)))
            if 'active' in self.home_stat_values:
                self.home_stat_values['active'].setText(str(active))
            if 'completed' in self.home_stat_values:
                self.home_stat_values['completed'].setText(str(completed))

    def remove_jobs(self):
        self.delete_selected_queue_items()

    def clear_completed(self):
        self.jobs = [j for j in self.jobs if j['status'] != 'Completed']
        self.persist_queue()
        self.render_queue()

    def render_queue(self):
        if not hasattr(self, 'queue_list'):
            return
        self.remember_queue_selection()

        while self.queue_list.count():
            item = self.queue_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.queue_checks = {}
        self.queue_cards = {}

        visible = [job for job in self.jobs if self.queue_job_visible(job)]
        if not visible:
            empty = QWidget()
            empty.setObjectName('queueEmpty')
            box = QVBoxLayout(empty)
            box.setContentsMargins(24, 44, 24, 44)
            icon = QLabel('↓')
            icon.setObjectName('queueEmptyIcon')
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            message = QLabel('No downloads in this view')
            message.setObjectName('queueEmptyTitle')
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            detail = QLabel('Add media from Home or switch the queue filter.')
            detail.setObjectName('muted')
            detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box.addWidget(icon)
            box.addWidget(message)
            box.addWidget(detail)
            self.queue_list.addWidget(empty)
        else:
            for job in visible:
                status = job.get('status', 'Waiting')
                card = QWidget()
                normalized = status.lower().replace(' ', '').replace('aftercurrent', '')
                if status in ('Analyzing', 'Downloading', 'Merging', 'Processing', 'Paused', 'Stopping'):
                    card.setObjectName('queueCardActive')
                elif status == 'Completed':
                    card.setObjectName('queueCardCompleted')
                elif status == 'Failed':
                    card.setObjectName('queueCardFailed')
                else:
                    card.setObjectName('queueCard')
                card.setMinimumHeight(UI["queue_card_min_height"])
                outer = QHBoxLayout(card)
                outer.setContentsMargins(14, 12, 14, 12)
                outer.setSpacing(12)

                check = QCheckBox()
                check.setObjectName('queueCheck')
                check.setChecked(job['id'] in self.queue_selected_ids)
                check.toggled.connect(lambda checked, job_id=job['id']: self.toggle_queue_job(job_id, checked))
                self.queue_checks[job['id']] = check
                outer.addWidget(check, 0, Qt.AlignmentFlag.AlignVCenter)

                thumb = QLabel('MEDIA')
                thumb.setObjectName('queueThumb')
                thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
                thumb.setFixedSize(96, 54)
                if job.get('thumb_url') in self.thumbs:
                    pix = self.thumbs[job['thumb_url']]
                    thumb.setPixmap(pix.scaled(thumb.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                outer.addWidget(thumb)

                center = QVBoxLayout()
                center.setSpacing(5)
                title = QLabel(job.get('title') or job.get('url', 'Untitled'))
                title.setObjectName('queueJobTitle')
                title.setTextFormat(Qt.TextFormat.PlainText)
                title.setWordWrap(True)
                center.addWidget(title)

                quality = job.get('exact') or (job['settings']['audio'] if job['mode'] == 'Audio' else job['quality'])
                meta = QLabel(f"{job.get('mode', 'Video')}  •  {quality}  •  {job.get('settings', {}).get('container', '') if job.get('mode') == 'Video' else job.get('settings', {}).get('audio', '')}")
                meta.setObjectName('queueJobMeta')
                center.addWidget(meta)

                progress_row = QHBoxLayout()
                progress_row.setSpacing(10)
                bar = QProgressBar()
                bar.setObjectName('queueProgress')
                bar.setTextVisible(False)
                bar.setRange(0, 100)
                bar.setValue(int(job.get('percent', 0) or 0))
                progress_row.addWidget(bar, 1)
                percent = QLabel(f"{int(job.get('percent', 0) or 0)}%")
                percent.setObjectName('queuePercent')
                percent.setFixedWidth(42)
                percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                progress_row.addWidget(percent)
                center.addLayout(progress_row)

                metrics = QLabel(f"{job.get('bytes', '—')}    {job.get('speed', '—')}    ETA {job.get('eta', '—')}")
                metrics.setObjectName('queueMetrics')
                center.addWidget(metrics)
                outer.addLayout(center, 1)

                side = QVBoxLayout()
                side.setSpacing(6)
                badge = QLabel(status.upper())
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if status in ('Analyzing', 'Downloading', 'Merging', 'Processing', 'Paused', 'Stopping'):
                    badge.setObjectName('statusActive')
                elif status == 'Completed':
                    badge.setObjectName('statusCompleted')
                elif status == 'Failed':
                    badge.setObjectName('statusFailed')
                elif status == 'Cancelled':
                    badge.setObjectName('statusCancelled')
                else:
                    badge.setObjectName('statusWaiting')
                badge.setMinimumWidth(96)
                side.addWidget(badge)
                side.addStretch()
                index_label = QLabel(f"#{self.jobs.index(job)+1:03d}")
                index_label.setObjectName('queueIndex')
                index_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                side.addWidget(index_label)
                outer.addLayout(side)

                self.queue_cards[job['id']] = card
                self.queue_list.addWidget(card)

        self.queue_list.addStretch()
        self.update_queue_summary()
        self.update_queue_selection_ui()

    def persist_queue(self):
        path = self.store.root / 'queue.json'
        temp = path.with_suffix('.tmp')
        try:
            temp.write_text(json.dumps(self.jobs, indent=2), 'utf-8')
            temp.replace(path)
        except OSError:
            logging.exception('Could not save queue')

    def restore_queue(self):
        try:
            self.jobs = json.loads((self.store.root / 'queue.json').read_text('utf-8'))
            for job in self.jobs:
                if job['status'] in ('Analyzing', 'Downloading', 'Merging', 'Processing', 'Paused', 'Stopping'):
                    job['status'] = 'Waiting'
            self.render_queue()
            self.load_queue_thumbnails()
        except (OSError, ValueError, KeyError, TypeError):
            self.jobs = []

    def load_queue_thumbnails(self):
        for url in {job.get('thumb_url', '') for job in self.jobs}:
            if not url.startswith(('http://', 'https://')) or url in self.thumbs or url in self.thumb_loading or url in self.thumb_pending:
                continue
            self.thumb_pending.append(url)
        self.pump_thumbnails()

    def pump_thumbnails(self):
        if self.closing:
            return
        while self.thumb_pending and len(self.thumb_loading) < 4:
            url = self.thumb_pending.pop(0)
            self.thumb_loading.add(url)
            def fetch(image_url=url):
                with urlopen(Request(image_url, headers={'User-Agent': 'MBQ-Media-Downloader/1.2'}), timeout=15) as response:
                    return response.read(5_000_000)
            def display(data, image_url=url):
                pix = QPixmap()
                if pix.loadFromData(data):
                    self.thumbs[image_url] = pix
                    self.render_queue()
            worker = FunctionWorker(fetch, self)
            worker.result.connect(display)
            worker.finished.connect(lambda image_url=url: self.finish_thumbnail(image_url))
            self.track(worker)

    def finish_thumbnail(self, url):
        self.thumb_loading.discard(url)
        self.pump_thumbnails()

    def selected_error(self):
        return '\n\n'.join(j.get('details', '') for j in self.selected_jobs()) or self.last_error or 'No error details.'

    def show_job_error(self):
        self.error('Selected download details', self.selected_error())

    def open_path(self, path, folder=False):
        if not path:
            self.error('No output file is available yet.')
            return
        file = Path(path)
        target = file.parent if folder else file
        if not target.exists():
            self.error('The file or folder no longer exists.', str(target))
            return
        if not folder and file.suffix.lower() not in {'.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.opus', '.wav', '.ogg', '.flac'}:
            self.error('This output is not a supported media file; open its containing folder instead.')
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve())))

    def open_job(self, folder=False):
        jobs = self.selected_jobs()
        if jobs:
            self.open_path(jobs[0].get('file'), folder)

    def refresh_history(self):
        rows = self.store.history(self.search.text())
        self.history_table.setRowCount(len(rows))
        if hasattr(self, 'history_count_label'):
            self.history_count_label.setText(f"{len(rows)} download{'s' if len(rows) != 1 else ''}")
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                self.history_table.setItem(row, col, QTableWidgetItem(str(value or '')))

    def clear_history(self):
        if QMessageBox.question(self, 'Clear history', 'Clear all history and the skip archive? Media files will remain on disk.') == QMessageBox.StandardButton.Yes:
            self.store.clear_history()
            self.refresh_history()

    def open_history(self, folder=False):
        row = self.history_table.currentRow()
        if row >= 0:
            self.open_path(self.history_table.item(row, 4).text(), folder)

    def default_application_settings(self):
        quality_default = QUALITIES[0][0] if QUALITIES else self.store.settings.get('quality', '')
        return {
            'folder': str((Path.home() / 'Downloads').resolve()),
            'theme': 'Dark',
            'quality': quality_default,
            'container': 'MP4',
            'audio': 'MP3',
            'browser': 'None',
            'languages': 'en',
            'template': '%(title)s.%(ext)s',
            'motion': True,
            'metadata': True,
            'thumbnail': True,
            'embed_subs': False,
            'write_subs': False,
            'auto_subs': False,
            'chapters': True,
            'playlist_folders': True,
            'skip': True,
            'concurrency': 2,
        }

    def reload_settings_controls(self):
        settings = self.store.settings
        if hasattr(self, 'folder'):
            self.folder.setText(settings.get('folder', str(Path.home() / 'Downloads')))

        for key, widget in getattr(self, 'settings_widgets', {}).items():
            value = settings.get(key)
            widget.blockSignals(True)
            if isinstance(widget, QComboBox):
                if value is not None and widget.findText(str(value)) >= 0:
                    widget.setCurrentText(str(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QSpinBox):
                try:
                    widget.setValue(int(value))
                except (TypeError, ValueError):
                    pass
            else:
                widget.setText('' if value is None else str(value))
            widget.blockSignals(False)

    def clear_app_cache(self, confirm=True):
        if confirm:
            answer = QMessageBox.question(
                self,
                'Clear MBQ cache',
                'Clear MBQ temporary/cache data?\\n\\n'
                'This removes cached thumbnails, disposable cache/temp folders and old log files.\\n'
                'Settings, queue, history and downloaded media files are preserved.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False

        self.thumbs.clear()
        self.thumb_pending.clear()
        self.thumb_loading.clear()

        removed = 0
        root = Path(self.store.root)

        # Rotating log backups are safe to delete. The active log can be locked on Windows,
        # so failure to remove it is harmless.
        for path in [root / 'mbq.log'] + [root / f'mbq.log.{i}' for i in range(1, 6)]:
            try:
                if path.is_file():
                    path.unlink()
                    removed += 1
            except OSError:
                pass

        for name in ('cache', '.cache', 'thumbnails', 'temp', 'tmp'):
            folder = root / name
            try:
                if folder.is_dir():
                    import shutil
                    shutil.rmtree(folder)
                    removed += 1
            except OSError:
                logging.exception('Could not remove cache directory: %s', folder)

        if hasattr(self, 'thumbnail'):
            self.thumbnail.clear()
            self.thumbnail.setText('VIDEO')

        if confirm:
            QMessageBox.information(
                self,
                'Cache cleared',
                f'MBQ cache cleared.\\n\\nRemoved {removed} cached/log item(s).\\n'
                'Downloaded media files were not touched.'
            )
        return True

    def reset_application_defaults(self, confirm=True):
        if self.active or self.analysis_worker or self.channel_workers:
            self.error('Finish or cancel active downloads/analysis before resetting MBQ.')
            return False

        if confirm:
            answer = QMessageBox.question(
                self,
                'Reset application defaults',
                'Restore MBQ settings and UI preferences to defaults?\\n\\n'
                'Download queue, history and downloaded media files will be preserved.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False

        defaults = self.default_application_settings()
        self.store.save_settings(defaults)

        # Legacy Qt UI state such as window state/geometry is local preference data.
        self.ui_settings.clear()

        self.reload_settings_controls()
        self.apply_theme()
        self.apply_motion()

        if hasattr(self, 'quality') and defaults['quality']:
            self.quality.setCurrentText(defaults['quality'])

        if confirm:
            QMessageBox.information(
                self,
                'Defaults restored',
                'MBQ settings were restored to defaults.\\n\\n'
                'Queue, history and downloaded media files were preserved.'
            )
        return True

    def reset_everything(self):
        if self.active or self.analysis_worker or self.channel_workers:
            self.error('Finish or cancel active downloads/analysis before using Reset Everything.')
            return

        answer = QMessageBox.warning(
            self,
            'Reset MBQ Media Downloader',
            'Return MBQ to a fresh-install state?\\n\\n'
            'This clears:\\n'
            '• Application settings and UI preferences\\n'
            '• Download queue\\n'
            '• Download history / skip archive\\n'
            '• Cached thumbnails, temporary data and logs\\n\\n'
            'YOUR DOWNLOADED MEDIA FILES WILL NOT BE DELETED.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.running = False
        self.stop_after_current = False
        self.jobs = []
        self.queue_selected_ids.clear()
        self.paused_job_status.clear()
        self.force_stopped_job_ids.clear()
        self.persist_queue()

        self.store.clear_history()
        self.clear_app_cache(confirm=False)
        self.reset_application_defaults(confirm=False)

        self.media.clear()
        self.current_info = None
        self.analysis_pending.clear()

        if hasattr(self, 'media_table'):
            self.media_table.setRowCount(0)
        if hasattr(self, 'history_table'):
            self.refresh_history()
        if hasattr(self, 'url_input'):
            self.url_input.clear()
        if hasattr(self, 'playlist_label'):
            self.playlist_label.setText('Single media / multiple URLs')

        self.reset_channel_media(cancel_workers=False)
        self.render_queue()

        QMessageBox.information(
            self,
            'Reset complete',
            'MBQ has been reset to a fresh-install state.\\n\\n'
            'Downloaded media files were preserved.\\n'
            'Restart MBQ once to reload every preference from the defaults.'
        )

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Default download folder', self.folder.text())
        if path:
            self.folder.setText(path)

    def save_settings(self):
        try:
            result = {'folder': str(Path(self.folder.text()).expanduser().resolve())}
            if not self.folder.text().strip():
                raise ValueError('Choose a download folder.')
            for key, widget in self.settings_widgets.items():
                if isinstance(widget, QComboBox):
                    result[key] = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    result[key] = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    result[key] = widget.value()
                else:
                    result[key] = widget.text()
            validate_template(result['template'])
            self.store.save_settings(result)
            self.apply_theme()
            self.apply_motion()
            self.quality.setCurrentText(result['quality'])
            self.change_mode(self.mode.currentText())
            self.statusBar().showMessage('Settings saved. New downloads will use these preferences.')
        except (OSError, ValueError) as exc:
            self.error(str(exc))

    def check_engine_ui(self):
        self.check_button.setEnabled(False)
        worker = FunctionWorker(check_engine, self)
        worker.result.connect(self.engine_status.setPlainText)
        worker.error.connect(self.error)
        worker.finished.connect(lambda: self.check_button.setEnabled(True))
        self.track(worker)

    def update_engine_ui(self):
        if self.active or self.analysis_worker or self.channel_workers:
            self.error('Wait for active downloads/analysis to finish, or cancel them, before updating the engine.')
            return
        self.update_button.setEnabled(False)
        self.engine_updating = True
        self.engine_status.setPlainText('Downloading official yt-dlp release and verifying checksum...')
        worker = FunctionWorker(update_engine, self)
        worker.result.connect(lambda message: self.statusBar().showMessage(message))
        worker.error.connect(self.error)
        worker.finished.connect(lambda: self.update_button.setEnabled(True))
        worker.finished.connect(lambda: setattr(self, 'engine_updating', False))
        worker.finished.connect(self.check_engine_ui)
        self.track(worker)

    def install_ffmpeg(self):
        import shutil
        folder = QFileDialog.getExistingDirectory(self, 'Select folder containing ffmpeg.exe AND ffprobe.exe')
        if not folder:
            return
        root = Path(folder)
        if not all((root / name).is_file() for name in ('ffmpeg.exe', 'ffprobe.exe')):
            self.error('Select the bin folder that contains both ffmpeg.exe and ffprobe.exe.')
            return
        if self.active:
            self.error('Wait for active downloads to finish before replacing FFmpeg.')
            return
        try:
            target = self.store.root / 'tools' / 'ffmpeg'
            target.mkdir(parents=True, exist_ok=True)
            for name in ('ffmpeg.exe', 'ffprobe.exe'):
                if (root / name).resolve() != (target / name).resolve():
                    shutil.copy2(root / name, target / name)
            self.check_engine_ui()
        except OSError as exc:
            self.error('Could not install local FFmpeg files.', str(exc))

    def view_log(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Technical log')
        dialog.resize(900, 600)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        def refresh():
            text.setPlainText(self.log_path.read_text('utf-8', errors='replace')[-200_000:] if self.log_path.exists() else 'No log entries yet.')
        refresh()
        layout.addWidget(text)
        row = QHBoxLayout()
        row.addWidget(button('Refresh', refresh))
        row.addWidget(button('Copy log', lambda: QApplication.clipboard().setText(text.toPlainText())))
        row.addWidget(button('Close', dialog.accept))
        layout.addLayout(row)
        dialog.exec()

    def closeEvent(self, event):
        # Do not destroy a running QThread. Cancel processes and defer close until
        # every worker exits; urllib and version probes have bounded timeouts.
        if self.workers:
            self.closing = True
            self.running = False
            self.analysis_pending.clear()
            for worker in list(self.workers):
                if isinstance(worker, ProcessWorker):
                    worker.cancel()
            self.statusBar().showMessage('Stopping background work before closing...')
            event.ignore()
            QTimer.singleShot(250, self.close)
            return
        self.persist_queue()
        self.store.db.close()
        event.accept()
