# Section 1: Imports
import sys
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from skfuzzy import membership as mf

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QSlider,
    QHBoxLayout, QVBoxLayout, QGridLayout, QProgressBar, QSizePolicy
)

# Section 2: Inputs & Outputs Variables
# Input
distance = ctrl.Antecedent(np.arange(0, 21, 0.1), 'distance')
rain = ctrl.Antecedent(np.arange(0, 101, 0.5), 'rain_intensity')
crowd = ctrl.Antecedent(np.arange(0, 1.51, 0.01), 'bus_crowding')

# Output
walk_suitability = ctrl.Consequent(np.arange(0, 101, 1), 'walk_suitability', defuzzify_method='centroid')
bus_suitability = ctrl.Consequent(np.arange(0, 101, 1), 'bus_suitability', defuzzify_method='centroid')
drive_suitability = ctrl.Consequent(np.arange(0, 101, 1), 'drive_suitability', defuzzify_method='centroid')

# Section 3: Membership functions
# Input MF
# Distance
distance['very_near'] = fuzz.trapmf(distance.universe, [0, 0, 1, 2.5])
distance['near'] = fuzz.trimf(distance.universe, [1, 3, 5])
distance['medium'] = fuzz.trimf(distance.universe, [3.5, 7, 10.5])
distance['far'] = fuzz.trimf(distance.universe, [9, 13, 17])
distance['very_far'] = fuzz.trapmf(distance.universe, [15, 17.5, 20, 20])

# Rain Intensity
rain['none'] = fuzz.trapmf(rain.universe, [0, 0, 2, 5])
rain['light'] = fuzz.trimf(rain.universe, [2, 8, 15])
rain['moderate'] = fuzz.trimf(rain.universe, [12, 25, 40])
rain['heavy'] = fuzz.trimf(rain.universe, [35, 55, 75])
rain['extreme'] = fuzz.trapmf(rain.universe, [65, 80, 100, 100])

# Bus Crowding
crowd['empty'] = fuzz.trapmf(crowd.universe, [0, 0, 0.2, 0.4])
crowd['comfortable'] = fuzz.trimf(crowd.universe, [0.3, 0.5, 0.7])
crowd['moderate'] = fuzz.trimf(crowd.universe, [0.6, 0.85, 1.1])
crowd['crowded'] = fuzz.trimf(crowd.universe, [1.0, 1.2, 1.4])
crowd['overcrowded'] = fuzz.trapmf(crowd.universe, [1.3, 1.4, 1.5, 1.5])

# Output MF
for output in [walk_suitability, bus_suitability, drive_suitability]:
    output['low'] = fuzz.trapmf(output.universe, [0, 0, 25, 40])
    output['medium'] = fuzz.trimf(output.universe, [30, 50, 70])
    output['high'] = fuzz.trapmf(output.universe, [60, 75, 100, 100])

# Section 4: Fuzzy Rules - Complete rule base to ensure all outputs are activated
rules = []

# ===== WALKING RULES =====
# Very short distances - walking is great
rules.append(ctrl.Rule(distance['very_near'] & rain['none'], walk_suitability['high']))
rules.append(ctrl.Rule(distance['very_near'] & rain['light'], walk_suitability['high']))
rules.append(ctrl.Rule(distance['very_near'] & rain['moderate'], walk_suitability['medium']))
rules.append(ctrl.Rule(distance['very_near'] & rain['heavy'], walk_suitability['low']))
rules.append(ctrl.Rule(distance['very_near'] & rain['extreme'], walk_suitability['low']))

# Short distances
rules.append(ctrl.Rule(distance['near'] & rain['none'], walk_suitability['high']))
rules.append(ctrl.Rule(distance['near'] & rain['light'], walk_suitability['medium']))
rules.append(ctrl.Rule(distance['near'] & rain['moderate'], walk_suitability['low']))
rules.append(ctrl.Rule(distance['near'] & (rain['heavy'] | rain['extreme']), walk_suitability['low']))

# Medium to far distances - walking not suitable
rules.append(ctrl.Rule(distance['medium'], walk_suitability['low']))
rules.append(ctrl.Rule(distance['far'], walk_suitability['low']))
rules.append(ctrl.Rule(distance['very_far'], walk_suitability['low']))

# ===== BUS RULES =====
# Very close - bus not needed
rules.append(ctrl.Rule(distance['very_near'], bus_suitability['low']))

# Short to medium distance with good crowding
rules.append(ctrl.Rule(distance['near'] & (crowd['empty'] | crowd['comfortable']), bus_suitability['high']))
rules.append(ctrl.Rule(distance['near'] & crowd['moderate'], bus_suitability['medium']))
rules.append(ctrl.Rule(distance['near'] & (crowd['crowded'] | crowd['overcrowded']), bus_suitability['low']))

rules.append(ctrl.Rule(distance['medium'] & (crowd['empty'] | crowd['comfortable']), bus_suitability['high']))
rules.append(ctrl.Rule(distance['medium'] & crowd['moderate'], bus_suitability['medium']))
rules.append(ctrl.Rule(distance['medium'] & (crowd['crowded'] | crowd['overcrowded']), bus_suitability['low']))

