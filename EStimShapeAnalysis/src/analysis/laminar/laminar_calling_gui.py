"""
Laminar calling GUI: one session at a time, call each channel superficial / middle (L4) /
deep / white matter / sulcus-out / unsure, and save the calls to LaminarCalls.

Left figure, depth increasing downward:
    Whole drive   PenetrationMetrics along the entire penetration (gamma and alpha-beta
                  band power, MUA rate, each scaled 0-1), with the ephys tissue model
                  (most likely of wm / gm / sulcus) and the MRI segmentation as strips.
                  The final probe span is shaded; nearest WM / sulcus above and below it
                  are listed in the side panel.
    CSD           GA stimulus-onset CSD at the final position (sinks red), from
                  laminar_profiles.py.
    Band power    relative alpha-beta and gamma per channel.
    Calls         one box per channel coloured by its class; EStim contacts outlined.
Right: MRI on the plane holding the trajectory (rotate it about the probe with the slider),
gray / white segmentation outlined, channels coloured by call, EStim contacts larger.

Calling: drag over the Calls column (or any probe-span panel) to select channels, then
press a class button or its number key (1-6). "Reset to suggestions" refills the calls from
the strongest CSD sink (or the gamma / alpha-beta crossover), the tissue model and the MRI
probe angle (see laminar_core.suggest_classes). Nothing is written until "Save calls".

Run laminar_profiles.py first for every session you want to call. Edit the settings at
the top of main(), then run.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parents[3]))

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.widgets import SpanSelector
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPushButton, QShortcut, QSlider, QSplitter,
                             QVBoxLayout, QWidget)
from PyQt5.QtGui import QKeySequence

from src.analysis.laminar.laminar_core import (
    CHANNEL_SPACING_UM, CLASS_COLORS, CLASS_LABELS, LAMINAR_CLASSES, channel_name, suggest_classes,
)
from src.analysis.laminar.laminar_mri import SEG_CSF, SEG_GM, SEG_WM, nearest_runs

TISSUE_COLORS = {'gm': '#8c8c8c', 'wm': '#f0f0f0', 'sulcus': '#3a87c8'}
SEG_TO_TISSUE = {SEG_CSF: 'sulcus', SEG_GM: 'gm', SEG_WM: 'wm'}


def main():
    # ---------------------------------------------------------------- settings
    MRI_CONFIG_PATH = str(Path(__file__).parents[2] / 'mri' / 'mri_viewer_config.json')
    CORRECTIONS_FILE = None          # an opt_*.json, or None = the MRI viewer's current corrections
    USE_TISSUE_MODEL = True          # fit the ephys tissue model (PIPE_AA_K3) for the whole-drive strip
    MIDDLE_FROM = 'sink'             # suggested L4: 'sink' (strongest CSD sink) or 'crossover' (gamma/alpha-beta)
    MIDDLE_HALF_WIDTH_UM = 100       # suggested middle = this far above and below the L4 marker
    STEEP_ANGLE_DEG = 45             # flag sessions whose probe is this far from the cortical normal
    START_SESSION = None             # e.g. "260702_0"; None = first session in LaminarSessions
    FONT_SIZE = 11
    # -------------------------------------------------------------------------
    from src.analysis.laminar.laminar_db import LaminarDBSource
    pipeline = None
    if USE_TISSUE_MODEL:
        from src.analysis.penetrations.run_pooled import PIPE_AA_K3
        pipeline = PIPE_AA_K3
    source = LaminarDBSource(MRI_CONFIG_PATH, CORRECTIONS_FILE, tissue_pipeline=pipeline)
    run_gui(source, middle_from=MIDDLE_FROM, middle_half_width_um=MIDDLE_HALF_WIDTH_UM,
            steep_angle_deg=STEEP_ANGLE_DEG, start_session=START_SESSION, font_size=FONT_SIZE)


def run_gui(source, **kwargs):
    app = QApplication.instance() or QApplication(sys.argv)
    win = LaminarCallingWindow(source, **kwargs)
    win.resize(1700, 950)
    win.show()
    app.exec_()
    return win


class LaminarCallingWindow(QMainWindow):
    def __init__(self, source, middle_from='sink', middle_half_width_um=100.0, steep_angle_deg=45.0,
                 start_session=None, font_size=11):
        super().__init__()
        self.source = source
        self.middle_from = middle_from
        self.middle_half_width_um = middle_half_width_um
        self.steep_angle_deg = steep_angle_deg
        self.font_size = font_size
        self.setWindowTitle('Laminar calls')
        self.sid = None
        self.calls: Dict[int, str] = {}
        self.selected: List[int] = []
        self.dirty = False

        # ---------------- top bar
        self.session_box = QComboBox()
        self.session_box.addItems(self.source.sessions())
        self.session_box.currentTextChanged.connect(self._on_session_changed)
        prev_btn, next_btn = QPushButton('◀'), QPushButton('▶')
        prev_btn.clicked.connect(lambda: self._step_session(-1))
        next_btn.clicked.connect(lambda: self._step_session(1))
        refresh_btn = QPushButton('Refresh sessions')
        refresh_btn.clicked.connect(self._refresh_sessions)
        reset_btn = QPushButton('Reset to suggestions')
        reset_btn.clicked.connect(self._reset_to_suggestions)
        save_btn = QPushButton('Save calls')
        save_btn.clicked.connect(self._save)
        self.status = QLabel('')
        top = QHBoxLayout()
        for w in (QLabel('Session'), self.session_box, prev_btn, next_btn, refresh_btn, reset_btn, save_btn):
            top.addWidget(w)
        top.addWidget(self.status, 1)

        # ---------------- class buttons
        cls_row = QHBoxLayout()
        cls_row.addWidget(QLabel('Set selected to:'))
        for i, cls in enumerate(LAMINAR_CLASSES):
            b = QPushButton(f'{i + 1}  {CLASS_LABELS[cls]}')
            b.setStyleSheet(f'background-color: {CLASS_COLORS[cls]}; color: '
                            f'{"white" if cls in ("middle", "deep", "sulcus") else "black"};')
            b.clicked.connect(lambda _, c=cls: self._apply_class(c))
            cls_row.addWidget(b)
            QShortcut(QKeySequence(str(i + 1)), self, activated=lambda c=cls: self._apply_class(c))
        self.sel_label = QLabel('No channels selected')
        cls_row.addWidget(self.sel_label, 1)

        # ---------------- profile figure
        self.prof_fig = Figure(figsize=(11, 8))
        self.prof_canvas = FigureCanvasQTAgg(self.prof_fig)
        prof_box = QVBoxLayout()
        prof_box.addWidget(NavigationToolbar2QT(self.prof_canvas, self))
        prof_box.addWidget(self.prof_canvas)
        prof_w = QWidget()
        prof_w.setLayout(prof_box)

        # ---------------- MRI figure + controls + info
        self.mri_fig = Figure(figsize=(6, 6))
        self.mri_canvas = FigureCanvasQTAgg(self.mri_fig)
        self.phi_slider = QSlider(Qt.Horizontal)
        self.phi_slider.setRange(0, 179)
        self.phi_slider.valueChanged.connect(self._on_phi_changed)
        self.phi_label = QLabel('0°')
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(2, 20)
        self.width_spin.setValue(4)
        self.width_spin.setSuffix(' mm')
        self.width_spin.valueChanged.connect(lambda _: self._draw_mri())
        mri_ctrl = QHBoxLayout()
        for w in (QLabel('Slice rotation'), self.phi_slider, self.phi_label, QLabel('Half width'), self.width_spin):
            mri_ctrl.addWidget(w)
        self.info = QLabel('')
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info.setAlignment(Qt.AlignTop)
        self.notes = QLineEdit()
        self.notes.setPlaceholderText('Notes for this session')
        self.notes.textEdited.connect(lambda _: self._mark_dirty())
        right = QVBoxLayout()
        right.addWidget(NavigationToolbar2QT(self.mri_canvas, self))
        right.addWidget(self.mri_canvas, 3)
        right.addLayout(mri_ctrl)
        right.addWidget(self.info, 2)
        right.addWidget(self.notes)
        right_w = QWidget()
        right_w.setLayout(right)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(prof_w)
        split.addWidget(right_w)
        split.setSizes([1100, 600])

        lay = QVBoxLayout()
        lay.addLayout(top)
        lay.addLayout(cls_row)
        lay.addWidget(split, 1)
        central = QWidget()
        central.setLayout(lay)
        self.setCentralWidget(central)

        if start_session and start_session in self.source.sessions():
            self.session_box.setCurrentText(start_session)
        if self.session_box.count():
            self._load_session(self.session_box.currentText())
        else:
            self._show_no_sessions()

    def _show_no_sessions(self):
        msg = 'No sessions with laminar profiles yet: run laminar_profiles.py, then Refresh sessions.'
        old = self.source.outdated_sessions() if hasattr(self.source, 'outdated_sessions') else []
        if old:
            msg += f' {len(old)} session(s) are from the old version and need a rerun: ' + ', '.join(old)
        self.status.setText(msg)

    def _refresh_sessions(self):
        current = self.sid
        sessions = self.source.sessions()
        self.session_box.blockSignals(True)
        self.session_box.clear()
        self.session_box.addItems(sessions)
        if current in sessions:
            self.session_box.setCurrentText(current)
        self.session_box.blockSignals(False)
        if not sessions:
            self._show_no_sessions()
        elif current not in sessions:
            self._load_session(self.session_box.currentText())
        else:
            self.status.setText(f'{len(sessions)} session(s) with laminar profiles')

    # ================================================================ session
    def _step_session(self, step):
        i = self.session_box.currentIndex() + step
        if 0 <= i < self.session_box.count():
            self.session_box.setCurrentIndex(i)

    def _on_session_changed(self, sid):
        if sid == self.sid or not sid:
            return
        if self.dirty:
            ans = QMessageBox.question(self, 'Unsaved calls', f'Save calls for {self.sid} first?',
                                       QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if ans == QMessageBox.Cancel:
                self.session_box.blockSignals(True)
                self.session_box.setCurrentText(self.sid)
                self.session_box.blockSignals(False)
                return
            if ans == QMessageBox.Save:
                self._save()
        self._load_session(sid)

    def _load_session(self, sid):
        self.sid = sid
        self.info_d = self.source.session_info(sid)
        self.prof = self.source.profiles(sid)
        self.drive = self.source.drive_metrics(sid)
        self.estim = set(self.source.estim_channels(sid))
        try:
            self.mri = self.source.mri(sid)
        except Exception as exc:          # no MRI should not stop calling from ephys
            print(f'{sid}: MRI unavailable: {exc!r}')
            self.mri = None
        self.depths = self.prof['depth_mm'].to_numpy(float)
        self.channels = self.prof['channel'].astype(int).tolist()
        self._compute_context()
        saved = self.source.load_calls(sid)
        self.notes.setText(saved['notes'] or '')
        self.phi_slider.blockSignals(True)
        self.phi_slider.setValue(int(saved['mri_phi_deg'] or 0))
        self.phi_slider.blockSignals(False)
        self.phi_label.setText(f'{self.phi_slider.value()}°')
        if saved['calls'] and set(saved['calls']) >= set(self.channels):
            self.calls = {ch: saved['calls'][ch] for ch in self.channels}
            self.status.setText(f'{sid}: loaded saved calls')
            self.dirty = False
        else:
            self.calls = dict(zip(self.channels, self._suggestions()))
            self.status.setText(f'{sid}: no saved calls, showing suggestions (not saved)')
            self.dirty = True
        self.selected = []
        self._update_sel_label()
        self._draw_profiles()
        self._draw_mri()
        self._update_info()

    # ============================================================ context
    def _compute_context(self):
        top, bottom = self.depths.min(), self.depths.max()
        half = CHANNEL_SPACING_UM / 2000.0
        self.span = (top - half, bottom + half)
        d = self.drive
        self.drive_depths = d['depth_under_chamber_mm'].to_numpy(float) if len(d) else np.array([])
        # ephys tissue class along the drive
        pcols = [c for c in ('p_wm', 'p_gm', 'p_sulcus') if c in d.columns]
        if pcols and len(d):
            P = d[pcols].to_numpy(float)
            ok = ~np.all(np.isnan(P), axis=1)
            idx = np.argmax(np.nan_to_num(P, nan=-1), axis=1)
            self.drive_tissue = np.array([pcols[i][2:] if o else '' for i, o in zip(idx, ok)], dtype=object)
        else:
            self.drive_tissue = None
        # MRI segmentation along the whole trajectory
        if self.mri is not None:
            dmax = max(self.drive_depths.max() if len(self.drive_depths) else 0, bottom) + 2.0
            self.mri_depths = np.arange(0, dmax, 0.05)
            self.mri_seg = self.mri.seg_along(self.mri_depths)
            self.angle = self._probe_angle()
        else:
            self.mri_depths, self.mri_seg, self.angle = None, None, None

    def _probe_angle(self) -> Optional[dict]:
        """Cortical angle at the L4 marker; if the segmentation has no gradient there
        (e.g. that point is deep in WM), the median over channels where it has one."""
        mid = self._middle_depth()
        a = self.mri.cortical_angle(mid) if mid is not None else None
        if a is not None:
            return a
        found = [x for z in self.depths[::4] if (x := self.mri.cortical_angle(z)) is not None]
        if not found:
            return None
        return dict(angle_deg=float(np.median([x['angle_deg'] for x in found])),
                    normal_order=bool(np.mean([x['normal_order'] for x in found]) >= 0.5))

    def _middle_depth(self) -> Optional[float]:
        sink, cross = self.info_d.get('sink_depth_mm'), self.info_d.get('crossover_depth_mm')
        first, second = (sink, cross) if self.middle_from == 'sink' else (cross, sink)
        return first if first is not None else second

    def _tissue_at_channels(self) -> List[Optional[str]]:
        if self.drive_tissue is not None and len(self.drive_depths):
            out = []
            for z in self.depths:
                i = int(np.argmin(np.abs(self.drive_depths - z)))
                ok = abs(self.drive_depths[i] - z) <= 0.1 and self.drive_tissue[i]
                out.append(self.drive_tissue[i] if ok else None)
            if any(t is not None for t in out):
                return out
        if self.mri is not None:
            return [SEG_TO_TISSUE.get(int(v)) for v in self.mri.seg_along(self.depths)]
        return [None] * len(self.depths)

    def _suggestions(self) -> List[str]:
        normal_order = self.angle['normal_order'] if self.angle else True
        return suggest_classes(self.depths, self._middle_depth(), self._tissue_at_channels(),
                               self.middle_half_width_um, normal_order)

    # ============================================================== calling
    def _on_span(self, ymin, ymax):
        lo, hi = min(ymin, ymax), max(ymin, ymax)
        half = CHANNEL_SPACING_UM / 2000.0
        self.selected = [ch for ch, z in zip(self.channels, self.depths) if lo - half <= z <= hi + half
                         and (hi - lo > half or abs(z - (lo + hi) / 2) <= half)]
        self._update_sel_label()
        self._draw_calls()

    def _update_sel_label(self):
        if not self.selected:
            self.sel_label.setText('No channels selected (drag over the Calls column)')
        else:
            self.sel_label.setText(f'{len(self.selected)} selected: '
                                   + ', '.join(channel_name(c) for c in self.selected))

    def _apply_class(self, cls):
        if not self.selected:
            return
        for ch in self.selected:
            self.calls[ch] = cls
        self._mark_dirty()
        self._draw_calls()
        self._draw_mri()
        self._update_info()

    def _reset_to_suggestions(self):
        self.calls = dict(zip(self.channels, self._suggestions()))
        self._mark_dirty()
        self._draw_calls()
        self._draw_mri()
        self._update_info()

    def _mark_dirty(self):
        self.dirty = True
        self.status.setText(f'{self.sid}: unsaved changes')

    def _save(self):
        self.source.save_calls(self.sid, self.calls, dict(zip(self.channels, self.depths)),
                               self.notes.text(), float(self.phi_slider.value()))
        self.dirty = False
        self.status.setText(f'{self.sid}: calls saved')

    # ============================================================ drawing
    def _draw_profiles(self):
        fig = self.prof_fig
        fig.clear()
        fs = self.font_size
        gs = fig.add_gridspec(1, 7, width_ratios=[0.25, 0.25, 1.6, 0.25, 2.2, 1.2, 0.6], wspace=0.08,
                              left=0.07, right=0.93, top=0.94, bottom=0.08)
        ax_te, ax_tm, ax_drive = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
        ax_csd = fig.add_subplot(gs[4])
        ax_band = fig.add_subplot(gs[5])
        ax_calls = fig.add_subplot(gs[6])
        self.ax_calls = ax_calls

        # ---- whole drive
        ylim_drive = self._drive_ylim()
        self._tissue_strip(ax_te, self.drive_depths, self.drive_tissue, 'Ephys\ntissue', ylim_drive, fs)
        mri_t = None if self.mri_seg is None else np.array([SEG_TO_TISSUE.get(int(v), '') for v in self.mri_seg],
                                                            dtype=object)
        self._tissue_strip(ax_tm, self.mri_depths, mri_t, 'MRI\ntissue', ylim_drive, fs)
        ax_te.set_ylabel('Depth under chamber (mm)', fontsize=fs)
        ax_tm.set_yticklabels([])
        d = self.drive
        for col, label, color in (('band_power_gamma', 'gamma', 'tab:red'),
                                  ('band_power_alpha_beta', 'alpha-beta', 'tab:blue'),
                                  ('spike_rate_hz', 'MUA rate', 'k')):
            if col in d.columns and len(d):
                v = d[col].to_numpy(float)
                rng = np.nanmax(v) - np.nanmin(v)
                ax_drive.plot((v - np.nanmin(v)) / (rng if rng else 1), self.drive_depths, color=color,
                              lw=1.5, label=label)
        ax_drive.axhspan(*self.span, color='gold', alpha=0.35, lw=0)
        ax_drive.set_ylim(*ylim_drive)
        ax_drive.set_yticklabels([])
        ax_drive.set_xlabel('Scaled 0-1', fontsize=fs)
        ax_drive.set_title('Whole drive', fontsize=fs + 1)
        if ax_drive.get_lines():
            ax_drive.legend(loc='lower right', fontsize=fs - 2, frameon=False)
        for a in (ax_te, ax_tm):
            a.axhspan(*self.span, facecolor='none', edgecolor='gold', lw=2)

        # ---- CSD at the final position
        csd = np.vstack(self.prof['csd'].to_list())
        pre_ms, sr = self.info_d['pre_ms'], self.info_d['sample_rate']
        t = np.arange(csd.shape[1]) / sr * 1000.0 - pre_ms
        lim = np.nanpercentile(np.abs(csd), 99) or 1.0
        ax_csd.imshow(-csd, aspect='auto', cmap='RdBu_r', vmin=-lim, vmax=lim, interpolation='bilinear',
                      extent=(t[0], t[-1], self.span[1], self.span[0]))
        ax_csd.axvline(0, color='k', lw=1)
        ax_csd.set_xlabel('Time from stim onset (ms)', fontsize=fs)
        ax_csd.set_ylabel('Depth (mm)', fontsize=fs)
        ax_csd.set_title('CSD (sink red)', fontsize=fs + 1)

        ax_band.plot(self.prof['alpha_beta_rel'], self.depths, color='tab:blue', lw=2, label='alpha-beta')
        ax_band.plot(self.prof['gamma_rel'], self.depths, color='tab:red', lw=2, label='gamma')
        ax_band.set_xlabel('Relative power', fontsize=fs)
        ax_band.set_title('Band power', fontsize=fs + 1)
        ax_band.legend(loc='lower right', fontsize=fs - 2, frameon=False)
        plt_setp_hidden(ax_band.get_yticklabels())

        for ax in (ax_csd, ax_band):
            if self.info_d.get('sink_depth_mm') is not None:
                ax.axhline(self.info_d['sink_depth_mm'], color='tab:red', ls='--', lw=1.2)
            if self.info_d.get('crossover_depth_mm') is not None:
                ax.axhline(self.info_d['crossover_depth_mm'], color='tab:purple', ls=':', lw=1.5)
        for ax in (ax_csd, ax_band):
            ax.set_ylim(self.span[1], self.span[0])

        self._spans = [SpanSelector(ax, self._on_span, 'vertical', useblit=True,
                                    props=dict(alpha=0.25, facecolor='tab:green'))
                       for ax in (ax_calls, ax_csd, ax_band)]
        self._draw_calls(draw=False)
        self.prof_canvas.draw_idle()

    def _drive_ylim(self):
        vals = [self.span[0], self.span[1]]
        if len(self.drive_depths):
            vals += [np.nanmin(self.drive_depths), np.nanmax(self.drive_depths)]
        return (max(vals) + 0.5, max(0.0, min(vals) - 0.5))

    @staticmethod
    def _tissue_strip(ax, depths, tissue, title, ylim, fs):
        ax.set_xticks([])
        ax.set_title(title, fontsize=fs - 1)
        ax.set_ylim(*ylim)
        if depths is None or tissue is None or len(depths) == 0:
            ax.text(0.5, np.mean(ylim), 'none', ha='center', va='center', rotation=90, fontsize=fs - 2)
            return
        depths = np.asarray(depths)
        edges = np.concatenate([[depths[0] - (depths[1] - depths[0]) / 2 if len(depths) > 1 else depths[0] - 0.05],
                                (depths[1:] + depths[:-1]) / 2,
                                [depths[-1] + (depths[-1] - depths[-2]) / 2 if len(depths) > 1 else depths[0] + 0.05]])
        for i, t in enumerate(tissue):
            if t in TISSUE_COLORS:
                ax.add_patch(Rectangle((0, edges[i]), 1, edges[i + 1] - edges[i], color=TISSUE_COLORS[t], lw=0))
        ax.set_xlim(0, 1)

    def _draw_calls(self, draw=True):
        ax = self.ax_calls
        ax.cla()
        fs = self.font_size
        h = CHANNEL_SPACING_UM / 1000.0
        for ch, z in zip(self.channels, self.depths):
            cls = self.calls.get(ch, 'unsure')
            ax.add_patch(Rectangle((0, z - h / 2), 1, h, facecolor=CLASS_COLORS[cls],
                                   edgecolor='0.6', lw=0.5))
            if ch in self.estim:
                ax.add_patch(Rectangle((0.04, z - h / 2 + 0.006), 0.92, h - 0.012, facecolor='none',
                                       edgecolor='lime', lw=2.5))
            if ch in self.selected:
                ax.add_patch(Rectangle((0, z - h / 2), 1, h, facecolor='none', edgecolor='k', lw=2))
        ax.set_xlim(0, 1)
        ax.set_ylim(self.span[1], self.span[0])
        ax.set_xticks([])
        ax.yaxis.tick_right()
        ax.set_yticks(self.depths)
        ax.set_yticklabels([channel_name(c) for c in self.channels], fontsize=max(6, fs - 4))
        ax.set_title('Calls', fontsize=fs + 1)
        if draw:
            self.prof_canvas.draw_idle()

    def _on_phi_changed(self, v):
        self.phi_label.setText(f'{v}°')
        self._mark_dirty()
        self._draw_mri()

    def _draw_mri(self):
        fig = self.mri_fig
        fig.clear()
        ax = fig.add_subplot(111)
        fs = self.font_size
        if self.mri is None:
            ax.text(0.5, 0.5, 'No MRI trajectory for this session', ha='center', va='center',
                    transform=ax.transAxes, fontsize=fs)
            ax.set_axis_off()
            self.mri_canvas.draw_idle()
            return
        lo, hi = self.span[0] - 4.0, self.span[1] + 4.0
        sl = self.mri.slice((lo, hi), half_width_mm=self.width_spin.value(), phi_deg=self.phi_slider.value())
        img = sl['mri']
        vmin, vmax = np.nanpercentile(img, [1, 99.5])
        ax.imshow(img, cmap='gray', vmin=vmin, vmax=vmax, extent=sl['extent'], interpolation='bilinear')
        seg = sl['seg']
        if np.any(seg >= 0):
            ext = sl['extent']
            xs = np.linspace(ext[0], ext[1], seg.shape[1])
            ys = np.linspace(ext[3], ext[2], seg.shape[0])
            ax.contour(xs, ys, (seg == SEG_WM).astype(float), levels=[0.5], colors='deepskyblue', linewidths=1)
            ax.contour(xs, ys, (seg >= SEG_GM).astype(float), levels=[0.5], colors='orange', linewidths=1)
        ax.plot([0, 0], [lo, hi], color='yellow', lw=0.8, alpha=0.6)
        for ch, z in zip(self.channels, self.depths):
            cls = self.calls.get(ch, 'unsure')
            big = ch in self.estim
            ax.scatter([0], [z], s=70 if big else 16, color=CLASS_COLORS[cls],
                       edgecolors='lime' if big else 'k', linewidths=2 if big else 0.4, zorder=5)
        ax.set_xlabel('Lateral (mm)', fontsize=fs)
        ax.set_ylabel('Depth under chamber (mm)', fontsize=fs)
        ax.set_title('MRI along the probe (orange = pia/GM, blue = WM)', fontsize=fs)
        fig.tight_layout()
        self.mri_canvas.draw_idle()

    def _update_info(self):
        i = self.info_d
        lines = [f"<b>{self.sid}</b>: final site tip {i['final_tip_mm']:.2f} mm, "
                 f"channels {self.span[0]:.2f}–{self.span[1]:.2f} mm, {i['n_trials']} GA trials"]
        if i.get('sink_channel') is not None:
            lines.append(f"Strongest early sink: {channel_name(i['sink_channel'])} at {i['sink_depth_mm']:.2f} mm, "
                         f"{i['sink_latency_ms']:.0f} ms")
        else:
            lines.append('Strongest early sink: none found')
        lines.append(f"Gamma / alpha-beta crossover: "
                     + (f"{i['crossover_depth_mm']:.2f} mm" if i.get('crossover_depth_mm') is not None else 'none'))
        if i['noisy_channels']:
            lines.append('Interpolated noisy channels: ' + ', '.join(channel_name(c) for c in i['noisy_channels']))
        if self.angle:
            steep = self.angle['angle_deg'] >= self.steep_angle_deg
            lines.append(f"Probe vs cortical normal (MRI): {self.angle['angle_deg']:.0f}°"
                         + (" <b><font color='red'>STEEP: CSD less reliable</font></b>" if steep else '')
                         + ('' if self.angle['normal_order'] else
                            " <b>reversed: probe runs from WM toward pia</b>"))
        elif self.mri is not None:
            lines.append('Probe vs cortical normal (MRI): no gray matter near the probe in the segmentation')
        for name, depths, tissue in (('Ephys', self.drive_depths, self.drive_tissue),
                                     ('MRI', self.mri_depths,
                                      None if self.mri_seg is None else
                                      np.array([SEG_TO_TISSUE.get(int(v), '') for v in self.mri_seg], dtype=object))):
            if tissue is None or depths is None or len(depths) == 0:
                continue
            parts = []
            for target, label in (('wm', 'WM'), ('sulcus', 'sulcus')):
                r = nearest_runs(depths, tissue, target, *self.span)
                txt = []
                if r['above'] is not None:
                    txt.append(f"{(self.span[0] - r['above']):.2f} mm above")
                if r['below'] is not None:
                    txt.append(f"{(r['below'] - self.span[1]):.2f} mm below")
                if r['on_probe']:
                    txt.append('on probe')
                parts.append(f"{label}: " + (', '.join(txt) if txt else 'none'))
            lines.append(f"Nearest {name}: " + '; '.join(parts))
        if self.estim:
            lines.append('EStim contacts: ' + ', '.join(
                f"{channel_name(c)} = {CLASS_LABELS[self.calls.get(c, 'unsure')]}"
                for c in self.channels if c in self.estim))
        else:
            lines.append('EStim contacts: none in EStimParameters')
        self.info.setText('<br>'.join(lines))


def plt_setp_hidden(labels):
    for lab in labels:
        lab.set_visible(False)


if __name__ == '__main__':
    main()
