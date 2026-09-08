# 🚀 AI Studio — Setup & Deployment Guide

## What You've Built

You now have a **dedicated AI Studio** that generates custom web UIs from natural language prompts. The UIs can invoke your agents, n8n workflows, and external APIs.

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI STUDIO                               │
│  Chat-based UI generator powered by your agents                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend (Node.js Express)           Backend (FastAPI)        │
│  📍 localhost:4000                     📍 localhost:8020        │
│  ✓ Chat UI for prompts                ✓ Agent orchestration    │
│  ✓ Real-time code preview              ✓ Project management    │
│  ✓ Code editor                         ✓ Workflow proxying     │
│  ✓ Project management                  ✓ SSE streaming         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Files Created

### Backend (Python + FastAPI)
```
services/ai-studio-server/
├── main.py              # FastAPI application
├── requirements.txt     # Dependencies
├── Dockerfile          # Container image
├── .dockerignore        # Build exclusions
└── README.md           # Full API documentation
```

### Frontend (Node.js + Express)
```
services/ai-studio-ui/
├── index.html          # Single-page application
├── server.js           # Express proxy server
├── package.json        # Dependencies
├── Dockerfile          # Container image
└── .dockerignore       # Build exclusions
```

### Docker Compose
```
docker-compose.yml     # Updated with 2 new services:
                       #  - ai-studio-server (port 8020)
                       #  - ai-studio-ui (port 4000)
```

---

## 🎯 Step 1: Start the Services

### Option A: Start Everything

```bash
cd /Users/rachitgupta/Library/CloudStorage/OneDrive-KPMG/Apps/agentic-platform/agentic-platform

docker-compose up -d ai-studio-server ai-studio-ui
```

### Option B: Start Individual Services

```bash
# Just the backend
docker-compose up -d ai-studio-server

# Just the frontend
docker-compose up -d ai-studio-ui

# Both
docker-compose up -d ai-studio-server ai-studio-ui
```

### Verify Services

```bash
# Check if they're running
docker-compose ps | grep ai-studio

# Expected output:
# ai-studio-server    Up (healthy)
# ai-studio-ui        Up (healthy)
```

---

## 🌐 Step 2: Access AI Studio

### In Your Browser

| Service | URL | Purpose |
|---------|-----|---------|
| **AI Studio UI** | http://localhost:4000 | Main interface for UI generation |
| **API Backend** | http://localhost:8020 | REST API for programmatic access |
| **Health Check** | http://localhost:8020/health | Verify backend is running |

### Quick Test

```bash
# Check backend health
curl http://localhost:8020/health

# Should return:
# {"status":"healthy","service":"ai-studio-server",...}
```

---

## 💬 Step 3: Generate Your First UI

### In AI Studio (http://localhost:4000)

**Type in the chat box:**

```
Create a simple form to collect email addresses for a newsletter.
Include:
- Email input field
- Subscribe button
- Validation (check for valid email)
- Success message when submitted
- Call my default agent to process the email

Make it look modern with a dark theme.
```

**Click "Send"** and watch as:
1. ✅ The prompt is sent to your Agent Service
2. ✅ An agent generates HTML/CSS/JavaScript
3. ✅ Code streams in real-time to your browser
4. ✅ Preview automatically updates
5. ✅ You can edit the code and refresh

---

## 🔧 Step 4: Configure (if needed)

### Environment Variables

**For ai-studio-server**, edit your `.env` or `docker-compose.yml`:

```bash
# Backend configuration
AGENT_URL=http://agent-service:8000   # Your agent service
N8N_URL=http://n8n:5678               # Your n8n instance
STUDIO_PORT=8020                      # Server port
```

**For ai-studio-ui**, edit your `.env` or `docker-compose.yml`:

```bash
# Frontend configuration
PORT=4000                             # UI port
STUDIO_API=http://ai-studio-server:8020  # Backend API
```

### Rebuild After Config Changes

```bash
# Rebuild and restart services
docker-compose up -d --build ai-studio-server ai-studio-ui
```

---

## 📋 API Examples

### Generate a UI from Terminal

```bash
curl -X POST http://localhost:8020/studio/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a form with name and email fields",
    "agent_id": "default"
  }'
```

### Stream UI Generation

```bash
curl -X POST http://localhost:8020/studio/generate/stream \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a todo list app"
  }' \
  -H "Accept: text/event-stream" | grep "data:"
```

### List All Projects

```bash
curl http://localhost:8020/studio/projects
```

---

## 🎨 Key Features

