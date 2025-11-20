// ========================================
// DOM ELEMENTS
// ========================================
const messagesEl = document.getElementById('messages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const drawer = document.getElementById('drawer');
const drawerContent = document.getElementById('drawerContent');
const overlay = document.getElementById('overlay');
const closeDrawerBtn = document.getElementById('closeDrawer');

// ========================================
// INITIALIZATION
// ========================================
drawer.classList.remove('open');
overlay.hidden = true;

// Focus input on load
window.addEventListener('load', () => {
  userInput.focus();
});

// ========================================
// AUTO-RESIZE TEXTAREA
// ========================================
function autoResizeTextarea(el, maxRatio = 0.5) {
  if (!el) return;
  el.style.height = 'auto';
  const needed = el.scrollHeight;
  const maxPx = Math.round(window.innerHeight * maxRatio);
  
  if (needed > maxPx) {
    el.style.height = maxPx + 'px';
    el.style.overflowY = 'auto';
  } else {
    el.style.height = needed + 'px';
    el.style.overflowY = 'hidden';
  }
}

// ========================================
// EVENT LISTENERS
// ========================================

// Auto-resize input as user types
userInput.addEventListener('input', () => {
  autoResizeTextarea(userInput, 0.4);
});

// Initialize input size
autoResizeTextarea(userInput, 0.4);

// Send message on button click
sendBtn.addEventListener('click', sendMessage);

// Send message on Enter (Shift+Enter for new line)
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Close drawer handlers
closeDrawerBtn.addEventListener('click', closeCitationDrawer);
overlay.addEventListener('click', closeCitationDrawer);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeCitationDrawer();
  }
});

// ========================================
// MESSAGE BUBBLE CREATION
// ========================================
function createBubble(text, who = 'bot', isThinking = false) {
  const el = document.createElement('div');
  el.className = `msg ${who}${isThinking ? ' thinking' : ''}`;
  el.textContent = text || '';
  return el;
}

// ========================================
// APPEND BOT MESSAGE WITH CITATIONS
// ========================================
function appendBotMessage(botText, citationsList = []) {
  const row = document.createElement('div');
  row.className = 'msg-row';
  
  // Create message bubble
  const bubble = createBubble(botText, 'bot', false);
  row.appendChild(bubble);

  // Add citation trigger button if citations exist
  if (Array.isArray(citationsList) && citationsList.length > 0) {
    const triggerRow = document.createElement('div');
    triggerRow.className = 'citation-trigger-row';
    
    const trigger = document.createElement('button');
    trigger.className = 'citation-trigger-below';
    trigger.type = 'button';
    trigger.setAttribute('aria-label', `View ${citationsList.length} citation${citationsList.length !== 1 ? 's' : ''}`);
    
    trigger.innerHTML = `
      <svg viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/>
      </svg>
      <span>View Citations</span>
      <span class="citation-count">${citationsList.length}</span>
    `;
    
    trigger.addEventListener('click', () => openCitationDrawer(citationsList));
    triggerRow.appendChild(trigger);
    row.appendChild(triggerRow);
  }

  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ========================================
// OPEN CITATION DRAWER
// ========================================
function openCitationDrawer(citationsList = []) {
  drawerContent.innerHTML = '';
  
  if (!Array.isArray(citationsList) || citationsList.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'citation-card';
    empty.innerHTML = '<p style="text-align: center; color: var(--text-muted); font-size: 16px;">No citations available for this message.</p>';
    drawerContent.appendChild(empty);
  } else {
    // Create citation cards
    citationsList.forEach((citationObj, index) => {
      const card = document.createElement('div');
      card.className = 'citation-card';

      // Layer label
      const layerVal = String(citationObj.layer || '');
      const layerLabel = document.createElement('div');
      layerLabel.className = 'layer-label';
      
      if (layerVal === '1') {
        layerLabel.classList.add('layer-1');
        layerLabel.innerHTML = '🟢 Layer 1';
      } else if (layerVal === '2') {
        layerLabel.classList.add('layer-2');
        layerLabel.innerHTML = '🔵 Layer 2';
      } else if (layerVal === '3') {
        layerLabel.classList.add('layer-3');
        layerLabel.innerHTML = '🟠 Layer 3';
      } else {
        layerLabel.textContent = `Layer ${layerVal}`;
      }
      
      card.appendChild(layerLabel);

      // Add citation number
      const citationNumber = document.createElement('div');
      citationNumber.style.cssText = 'font-size: 12px; color: var(--text-muted); margin-top: -8px; margin-bottom: 8px;';
      citationNumber.textContent = `Citation #${index + 1}`;
      card.appendChild(citationNumber);

      // Process each field
      Object.keys(citationObj).forEach((key) => {
        if (key === 'layer') return; // Skip layer as it's already shown
        
        const field = document.createElement('div');
        field.className = 'citation-field';
        
        // Field label
        const label = document.createElement('div');
        label.className = 'field-label';
        label.textContent = formatFieldName(key);
        
        // Wrapper for textarea and copy button
        const wrapper = document.createElement('div');
        wrapper.className = 'citation-value-wrapper';
        
        // Textarea for value
        const textarea = document.createElement('textarea');
        textarea.className = 'citation-input';
        
        // Special styling for transcript_chunk (metadata)
        if (key === 'transcript_chunk') {
          textarea.classList.add('metadata');
        }
        
        textarea.readOnly = true;
        
        // Format value
        let raw = citationObj[key];
        if (typeof raw === 'object' && raw !== null) {
          raw = JSON.stringify(raw, null, 2);
        } else {
          raw = raw || '';
        }
        textarea.value = String(raw);
        
        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-in-field';
        copyBtn.type = 'button';
        copyBtn.setAttribute('aria-label', 'Copy to clipboard');
        copyBtn.innerHTML = `
          <svg viewBox="0 0 24 24">
            <path d="M16 1H4a2 2 0 0 0-2 2v12h2V3h12V1zM20 5H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h12v14z"/>
          </svg>
        `;
        
        copyBtn.addEventListener('click', async (ev) => {
          ev.preventDefault();
          await copyToClipboard(textarea.value, copyBtn);
        });
        
        wrapper.appendChild(textarea);
        wrapper.appendChild(copyBtn);
        field.appendChild(label);
        field.appendChild(wrapper);
        card.appendChild(field);
        
        // Auto-resize non-metadata fields
        if (key !== 'transcript_chunk') {
          autoResizeTextarea(textarea, 0.5);
        }
      });

      drawerContent.appendChild(card);
    });
  }

  // Open drawer
  drawer.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  overlay.hidden = false;
  setTimeout(() => overlay.classList.add('show'), 10);
}

// ========================================
// CLOSE CITATION DRAWER
// ========================================
function closeCitationDrawer() {
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  overlay.classList.remove('show');
  setTimeout(() => {
    overlay.hidden = true;
  }, 300);
}

// ========================================
// COPY TO CLIPBOARD
// ========================================
async function copyToClipboard(text, button) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      // Fallback for older browsers
      const tempTextarea = document.createElement('textarea');
      tempTextarea.value = text;
      tempTextarea.style.position = 'fixed';
      tempTextarea.style.opacity = '0';
      document.body.appendChild(tempTextarea);
      tempTextarea.select();
      document.execCommand('copy');
      document.body.removeChild(tempTextarea);
    }
    
    // Visual feedback
    button.classList.add('copied');
    const prevHTML = button.innerHTML;
    button.innerHTML = '<span style="color: white; font-weight: bold;">✓</span>';
    
    setTimeout(() => {
      button.classList.remove('copied');
      button.innerHTML = prevHTML;
    }, 1500);
  } catch (err) {
    console.error('Copy failed:', err);
    alert('Failed to copy to clipboard');
  }
}

