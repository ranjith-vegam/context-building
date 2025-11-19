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
function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = (el.scrollHeight) + 'px';
}

/* Auto-resize on input */
userInput.addEventListener('input', () => autoResizeTextarea(userInput));

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

/* Create message bubble */
function createBubble(text, who = 'bot', isThinking = false) {
  const el = document.createElement('div');
  el.className = `msg ${who}` + (isThinking ? ' thinking' : '');
  el.innerText = text || '';
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

/* Add citation action under bot message */
function addCitationAction(parentBubble, citationsList) {
  // small container to hold button(s)
  const container = document.createElement('div');
  container.className = 'citation-action';

  const btn = document.createElement('button');
  btn.className = 'citation-btn';
  btn.type = 'button';
  btn.innerText = `View ${citationsList.length} citation${citationsList.length>1?'s':''}`;

  btn.addEventListener('click', () => {
    openCitationDrawer(citationsList);
  });

  container.appendChild(btn);
  parentBubble.appendChild(container);
  // ensure scroll
  messagesEl.scrollTop = messagesEl.scrollHeight;
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
      // optional header if citation has a title-like field
      // render each key / value pair: bold key + value below
      Object.keys(citationObj).forEach((k) => {
        const field = document.createElement('div');
        field.className = 'citation-field';

        const label = document.createElement('div');
        label.className = 'field-label';
        label.innerText = k;

        const value = document.createElement('div');
        value.className = 'citation-value';

        // if value looks like a URL, render as anchor
        const raw = citationObj[k];
        if (typeof raw === 'string' && (raw.startsWith('http://') || raw.startsWith('https://'))) {
          const a = document.createElement('a');
          a.href = raw;
          a.innerText = raw;
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          value.appendChild(a);
        } else if (typeof raw === 'string') {
          value.innerText = raw;
        } else {
          // for non-string values (arrays/objects) stringify with indentation
          try {
            value.innerText = JSON.stringify(raw, null, 2);
          } catch (e) {
            value.innerText = String(raw);
          }
        }

        field.appendChild(label);
        field.appendChild(value);
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
  createBubble(content, 'user');

  // clear input
  userInput.value = '';
  autoResizeTextarea(userInput);

  // thinking bubble
  const thinkingEl = createBubble('Thinking...', 'bot', true);

  try {
    const resp = await fetch('http://localhost:6789/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: content })
    });

    if (!resp.ok) throw new Error('Network response not ok');

    const data = await resp.json();

    // remove thinking bubble
    thinkingEl.remove();

    // render bot response
    const botEl = createBubble(data.response || 'No response', 'bot', false);

    // expect citations as list of dicts: [{...}, {...}]
    const citations = data.citations;
    if (Array.isArray(citations) && citations.length > 0) {
      addCitationAction(botEl, citations);
    }

  } catch (err) {
    thinkingEl.remove();
    createBubble('Error contacting server. Please try again.', 'bot');
    console.error('sendMessage error:', err);
  }
}
