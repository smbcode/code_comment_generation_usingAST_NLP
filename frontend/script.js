// Configuration for Monaco Editor loader
require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }});

// Default C++ boilerplate
const DEFAULT_CODE = `#include <iostream>
using namespace std;
// This is basic boilerplate code for C++ paste your code here 
//or edit it
// This function multiplies two integers
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

// Auto-load Monaco editor when AMD require is ready
require(['vs/editor/editor.main'], function() {
    
    const container = document.getElementById('editor-container');
    
    // Define a custom sophisticated dark theme based on our CSS variables
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
});

// UI Interaction
document.addEventListener("DOMContentLoaded", () => {
    const generateBtn = document.getElementById("generateBtn");
    const outputContainer = document.getElementById("output-container");
    const emptyState = document.querySelector(".empty-state");

    generateBtn.addEventListener("click", () => {
        // Validate editor is loaded
        if (!editorInstance) return;

        const currentCode = editorInstance.getValue();
        
        // Ensure there's code to run
        if (!currentCode.trim()) {
            alert("Please enter some C++ code first.");
            return;
        }

        // UX: loading state
        generateBtn.classList.add("loading");
        const originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<i class="fa-solid fa-spinner"></i> Analyzing AST...';
        
        // Remove empty state if present
        if (emptyState) {
            outputContainer.innerHTML = '';
        }

        // MOCK BACKEND REQUEST (Timeout to simulate network/processing delay)
        setTimeout(() => {
            // Restore button
            generateBtn.classList.remove("loading");
            generateBtn.innerHTML = originalText;

            // Render mock results
            renderMockResults();
        }, 1500); 
    });
    
    function renderMockResults() {
        // This is a placeholder for when we actually plug in the neurosymbolic layout
        // For now, it dynamically injects HTML simulating an NLP summary

        const resultHTML = `
            <div class="result-card" style="animation-delay: 0.1s">
                <h4><i class="fa-solid fa-microchip"></i> AST Extraction</h4>
                <p>Successfully extracted 2 functions (<code>fun</code>, <code>main</code>) and 4 local variables. No recursive calls detected.</p>
            </div>
            
            <div class="result-card" style="animation-delay: 0.2s">
                <h4><i class="fa-solid fa-code-compare"></i> Neurosymbolic Analysis</h4>
                <p><strong>Intent:</strong> The code performs a basic arithmetic multiplication operation within a dedicated function and outputs the result using standard I/O streams.</p>
            </div>

            <div class="result-card" style="animation-delay: 0.3s">
                <h4><i class="fa-solid fa-comment-dots"></i> Generated Documentation</h4>
                <p style="font-family: monospace; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 4px; border: 1px solid var(--border-color); color: #fff;">
/**
 * Executes a basic entry-point routine.
 * Initializes test parameters, performs a multiplication via fun(),
 * and streams the result '45' to standard output.
 * @returns {int} Exit status code.
 */
                </p>
            </div>
        `;

        // We replace the inner HTML to ensure freshness
        outputContainer.innerHTML = resultHTML;
    }
});
