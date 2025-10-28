# Eco-Commute Buddy — PySide6 Minimal UI (cleaned)
# - Removed: Tight Schedule input
# - Removed: Generate CSV & Save MF plots buttons
# - Reset button moved to top-right in header strip
# Run: pip install PySide6 numpy scikit-fuzzy
#      python eco_commute_qt_min_clean.py

import sys
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QSlider,
    QHBoxLayout, QVBoxLayout, QGridLayout, QProgressBar, QSizePolicy
)

# ---------- FIS (tight schedule removed) ----------
distance = ctrl.Antecedent(np.linspace(0, 8, 401), 'distance_km')
rain     = ctrl.Antecedent(np.linspace(0, 20, 401), 'rain_mmph')
crowd    = ctrl.Antecedent(np.linspace(0.0, 1.2, 401), 'bus_crowd')

rush     = ctrl.Antecedent(np.linspace(0.0, 1.0, 201), 'rush_index')
punct    = ctrl.Antecedent(np.linspace(0.0, 1.0, 201), 'bus_punctuality')
flex     = ctrl.Antecedent(np.linspace(0.0, 1.0, 201), 'flexibility')

suit     = ctrl.Consequent(np.linspace(0, 10, 401), 'mode_suitability')

distance['short']  = fuzz.trapmf(distance.universe, [0, 0, 1.0, 2.0])
distance['medium'] = fuzz.trimf(distance.universe,  [1.5, 3.0, 5.0])
distance['long']   = fuzz.trapmf(distance.universe, [4.0, 6.0, 8.0, 8.0])

rain['nice']    = fuzz.trapmf(rain.universe, [0, 0, 0.2, 1.0])
rain['drizzle'] = fuzz.trimf(rain.universe,  [0.5, 1.5, 3.0])
rain['rainy']   = fuzz.trapmf(rain.universe, [2.0, 5.0, 20.0, 20.0])

crowd['low']    = fuzz.trapmf(crowd.universe, [0.0, 0.0, 0.40, 0.60])
crowd['medium'] = fuzz.trimf(crowd.universe,  [0.50, 0.75, 0.95])
crowd['high']   = fuzz.trapmf(crowd.universe, [0.85, 1.00, 1.20, 1.20])

rush['offpeak'] = fuzz.trapmf(rush.universe, [0.0, 0.0, 0.30, 0.60])
rush['rush']    = fuzz.trapmf(rush.universe, [0.40, 0.70, 1.00, 1.00])

punct['on_time']= fuzz.trapmf(punct.universe, [0.0, 0.0, 0.30, 0.50])
punct['delayed']= fuzz.trapmf(punct.universe, [0.50, 0.70, 1.00, 1.00])

flex['low']     = fuzz.trapmf(flex.universe,  [0.0, 0.0, 0.30, 0.50])
flex['high']    = fuzz.trapmf(flex.universe,  [0.50, 0.70, 1.00, 1.00])

suit['walk']  = fuzz.trimf(suit.universe,  [0.0, 0.0, 4.0])
suit['bus']   = fuzz.trimf(suit.universe,  [3.0, 5.5, 8.0])
suit['drive'] = fuzz.trimf(suit.universe,  [6.5, 10.0, 10.0])

base_rules = [
    ctrl.Rule(distance['short']  & rain['nice'],                      suit['walk']),
    ctrl.Rule(distance['short']  & rain['drizzle'],                   suit['walk']),
    ctrl.Rule(distance['short']  & rain['rainy'] & crowd['low'],      suit['bus']),
    ctrl.Rule(distance['short']  & rain['rainy'] & crowd['medium'],   suit['bus']),
    ctrl.Rule(distance['short']  & rain['rainy'] & crowd['high'],     suit['drive']),
    ctrl.Rule(distance['medium'] & rain['nice']  & crowd['low'],      suit['bus']),
    ctrl.Rule(distance['medium'] & rain['drizzle'] & crowd['low'],    suit['bus']),
    ctrl.Rule(distance['medium'] & rain['drizzle'] & crowd['medium'], suit['bus']),
    ctrl.Rule(distance['medium'] & rain['rainy'],                      suit['drive']),
    ctrl.Rule(distance['long']   & rain['nice'],                       suit['drive']),
    ctrl.Rule(distance['long']   & rain['drizzle'],                    suit['drive']),
    ctrl.Rule(distance['long']   & rain['rainy'],                      suit['drive']),
    ctrl.Rule(distance['medium'] & rain['nice'] & crowd['high'],      suit['walk']),
]

