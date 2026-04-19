require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }});

// Default C++ boilerplate
const DEFAULT_CODE = `#include <iostream>
using namespace std;
// This is basic boilerplate code for C++ paste your code here 
//or edit it
int fun(int a, int b){
    int c = a * b;
    return c;
}

int main() {
    int x = 5;
    int y = 9;
    
    int result = fun(x, y);
    cout << "Result: " << result << endl;
    
    return 0;
}`;

let editorInstance;
let outputEditorInstance;

require(['vs/editor/editor.main'], function() {
    
    const container = document.getElementById('editor-container');
    
    monaco.editor.defineTheme('neuro-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'comment', foreground: '64748b', fontStyle: 'italic' },
            { token: 'keyword', foreground: '818cf8', fontStyle: 'bold' },
            { token: 'string', foreground: '2dd4bf' },
            { token: 'number', foreground: 'f472b6' },
            { token: 'type', foreground: '22d3ee' }
        ],
        colors: {
            'editor.background': '#111827', 
            'editor.foreground': '#f8fafc',
            'editorLineNumber.foreground': '#475569',
            'editor.lineHighlightBackground': '#1e293b', 
            'editor.selectionBackground': '#334155',
            'editorCursor.foreground': '#22d3ee',
        }
    });

    editorInstance = monaco.editor.create(container, {
        value: DEFAULT_CODE,
        language: 'cpp',
        theme: 'neuro-dark',
        automaticLayout: true,
        fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
        fontSize: 14,
        fontLigatures: true,
        minimap: { enabled: false }, // disable minimap to save space
        padding: { top: 16, bottom: 16 },
        scrollBeyondLastLine: false,
        smoothScrolling: true,
        cursorBlinking: "smooth",
        cursorSmoothCaretAnimation: "on"
    });

    outputEditorInstance = monaco.editor.create(document.getElementById('output-editor'), {
        value: "// Generated code will appear here...",
        language: 'cpp',
        theme: 'neuro-dark',
        automaticLayout: true,
        fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
        fontSize: 14,
        readOnly: true,
        minimap: { enabled: false },
        padding: { top: 16, bottom: 16 },
        scrollBeyondLastLine: false,
        smoothScrolling: true,
        wordWrap: "on"
    });
});

document.addEventListener("DOMContentLoaded", () => {
    const generateBtn = document.getElementById("generateBtn");
    const outputContainer = document.getElementById("output-container");
    const emptyState = document.querySelector(".empty-state");

    generateBtn.addEventListener("click", async () => {
        if (!editorInstance) return;
        const currentCode = editorInstance.getValue();
        if (!currentCode.trim()) {
            alert("Please enter some C++ code first.");
            return;
        }

        generateBtn.classList.add("loading");
        const originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<i class="fa-solid fa-spinner"></i> Analyzing AST...';

        try {
            const response = await fetch("http://127.0.0.1:8000/api/generate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ code: currentCode })
            });

            if (!response.ok) {
                throw new Error("Server error: " + response.statusText);
            }

            const data = await response.json();
            
            const emptyStateWrapper = document.getElementById("empty-state-wrapper");
            const outputEditorEl = document.getElementById("output-editor");
            
            if (emptyStateWrapper) emptyStateWrapper.style.display = "none";
            outputEditorEl.style.display = "flex";

            if (data.commented_code) {
                outputEditorInstance.setValue(data.commented_code);
            } else {
                outputEditorInstance.setValue("// An error occurred: No code returned from backend.");
            }
            outputEditorInstance.layout();

            generateBtn.classList.remove("loading");
            generateBtn.innerHTML = originalText;

        } catch (error) {
            generateBtn.classList.remove("loading");
            generateBtn.innerHTML = originalText;
            
            if (outputEditorInstance) {
                const emptyStateWrapper = document.getElementById("empty-state-wrapper");
                const outputEditorEl = document.getElementById("output-editor");
                if (emptyStateWrapper) emptyStateWrapper.style.display = "none";
                outputEditorEl.style.display = "flex";
                
                outputEditorInstance.setValue(`/*\n * API ERROR\n * ${error.message}\n */`);
            } else {
                alert("Analysis Failed: " + error.message);
            }
        }
    });
});