# Far distances
rules.append(ctrl.Rule(distance['far'] & (crowd['empty'] | crowd['comfortable']), bus_suitability['high']))
rules.append(ctrl.Rule(distance['far'] & crowd['moderate'], bus_suitability['medium']))
rules.append(ctrl.Rule(distance['far'] & (crowd['crowded'] | crowd['overcrowded']), bus_suitability['low']))

rules.append(ctrl.Rule(distance['very_far'] & (crowd['empty'] | crowd['comfortable']), bus_suitability['medium']))
rules.append(ctrl.Rule(distance['very_far'] & ~(crowd['empty'] | crowd['comfortable']), bus_suitability['low']))

# Extreme rain makes bus attractive even if crowded
rules.append(ctrl.Rule(rain['extreme'] & crowd['empty'], bus_suitability['high']))

# ===== DRIVING RULES =====
# Very close or close - driving not efficient
rules.append(ctrl.Rule(distance['very_near'], drive_suitability['low']))
rules.append(ctrl.Rule(distance['near'] & rain['none'], drive_suitability['low']))
rules.append(ctrl.Rule(distance['near'] & rain['light'], drive_suitability['low']))
rules.append(ctrl.Rule(distance['near'] & rain['moderate'], drive_suitability['medium']))
rules.append(ctrl.Rule(distance['near'] & (rain['heavy'] | rain['extreme']), drive_suitability['medium']))

# Medium distance - contextual
rules.append(ctrl.Rule(distance['medium'] & rain['none'] & crowd['comfortable'], drive_suitability['low']))
rules.append(ctrl.Rule(distance['medium'] & rain['light'] & crowd['comfortable'], drive_suitability['low']))
rules.append(ctrl.Rule(distance['medium'] & rain['moderate'], drive_suitability['medium']))
rules.append(ctrl.Rule(distance['medium'] & (rain['heavy'] | rain['extreme']), drive_suitability['high']))
rules.append(ctrl.Rule(distance['medium'] & crowd['overcrowded'], drive_suitability['medium']))

# Far distances - driving becomes attractive
rules.append(ctrl.Rule(distance['far'] & rain['none'], drive_suitability['medium']))
rules.append(ctrl.Rule(distance['far'] & (rain['light'] | rain['moderate']), drive_suitability['high']))
rules.append(ctrl.Rule(distance['far'] & (rain['heavy'] | rain['extreme']), drive_suitability['high']))

# Very far - driving is best
rules.append(ctrl.Rule(distance['very_far'], drive_suitability['high']))

# Create control system
system = ctrl.ControlSystem(rules)
sim = ctrl.ControlSystemSimulation(system)

# Section 5: Fuzzy Inference Function
def fis_recommend(dist_km, rain_mmph, crowd_ratio):
    """
    Fuzzy inference for commute recommendation
    
    Parameters:
    - dist_km: distance in km (0-20)
    - rain_mmph: rain intensity in mm/h (0-100)
    - crowd_ratio: bus occupancy ratio (0-1.5)
    
    Returns: label, crisp_score, memberships, inputs, explanation
    """
    d = float(np.clip(dist_km, 0, 20))
    r = float(np.clip(rain_mmph, 0, 100))
    c = float(np.clip(crowd_ratio, 0.0, 1.5))

    try:
        sim.input['distance'] = d
        sim.input['rain_intensity'] = r
        sim.input['bus_crowding'] = c
        sim.compute()

        walk_score = float(sim.output['walk_suitability'])
        bus_score = float(sim.output['bus_suitability'])
        drive_score = float(sim.output['drive_suitability'])
        
    except Exception as e:
        print(f"FIS computation error: {e}")
        # Default fallback values
        walk_score = 50.0
        bus_score = 50.0
        drive_score = 50.0
    
    # Normalize to 0-1 range for membership display
    mu_w = walk_score / 100.0
    mu_b = bus_score / 100.0
    mu_d = drive_score / 100.0
    
    # Determine recommendation
    scores = {'Walk': walk_score, 'Bus': bus_score, 'Drive': drive_score}
    label = max(scores, key=scores.get)
    crisp = scores[label] / 10.0  # Convert to 0-10 scale

    # Helper function to get linguistic label
    def best_label(var, value, labels):
        scores_list = [(L, fuzz.interp_membership(var.universe, var[L].mf, value)) for L in labels]
        return max(scores_list, key=lambda t: t[1])[0]

    dL = best_label(distance, d, ['very_near', 'near', 'medium', 'far', 'very_far'])
    rL = best_label(rain, r, ['none', 'light', 'moderate', 'heavy', 'extreme'])
    cL = best_label(crowd, c, ['empty', 'comfortable', 'moderate', 'crowded', 'overcrowded'])

    explain = (f"{label} (suitability={crisp:.1f}/10) — distance {dL}, rain {rL}, crowd {cL}.")
    return label, crisp, (mu_w, mu_b, mu_d), (d, r, c), explain