new_rules = [
    ctrl.Rule(distance['short']  & rain['nice'] & flex['high'],                suit['walk']),
    ctrl.Rule(distance['short']  & rush['offpeak'] & flex['high'],             suit['walk']),
    ctrl.Rule(distance['medium'] & rush['offpeak'] & punct['on_time'] & (crowd['low'] | crowd['medium']), suit['bus']),
    ctrl.Rule(distance['short']  & rush['offpeak'] & punct['on_time'] & crowd['low'],                     suit['bus']),
    ctrl.Rule(rush['rush'] & punct['delayed'] & crowd['high'],                  suit['drive']),
    # removed tight_schedule rules
    ctrl.Rule(distance['long'] & punct['delayed'],                               suit['drive']),
    ctrl.Rule(distance['medium'] & rain['drizzle'] & flex['high'] & (crowd['low'] | crowd['medium']), suit['bus']),
    ctrl.Rule(distance['short'] & rain['drizzle'] & flex['high'],               suit['walk']),
    ctrl.Rule(rush['offpeak'] & punct['on_time'] & (crowd['low'] | crowd['medium']) & (distance['short'] | distance['medium']), suit['bus']),
]

rules = base_rules + new_rules
system = ctrl.ControlSystem(rules)
sim = ctrl.ControlSystemSimulation(system)

def fis_recommend(dist_km, rain_mmph, crowd_ratio, rush_idx, bus_punct, flexi):
    d  = float(np.clip(dist_km,    0,   8))
    r  = float(np.clip(rain_mmph,  0,  20))
    c  = float(np.clip(crowd_ratio,0.0,1.2))
    t  = float(np.clip(rush_idx,   0.0,1.0))
    p  = float(np.clip(bus_punct,  0.0,1.0))
    f  = float(np.clip(flexi,      0.0,1.0))

    sim.input['distance_km']     = d
    sim.input['rain_mmph']       = r
    sim.input['bus_crowd']       = c
    sim.input['rush_index']      = t
    sim.input['bus_punctuality'] = p
    sim.input['flexibility']     = f
    sim.compute()

    crisp = float(sim.output['mode_suitability'])
    mu_w  = float(fuzz.interp_membership(suit.universe, suit['walk'].mf,  crisp))
    mu_b  = float(fuzz.interp_membership(suit.universe, suit['bus'].mf,   crisp))
    mu_d  = float(fuzz.interp_membership(suit.universe, suit['drive'].mf, crisp))
    label = max([('Walk', mu_w), ('Bus', mu_b), ('Drive', mu_d)], key=lambda x: x[1])[0]

    def best_label(var, value, labels):
        scores = [(L, fuzz.interp_membership(var.universe, var[L].mf, value)) for L in labels]
        return max(scores, key=lambda t: t[1])[0]

    dL  = best_label(distance, d, ['short','medium','long'])
    rL  = best_label(rain,     r, ['nice','drizzle','rainy'])
    cL  = best_label(crowd,    c, ['low','medium','high'])
    tL  = best_label(rush,     t, ['offpeak','rush'])
    pL  = best_label(punct,    p, ['on_time','delayed'])
    fL  = best_label(flex,     f, ['low','high'])

    explain = (f"{label} (suitability={crisp:.1f}/10) — distance {dL}, rain {rL}, crowd {cL}, "
               f"time {tL}, buses {pL}, flexibility {fL}.")
    return label, crisp, (mu_w, mu_b, mu_d), (d, r, c, t, p, f), explain

def expected_label(d, r, c, t, p, f):
    if (t >= 0.7 and p >= 0.6 and c >= 0.85): return 'Drive'
    if d <= 2.0 and r < 1.5 and f >= 0.6:     return 'Walk'
    if 1.5 < d <= 5.0 and t < 0.5 and p < 0.5 and c < 0.8: return 'Bus'
    if d > 5.0:                                return 'Drive'
    if r >= 2.0 and p >= 0.5:                  return 'Drive'
    if 1.5 < d <= 5.0:                         return 'Bus'
    return 'Walk'

