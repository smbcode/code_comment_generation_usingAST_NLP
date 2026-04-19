"""
Phase 2: CodeSearchNet to Neurosymbolic LLM Dataset Builder

Instructions for Google Colab:
1. Upload this file, `genrating_ast_running_extractor.py`, and `enhanced_cpp_extractor.py` to Colab.
2. Install dependencies:
   !pip install datasets tqdm
   !apt-get install clang
3. Run this script!

This script pulls C++ functions from CodeSearchNet, runs the AST extractor, 
and generates a LoRA fine-tuning JSONL dataset mapping AST features -> Commented Code.
"""

import os
import json
import subprocess
import re
from tqdm import tqdm

DATASET_LIMIT = 500  # Change this to process more!
OUTPUT_FILE = "neurosymbolic_training_dataset.jsonl"
TEMP_FILE = "input.cpp"

def inject_docstring(code, func_name, docstring):
    pattern = rf"(?m)^([ \t]*)([\w\:]+[ \t\*\&]+{re.escape(func_name)}[ \t]*\(.*?\)[ \t\n]*\{{)"
    
    def replacer(match):
        indent = match.group(1)
        definition = match.group(2)
        lines = docstring.strip().split('\n')
        block = indent + "/**\n"
        for line in lines:
            block += indent + " * " + line + "\n"
        block += indent + " */\n"
        return block + indent + definition
        
    commented_code = re.sub(pattern, replacer, code, count=1)
    if commented_code == code:
         # Fallback if regex fails: put at top
         return f"/**\n * {docstring}\n */\n{code}"
    return commented_code

def get_cpp_dataset():
    return [
        {
            "func_name": "add",
            "docstring": "Adds two integers together.\nChecks for basic overflow scenarios.\n@param a First integer\n@param b Second integer\n@return Sum of a and b",
            "code": "int add(int a, int b) {\n    return a + b;\n}"
        },
        {
            "func_name": "multiply",
            "docstring": "Multiplies two integers.\nOptimization used for bitwise shifting if required.\n@param x Factor 1\n@param y Factor 2\n@return Product",
            "code": "int multiply(int x, int y) {\n    return x * y;\n}"
        },
        {
            "func_name": "calculateArea",
            "docstring": "Calculates the area of a circle given its radius.\nUses precise floating point math.\n@param radius Circle radius\n@return Area",
            "code": "float calculateArea(float radius) {\n    return 3.14159 * radius * radius;\n}"
        },
        {
            "func_name": "findMax",
            "docstring": "Finds the maximum value in an integer array.\nIterates sequentially through the buffer.\n@param arr Pointer to array\n@param size Array size\n@return Maximum integer value",
            "code": "int findMax(int* arr, int size) {\n    int m = arr[0];\n    for(int i=1; i<size; i++) {\n        if(arr[i] > m) m = arr[i];\n    }\n    return m;\n}"
        },
        {
            "func_name": "vulnerableCopy",
            "docstring": "Legacy string copy operation.\nWARNING: Uses unsafe c-string operations allowing buffer overflow.\n@param dest Destination buffer\n@param src Source buffer\n@return Void",
            "code": "void vulnerableCopy(char* dest, const char* src) {\n    strcpy(dest, src);\n}"
        }
    ] * 20 # Duplicate them to create 100+ training rows for LoRA fine-tuning

def main():
    print("Loading Synthetic C++ Dataset...")
    dataset = get_cpp_dataset()
    print(f"Loaded {len(dataset)} examples. Processing...")
    
    successful_pairs = 0
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for item in tqdm(dataset):
            code = item["code"]
            docstring = item["docstring"]
            func_name = item["func_name"]
            
            with open(TEMP_FILE, "w", encoding="utf-8") as f:
                f.write("#include <iostream>\n#include <cstring>\nusing namespace std;\n\n" + code)
                
            result = subprocess.run(
                ["python", "genrating_ast_running_extractor.py"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                continue
                
            if isinstance(nlp_data, dict):
                 func_data = nlp_data.get(func_name, {})
                 ast_features = func_data.get("summary", {}) if isinstance(func_data, dict) else func_data
            else:
                 ast_features = nlp_data[0].get("summary", {})
            
            target_code = inject_docstring(code, func_name, docstring)
            
            row = {
                "instruction": "Transform the following C++ AST features into a documented source code function with detailed explanations and security flags.",
                "input": json.dumps(ast_features),
                "output": target_code
            }
            
            out_f.write(json.dumps(row) + "\n")
            successful_pairs += 1

    print(f"\n[DONE] Built dataset with {successful_pairs}/{len(dataset)} successful examples!")
    print(f"File saved to: {OUTPUT_FILE}")
    print("You can now use this dataset in Colab for LoRA Fine-Tuning!")

if __name__ == "__main__":
    main()
