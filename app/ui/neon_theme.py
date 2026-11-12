"""MBQ theme: one stylesheet template + two token palettes (Dark / Light).

Every colour in the stylesheet comes from a token, so a new colour is added
in ONE place per theme (the DARK and LIGHT dicts) instead of being hand
mapped.  Painted widgets (neon.py) read the same palettes through palette().
"""
from string import Template

DARK = {
    # cinematic graphite surfaces
    'bg': '#05070a', 'bg_top': '#0a0e13',
    'sidebar': 'rgba(7, 9, 13, 248)', 'sidebar_border': '#242b33',
    'card': 'rgba(12, 16, 22, 242)', 'card_soft': 'rgba(15, 20, 27, 230)',
    'card_hi': 'rgba(17, 23, 31, 248)', 'card_dim': 'rgba(9, 12, 17, 204)',
    'field': '#0d1219', 'field_deep': '#090d12', 'hover': '#151c25',
    'btn': '#11171f', 'btn_hover': '#18212b', 'btn_pressed': '#0b1016',
    'select': '#14303a', 'select_soft': 'rgba(24, 54, 63, 210)',
    'hover_soft': 'rgba(20, 27, 35, 220)',
    # structural lines
    'border': '#252e38', 'border2': '#36414d', 'border_soft': '#1b222b',
    'field_border': '#303b47', 'field_border_h': '#526372',
    # typography
    'text': '#e5e9ef', 'text_strong': '#f8fafc', 'text2': '#aab3bf', 'text3': '#737f8e',
    'text4': '#525c69', 'text_btn': '#e7ebef',
    # MBQ signal system
    'accent': '#62e5f5', 'accent2': '#2d8cff', 'accent_text': '#8deef8', 'accent_hi': '#d1fbff',
    'accent_bg': '#10292e', 'accent_border': '#2b8794', 'eyebrow': '#8a98a8',
    'signal': '#ff7b22', 'signal_text': '#ff9a55', 'signal_bg': '#2a190e', 'signal_border': '#8f4d1f',
    'g1': '#72e6f2', 'g2': '#338fd9', 'g3': '#18527e',
    'g1h': '#91eef7', 'g2h': '#4ba5ea', 'g3h': '#236899',
    'on_accent': '#061015', 'select_text': '#ffffff',
    # states
    'danger_bg': '#2b151a', 'danger_border': '#6d303b', 'danger_text': '#ff9aaa', 'danger_h': '#381a22',
    'ok_text': '#72dcb4', 'ok_bg': '#102921', 'ok_border': '#2a6a54',
    'err_text': '#ff9aaa', 'err_bg': '#32171f', 'err_border': '#79404f', 'err_card': 'rgba(49, 20, 31, 190)',
    'cancel_text': '#d3b5ff', 'cancel_bg': '#261d34', 'cancel_border': '#5f4b7d',
    'disabled_text': '#65717f', 'disabled_bg': '#121820', 'disabled_border': '#29323c',
    'disabled_accent': '#20343a', 'disabled_accent_text': '#718d92',
    # misc
    'progress_bg': '#111820', 'scroll': '#35404b', 'scroll_h': '#4b5a67',
    'check_bg': '#0b1016', 'check_border': '#52606c', 'tip_bg': '#11161d',
    'table_bg': '#0a0f15', 'table_alt': '#0e141b', 'table_head': '#111821',
    'console': '#080c11', 'status_bg': '#080c11', 'win_hover': 'rgba(255,255,255,20)',
    'win_close': '#e64858',
}

