import math

class ExtrusionCalculator:
    """
    Třída pro výpočet extruze (vytlačování kapaliny) pro 2D tisk.
    Převádí požadovaný objem na délku 'filamentu' (E-kroky) v G-kódu.
    """
    
    def __init__(self, filament_diameter=1.75, flow_multiplier=1.0):
        self.filament_diameter = filament_diameter
        self.flow_multiplier = flow_multiplier
        # Plocha průřezu "virtuálního filamentu" v mm²
        self.filament_area = math.pi * ((self.filament_diameter / 2.0) ** 2)

    def calculate_e_per_mm(self, volume_ul_cm, nozzle_diam=0.4, speed_mm_min=1500):
        """
        Vypočítá kolik mm filamentu (E) se má vytlačit na 1 mm dráhy.
        
        Args:
            volume_ul_cm: Požadovaný objem v mikrolitrech na centimetr dráhy (µl/cm).
            nozzle_diam: Průměr trysky v mm (pro případné korekce šířky čáry).
            speed_mm_min: Rychlost tisku (pro budoucí rychlostní kompenzace).
            
        Returns:
            Délka filamentu v mm na 1 mm dráhy (E/mm).
        """
        # 1. Převod µl/cm na mm³/mm (objem na jednotku délky)
        # 1 µl = 1 mm³
        # 1 cm = 10 mm
        volume_mm3_mm = volume_ul_cm / 10.0
        
        # 2. Výpočet délky filamentu potřebné pro tento objem
        # Volume = Area * Length  => Length = Volume / Area
        e_per_mm = volume_mm3_mm / self.filament_area
        
        # 3. Aplikace multiplikátoru (Flow rate)
        e_per_mm *= self.flow_multiplier
        
        # 4. Zde mohou být budoucí kompenzace (např. nelineární flow při vysokých rychlostech)
        # e_per_mm = self._apply_speed_compensation(e_per_mm, speed_mm_min)
        
        return e_per_mm

    def calculate_dot_extrusion(self, volume_ul):
        """
        Vypočítá extruzi pro jeden bod (tečku) o daném objemu.
        
        Args:
            volume_ul: Objem jedné tečky v mikrolitrech (µl).
            
        Returns:
            Celková délka filamentu (E) v mm.
        """
        volume_mm3 = volume_ul
        return (volume_mm3 / self.filament_area) * self.flow_multiplier

    def _apply_speed_compensation(self, e_per_mm, speed_mm_min):
        # Placeholder pro budoucí vývoj (viskozita, tlakové kompenzace)
        return e_per_mm

# Příklad použití:
# calc = ExtrusionCalculator(filament_diameter=1.75)
# e_step = calc.calculate_e_per_mm(volume_ul_cm=10.0) # pro 10µl/cm
