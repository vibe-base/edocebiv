/**
 * JavaScript for AI Reasoning functionality
 */

// Format code blocks in reasoning responses
function formatCodeBlocks() {
    document.querySelectorAll('.markdown-content').forEach(element => {
        // Replace code blocks with proper formatting
        element.innerHTML = element.innerHTML.replace(/```(\w*)([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
        
        // Replace inline code
        element.innerHTML = element.innerHTML.replace(/`([^`]+)`/g, '<code>$1</code>');
    });
}

// Show loading indicator
function showLoading(message = 'Processing...') {
    const loadingModal = new bootstrap.Modal(document.getElementById('loading-modal'));
    document.getElementById('loading-message').textContent = message;
    loadingModal.show();
    return loadingModal;
}

// Hide loading indicator
function hideLoading(loadingModal) {
    if (loadingModal) {
        loadingModal.hide();
    }
}

// Execute a reasoning step
function executeReasoningStep(projectId, sessionId, stepType, prompt, callback) {
    const loadingModal = showLoading('The AI is working on this step. This may take a minute...');
    
    fetch(`/users/projects/${projectId}/reasoning/sessions/${sessionId}/step/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            step_type: stepType,
            prompt: prompt
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading(loadingModal);
        
        if (data.status === 'success') {
            if (callback) callback(data);
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        hideLoading(loadingModal);
        alert(`Error: ${error.message}`);
    });
}

// Execute a full reasoning chain
function executeFullReasoning(projectId, task, context, callback) {
    const loadingModal = showLoading('Executing full reasoning chain. This may take several minutes...');
    
    fetch(`/users/projects/${projectId}/reasoning/execute/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            task: task,
            current_file: context.currentFile || null,
            current_file_content: context.currentFileContent || null
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading(loadingModal);
        
        if (data.status === 'success') {
            if (callback) callback(data);
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        hideLoading(loadingModal);
        alert(`Error: ${error.message}`);
    });
}

// Get CSRF token from cookies
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Initialize reasoning functionality when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Format code blocks in reasoning responses
    formatCodeBlocks();
    
    // Add event listeners for reasoning buttons
    const startReasoningBtn = document.getElementById('start-reasoning-btn');
    if (startReasoningBtn) {
        startReasoningBtn.addEventListener('click', function() {
            // Implementation in the specific page
        });
    }
    
    const executeFullReasoningBtn = document.getElementById('execute-full-reasoning-btn');
    if (executeFullReasoningBtn) {
        executeFullReasoningBtn.addEventListener('click', function() {
            // Implementation in the specific page
        });
    }
});
