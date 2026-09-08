# 🎨 AI Studio — AI-Powered Custom UI Generator

Build **production-ready web applications** by describing them in natural language. AI Studio uses your agent service to generate, preview, and deploy custom UIs that can invoke agents, n8n workflows, and external APIs.

## 🎯 What is AI Studio?

AI Studio is a **no-code/low-code** UI builder that:

- **Generates UIs from prompts** — Describe what you want, AI builds it
- **Calls your agents** — Generated UIs can invoke any agent you've created
- **Invokes n8n workflows** — Wire up automation workflows directly from the UI
- **Real-time preview** — See changes instantly
- **Customizable code** — Full HTML/CSS/JavaScript control
- **Docker-native** — Two containerized services (backend + frontend)

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│ AI Studio UI (Port 4000)                                 │
│ • Express.js server serving index.html                   │
│ • Chat interface for prompt-based generation             │
│ • Real-time preview + code editor                        │
│ • Project management                                     │
└─────────────────────────────────────────────────────────┘
         ↓ (REST API)
┌─────────────────────────────────────────────────────────┐
│ AI Studio Server (Port 8020)                             │
│ • FastAPI backend                                        │
│ • Calls Agent Service to generate UI code                │
│ • Manages projects & sessions                            │
│ • Proxies agent/workflow invocations                     │
│ • Serves generated UIs with agent integration            │
└─────────────────────────────────────────────────────────┘
         ↓ (Internal Docker network)
┌──────────────┬──────────────┬──────────────────────────┐
│ Agent        │ n8n          │ External APIs            │
│ Service      │ Workflows    │ (via HTTP tools)         │
└──────────────┴──────────────┴──────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Start the Services

```bash
# In your workspace root
docker-compose up -d ai-studio-server ai-studio-ui

# Verify they're running
docker-compose ps | grep ai-studio
```

### 2. Access AI Studio

Open your browser:
- **UI**: http://localhost:4000
- **Backend API**: http://localhost:8020

### 3. Generate Your First UI

In the chat panel:

```
Create a contact form with name, email, and message fields. 
Add a send button that submits to my email-sending agent. 
Include validation and a loading state.
```

Click "Send" and watch the AI generate the code in real-time!

---

## 📖 How It Works

### Step 1: Describe the UI

```
Create a dashboard showing:
- Total revenue card (top-left)
- Orders chart (top-right)
- Recent transactions table (bottom)
- Refresh button that calls my "fetch-data" agent
```

### Step 2: AI Generates Code

The agent service receives your description and outputs:
- Clean HTML/CSS/JavaScript
- Responsive design
- Built-in agent invocation hooks
- Error handling + loading states

### Step 3: Preview & Customize

- **Preview Tab** — See the live UI in an iframe
- **Code Tab** — Edit the HTML/CSS/JavaScript directly
- **Real-time Refresh** — Changes appear instantly

### Step 4: Save & Integrate

```javascript
// Generated UI automatically includes this helper:
async function invokeAgent(agentId, prompt, sessionId = null) {
    const response = await fetch('/studio/invoke-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            agent_id: agentId,
            prompt: prompt,
            session_id: sessionId
        })
    });
    return response.json();
}

// Buttons with data attributes auto-wire to agents:
// <button data-action="agentCall" data-agent-id="email-sender" data-prompt="Send email">Send</button>
```

---

## 🔌 API Endpoints

### Generate UI from Prompt

**POST** `/studio/generate`

```bash
curl -X POST http://localhost:8020/studio/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a form to collect feedback",
    "agent_id": "default",
    "project_id": null
  }'
```

**Response:**
```json
{
  "id": "uuid-123",
  "name": "Create a form to collect feedback",
  "description": "...",
  "ui_code": "<html>...</html>",
  "preview_url": "/studio/preview/uuid-123",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Stream UI Generation (Real-time)

**POST** `/studio/generate/stream`

Returns Server-Sent Events (SSE) for real-time streaming:

```javascript
const eventSource = new EventSource('/api/studio/generate/stream?description=...');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.content) console.log('Received:', data.content);
    if (data.done) console.log('Project created:', data.project_id);
};
```

### Invoke Agent from UI

**POST** `/studio/invoke-agent`

Called by generated UIs to execute agents:

```bash
curl -X POST http://localhost:8020/studio/invoke-agent \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "email-sender",
    "prompt": "Send email to user@example.com with subject Welcome",
    "session_id": "session-123"
  }'
