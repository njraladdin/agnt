import subprocess


print("Installing editable mode...")
subprocess.run(["pip", "install", "-e", '.'], check=True)