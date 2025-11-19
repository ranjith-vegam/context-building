/* eslint-disable no-unused-vars */
/* Globals */
const messagesEl = document.getElementById('messages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

const drawer = document.getElementById('drawer');
const drawerContent = document.getElementById('drawerContent');
const overlay = document.getElementById('overlay');
const closeDrawer = document.getElementById('closeDrawer');

/* Ensure drawer starts closed */
drawer.classList.remove('open');
overlay.hidden = true;

/* Helpers */

/**
 * Auto-resize a textarea element to fit its content.
 * - shrinks when text is removed
 * - grows until a maxHeightRatio of viewport (default 0.5)
 * - if content exceeds maxHeight, enable internal scrollbar
 *
 * @param {HTMLTextAreaElement} el
 * @param {number} maxHeightRatio 0..1 fraction of viewport height (optional)
 */
function autoResizeTextarea(el, maxHeightRatio = 0.5) {
  if (!el) return;

  // reset so scrollHeight reports actual needed height
  el.style.height = 'auto';

  // compute desired height (include a small fudge for border/padding)
  const needed = el.scrollHeight;

  // compute maximum allowed height in px (use provided ratio, fallback 0.5)
  const ratio = (typeof maxHeightRatio === 'number' && maxHeightRatio > 0 && maxHeightRatio <= 1)
    ? maxHeightRatio
    : 0.5;
  const maxPx = Math.round(window.innerHeight * ratio);

  if (needed > maxPx) {
    el.style.height = maxPx + 'px';
    el.style.overflowY = 'auto'; // enable scrollbar when too tall
  } else {
    el.style.height = needed + 'px';
    el.style.overflowY = 'hidden';
  }
}



/* Auto-resize on input for composer */
userInput.addEventListener('input', () => {
  // composer should grow up to 40% of viewport height
  autoResizeTextarea(userInput, 0.4);
});

/* Set initial small height for input so its not huge on load */
autoResizeTextarea(userInput, 0.4);

/* Send handlers */
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

/* Close drawer handlers */
closeDrawer.addEventListener('click', closeCitationDrawer);
overlay.addEventListener('click', closeCitationDrawer);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeCitationDrawer();
});

/* Create message bubble (returns element) */
function createBubble(text, who = 'bot', isThinking = false) {
  const el = document.createElement('div');
  el.className = `msg ${who}` + (isThinking ? ' thinking' : '');
  el.innerText = text || '';
  return el;
}

