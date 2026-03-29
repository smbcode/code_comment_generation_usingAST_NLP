import subprocess
import os
import json
import enhanced_cpp_extractor

input_file = "input.cpp"
ast_file = "ast1.json"

print("Generating AST...")

# Run clang and capture output
result = subprocess.run(
    [
        "clang++",
        "-std=c++17",
        "-Xclang", "-ast-dump=json",
        "-fsyntax-only",
        input_file
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Check for errors
if result.returncode != 0:
    print("[ERROR] Clang failed:")
    print(result.stderr)
    exit(1)

raw_output = result.stdout.strip()

if not raw_output:
    print("[ERROR] Empty AST output")
    exit(1)

# Parse the single JSON TranslationUnitDecl
try:
    ast_data = json.loads(raw_output)
except json.JSONDecodeError as e:
    print("[ERROR] Failed to parse AST JSON:", e)
    exit(1)

# Filter out nodes from included header files
json_objects = []
current_file = ""

for node in ast_data.get("inner", []):
    loc = node.get("loc", {})
    
    # Update current file if 'loc' contains 'file'
    if isinstance(loc, dict) and "file" in loc:
        current_file = loc["file"]
        
    # Only append nodes that come from our input file
    if input_file in current_file:
        json_objects.append(node)

# Save as proper JSON array for the extractor
with open(ast_file, "w", encoding="utf-8") as f:
    json.dump(json_objects, f, indent=2)

print("AST generated.")

# Run extractor
print("Running extractor...")
enhanced_cpp_extractor.run_function()

print("Process complete.")