```

### Stream Agent Response

**POST** `/studio/invoke-agent/stream`

Real-time agent output:

```javascript
const eventSource = new EventSource('/api/studio/invoke-agent/stream?agent_id=...');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Agent output:', data.content);
};
```

### Invoke n8n Workflow

**POST** `/studio/invoke-workflow`

```bash
curl -X POST http://localhost:8020/studio/invoke-workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "my-workflow-123",
    "data": {
      "email": "user@example.com",
      "subject": "Welcome"
    }
  }'
```

### Project Management

**List projects:**
```bash
GET /studio/projects
```

**Get project:**
```bash
GET /studio/projects/{project_id}
```

**Update project code:**
```bash
POST /studio/projects/{project_id}/update
{
  "ui_code": "<html>...</html>"
}
```

**Delete project:**
```bash
DELETE /studio/projects/{project_id}
```

---

## 🎨 Generated UI Features

All generated UIs automatically include:

### 1. Agent Invocation Helper

```html
<!-- Auto-included in every generated UI -->
<script>
  async function invokeAgent(agentId, prompt, sessionId = null) {
    // Calls /studio/invoke-agent
    // Returns agent response
    // Handles errors gracefully
  }
</script>
```

### 2. Auto-wired Agent Buttons

```html
<!-- Any button with these data attributes auto-invokes agents -->
<button 
  data-action="agentCall" 
  data-agent-id="my-agent"
  data-prompt="What should I do?"
  data-session-id="session-123">
  Call Agent
</button>
```

### 3. Event Listeners

```javascript
// Listen for agent responses in your custom code
window.addEventListener('agentResponse', (event) => {
  const response = event.detail;
  console.log('Agent returned:', response);
});
```

### 4. CSS Variables (Dark Mode Ready)

```css
:root {
  --glass-bg: rgba(30, 41, 59, 0.8);
  --text-1: #e2e8f0;
  --text-2: #cbd5e1;
  --text-3: #94a3b8;
  --divider: rgba(148, 163, 184, 0.1);
  --accent: #06b6d4;
}
```

---

## 📝 Example: Email Signup Form

### Prompt

```
Create a newsletter signup form with:
- Email input field
- Subscribe button
- Success/error messages
- Loading spinner during submission
- Call my "newsletter-signup" agent on submit
```

### Generated Code (Sample)

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: system-ui; background: #f5f5f5; }
    .container { max-width: 400px; margin: 50px auto; }
    .form { background: white; padding: 2rem; border-radius: 8px; }
    .input { width: 100%; padding: 0.75rem; margin-bottom: 1rem; }
    .btn { width: 100%; padding: 0.75rem; background: #06b6d4; color: white; border: none; }
    .message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
    .error { background: #fee2e2; color: #991b1b; }
    .success { background: #dcfce7; color: #166534; }
  </style>
</head>
<body>
  <div class="container">
    <div class="form">
      <h2>Newsletter</h2>
      <input id="email" type="email" class="input" placeholder="your@email.com">
      <button class="btn" data-action="agentCall" data-agent-id="newsletter-signup" data-prompt="">
        Subscribe
      </button>
      <div id="message"></div>
    </div>
  </div>

  <script>
    document.querySelector('[data-action="agentCall"]').addEventListener('click', async (e) => {
      const email = document.getElementById('email').value;
      if (!email) return alert('Enter email');
      
      const btn = e.target;
      btn.disabled = true;
      const msg = document.getElementById('message');
      
      try {
        const result = await invokeAgent('newsletter-signup', `Subscribe ${email}`);
        msg.textContent = result.message || 'Subscribed!';
        msg.className = 'message success';
        document.getElementById('email').value = '';
      } catch (error) {
        msg.textContent = error.message;
        msg.className = 'message error';
      } finally {
        btn.disabled = false;
      }
    });
  </script>
</body>
</html>
```