# ---------- Minimal UI ----------
class FloatSlider(QWidget):
    valueChanged = Signal(float)

    def __init__(self, title, vmin, vmax, init, unit=""):
        super().__init__()
        self.vmin, self.vmax = vmin, vmax
        self.unit = unit
        self.scale = 1000

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color:#1f2937;")
        self.val_lbl = QLabel("")
        self.val_lbl.setStyleSheet("color:#6b7280;")
        self.val_lbl.setMinimumWidth(70)

        top = QHBoxLayout()
        top.addWidget(title_lbl)
        top.addStretch(1)
        top.addWidget(self.val_lbl)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self.scale)
        self.slider.valueChanged.connect(self._on_change)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.addLayout(top)
        lay.addWidget(self.slider)

        self.setValue(init)

    def value(self) -> float:
        t = self.slider.value()/self.scale
        return self.vmin + t*(self.vmax - self.vmin)

    def setValue(self, f: float):
        t = int((f - self.vmin)/(self.vmax - self.vmin) * self.scale)
        self.slider.blockSignals(True)
        self.slider.setValue(max(0, min(self.scale, t)))
        self.slider.blockSignals(False)
        self._update_label(self.value())

    def _on_change(self, _):
        self._update_label(self.value())
        self.valueChanged.emit(self.value())

    def _update_label(self, f):
        self.val_lbl.setText(f"{f:.2f}" + (f" {self.unit}" if self.unit else ""))

class MinimalWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eco-Commute Buddy — Minimal")
        self.resize(1040, 680)

        # minimalist light style
        self.setStyleSheet("""
            QWidget   { background: #ffffff; color:#111827; font-family: 'Segoe UI', Arial; font-size: 14px; }
            QLabel    { color:#111827; }
            QSlider::groove:horizontal { height:6px; background:#e5e7eb; border-radius:4px; }
            QSlider::handle:horizontal { background:#3b82f6; width:14px; height:14px; margin:-5px 0; border-radius:7px; }
            QProgressBar { background:#e5e7eb; border:none; border-radius:6px; height:14px; text-align:center; color:#374151; }
            QProgressBar::chunk { background:#3b82f6; border-radius:6px; }
            QPushButton { background:#f3f4f6; border:1px solid #e5e7eb; padding:8px 12px; border-radius:8px; }
            QPushButton:hover { background:#e5e7eb; }
        """)

        root = QWidget(); self.setCentralWidget(root)
        main = QVBoxLayout(root); main.setContentsMargins(24, 24, 24, 24); main.setSpacing(18)

        # Header row with Reset at top-right
        header_row = QHBoxLayout(); header_row.setSpacing(18)
        title_box = QVBoxLayout()
        h1 = QLabel("Eco-Commute Buddy")
        h1.setFont(QFont("Segoe UI", 22, QFont.Bold))
        sub = QLabel("Walk • Bus • Drive — simple, interpretable fuzzy decision")
        sub.setStyleSheet("color:#6b7280;")
        title_box.addWidget(h1); title_box.addWidget(sub)
        header_row.addLayout(title_box)
        header_row.addStretch(1)
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.on_reset)
        header_row.addWidget(btn_reset)
        main.addLayout(header_row)

        # Top result strip
        strip = QHBoxLayout(); strip.setSpacing(18)
        self.mode_badge = QLabel("—")
        self.mode_badge.setStyleSheet("background:#f3f4f6; border-radius:12px; padding:6px 10px; color:#111827; font-weight:600;")
        self.suit_lbl = QLabel("Suitability: — / 10"); self.suit_lbl.setStyleSheet("color:#374151;")
        self.heur_lbl = QLabel("Heuristic: —");        self.heur_lbl.setStyleSheet("color:#9ca3af;")
        strip.addWidget(self.mode_badge); strip.addWidget(self.suit_lbl); strip.addWidget(self.heur_lbl)
        strip.addStretch(1)
        main.addLayout(strip)

        # Content grid
        grid = QGridLayout(); grid.setHorizontalSpacing(32); grid.setVerticalSpacing(8)
        main.addLayout(grid)

        # Left column (environment)
        self.sl_dist  = FloatSlider("Distance (km)",       0.0, 8.0, 1.2, "km")
        self.sl_rain  = FloatSlider("Rain (mm/h)",         0.0, 20.0, 0.0, "mm/h")
        self.sl_crowd = FloatSlider("Bus crowd (ratio)",   0.0, 1.2, 0.50, "")

        # Right column (time + preference)
        self.sl_rush  = FloatSlider("Time of day (0 off-peak → 1 rush)", 0.0, 1.0, 0.2, "")
        self.sl_punct = FloatSlider("Bus punctuality (0 on-time → 1 delayed)", 0.0, 1.0, 0.2, "")
        self.sl_flex  = FloatSlider("Flexibility (0 low → 1 high)", 0.0, 1.0, 0.7, "")

        # place sliders (2 columns)
        grid.addWidget(self.sl_dist,  0, 0)
        grid.addWidget(self.sl_rush,  0, 1)
        grid.addWidget(self.sl_rain,  1, 0)
        grid.addWidget(self.sl_punct, 1, 1)
        grid.addWidget(self.sl_crowd, 2, 0)
        grid.addWidget(self.sl_flex,  2, 1)

        # Spacer to keep nice bottom breathing room
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main.addWidget(spacer)

        # Membership bars
        mem = QHBoxLayout(); mem.setSpacing(18)
        self.pb_walk = self._bar("Walk", "#10b981")
        self.pb_bus  = self._bar("Bus",  "#3b82f6")
        self.pb_drive= self._bar("Drive","#ef4444")
        mem.addWidget(self.pb_walk); mem.addWidget(self.pb_bus); mem.addWidget(self.pb_drive)
        main.addLayout(mem)

        # Explanation
        self.why_lbl = QLabel("—")
        self.why_lbl.setWordWrap(True)
        self.why_lbl.setStyleSheet("color:#6b7280;")
        main.addWidget(self.why_lbl)

        # Wire events
        for s in (self.sl_dist, self.sl_rain, self.sl_crowd, self.sl_rush,
                  self.sl_punct, self.sl_flex):
            s.valueChanged.connect(self.recompute)

        self.recompute()

    def _bar(self, title, color_hex):
        box = QVBoxLayoutWidget(title)
        pb = QProgressBar(); pb.setRange(0,100); pb.setValue(0); pb.setFormat("%p%")
        pb.setStyleSheet(f"QProgressBar::chunk {{ background:{color_hex}; border-radius:6px; }}")
        box.layout.addWidget(pb)
        box.progress = pb
        return box

    # ---- actions ----
    def on_reset(self):
        self.sl_dist.setValue(1.2); self.sl_rain.setValue(0.0); self.sl_crowd.setValue(0.50)
        self.sl_rush.setValue(0.2); self.sl_punct.setValue(0.2); self.sl_flex.setValue(0.7)
        self.recompute()

    # ---- compute ----
    def recompute(self):
        d  = self.sl_dist.value(); r = self.sl_rain.value(); c = self.sl_crowd.value()
        t  = self.sl_rush.value(); p = self.sl_punct.value(); f = self.sl_flex.value()

        label, score, (mu_w, mu_b, mu_d), *_rest, explain = fis_recommend(d, r, c, t, p, f)

        col = {"Walk":"#10b981", "Bus":"#3b82f6", "Drive":"#ef4444"}.get(label, "#e5e7eb")
        self.mode_badge.setText(f"  {label}  ")
        self.mode_badge.setStyleSheet(f"background:{col}; border-radius:12px; padding:6px 10px; color:#ffffff; font-weight:600;")
        self.suit_lbl.setText(f"Suitability: {score:.1f} / 10")
        self.why_lbl.setText(explain)

        self.pb_walk.progress.setValue(int(round(mu_w*100)))
        self.pb_bus.progress.setValue(int(round(mu_b*100)))
        self.pb_drive.progress.setValue(int(round(mu_d*100)))

class QVBoxLayoutWidget(QWidget):
    """Tiny helper for a titled vertical block without borders."""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); self.layout = lay
        if title:
            lbl = QLabel(title); lbl.setStyleSheet("color:#374151; font-weight:600;")
            lay.addWidget(lbl)

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 12))
    win = MinimalWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