### 1. **Prompt-Based Generation**
Describe any UI in natural language—the agent builds it.

### 2. **Real-Time Preview**
See generated code live in an iframe as you edit.

### 3. **Agent Integration**
Generated UIs can call agents you've created in the main console.

### 4. **Workflow Support**
Invoke n8n workflows directly from generated UIs.

### 5. **Code Editing**
Full HTML/CSS/JavaScript control—edit generated code manually.

### 6. **Project Management**
- Create, view, edit, delete projects
- Export as HTML files
- Save to database (future enhancement)

### 7. **Real-Time Streaming**
SSE/WebSocket support for long-running agent calls.

---

## 🔗 Integration with Main Console

### Link to AI Studio from Dashboard

Edit: `services/ui-console/views/layout.ejs`

Find the navigation section and add:

```html
<!-- Add this to the nav menu -->
<li>
  <a href="http://localhost:4000" target="_blank" class="nav-link">
    <span class="icon">✨</span>
    <span>AI Studio</span>
  </a>
</li>
```

### Access from Main Console

After adding the link, you'll see "AI Studio" in the sidebar. Click it to jump to the UI builder.

---

## 📖 Generated UI Features

Every generated UI includes:

### Auto-Wired Agent Buttons

```html
<!-- Any button with these attributes auto-calls agents -->
<button 
  data-action="agentCall" 
  data-agent-id="my-agent"
  data-prompt="Do something">
  Call Agent
</button>
```

### Agent Helper Function

```javascript
// Available in all generated UIs
async function invokeAgent(agentId, prompt, sessionId) {
  // Calls your agent service
  // Handles errors
  // Returns result
}
```

### Event Listeners

```javascript
// Listen for agent responses
window.addEventListener('agentResponse', (event) => {
  console.log('Agent returned:', event.detail);
});
```

---

## 🐛 Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs ai-studio-server
docker-compose logs ai-studio-ui

# Rebuild from scratch
docker-compose down
docker-compose up --build ai-studio-server ai-studio-ui
```

### UI won't load at localhost:4000

```bash
# Check if ui service is running
docker ps | grep ai-studio-ui

# Check network connectivity
curl -I http://localhost:4000

# View ui logs
docker-compose logs ai-studio-ui
```

### Agent calls fail

```bash
# 1. Verify Agent Service is running
curl http://localhost:8010/health

# 2. Check agent exists in main console
# Go to http://localhost:3005 → Agents

# 3. View ai-studio-server logs
docker-compose logs ai-studio-server

# 4. Test agent directly
curl -X POST http://localhost:8010/run \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello", "agent_id":"default"}'
```

### Streaming stops or hangs

- Check network connection
- Verify `AGENT_URL` environment variable is correct
- Increase timeout in your HTTP client
- Check agent service logs for errors

---

## 🚢 What's Next?

### Short Term
1. ✅ **Start the services** — `docker-compose up -d ai-studio-server ai-studio-ui`
2. ✅ **Generate a UI** — Try a simple form first
3. ✅ **Test agent calls** — Click buttons in the preview
4. ✅ **Customize code** — Edit HTML/CSS as needed

### Medium Term
1. Add persistent storage (PostgreSQL for projects)
2. Add user authentication
3. Create skill templates for common UIs
4. Add real-time collaboration (WebSocket)
5. Deploy to production

### Long Term
1. Visual UI builder (drag-and-drop, not just prompts)
2. Component library
3. A/B testing framework
4. Analytics dashboard
5. Team collaboration features

---

## 📚 Full Documentation

See: `services/ai-studio-server/README.md` for:
- Complete API reference
- More examples
- Deployment guide
- Architecture details
- Security notes

---

## ✨ You Now Have

- ✅ Custom AI UI generator
- ✅ Real-time prompt-to-code pipeline
- ✅ Agent integration layer
- ✅ n8n workflow support
- ✅ Production-ready architecture
- ✅ Full source code control
- ✅ Open source (no vendor lock-in)

---

## 🎉 Quick Commands Reference

```bash
# Start everything
docker-compose up -d ai-studio-server ai-studio-ui

# View logs
docker-compose logs -f ai-studio-server
docker-compose logs -f ai-studio-ui

# Restart
docker-compose restart ai-studio-server ai-studio-ui

# Stop
docker-compose stop ai-studio-server ai-studio-ui

# Remove containers (keep volumes)
docker-compose rm ai-studio-server ai-studio-ui

# Full clean (remove everything)
docker-compose down
```

---

**Ready? Head to http://localhost:4000 and start building! 🚀**
