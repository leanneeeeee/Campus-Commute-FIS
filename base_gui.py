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
# Distance (5 terms)
distance['very_near'] = fuzz.trapmf(distance.universe, [0, 0, 1, 2.5])
distance['near'] = fuzz.trimf(distance.universe, [1, 3, 5])
distance['medium'] = fuzz.trimf(distance.universe, [3.5, 7, 10.5])
distance['far'] = fuzz.trimf(distance.universe, [9, 13, 17])
distance['very_far'] = fuzz.trapmf(distance.universe, [15, 17.5, 20, 20])

# Rain Intensity (3 terms)
rain['low'] = fuzz.trapmf(rain.universe, [0, 0, 10, 30])
rain['moderate'] = fuzz.trimf(rain.universe, [20, 50, 80])
rain['heavy'] = fuzz.trapmf(rain.universe, [70, 90, 100, 100])

# Bus Crowding (3 terms)
crowd['low'] = fuzz.trapmf(crowd.universe, [0, 0, 0.3, 0.6])
crowd['medium'] = fuzz.trimf(crowd.universe, [0.4, 0.8, 1.2])
crowd['high'] = fuzz.trapmf(crowd.universe, [1.0, 1.3, 1.5, 1.5])

# Output MF (3 terms)
for output in [walk_suitability, bus_suitability, drive_suitability]:
    output['low'] = fuzz.trapmf(output.universe, [0, 0, 25, 40])
    output['medium'] = fuzz.trimf(output.universe, [30, 50, 70])
    output['high'] = fuzz.trapmf(output.universe, [60, 75, 100, 100])


# Section 4: Fuzzy Rules Definition
rules = []

# Distance labels used as columns (5 terms)
D_COLS = ['very_near', 'near', 'medium', 'far', 'very_far']
# Rain labels used as rows (3 terms)
R_ROWS = ['low', 'moderate', 'heavy']
# Crowd labels used as tables (3 terms)
C_TABLES = ['low', 'medium', 'high']

# Helper to add a single rule from (mode, level)
def _add_rule(d_lab, r_lab, c_lab, mode, level):
    cons_map = {'walk': walk_suitability, 'bus': bus_suitability, 'drive': drive_suitability}
    rules.append(ctrl.Rule(distance[d_lab] & rain[r_lab] & crowd[c_lab], cons_map[mode][level]))

# --- NEW RULE TABLES (5x3x3 = 45 rules) ---

# Table 1: Bus Crowding = low (Bus is favorable/Walk for short distances)
T_LOW_CROWD = {
    # Dist: V_Near, Near, Medium, Far, V_Far
    'low':      {'very_near': ('walk','high'),  'near': ('walk','high'),  'medium': ('bus','high'),  'far': ('bus','high'),  'very_far': ('bus','high')},
    'moderate': {'very_near': ('walk','medium'),'near': ('walk','medium'),'medium': ('bus','high'),  'far': ('bus','high'),  'very_far': ('bus','medium')},
    'heavy':    {'very_near': ('walk','low'),   'near': ('bus','medium'), 'medium': ('bus','high'),  'far': ('drive','medium'),'very_far': ('drive','high')},
}

# Table 2: Bus Crowding = medium (Walk preferred for short, Bus still viable mid-distance, Drive for long)
T_MEDIUM_CROWD = {
    # Dist: V_Near, Near, Medium, Far, V_Far
    'low':      {'very_near': ('walk','high'),  'near': ('walk','medium'),'medium': ('bus','medium'), 'far': ('bus','medium'), 'very_far': ('drive','medium')},
    'moderate': {'very_near': ('walk','medium'),'near': ('bus','medium'), 'medium': ('bus','medium'), 'far': ('drive','medium'),'very_far': ('drive','medium')},
    'heavy':    {'very_near': ('bus','low'),    'near': ('drive','medium'),'medium': ('drive','medium'),'far': ('drive','high'),  'very_far': ('drive','high')},
}

