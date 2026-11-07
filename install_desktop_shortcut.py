"""
Desktop shortcut installer utility for Windows.
"""

import os
import sys
import subprocess


def install_desktop_shortcut():
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    shortcut_path = os.path.join(desktop, 'AutoCAD 2026.lnk')
    cad_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(cad_dir, 'AutoCAD 2026', 'AutoCAD 2026.exe')
    main_py = os.path.join(cad_dir, 'main.py')
    icon_path = os.path.join(cad_dir, 'icons', 'autocad.ico')

    if os.path.exists(exe_path):
        target_path = exe_path
        arguments = ""
        work_dir = os.path.join(cad_dir, 'AutoCAD 2026')
    else:
        python_exe = sys.executable
        pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
        target_path = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
        arguments = f'"{main_py}"'
        work_dir = cad_dir

    # PowerShell script to create the Windows Shortcut (.lnk)
    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_path}"
$Shortcut.Arguments = '{arguments}'
$Shortcut.WorkingDirectory = "{work_dir}"
$Shortcut.IconLocation = "{icon_path}, 0"
$Shortcut.Description = "AutoCAD 2026 Engine - Computer Aided Design Suite"
$Shortcut.WindowStyle = 1
$Shortcut.Save()
"""

    ps_file = os.path.join(cad_dir, "_temp_shortcut.ps1")
    with open(ps_file, "w", encoding="utf-8") as f:
        f.write(ps_script)

    try:
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_file], check=True)
    finally:
        if os.path.exists(ps_file):
            os.remove(ps_file)

    if os.path.exists(shortcut_path):
        print(f"SUCCESS: Desktop shortcut installed successfully at: {shortcut_path}")
        return True
    else:
        print("ERROR: Failed to create shortcut.")
        return False


if __name__ == "__main__":
    install_desktop_shortcut()