---

## 🔧 Configuration

### Environment Variables

**ai-studio-server:**

```bash
STUDIO_PORT=8020                    # Server port
AGENT_URL=http://agent-service:8000  # Agent service URL
N8N_URL=http://n8n:5678            # n8n URL
```

**ai-studio-ui:**

```bash
PORT=4000                           # UI port
STUDIO_API=http://ai-studio-server:8020  # Backend API URL
```

### Docker Compose Override

In `.env` or `docker-compose.yml`:

```bash
# Change ports if needed
AI_STUDIO_UI_PORT=4000
AI_STUDIO_SERVER_PORT=8020
```

---

## 💡 Use Cases

### 1. **Customer Dashboard**
"Create a dashboard showing customer stats, orders, and a button to export data to CSV using my export agent"

### 2. **Admin Panel**
"Build an admin form with fields for user management. Include add, edit, delete buttons that call my user-management agent"

### 3. **Data Entry App**
"Generate a multi-step form for collecting survey responses. On submit, call my data-ingestion agent"

### 4. **Workflow Trigger UI**
"Create a control panel with buttons to trigger my n8n workflows (send emails, process invoices, etc.)"

### 5. **Chatbot Interface**
"Build a chat interface that sends messages to my conversational agent and displays streaming responses"

---

## 🐛 Troubleshooting

### AI Studio Server isn't responding

```bash
# Check if it's running
docker-compose ps ai-studio-server

# View logs
docker-compose logs ai-studio-server

# Restart it
docker-compose restart ai-studio-server
```

### Generated UI won't display

- Check browser console for errors (`F12`)
- Verify agent service is running: `curl http://localhost:8010/health`
- Check AI Studio server logs for streaming errors

### Agent calls failing

- Verify `AGENT_URL` is correct in ai-studio-server env
- Check if agent exists: Visit http://localhost:3005 → Agents
- Test agent directly: Use "Run Agent" page in main console

---

## 📚 Integration with Main Console

AI Studio is integrated into your main dashboard:

1. **Link in Console** — Add "AI Studio" button to ui-console navigation
2. **Shared Sessions** — Projects can reference agents created in the main console
3. **Unified APIs** — Both use the same Agent Service backend

### To Add to ui-console Navigation

Edit `services/ui-console/views/layout.ejs`:

```html
<a href="http://localhost:4000" class="nav-item" target="_blank">
  ✨ AI Studio
</a>
```

---

## 🔒 Security Notes

- ✅ AI-generated code runs in an `<iframe sandbox>` by default
- ✅ All agent calls require valid authentication (if configured)
- ✅ API calls are proxied through ai-studio-server (no direct client-to-agent)
- ⚠️ Generated code can execute JavaScript — review before deploying to production
- ⚠️ Agent calls respect your agent's own security rules

---

## 📊 How Data Flows

```
User Types Prompt
    ↓
AI Studio UI (port 4000)
    ↓
POST /studio/generate
    ↓
AI Studio Server (port 8020)
    ↓
Calls Agent Service with system prompt
    ↓
Agent generates HTML/CSS/JavaScript
    ↓
Response streamed back to UI
    ↓
Preview shows in iframe
    ↓
User clicks agent button in preview
    ↓
Generated UI calls /studio/invoke-agent
    ↓
Server proxies to Agent Service
    ↓
Agent executes and returns result
    ↓
Result displayed in UI
```

---

## 🚢 Deployment

### Local Development

```bash
docker-compose up ai-studio-server ai-studio-ui
# Visit http://localhost:4000
```

### Production Considerations

1. **Persistent Storage** — Projects stored in memory; add database for persistence
2. **Authentication** — Add user validation in ai-studio-server endpoints
3. **Rate Limiting** — Add request throttling for agent calls
4. **Logging** — Enable full tracing for audit/debug
5. **Backup** — Export important projects regularly

---

## 📞 Support

- **Issues?** Check logs: `docker-compose logs ai-studio-server`
- **Questions?** Review API docs above
- **Feature Requests?** Modify `services/ai-studio-server/main.py`

---

**Built with ❤️ on the Agentic Platform**
