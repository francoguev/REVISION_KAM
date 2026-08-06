import subprocess

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=r'C:\Users\gueva\.gemini\antigravity\scratch\sales_dashboard')
    print(f"Command: {cmd}\nExit Code: {result.returncode}\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}\n")

run_cmd("git add .")
run_cmd('git commit -m "feat: Add Inicio Portada, reorder pages 0-7, unify Tabla Presentacion rules, and update Page 3 Cedente in Red"')
run_cmd("git push origin main")