# Section 6: GUI Design
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
        t = self.slider.value() / self.scale
        return self.vmin + t * (self.vmax - self.vmin)

    def setValue(self, f: float):
        t = int((f - self.vmin) / (self.vmax - self.vmin) * self.scale)
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
        self.setWindowTitle("Commuting Buddy — Fuzzy Inference System")
        self.resize(900, 600)

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

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(24, 24, 24, 24)
        main.setSpacing(18)

        # Header row with Reset at top-right
        header_row = QHBoxLayout()
        header_row.setSpacing(18)
        title_box = QVBoxLayout()
        h1 = QLabel("Commuting Buddy")
        h1.setFont(QFont("Segoe UI", 22, QFont.Bold))
        sub = QLabel("Walk • Bus • Drive — Fuzzy decision support system")
        sub.setStyleSheet("color:#6b7280;")
        title_box.addWidget(h1)
        title_box.addWidget(sub)
        header_row.addLayout(title_box)
        header_row.addStretch(1)
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.on_reset)
        header_row.addWidget(btn_reset)
        main.addLayout(header_row)

        # Top result strip
        strip = QHBoxLayout()
        strip.setSpacing(18)
        self.mode_badge = QLabel("—")
        self.mode_badge.setStyleSheet("background:#f3f4f6; border-radius:12px; padding:6px 10px; color:#111827; font-weight:600;")
        self.suit_lbl = QLabel("Suitability: — / 10")
        self.suit_lbl.setStyleSheet("color:#374151;")
        strip.addWidget(self.mode_badge)
        strip.addWidget(self.suit_lbl)
        strip.addStretch(1)
        main.addLayout(strip)

        # Input sliders
        grid = QVBoxLayout()
        grid.setSpacing(8)
        main.addLayout(grid)

        self.sl_dist = FloatSlider("Distance (km)", 0.0, 20.0, 5.0, "km")
        self.sl_rain = FloatSlider("Rain Intensity (mm/h)", 0.0, 100.0, 10.0, "mm/h")
        self.sl_crowd = FloatSlider("Bus Crowding (ratio)", 0.0, 1.5, 0.7, "")

        grid.addWidget(self.sl_dist)
        grid.addWidget(self.sl_rain)
        grid.addWidget(self.sl_crowd)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main.addWidget(spacer)

        # Membership bars
        mem = QHBoxLayout()
        mem.setSpacing(18)
        self.pb_walk = self._bar("Walk", "#10b981")
        self.pb_bus = self._bar("Bus", "#3b82f6")
        self.pb_drive = self._bar("Drive", "#ef4444")
        mem.addWidget(self.pb_walk)
        mem.addWidget(self.pb_bus)
        mem.addWidget(self.pb_drive)
        main.addLayout(mem)

        # Explanation
        self.why_lbl = QLabel("—")
        self.why_lbl.setWordWrap(True)
        self.why_lbl.setStyleSheet("color:#6b7280;")
        main.addWidget(self.why_lbl)

        # Wire events
        for s in (self.sl_dist, self.sl_rain, self.sl_crowd):
            s.valueChanged.connect(self.recompute)

        self.recompute()

    def _bar(self, title, color_hex):
        box = QVBoxLayoutWidget(title)
        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setValue(0)
        pb.setFormat("%p%")
        pb.setStyleSheet(f"QProgressBar::chunk {{ background:{color_hex}; border-radius:6px; }}")
        box.layout.addWidget(pb)
        box.progress = pb
        return box

    def on_reset(self):
        self.sl_dist.setValue(5.0)
        self.sl_rain.setValue(10.0)
        self.sl_crowd.setValue(0.7)
        self.recompute()

    def recompute(self):
        d = self.sl_dist.value()
        r = self.sl_rain.value()
        c = self.sl_crowd.value()

        label, score, (mu_w, mu_b, mu_d), *_rest, explain = fis_recommend(d, r, c)

        col = {"Walk": "#10b981", "Bus": "#3b82f6", "Drive": "#ef4444"}.get(label, "#e5e7eb")
        self.mode_badge.setText(f"  {label}  ")
        self.mode_badge.setStyleSheet(
            f"background:{col}; border-radius:12px; padding:6px 10px; color:#ffffff; font-weight:600;"
        )
        self.suit_lbl.setText(f"Suitability: {score:.1f} / 10")
        self.why_lbl.setText(explain)

        self.pb_walk.progress.setValue(int(round(mu_w * 100)))
        self.pb_bus.progress.setValue(int(round(mu_b * 100)))
        self.pb_drive.progress.setValue(int(round(mu_d * 100)))

class QVBoxLayoutWidget(QWidget):
    """Tiny helper for a titled vertical block without borders."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.layout = lay
        if title:
            lbl = QLabel(title)
            lbl.setStyleSheet("color:#374151; font-weight:600;")
            lay.addWidget(lbl)

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 12))
    win = MinimalWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()