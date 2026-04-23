import math

class ExtrusionCalculator:
    """
    Třída pro výpočet extruze (vytlačování kapaliny) pro 2D tisk.
    Převádí požadovaný objem na délku 'filamentu' (E-kroky) v G-kódu.
    """

    def __init__(self, filament_diameter=9.5, flow_multiplier=1.0, calibration_factor=1.0):
        self.filament_diameter = filament_diameter
        self.flow_multiplier = flow_multiplier
        # Plocha průřezu "virtuálního filamentu" v mm²
        self.filament_area = math.pi * ((self.filament_diameter / 2.0) ** 2)
        # Kalibrační faktor: kolik E jednotek (mm filamentu) odpovídá 1 µl objemu
        # Výchozí: 1 mm³ (1 µl) / filament_area
        self.calibration_factor = calibration_factor

    def calculate_e_per_mm(self, rate, unit="µl/mm", nozzle_diam=0.4, speed_mm_min=1500):
        """
        Vypočítá kolik mm filamentu (E) se má vytlačit na 1 mm dráhy.
        """
        if unit == "kroky/mm":
            return rate * self.flow_multiplier

        # 1. Objem v µl/mm
        volume_ul_mm = rate

        # 2. Převod na E jednotky pomocí kalibračního faktoru
        e_per_mm = volume_ul_mm * self.calibration_factor

        # 3. Aplikace multiplikátoru (Flow rate)
        e_per_mm *= self.flow_multiplier

        return e_per_mm

    def calculate_dot_extrusion(self, volume_ul, unit="µl"):
        """
        Vypočítá extruzi pro jeden bod (tečku).
        """
        if unit == "kroky":
            return volume_ul * self.flow_multiplier

        return volume_ul * self.calibration_factor * self.flow_multiplier

    def _apply_speed_compensation(self, e_per_mm, speed_mm_min):
        # Placeholder pro budoucí vývoj (viskozita, tlakové kompenzace)
        return e_per_mm

# Příklad použití:
# calc = ExtrusionCalculator(filament_diameter=9.5)
# e_step = calc.calculate_e_per_mm(volume_ul_cm=10.0) # pro 10µl/cm