LIGHT = {
    # editorial paper / studio-light counterpart
    'bg': '#f4f1ec', 'bg_top': '#faf8f4',
    'sidebar': 'rgba(249, 247, 243, 250)', 'sidebar_border': '#d1ccc4',
    'card': 'rgba(255, 255, 255, 238)', 'card_soft': 'rgba(250, 248, 244, 235)',
    'card_hi': 'rgba(255, 255, 255, 250)', 'card_dim': 'rgba(244, 241, 236, 215)',
    'field': '#ffffff', 'field_deep': '#f1efeb', 'hover': '#ece8e2',
    'btn': '#ffffff', 'btn_hover': '#f0ede8', 'btn_pressed': '#e6e1da',
    'select': '#d9eef1', 'select_soft': 'rgba(221, 239, 241, 235)',
    'hover_soft': 'rgba(238, 234, 228, 235)',
    'border': '#d6d0c8', 'border2': '#bab3aa', 'border_soft': '#e6e1da',
    'field_border': '#c9c2b9', 'field_border_h': '#918a82',
    'text': '#25282c', 'text_strong': '#0c0e11', 'text2': '#555d66', 'text3': '#77808a',
    'text4': '#969da5', 'text_btn': '#22272c',
    'accent': '#159db1', 'accent2': '#276fb4', 'accent_text': '#087d8c', 'accent_hi': '#075e69',
    'accent_bg': '#dff2f3', 'accent_border': '#54aeba', 'eyebrow': '#6a727b',
    'signal': '#e76016', 'signal_text': '#b7470d', 'signal_bg': '#fff0e5', 'signal_border': '#e4a373',
    'g1': '#36b9c9', 'g2': '#3e86c2', 'g3': '#28587f',
    'g1h': '#4fc5d3', 'g2h': '#5598cf', 'g3h': '#386d94',
    'on_accent': '#ffffff', 'select_text': '#182126',
    'danger_bg': '#fdebee', 'danger_border': '#eeb6c0', 'danger_text': '#b12f46', 'danger_h': '#f8dce2',
    'ok_text': '#176a4b', 'ok_bg': '#e5f3ed', 'ok_border': '#a7d3c0',
    'err_text': '#b12f46', 'err_bg': '#fcebed', 'err_border': '#eeb6c0', 'err_card': 'rgba(252, 235, 237, 235)',
    'cancel_text': '#68449c', 'cancel_bg': '#f0e9f8', 'cancel_border': '#cab9df',
    'disabled_text': '#8a9299', 'disabled_bg': '#e9e5df', 'disabled_border': '#d1cbc3',
    'disabled_accent': '#dce8e8', 'disabled_accent_text': '#74898b',
    'progress_bg': '#e5e1da', 'scroll': '#bbb4ac', 'scroll_h': '#918a82',
    'check_bg': '#ffffff', 'check_border': '#9d958d', 'tip_bg': '#ffffff',
    'table_bg': '#ffffff', 'table_alt': '#f7f5f1', 'table_head': '#efebe5',
    'console': '#f7f5f1', 'status_bg': '#efebe5', 'win_hover': 'rgba(20,20,20,16)',
    'win_close': '#df4251',
}

