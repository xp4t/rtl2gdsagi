import os
import subprocess
import sys
import glob

base_dir = os.path.dirname(os.path.abspath(__file__))
runs = sorted(glob.glob(os.path.join(base_dir, "*", "run.yaml")))
pdk_root = "/home/vlsi/.volare/sky130A"
rtl2gdsagi_bin = os.path.abspath(os.path.join(base_dir, "..", ".venv", "bin", "rtl2gdsagi"))

print(f"Found {len(runs)} designs to test.")

for run_yaml in runs:
    design_name = os.path.basename(os.path.dirname(run_yaml))
    print(f"\n======================================")
    print(f"Testing design: {design_name}")
    print(f"======================================")
    
    cmd_str = f"bash -i -c '{rtl2gdsagi_bin} run --config {run_yaml} --pdk-root {pdk_root} --max-model-tokens 16384'"
    
    print(f"Running: {cmd_str}")
    result = subprocess.run(cmd_str, shell=True)
    
    if result.returncode == 0:
        print(f"[PASS] {design_name} successfully finished the flow.")
    else:
        print(f"[FAIL] {design_name} failed with exit code {result.returncode}.")
        
print("\nAll tests completed.")