/* Append bot message with citation trigger BELOW the bubble (right-aligned) */
function appendBotMessage(botText, citationsList = []) {
  const row = document.createElement('div');
  row.className = 'msg-row';

  const bubble = createBubble(botText, 'bot', false);
  row.appendChild(bubble);

  // trigger row (right-aligned) below the bubble (tight)
  const triggerRow = document.createElement('div');
  triggerRow.style.display = 'flex';
  triggerRow.style.justifyContent = 'flex-start'; // Option B: left-aligned below
  triggerRow.style.alignItems = 'center';
  triggerRow.style.marginTop = '-4px';  // tighter attachment to bubble

  // small icon button (only shown when citations exist)
  const trigger = document.createElement('button');
  trigger.className = 'citation-trigger-below';
  trigger.type = 'button';
  trigger.setAttribute('aria-label', `Open citations (${Array.isArray(citationsList) ? citationsList.length : 0})`);
  trigger.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm.75 15h-1.5v-6h1.5v6zm0-8h-1.5V7h1.5v2z"/>
    </svg>
  `;

  trigger.addEventListener('click', () => {
    openCitationDrawer(citationsList);
  });

  if (!Array.isArray(citationsList) || citationsList.length === 0) {
    trigger.style.visibility = 'hidden';
  }

  // left align the trigger below bubble by putting in same container and adding small left margin
  trigger.style.marginLeft = '2px';

  triggerRow.appendChild(trigger);
  row.appendChild(triggerRow);

  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  return bubble;
}

/* Open drawer and populate with a list of dicts */
function openCitationDrawer(citationsList = []) {
  drawerContent.innerHTML = ''; // reset

  if (!Array.isArray(citationsList) || citationsList.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'citation-card';
    empty.innerText = 'No citations available.';
    drawerContent.appendChild(empty);
  } else {
    // For each citation dict, create a card
    citationsList.forEach((citationObj, idx) => {
      const card = document.createElement('div');
      card.className = 'citation-card';

      // LAYER LABEL (coerce to number to be robust)
      const layerVal = String(citationObj.layer);
      const layerLabel = document.createElement('div');
      layerLabel.className = 'layer-label';
      if (layerVal === "1") { layerLabel.classList.add('layer-1'); layerLabel.innerText = 'Layer 1'; }
      else if (layerVal === "2") { layerLabel.classList.add('layer-2'); layerLabel.innerText = 'Layer 2'; }
      else if (layerVal === "3") { layerLabel.classList.add('layer-3'); layerLabel.innerText = 'Layer 3'; }
      else { layerLabel.innerText = `Layer ${String(citationObj.layer || '')}`; }
      card.appendChild(layerLabel);

      // render each key / value pair except layer
      Object.keys(citationObj).forEach((k) => {
        if (k === 'layer') return;

        const field = document.createElement('div');
        field.className = 'citation-field';

        const label = document.createElement('div');
        label.className = 'field-label';
        label.innerText = k;

        const wrapper = document.createElement('div');
        wrapper.className = 'citation-value-wrapper';

        // create readonly textarea to host the value
        const textarea = document.createElement('textarea');
        textarea.className = 'citation-input';
        textarea.readOnly = true;
        textarea.rows = 1; // start small

        // convert raw value to string safely
        let raw = citationObj[k];
        if (typeof raw === 'object' && raw !== null) {
          try { raw = JSON.stringify(raw, null, 2); } catch (e) { raw = String(raw); }
        } else if (raw === null || raw === undefined) {
          raw = '';
        } else {
          raw = String(raw);
        }

        textarea.value = raw;
        textarea.dataset.maxRatio = '0.5';

        // make sure layout is stable, then measure & resize
        textarea.style.height = 'auto';
        textarea.style.overflowY = 'hidden';

        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            autoResizeTextarea(textarea, Number(textarea.dataset.maxRatio || 0.5));
          });
        });



        // copy icon inside the field
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-in-field';
        copyBtn.type = 'button';
        copyBtn.setAttribute('aria-label', `Copy value for ${k}`);
        copyBtn.innerHTML = `
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">
            <path d="M16 1H4a2 2 0 0 0-2 2v12h2V3h12V1zM20 5H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h12v14z"/>
          </svg>
        `;

        // copy handler with fallback and UX feedback
        copyBtn.addEventListener('click', async (ev) => {
          ev.preventDefault();
          const textToCopy = textarea.value;
          try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
              await navigator.clipboard.writeText(textToCopy);
            } else {
              // fallback: select & execCommand
              textarea.select();
              document.execCommand('copy');
              window.getSelection().removeAllRanges();
            }
            // brief feedback: show "✓" then revert
            const prev = copyBtn.innerHTML;
            copyBtn.innerHTML = '✓';
            setTimeout(() => { copyBtn.innerHTML = prev; }, 900);
          } catch (err) {
            console.error('copy failed', err);
          }
        });

        wrapper.appendChild(textarea);
        wrapper.appendChild(copyBtn);

        field.appendChild(label);
        field.appendChild(wrapper);
        card.appendChild(field);
      });

      drawerContent.appendChild(card);
    });
  }

  // show drawer + overlay
  drawer.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  overlay.hidden = false;
  setTimeout(() => overlay.classList.add('show'), 10);

  // move focus into drawer for keyboard users
  drawerContent.focus();
}

/* Close */
function closeCitationDrawer() {
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  overlay.classList.remove('show');
  setTimeout(() => { overlay.hidden = true; }, 220);
}

/* Send message to backend */
async function sendMessage() {
  const content = userInput.value.trim();
  if (!content) return;

  // user bubble
  const userBubble = createBubble(content, 'user', false);
  const userRow = document.createElement('div');
  userRow.className = 'msg-row';
  userRow.appendChild(userBubble);
  messagesEl.appendChild(userRow);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // clear input
  userInput.value = '';
  autoResizeTextarea(userInput, 0.4);

  // thinking placeholder
  const thinkingRow = document.createElement('div');
  thinkingRow.className = 'msg-row';
  const thinkingBubble = createBubble('Thinking...', 'bot', true);
  thinkingRow.appendChild(thinkingBubble);
  const placeholderTrigger = document.createElement('div');
  placeholderTrigger.style.alignSelf = 'flex-start'; // left-aligned
  placeholderTrigger.style.width = '36px';
  thinkingRow.appendChild(placeholderTrigger);
  messagesEl.appendChild(thinkingRow);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  try {
    const resp = await fetch('http://localhost:6789/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: content })
    });

    if (!resp.ok) throw new Error('Network response not ok');

    const data = await resp.json();

    // remove thinking
    thinkingRow.remove();

    const citations = Array.isArray(data.citations) ? data.citations : [];
    appendBotMessage(data.response || 'No response', citations);

  } catch (err) {
    thinkingRow.remove();
    appendBotMessage('Error contacting server. Please try again.', []);
    console.error('sendMessage error:', err);
  }
}