QSS = Template(r'''
QWidget {
    background: transparent;
    color: $text;
    font-family: "Segoe UI Variable Text", "Segoe UI";
    font-size: 10pt;
}
QMainWindow { background: $bg; }
QLabel#title { font-size: 25pt; font-weight: 800; color: $text_strong; }
QLabel#muted { color: $text2; }
QLabel#eyebrow { color: $eyebrow; font-size: 8pt; font-weight: 700; letter-spacing: 1.4px; }
QLabel#sidebarFooter { color: $text3; font-size: 8pt; }

/* ---- Shell: sidebar, header, window controls ------------------------- */
QWidget#sidebar { background: $sidebar; border-right: 1px solid $sidebar_border; }
QListWidget#nav { background: transparent; border: none; padding: 0px; outline: none; }
QListWidget#nav::item {
    min-height: 26px; padding: 9px 12px; margin: 3px 0; border-radius: 10px;
    color: $text2; border: 1px solid transparent; font-weight: 600;
}
QListWidget#nav::item:hover { background: $hover_soft; color: $text_strong; }
QListWidget#nav::item:selected { background: transparent; color: $text_strong; border: 1px solid transparent; }
QPushButton#sidebarAbout {
    background: transparent; border: none; color: $text3; font-size: 8pt; font-weight: 600;
    text-align: left; padding: 4px 6px; min-height: 0px;
}
QPushButton#sidebarAbout:hover { color: $accent_text; background: transparent; }
QWidget#headerBar { background: transparent; }
QLabel#headerTitle { color: $text_strong; background: transparent; }
QLabel#headerSub { color: $text2; font-size: 12pt; background: transparent; }

/* ---- Home cards -------------------------------------------------------- */
QWidget#mediaCard { background: $card; border: 1px solid $border; border-radius: 14px; }
QWidget#analyzerCard, QWidget#mediaProfileCard { background: $card; border: 1px solid $border; border-radius: 14px; }
QWidget#playlistPanel { background: $card_dim; border: 1px solid $border_soft; border-radius: 11px; }
QWidget#segmentGroup { background: $card_dim; border: 1px solid $border; border-radius: 12px; }
QPlainTextEdit#urlInput { background: $field; border: 1px solid $field_border; border-radius: 11px; padding: 11px 14px; font-size: 10.5pt; }
QPlainTextEdit#urlInput:focus { border: 1px solid $accent; background: $field; }
QPushButton#analyzePrimary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $g1,stop:.52 $g2,stop:1 $g3);
    border: 1px solid $accent_hi; border-radius: 11px; color: $on_accent;
    font-size: 10.5pt; font-weight: 800; padding: 0 22px;
}
QPushButton#analyzePrimary:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $g1h,stop:1 $g3h); border-color: $accent_hi; }
QPushButton#analyzePrimary:disabled { background: $disabled_accent; color: $disabled_accent_text; border-color: $disabled_border; }
QPushButton#chip { background: $card_soft; border: 1px solid $field_border; border-radius: 10px; padding: 7px 14px; color: $text_btn; }
QPushButton#chip:hover { border-color: $accent; color: $text_strong; background: $hover; }
QPushButton#segment { background: transparent; border: 1px solid transparent; border-radius: 9px; padding: 8px 14px; min-width: 62px; color: $text2; font-weight: 700; }
QPushButton#segment:hover { color: $text_strong; background: $hover_soft; }
QPushButton#segment:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0d84e8,stop:1 $accent2);
    border: 1px solid $accent; color: #ffffff;
}
QLabel#mediaThumbnail { background: $field_deep; border: 1px solid $border2; border-radius: 10px; color: $accent; font-size: 20pt; font-weight: 800; }
QLabel#mediaTitle { color: $text_strong; font-size: 15pt; font-weight: 800; }
QLabel#mediaCreator { color: $text; font-size: 10.5pt; font-weight: 600; }
QLabel#mediaMeta { color: $text2; font-size: 9.5pt; }
QLabel#formatHint { color: $text3; font-size: 8.5pt; }

/* ---- Buttons ------------------------------------------------------------ */
QPushButton {
    min-height: 18px; background: $btn; border: 1px solid $field_border; border-radius: 10px;
    padding: 8px 14px; color: $text_btn; font-weight: 600;
}
QPushButton:hover { background: $btn_hover; border-color: $field_border_h; color: $text_strong; }
QPushButton:pressed { background: $btn_pressed; border-color: $border2; }
QPushButton:checked { background: $accent_bg; border-color: $accent; color: $accent_text; }
QPushButton:disabled { color: $disabled_text; background: $disabled_bg; border-color: $disabled_border; }
QPushButton#primary {
    min-height: 22px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $g1,stop:.44 $g2,stop:1 $g3);
    border: 1px solid $accent_hi; border-radius: 11px; color: $on_accent; padding: 10px 20px; font-weight: 800;
}
QPushButton#primary:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $g1h,stop:.48 $g2h,stop:1 $g3h); border-color: $accent_hi; }
QPushButton#primary:pressed { background: $g2; }
QPushButton#primary:disabled { background: $disabled_accent; color: $disabled_accent_text; border-color: $disabled_border; }
QPushButton#ghost { background: transparent; border: 1px solid transparent; border-radius: 9px; padding: 7px 12px; color: $text2; }
QPushButton#ghost:hover { background: $hover; border-color: $border2; color: $text_strong; }
QPushButton#danger { background: $danger_bg; border-color: $danger_border; color: $danger_text; }
QPushButton#danger:hover { background: $danger_h; border-color: $danger_text; color: $danger_text; }

/* ---- Inputs ------------------------------------------------------------ */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background: $field; border: 1px solid $field_border; border-radius: 10px;
    padding: 8px 10px; color: $text; selection-background-color: $select;
    selection-color: $select_text;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover, QSpinBox:hover { border-color: $field_border_h; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: $accent; }
QComboBox { padding-right: 26px; }
QComboBox QAbstractItemView { background: $tip_bg; border: 1px solid $border2; selection-background-color: $select; selection-color: $select_text; outline: none; }

/* ---- Tables ------------------------------------------------------------- */
QTableWidget { background: $table_bg; alternate-background-color: $table_alt; border: 1px solid $border; gridline-color: transparent; border-radius: 11px; outline: none; }
QTableWidget::item { padding: 7px; border-bottom: 1px solid $border_soft; color: $text; }
QTableWidget::item:selected { background: $select; color: $select_text; }
QHeaderView::section { background: $table_head; color: $text2; border: none; border-bottom: 1px solid $border; padding: 9px; font-size: 8pt; font-weight: 700; }

/* ---- Progress ----------------------------------------------------------- */
QProgressBar { border: 1px solid $border; background: $progress_bg; border-radius: 5px; text-align: center; min-height: 8px; max-height: 20px; color: $text; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $g1,stop:1 $accent2); border-radius: 4px; }

/* ---- Lists & checkboxes ------------------------------------------------- */
QListWidget { background: transparent; border: none; padding: 5px 7px; outline: none; }
QListWidget::item { min-height: 28px; padding: 10px 12px; margin: 3px 0; border-radius: 10px; color: $text2; border: 1px solid transparent; }
QListWidget::item:selected { background: $select_soft; color: $text_strong; border: 1px solid $border2; }
QListWidget::item:hover { background: $hover_soft; color: $text_strong; }
QCheckBox { spacing: 9px; padding: 4px; color: $text; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid $check_border; border-radius: 4px; background: $check_bg; }
QCheckBox::indicator:hover { border-color: $accent; }
QCheckBox::indicator:checked { background: $accent; border-color: $accent_hi; }

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: $scroll; min-height: 30px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: $scroll_h; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background: transparent; height: 9px; }
QScrollBar::handle:horizontal { background: $scroll; min-width: 30px; border-radius: 4px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---- Channel extractor -------------------------------------------------- */
QWidget#extractorCard { background: $card; border: 1px solid $border; border-radius: 15px; }
QWidget#extractorProfile { background: $card_soft; border: 1px solid $border; border-radius: 13px; }
QLabel#channelName { color: $text_strong; font-size: 16pt; font-weight: 800; }
QLabel#channelMeta { color: $text2; font-size: 9.5pt; }
QLabel#channelScanText { color: $text3; font-size: 8.5pt; }
QLabel#progressHint { color: $accent_text; font-size: 7.5pt; font-weight: 800; letter-spacing: 1px; }
QWidget#statCard { min-width: 120px; background: $card_soft; border: 1px solid $border2; border-radius: 11px; }
QLabel#statLabel { color: $text3; font-size: 7.5pt; font-weight: 800; letter-spacing: .8px; }
QLabel#statValue { color: $text_strong; font-size: 17pt; font-weight: 800; }
QPushButton#outlineAction { background: $card_soft; border: 1px solid $accent_border; border-radius: 9px; color: $accent_text; font-size: 8pt; font-weight: 800; padding: 8px 13px; }
QPushButton#outlineAction:hover { border-color: $accent; background: $accent_bg; color: $text_strong; }
QLineEdit#channelSearch { min-height: 20px; background: $field_deep; border-color: $field_border; }
QWidget#extractorListPanel { background: $card_soft; border: 1px solid $border; border-radius: 12px; }
QLabel#listSectionTitle { color: $text2; font-size: 9pt; font-weight: 800; letter-spacing: .7px; }
QTableWidget#extractorTable { background: transparent; alternate-background-color: $hover_soft; border: none; border-radius: 8px; }
QTableWidget#extractorTable::item { padding: 7px; border-bottom: 1px solid $border_soft; }
QTableWidget#extractorTable QHeaderView::section { background: $table_head; color: $text3; border-bottom: 1px solid $border; padding: 7px; }
QWidget#extractorActionBar { background: $card_hi; border: 1px solid $border2; border-radius: 12px; }
QLabel#selectedSummary { color: $text; font-size: 11pt; font-weight: 700; }

/* ---- Persistent download footer ----------------------------------------- */
QWidget#downloadFooter { background: $card_hi; border: 1px solid $border2; border-radius: 14px; }
QLabel#footerSummary { color: $text; font-size: 10.5pt; font-weight: 700; }
QLabel#footerChannelSummary { color: $text_strong; font-size: 12pt; font-weight: 800; }
QWidget#footerDivider { background: $border; border: none; }
QWidget#footerControls { background: transparent; border: none; }
QLabel#footerControlLabel { color: $text3; font-size: 8.5pt; font-weight: 700; }
QPushButton#footerPrimary {
    min-width: 220px; min-height: 28px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $g1,stop:.46 $g2,stop:1 $g3);
    border: 1px solid $accent_hi; border-radius: 12px; color: $on_accent; padding: 10px 22px; font-size: 10.5pt; font-weight: 800;
}
QPushButton#footerPrimary:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $g1h,stop:.5 $g2h,stop:1 $g3h); border-color: $accent_hi; }
QPushButton#footerPrimary:disabled { background: $disabled_accent; color: $disabled_accent_text; border-color: $disabled_border; }
QComboBox#bulkQuality { min-width: 145px; min-height: 28px; background: $field; border-color: $field_border; font-weight: 700; }

/* ---- Downloads workspace ------------------------------------------------ */
QWidget#queueControlCard { background: $card_hi; border: 1px solid $border2; border-radius: 14px; }
QLabel#queueSummary { color: $text2; font-size: 9pt; font-weight: 600; }
QWidget#queueStat { background: $card_soft; border: 1px solid $border; border-radius: 12px; }
QLabel#queueStatValue { color: $text_strong; font-size: 18pt; font-weight: 800; }
QLabel#queueStatLabel { color: $text3; font-size: 8pt; font-weight: 800; letter-spacing: 1px; }
QWidget#queueToolbar { background: $card; border: 1px solid $border; border-radius: 12px; }
QPushButton#queueFilter { background: transparent; border: 1px solid transparent; border-radius: 8px; color: $text2; padding: 7px 12px; font-weight: 700; }
QPushButton#queueFilter:hover { color: $text_strong; background: $hover; border-color: $border; }
QPushButton#queueFilter:checked { color: $accent_text; background: $accent_bg; border-color: $accent_border; }
QScrollArea#queueScroll { background: transparent; border: none; }
QWidget#queueList { background: transparent; }
QWidget#queueCard, QWidget#queueCardActive, QWidget#queueCardCompleted, QWidget#queueCardFailed { background: $card_soft; border: 1px solid $border; border-radius: 13px; }
QWidget#queueCardActive { border-color: $accent_border; background: $card; }
QWidget#queueCardCompleted { border-color: $border2; }
QWidget#queueCardFailed { border-color: $err_border; background: $err_card; }
QLabel#queueThumb { background: $table_head; border: 1px solid $field_border; border-radius: 9px; color: $text3; font-size: 8pt; font-weight: 800; }
QLabel#queueJobTitle { color: $text_strong; font-size: 10.5pt; font-weight: 800; }
QLabel#queueJobMeta { color: $text3; font-size: 8.5pt; }
QLabel#queueMetrics { color: $text3; font-size: 8pt; }
QLabel#queuePercent { color: $text2; font-size: 8pt; font-weight: 800; }
QLabel#queueIndex { color: $text4; font-size: 8pt; font-weight: 700; }
QProgressBar#queueProgress { min-height: 7px; max-height: 7px; border: none; background: $progress_bg; border-radius: 3px; text-align: center; }
QProgressBar#queueProgress::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $g1,stop:.55 $g2,stop:1 $g3); border-radius: 3px; }
QCheckBox#queueCheck { padding: 0px; spacing: 0px; }
QCheckBox#queueCheck::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid $field_border_h; background: $field_deep; }
QCheckBox#queueCheck::indicator:checked { background: $accent; border-color: $accent_hi; }
QLabel#statusActive, QLabel#statusCompleted, QLabel#statusFailed, QLabel#statusCancelled, QLabel#statusWaiting { padding: 5px 9px; border-radius: 8px; font-size: 7.5pt; font-weight: 800; }
QLabel#statusActive { color: $accent_text; background: $accent_bg; border: 1px solid $accent_border; }
QLabel#statusCompleted { color: $ok_text; background: $ok_bg; border: 1px solid $ok_border; }
QLabel#statusFailed { color: $err_text; background: $err_bg; border: 1px solid $err_border; }
QLabel#statusCancelled { color: $cancel_text; background: $cancel_bg; border: 1px solid $cancel_border; }
QLabel#statusWaiting { color: $text2; background: $table_head; border: 1px solid $field_border; }
QWidget#queueEmpty { background: $card_dim; border: 1px dashed $field_border; border-radius: 14px; }
QLabel#queueEmptyIcon { color: $field_border_h; font-size: 25pt; font-weight: 800; }
QLabel#queueEmptyTitle { color: $text; font-size: 12pt; font-weight: 800; }

/* ---- Secondary workspaces ------------------------------------------------ */
QWidget#sectionCard, QWidget#engineCard, QWidget#settingsCard { background: $card; border: 1px solid $border; border-radius: 14px; }
QWidget#engineCard { border-color: $border2; background: $card_hi; }
QLabel#sectionTitle { color: $eyebrow; font-size: 8.5pt; font-weight: 800; letter-spacing: 1.3px; }
QLabel#sectionHint { color: $text3; font-size: 8.5pt; }
QLabel#advancedMediaLabel { color: $text; font-size: 11pt; font-weight: 700; }
QLineEdit#historySearch { min-height: 28px; }
QTableWidget#premiumTable { background: $table_bg; alternate-background-color: $table_alt; border: 1px solid $border; border-radius: 10px; gridline-color: $border_soft; }
QTableWidget#premiumTable::item { padding: 7px; border-bottom: 1px solid $border_soft; }
QTableWidget#premiumTable::item:selected { background: $select; color: $select_text; }
QTableWidget#premiumTable QHeaderView::section { background: $table_head; color: $text2; border: none; border-bottom: 1px solid $border; padding: 9px; font-size: 8pt; font-weight: 800; }
QLabel#engineBadge { color: $accent_text; background: $accent_bg; border: 1px solid $accent_border; border-radius: 8px; padding: 5px 9px; font-size: 8pt; font-weight: 800; }
QPlainTextEdit#engineStatus { background: $console; border: 1px solid $border; border-radius: 10px; padding: 10px; color: $text; font-family: "Consolas"; font-size: 9pt; }
QScrollArea#settingsScroll { background: transparent; border: none; }
QWidget#settingsCard QLabel { background: transparent; }
QWidget#settingsCard QLineEdit, QWidget#settingsCard QComboBox, QWidget#settingsCard QSpinBox { min-height: 28px; }
QWidget#settingsSaveBar { background: $card_hi; border: 1px solid $border2; border-radius: 13px; }

QToolTip, QDialog, QMessageBox { background: $tip_bg; color: $text; }
QToolTip { border: 1px solid $border2; padding: 6px; }
QStatusBar { background: transparent; border: none; color: $text3; font-size: 8pt; }
QStatusBar::item { border: none; }

/* ========================================================================
   MBQ CINEMATIC MEDIA CONSOLE / CYBER EDITORIAL OVERRIDE
   ======================================================================== */
QWidget { font-family: "Segoe UI Variable Text", "Segoe UI"; }
QWidget#sidebar { background: $sidebar; border-right: 1px solid $sidebar_border; }
QListWidget#nav::item {
    min-height: 27px; padding: 10px 11px; margin: 2px 0; border-radius: 4px;
    color: $text2; border: none; font-weight: 650;
}
QListWidget#nav::item:hover { background: $hover_soft; color: $text_strong; }
QListWidget#nav::item:selected { background: transparent; color: $text_strong; }
QLabel#headerTitle { color: $text_strong; letter-spacing: .4px; }
QLabel#headerSub { color: $text3; font-family: "Consolas"; font-size: 8pt; letter-spacing: .8px; }

/* Hero / signature console */
QWidget#heroDeck {
    background: $card_dim; border: 1px solid $border2; border-radius: 8px;
}
QWidget#heroCopyPane { background: transparent; border: none; }
QLabel#heroKicker {
    color: $signal_text; font-family: "Consolas"; font-size: 8pt; font-weight: 800; letter-spacing: 1.7px;
}
QLabel#heroTitle {
    color: $text_strong; font-family: "Segoe UI Variable Display", "Segoe UI";
    font-size: 30pt; font-weight: 900; letter-spacing: -.4px;
}
QLabel#heroBody { color: $text2; font-size: 10pt; }
QLabel#heroState {
    color: $accent_text; font-family: "Consolas"; font-size: 8pt; font-weight: 800; letter-spacing: 1px;
}
QLabel#heroIndex { color: $text4; font-family: "Consolas"; font-size: 7.5pt; font-weight: 800; }
QWidget#sourceCommand {
    background: $field_deep; border: 1px solid $field_border; border-left: 3px solid $signal;
    border-radius: 5px;
}
QPlainTextEdit#urlInput {
    background: transparent; border: none; border-radius: 0px; padding: 8px 10px;
    font-family: "Segoe UI Variable Text", "Segoe UI"; font-size: 10.5pt;
}
QPlainTextEdit#urlInput:focus { border: none; background: transparent; }
QPushButton#analyzePrimary {
    background: $accent; border: 1px solid $accent_hi; border-radius: 4px; color: $on_accent;
    font-size: 9.5pt; font-weight: 900; padding: 0 22px;
}
QPushButton#analyzePrimary:hover { background: $accent_hi; color: $bg; border-color: $accent_hi; }
QWidget#analysisProgressWrap { background: transparent; border: none; }
QProgressBar#analysisProgress, QProgressBar#channelProgress {
    min-height: 10px; max-height: 14px; border: none; border-radius: 2px;
    background: $progress_bg; color: $text_strong; font-family: "Consolas"; font-size: 7pt; font-weight: 800;
}
QProgressBar#analysisProgress::chunk, QProgressBar#channelProgress::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $accent,stop:.7 $accent2,stop:1 $signal);
    border-radius: 2px;
}

/* Live instrumentation strip */
QWidget#liveStrip { background: $card; border: 1px solid $border; border-radius: 5px; }
QWidget#liveCell { border-right: 1px solid $border_soft; }
QLabel#liveCaption { color: $text4; font-family: "Consolas"; font-size: 7pt; font-weight: 800; letter-spacing: 1px; }
QLabel#liveValue { color: $text_strong; font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 13pt; font-weight: 850; }
QLabel#liveValueSignal { color: $signal_text; font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 13pt; font-weight: 850; }

/* Media profile is a workstation deck, not a floating SaaS card. */
QWidget#mediaProfileCard {
    background: $card; border: 1px solid $border; border-left: 3px solid $accent; border-radius: 6px;
}
QLabel#mediaDeckKicker, QLabel#stackKicker, QLabel#channelDeckKicker {
    color: $text3; font-family: "Consolas"; font-size: 7.5pt; font-weight: 800; letter-spacing: 1.3px;
}
QLabel#mediaTitle { color: $text_strong; font-size: 17pt; font-weight: 850; }
QLabel#mediaCreator { color: $signal_text; font-size: 9pt; font-weight: 750; }
QLabel#mediaMeta { color: $text3; font-family: "Consolas"; font-size: 8pt; }
QLabel#mediaThumbnail { background: $field_deep; border: 1px solid $border2; border-radius: 4px; color: $text4; }
QWidget#segmentGroup { background: $field_deep; border: 1px solid $border; border-radius: 4px; }
QPushButton#segment { border-radius: 3px; }
QWidget#playlistPanel { background: $card_dim; border: 1px solid $border; border-radius: 5px; }

/* Channel / creator signal deck */
QWidget#extractorCard { background: $card; border: 1px solid $border2; border-left: 3px solid $signal; border-radius: 6px; }
QWidget#extractorProfile { background: $card_soft; border: 1px solid $border; border-radius: 4px; }
QWidget#statCard { background: $field_deep; border: 1px solid $border; border-radius: 4px; }
QWidget#extractorListPanel { background: $card_dim; border: 1px solid $border; border-radius: 4px; }
QLineEdit#channelSearch { border-radius: 4px; }
QPushButton#outlineAction { border-radius: 4px; }

/* Persistent action rail */
QWidget#downloadFooter {
    background: $card_hi; border: 1px solid $border2; border-top: 2px solid $signal; border-radius: 6px;
}
QPushButton#footerPrimary {
    background: $accent; border: 1px solid $accent_hi; border-radius: 4px; color: $on_accent;
    padding: 10px 22px; font-size: 10pt; font-weight: 900;
}
QPushButton#footerPrimary:hover { background: $accent_hi; color: $bg; }

/* Queue becomes a transfer console. */
QWidget#queueControlCard { background: $card_hi; border: 1px solid $border2; border-left: 3px solid $signal; border-radius: 6px; }
QLabel#queueDeckKicker { color: $signal_text; font-family: "Consolas"; font-size: 8pt; font-weight: 800; letter-spacing: 1.5px; }
QLabel#queueStateWord { color: $text_strong; font-size: 24pt; font-weight: 900; }
QLabel#queueSummary { color: $text3; font-family: "Consolas"; font-size: 8pt; font-weight: 600; }
QWidget#queueStat { background: $card_dim; border: 1px solid $border; border-radius: 4px; }
QLabel#queueStatValue { color: $text_strong; font-size: 21pt; font-weight: 900; }
QLabel#queueStatLabel { color: $text4; font-family: "Consolas"; font-size: 7pt; font-weight: 800; letter-spacing: 1px; }
QWidget#queueToolbar { background: $card_dim; border: 1px solid $border; border-radius: 4px; }
QPushButton#queueFilter { border-radius: 3px; }
QWidget#queueCard, QWidget#queueCardActive, QWidget#queueCardCompleted, QWidget#queueCardFailed {
    background: $card_soft; border: 1px solid $border; border-radius: 5px;
}
QWidget#queueCardActive { border-left: 3px solid $accent; }
QWidget#queueCardCompleted { border-left: 3px solid $ok_border; }
QWidget#queueCardFailed { border-left: 3px solid $err_border; }
QLabel#queueThumb { border-radius: 3px; }
QProgressBar#queueProgress { border-radius: 1px; }
QProgressBar#queueProgress::chunk { border-radius: 1px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 $accent,stop:.82 $accent2,stop:1 $signal); }

/* Keep the rest of the application consistent without turning every surface into a pill. */
QWidget#sectionCard, QWidget#engineCard, QWidget#settingsCard { border-radius: 6px; }
QWidget#settingsSaveBar { border-radius: 5px; border-top: 2px solid $signal; }
QPushButton#primary, QPushButton#ghost, QPushButton#chip { border-radius: 4px; }
QPushButton#primary {
    background: $accent; color: $on_accent; border: 1px solid $accent_hi;
    font-weight: 900;
}
QPushButton#primary:hover { background: $accent_hi; color: $bg; border-color: $accent_hi; }
QPushButton#primary:pressed { background: $accent2; color: #ffffff; }
QComboBox, QLineEdit, QPlainTextEdit, QSpinBox { border-radius: 4px; }
QTableWidget#premiumTable { border-radius: 4px; }

''')


def palette(theme):
    """Token dict for 'Dark' / 'Light' (copy, safe to mutate)."""
    return dict(LIGHT if theme == 'Light' else DARK)


def stylesheet(theme):
    return QSS.safe_substitute(palette(theme))


STYLE = stylesheet('Dark')
