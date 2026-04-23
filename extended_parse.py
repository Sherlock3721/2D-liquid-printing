import ast
import os

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception:
        return None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    
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
                        # self.variable
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == 'self':
                            vars_set.add(t.attr)
                        # pyqtSignal
                        if isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and n.value.func.id == 'pyqtSignal':
                            if isinstance(t, ast.Name):
                                signals.add(t.id)
                            elif isinstance(t, ast.Attribute):
                                signals.add(t.attr)
                elif isinstance(n, ast.Call):
                    # .connect()
                    if isinstance(n.func, ast.Attribute) and n.func.attr == 'connect':
                        if isinstance(n.func.value, ast.Attribute):
                            sig = n.func.value.attr
                            connections.add(sig)
                        elif isinstance(n.func.value, ast.Name):
                            sig = n.func.value.id
                            connections.add(sig)
            
            classes[c_name] = {
                'vars': sorted(list(vars_set)),
                'signals': sorted(list(signals)),
                'connections': sorted(list(connections))
            }
    return classes

def main():
    base_dir = "."
    dirs_to_scan = ['core', 'gui']
    individual_files = ['main.py', 'printer_com.py']
    
    all_results = {}
    
    for f in individual_files:
        res = analyze_file(f)
        if res: all_results[f] = res
            
    for d in dirs_to_scan:
        path = os.path.join(base_dir, d)
        if not os.path.exists(path): continue
        for entry in os.listdir(path):
            if entry.endswith(".py") and entry != "__init__.py":
                f_path = os.path.join(d, entry)
                res = analyze_file(f_path)
                if res: all_results[f_path] = res

    # Format for Markdown
    for f_path, classes in sorted(all_results.items()):
        print(f"### [[{f_path}]]")
        for c_name, data in classes.items():
            print(f"- **Třída `{c_name}`**")
            if data['vars']:
                # Limit to most important/representative if too many
                v_str = ", ".join(f"`{v}`" for v in data['vars'][:15])
                if len(data['vars']) > 15: v_str += " ..."
                print(f"  - Proměnné: {v_str}")
            if data['signals']:
                s_str = ", ".join(f"`{s}`" for s in data['signals'])
                print(f"  - Signály: {s_str}")
            if data['connections']:
                c_str = ", ".join(f"`{c}`" for c in data['connections'])
                print(f"  - Konexe: {c_str}")
        print()

if __name__ == "__main__":
    main()
