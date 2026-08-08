import subprocess
from concurrent.futures import ThreadPoolExecutor

def run_script(name):
    print(f"Starting {name}...")
    result = subprocess.run(["python", name], capture_output=True, text=True)
    print(f"--- {name} output ---\n{result.stdout}")
    if result.returncode != 0:
        print(f"--- {name} stderr ---\n{result.stderr}")
    return name, result.returncode

scripts = ["generate_images.py", "fetch_broll.py", "fetch_sfx.py"]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(run_script, scripts))

for name, code in results:
    status = "OK" if code == 0 else "FAILED (non-critical, pipeline continues)"
    print(f"{name}: {status}")