// ========================================
// FORMAT FIELD NAME
// ========================================
function formatFieldName(key) {
  // Convert snake_case or camelCase to Title Case
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
    .trim();
}

// ========================================
// SEND MESSAGE
// ========================================
async function sendMessage() {
  const content = userInput.value.trim();
  if (!content) return;
  
  // Disable send button during request
  sendBtn.disabled = true;
  
  // Create and append user message
  const userBubble = createBubble(content, 'user', false);
  const userRow = document.createElement('div');
  userRow.className = 'msg-row';
  userRow.appendChild(userBubble);
  messagesEl.appendChild(userRow);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  
  // Clear input
  userInput.value = '';
  autoResizeTextarea(userInput, 0.4);

  // Show thinking indicator
  const thinkingRow = document.createElement('div');
  thinkingRow.className = 'msg-row';
  const thinkingBubble = createBubble('Thinking...', 'bot', true);
  thinkingRow.appendChild(thinkingBubble);
  messagesEl.appendChild(thinkingRow);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  try {
    // Make API request
    const response = await fetch('http://localhost:6789/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message: content })
    });
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Remove thinking indicator
    thinkingRow.remove();
    
    // Extract citations
    const citations = Array.isArray(data.citations) ? data.citations : [];
    
    // Append bot response with citations
    appendBotMessage(data.response || 'No response received.', citations);
    
  } catch (err) {
    console.error('Chat error:', err);
    
    // Remove thinking indicator
    thinkingRow.remove();
    
    // Show error message
    const errorMessage = err.message.includes('Failed to fetch')
      ? '⚠️ Unable to connect to the server. Please check if the server is running on http://localhost:6789'
      : `⚠️ Error: ${err.message}`;
    
    appendBotMessage(errorMessage, []);
    
  } finally {
    // Re-enable send button
    sendBtn.disabled = false;
    userInput.focus();
  }
}

// ========================================
// UTILITY: Scroll to bottom on resize
// ========================================
window.addEventListener('resize', () => {
  if (messagesEl.scrollHeight > messagesEl.clientHeight) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
});