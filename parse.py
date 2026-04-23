import ast
import os

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception:
        return
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return
    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            c_name = node.name
            vars_set = set()
            signals = set()
            connections = set()
            for n in ast.walk(node):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == 'self':
                            vars_set.add(t.attr)
                        if isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and n.value.func.id == 'pyqtSignal':
                            if isinstance(t, ast.Name):
                                signals.add(t.id)
                            elif isinstance(t, ast.Attribute):
                                signals.add(t.attr)
                elif isinstance(n, ast.Call):
                    if isinstance(n.func, ast.Attribute) and n.func.attr == 'connect':
                        # roughly capture connection
                        if isinstance(n.func.value, ast.Attribute):
                            sig = n.func.value.attr
                            connections.add(sig)
            if vars_set or signals or connections:
                classes[c_name] = {'vars': list(vars_set), 'signals': list(signals), 'connections': list(connections)}
    if classes:
        print(f"--- {filepath} ---")
        for c, data in classes.items():
            print(f"  Class: {c}")
            if data['vars']: print(f"    Vars: {', '.join(data['vars'][:10])}")
            if data['signals']: print(f"    Signals: {', '.join(data['signals'])}")
            if data['connections']: print(f"    Connections: {', '.join(data['connections'])}")

files_to_check = [
    'main.py', 'core/logic.py', 'core/gcode_generator.py', 'core/csv_exporter.py',
    'core/vector_slicer.py', 'gui/left_panel.py', 'gui/right_panel.py', 'gui/graphics_view.py',
    'gui/settings.py', 'printer_com.py'
]
for f in files_to_check:
    analyze_file(f)
