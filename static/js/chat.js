/**
 * Chat interface script for interacting with the crypto AI agent via natural language
 */

// Chat history will be stored here
let chatHistory = [];

// Initialize chat interface when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Get elements
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const loadingIndicator = document.getElementById('chat-loading');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    const suggestedQuestionsContainer = document.getElementById('suggested-questions');
    
    // Initialize chat interface
    initializeChat();
    
    // Event listeners
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = chatInput.value.trim();
            
            if (message) {
                // Add user message to chat
                addMessageToChat('user', message);
                
                // Clear input
                chatInput.value = '';
                
                // Show loading indicator
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'block';
                }
                
                // Send message to server
                sendMessageToAgent(message);
            }
        });
    }
    
    // Clear chat button
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to clear the chat history?')) {
                clearChat();
            }
        });
    }
    
    // Initialize suggested questions
    if (suggestedQuestionsContainer) {
        setupSuggestedQuestions();
    }
});

// Initialize chat
function initializeChat() {
    // Try to load chat history from local storage
    const storedChat = localStorage.getItem('cryptoAiChatHistory');
    if (storedChat) {
        try {
            chatHistory = JSON.parse(storedChat);
            
            // Render stored messages
            const chatMessages = document.getElementById('chat-messages');
            if (chatMessages) {
                chatMessages.innerHTML = '';
                
                // Add welcome message if no chat history
                if (chatHistory.length === 0) {
                    addWelcomeMessage();
                } else {
                    // Render chat history
                    chatHistory.forEach(message => {
                        renderMessage(message.sender, message.content, message.timestamp);
                    });
                }
            }
        } catch (error) {
            console.error('Error parsing stored chat history:', error);
            chatHistory = [];
            addWelcomeMessage();
        }
    } else {
        // No stored chat, add welcome message
        addWelcomeMessage();
    }
}

// Add welcome message to chat
function addWelcomeMessage() {
    const welcomeMessage = `
        <div class="chat-system-card">
            <div class="card-body">
                <h5 class="card-title"><i class="fas fa-robot me-2"></i>Crypto AI Agent</h5>
                <p class="card-text">Hello! I'm your Crypto AI Agent. I can help you with:</p>
                <ul>
                    <li>Analyzing market conditions</li>
                    <li>Optimizing trading parameters</li>
                    <li>Monitoring trader performance</li>
                    <li>Detecting issues with your traders</li>
                    <li>Providing recommendations for trades</li>
                </ul>
                <p>What would you like to know about your crypto trading operations today?</p>
            </div>
        </div>
    `;
    
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.innerHTML = welcomeMessage;
    }
}

// Add a message to the chat
function addMessageToChat(sender, content) {
    const timestamp = new Date().toISOString();
    
    // Add to history
    chatHistory.push({
        sender,
        content,
        timestamp
    });
    
    // Save to localStorage
    localStorage.setItem('cryptoAiChatHistory', JSON.stringify(chatHistory));
    
    // Render the message
    renderMessage(sender, content, timestamp);
    
    // Scroll to bottom
    scrollChatToBottom();
}

// Render a message in the chat
function renderMessage(sender, content, timestamp) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message chat-message-${sender}`;
    
    const formattedTime = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    if (sender === 'user') {
        messageElement.innerHTML = `
            <div class="chat-bubble user-bubble">
                <div class="chat-content">${content}</div>
                <div class="chat-time">${formattedTime}</div>
            </div>
        `;
    } else {
        messageElement.innerHTML = `
            <div class="chat-bubble agent-bubble">
                <div class="chat-content">${formatAgentResponse(content)}</div>
                <div class="chat-time">${formattedTime}</div>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageElement);
}

// Format agent response (convert markdown-like syntax, add links, etc.)
function formatAgentResponse(text) {
    // Convert markdown-like syntax
    let formattedText = text
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Code blocks
        .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>')
        // Inline code
        .replace(/`(.*?)`/g, '<code>$1</code>')
        // Headers
        .replace(/^### (.*?)$/gm, '<h5>$1</h5>')
        .replace(/^## (.*?)$/gm, '<h4>$1</h4>')
        .replace(/^# (.*?)$/gm, '<h3>$1</h3>')
        // Lists
        .replace(/^\* (.*?)$/gm, '<li>$1</li>')
        .replace(/^\- (.*?)$/gm, '<li>$1</li>')
        .replace(/^\d+\. (.*?)$/gm, '<li>$1</li>');
    
    // Wrap lists
    formattedText = formattedText.replace(/<li>(.*?)<\/li>/g, function(match) {
        return '<ul>' + match + '</ul>';
    }).replace(/<\/ul><ul>/g, '');
    
    // Add line breaks
    formattedText = formattedText.replace(/\n/g, '<br>');
    
    return formattedText;
}

// Send a message to the AI agent
function sendMessageToAgent(message) {
    // Make API request
    fetch('/api/chat/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: message })
    })
    .then(response => response.json())
    .then(data => {
        // Hide loading indicator
        const loadingIndicator = document.getElementById('chat-loading');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        
        if (data.success) {
            // Add agent response to chat
            addMessageToChat('agent', data.response);
        } else {
            // Show error
            addMessageToChat('agent', `I'm sorry, I encountered an error: ${data.error}. Please try again.`);
        }
    })
    .catch(error => {
        console.error('Error sending message to agent:', error);
        
        // Hide loading indicator
        const loadingIndicator = document.getElementById('chat-loading');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        
        // Show error message
        addMessageToChat('agent', `I'm sorry, I encountered an error while processing your request. Please try again later.`);
    });
}

// Clear the chat
function clearChat() {
    chatHistory = [];
    localStorage.removeItem('cryptoAiChatHistory');
    
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
        addWelcomeMessage();
    }
}

// Scroll to the bottom of the chat
function scrollChatToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Setup suggested questions
function setupSuggestedQuestions() {
    const suggestedQuestions = [
        "How are market conditions looking today?",
        "What trading pairs are performing best?",
        "Can you analyze the BTC/USDT market?",
        "Are there any traders that need parameter optimization?",
        "Which traders have issues that need attention?",
        "What's the overall performance of my trading pairs?",
        "Should I be placing trades in the current market?",
        "How has volatility changed in the last 24 hours?"
    ];
    
    const container = document.getElementById('suggested-questions');
    if (!container) return;
    
    // Create buttons for suggested questions
    suggestedQuestions.forEach(question => {
        const button = document.createElement('button');
        button.className = 'btn btn-sm btn-outline-secondary me-2 mb-2';
        button.textContent = question;
        
        button.addEventListener('click', function() {
            // Set the question in the input
            const chatInput = document.getElementById('chat-input');
            if (chatInput) {
                chatInput.value = question;
                chatInput.focus();
            }
            
            // Optionally auto-submit
            const chatForm = document.getElementById('chat-form');
            if (chatForm) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
        
        container.appendChild(button);
    });
}
