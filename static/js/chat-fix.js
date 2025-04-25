/**
 * Fix for the chat panel closing when running a file
 */
document.addEventListener('DOMContentLoaded', function() {
    // Override the openFile function to prevent page reload when running files from chat
    const originalOpenFile = window.openFile;

    window.openFile = function(path, preventReload = false) {
        if (preventReload) {
            // Get the project ID from the URL
            const projectId = window.location.pathname.split('/')[3];

            // Instead of navigating, fetch the file content via AJAX
            fetch(`/users/projects/${projectId}/code_editor/?file=${encodeURIComponent(path)}`)
                .then(response => response.text())
                .then(html => {
                    // Extract the file content from the HTML
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const fileContent = doc.getElementById('editor-textarea')?.value || '';

                    // Update the editor
                    const editorTextarea = document.getElementById('editor-textarea');
                    if (editorTextarea) {
                        editorTextarea.value = fileContent;
                    }

                    // Update the tab
                    const editorTabs = document.getElementById('editor-tabs');
                    const fileName = path.split('/').pop();

                    // Clear existing tabs
                    editorTabs.innerHTML = '';

                    // Create new tab
                    const tab = document.createElement('div');
                    tab.className = 'editor-tab active';
                    tab.setAttribute('data-path', path);
                    tab.innerHTML = `
                        <i class="bi bi-file-earmark-code"></i>
                        <span class="editor-tab-name">${fileName}</span>
                        <span class="editor-tab-close" onclick="closeTab('${path}')">×</span>
                    `;
                    editorTabs.appendChild(tab);

                    // Update hidden input for file path
                    const filePathInput = document.querySelector('input[name="file_path"]');
                    if (filePathInput) {
                        filePathInput.value = path;
                    }

                    // Show toast notification
                    if (window.showToast) {
                        window.showToast(`File ${fileName} opened`, 'success');
                    }

                    // Enable run button if container is running
                    const runFileBtn = document.getElementById('run-file-btn');
                    if (runFileBtn) {
                        runFileBtn.disabled = !window.containerRunning;
                    }
                })
                .catch(error => {
                    console.error('Error opening file:', error);
                    if (window.showToast) {
                        window.showToast(`Error opening file: ${error.message}`, 'error');
                    }
                });
        } else {
            // Use the original function for normal navigation
            originalOpenFile(path);
        }
    };

    // Override the runFileAfterSave function to use our new openFile function
    window.runFileAfterSave = function(filePath) {
        // Get the project ID from the URL
        const projectId = window.location.pathname.split('/')[3];

        // Call the API to run the file
        fetch(`/users/projects/${projectId}/run_file/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value
            },
            body: JSON.stringify({
                file_path: filePath
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Add command to terminal
                if (window.addTerminalMessage) {
                    window.addTerminalMessage(`$ ${data.command}`, 'command');

                    // Add stdout if any
                    if (data.stdout) {
                        window.addTerminalMessage(data.stdout, 'stdout');
                    }

                    // Add stderr if any
                    if (data.stderr) {
                        window.addTerminalMessage(data.stderr, 'stderr');
                    }

                    // Add completion message
                    if (data.return_code === 0) {
                        window.addTerminalMessage(`Process completed with exit code 0`, 'success');
                    } else {
                        window.addTerminalMessage(`Process completed with exit code ${data.return_code}`, 'error');
                    }
                }
            } else {
                // Add error message
                if (window.addTerminalMessage) {
                    window.addTerminalMessage(`Error: ${data.message}`, 'error');
                }
            }
        })
        .catch(error => {
            // Add error message
            if (window.addTerminalMessage) {
                window.addTerminalMessage(`Error: ${error.message}`, 'error');
            }
        });
    };

    // Override the sendMessage function to use our new openFile function
    const originalSendMessage = window.sendMessage;
    if (originalSendMessage) {
        window.sendMessage = function(message) {
            // Use the original function
            originalSendMessage(message);

            // Override the openFile function in the tool results handler
            const originalOpenFile = window.openFile;
            setTimeout(() => {
                // Find the openFile calls in the tool results handler
                const fileOperations = document.querySelectorAll('.chat-tool-result');
                fileOperations.forEach(op => {
                    // If this is a file operation, make sure we use preventReload=true
                    if (op.dataset.toolType === 'create_file' || op.dataset.toolType === 'update_file') {
                        const filePath = op.querySelector('.file-path')?.textContent;
                        if (filePath) {
                            // Open the file without reloading
                            window.openFile(filePath, true);
                        }
                    }
                });
            }, 1000); // Wait for the response to be processed
        };
    }

    // Make containerRunning available to our script
    // We'll check if the run button is enabled to determine if the container is running
    const runFileBtn = document.getElementById('run-file-btn');
    window.containerRunning = runFileBtn ? !runFileBtn.disabled : false;

    // Expose addTerminalMessage function globally
    if (typeof window.addTerminalMessage !== 'function') {
        window.addTerminalMessage = function(message, type) {
            const terminalOutput = document.getElementById('terminal-output');
            if (!terminalOutput) return;

            const messageDiv = document.createElement('div');
            messageDiv.className = `terminal-${type}`;
            messageDiv.textContent = message;

            terminalOutput.appendChild(messageDiv);
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        };
    }
});
