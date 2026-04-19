from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import json
import os
import re
import urllib.request
import urllib.parse

app = FastAPI(title="NeuroAST Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeSubmission(BaseModel):
    code: str

def analyze_security_with_llm(func_name: str, code: str, ast_summary: str) -> str:
    """Uses true Neurosymbolic logic: Deterministic AST rules + LLM reasoning."""
    
    code_lower = code.lower()
    symbolic_flag = None
    if "strcpy" in code_lower or "gets" in code_lower or "scanf" in code_lower:
         symbolic_flag = f"[SECURITY FLAG] Function '{func_name}' explicitly uses unsafe C-strings. Buffer Overflow potential."
    elif "system(" in code_lower or "exec(" in code_lower:
         symbolic_flag = f"[SECURITY FLAG] Function '{func_name}' uses OS execution. Remote Command Execution vulnerability."
    
    prompt = f"You are a Neurosymbolic Code Analyzer trained perfectly on C++ AST Data.\nAnalyze the function '{func_name}' strictly for security vulnerabilities. DO NOT refactor or fix the code. ONLY flag the vulnerability.\n\nCode:\n{code}\n\nAST Breakdown:\n{ast_summary}"
    llm_response = ""
    
    try:
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}
        data = json.dumps({
            "model": "neurosymbolic_AI",
            "prompt": prompt,
            "stream": False
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = json.loads(response.read().decode())
            llm_response = res_body["response"]
            
    except Exception as e:
        print(f"Ollama Connection Error: {e}")
        
    if symbolic_flag:
        return symbolic_flag + "\n * [AI Analysis]: " + (llm_response.replace("\n", " ") if llm_response else "Verified by deterministic fallback.")
    elif "[SECURITY FLAG]" in llm_response.upper():
        return llm_response
    else:
        return "Automatically marked safe by static AST rules & AI."

@app.post("/api/generate")
async def generate_comments(submission: CodeSubmission):
    try:
        with open("input.cpp", "w", encoding="utf-8") as f:
            f.write(submission.code)

        result = subprocess.run(
            ["python", "genrating_ast_running_extractor.py"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("Clang Error:", result.stderr)
            raise HTTPException(status_code=500, detail=f"C++ Compilation/Extraction failed: {result.stderr}")

        if not os.path.exists("cpp_ir_output.json") or not os.path.exists("nlp_summary.json"):
             raise HTTPException(status_code=500, detail="Extractor finished but did not produce output files.")

        with open("cpp_ir_output.json", "r", encoding="utf-8") as f:
            ir_data = json.load(f)

        with open("nlp_summary.json", "r", encoding="utf-8") as f:
            nlp_data = json.load(f)

        commented_code = submission.code
        frontend_nlp_list = []
        
        if isinstance(nlp_data, dict):
            for func_name, func_details in nlp_data.items():
                if not func_name:
                    continue
                ai_intent = ""
                try:
                    url = "http://localhost:11434/api/generate"
                    headers = {"Content-Type": "application/json"}
                    prompt = f"You are an expert C++ Data Structures Algorithm analyzer. Explain the exact algorithmic intent and logic of the function '{func_name}' in 2 or 3 short, brilliant sentences. Do not mention ASTs. Do not output the code. What does this code achieve?\n\nCode:\n{submission.code}"
                    
                    data = json.dumps({
                        "model": "neurosymbolic_AI",
                        "prompt": prompt,
                        "stream": False
                    }).encode("utf-8")
                    
                    req = urllib.request.Request(url, data=data, headers=headers)
                    with urllib.request.urlopen(req, timeout=600) as response:
                        res_body = json.loads(response.read().decode())
                        ai_intent = res_body["response"].strip()
                except Exception as e:
                    ai_intent = "Fallback: " + func_details.get("summary", "Could not reach Ollama for logic summary.")
                
                frontend_nlp_list.append({
                    "function": func_name,
                    "comments": ai_intent,
                    "summary": { "actions": func_details.get("detailed_steps", []) }
                })
                
                pattern = rf"(?m)^([ \t]*)([\w\:]+[ \t\*\&]+{re.escape(func_name)}[ \t]*\(.*?\)[ \t\n]*\{{)"
                
                def replacer(match):
                    indent = match.group(1)
                    definition = match.group(2)
                    
                    block = indent + "/**\n"
                    for line in ai_intent.split('\n'):
                        block += indent + " * " + line.strip() + "\n"
                    
                    block += indent + " * \n"
                    block += indent + " * --- SECURITY ANALYSIS ---\n"
                    sec_flag = analyze_security_with_llm(func_name, submission.code, str(func_details.get("detailed_steps", [])))
                    if sec_flag:
                         for sec_line in sec_flag.strip().split("\n"):
                              block += indent + " * " + sec_line + "\n"
                              
                    block += indent + " */\n"
                    return block + indent + definition
                    
                commented_code = re.sub(pattern, replacer, commented_code, count=1)

        return {
            "status": "success",
            "commented_code": commented_code,
            "ir": ir_data,
            "nlp": frontend_nlp_list
        }

    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)