# Table 3: Bus Crowding = high (Bus strongly penalized, Drive preferred for long distance)
T_HIGH_CROWD = {
    # Dist: V_Near, Near, Medium, Far, V_Far
    'low':      {'very_near': ('walk','high'),  'near': ('walk','low'),   'medium': ('drive','medium'),'far': ('drive','high'),  'very_far': ('drive','high')},
    'moderate': {'very_near': ('walk','medium'),'near': ('bus','low'),    'medium': ('drive','medium'),'far': ('drive','high'),  'very_far': ('drive','high')},
    'heavy':    {'very_near': ('drive','medium'),'near': ('drive','medium'),'medium': ('drive','high'),  'far': ('drive','high'),  'very_far': ('drive','high')},
}

# Iterate through all 45 rules and add them
rule_tables = {'low': T_LOW_CROWD, 'medium': T_MEDIUM_CROWD, 'high': T_HIGH_CROWD}

for c_lab, table in rule_tables.items():
    for r_lab, row in table.items():
        for d_lab, (mode, level) in row.items():
            _add_rule(d_lab, r_lab, c_lab, mode, level)

# Baseline rules to ensure every consequent always yields a value (prevents missing outputs)
any_distance = distance['very_near'] | distance['near'] | distance['medium'] | distance['far'] | distance['very_far']
any_rain     = rain['low'] | rain['moderate'] | rain['heavy']
any_crowd    = crowd['low'] | crowd['medium'] | crowd['high']

rules.append(ctrl.Rule(any_distance & any_rain & any_crowd, walk_suitability['low']))
rules.append(ctrl.Rule(any_distance & any_rain & any_crowd, bus_suitability['low']))
rules.append(ctrl.Rule(any_distance & any_rain & any_crowd, drive_suitability['low']))

system = ctrl.ControlSystem(rules)

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

    # Fresh simulation each call to avoid stale state
    sim = ctrl.ControlSystemSimulation(system)

    try:
        sim.input['distance'] = d
        sim.input['rain_intensity'] = r
        sim.input['bus_crowding'] = c
        sim.compute()

        # Safe reads: some consequents might have no activation -> missing key
        outs = sim.output

        def safe_get(name: str) -> float:
            v = outs[name] if name in outs else 0.0
            try:
                v = float(v)
            except Exception:
                v = 0.0
            if np.isnan(v):
                v = 0.0
            return v

        walk_score = safe_get('walk_suitability')
        bus_score = safe_get('bus_suitability')
        drive_score = safe_get('drive_suitability')

    except Exception as e:
        print(f"FIS compute error: {e}")
        # Default fallback values
        walk_score = 0.0
        bus_score = 0.0
        drive_score = 0.0

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
        # Handle case where all membership is 0 (shouldn't happen with proper MF coverage)
        if not scores_list:
            return "N/A"
        return max(scores_list, key=lambda t: t[1])[0]

    dL = best_label(distance, d, ['very_near', 'near', 'medium', 'far', 'very_far'])
    rL = best_label(rain, r, ['low', 'moderate', 'heavy']) # Updated labels
    cL = best_label(crowd, c, ['low', 'medium', 'high'])    # Updated labels

    explain = (f"{label} (suitability={crisp:.1f}/10) — distance {dL}, rain {rL}, crowd {cL}.")
    return label, crisp, (mu_w, mu_b, mu_d), (d, r, c), explain

# Section 6: GUI Design (GUI code remains the same as it handles any input range)

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
        pb.setTextVisible(True)
        pb.setFormat("%p%")
        pb.setStyleSheet(f"QProgressBar::chunk {{ background:{color_hex}; border-radius:6px; }}")
        box.layout.addWidget(pb)
        val = QLabel("0%")
        val.setStyleSheet("color:#6b7280;")
        box.layout.addWidget(val)
        box.progress = pb
        box.value_label = val
        return box

    def on_reset(self):
        # Reset to new sensible defaults for the new system
        self.sl_dist.setValue(5.0)
        self.sl_rain.setValue(10.0)
        self.sl_crowd.setValue(0.7)
        self.recompute()

    def recompute(self, *_):  # Accept and ignore signal args
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

        # Update numeric labels so percentages are always visible
        self.pb_walk.value_label.setText(f"{int(round(mu_w * 100))}%")
        self.pb_bus.value_label.setText(f"{int(round(mu_b * 100))}%")
        self.pb_drive.value_label.setText(f"{int(round(mu_d * 100))}%")

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

# Entrypoint

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 12))
    win = MinimalWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()