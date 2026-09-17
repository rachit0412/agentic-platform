# Continue.dev + DeepSeek-R1: Seamless VS Code Setup

## Prerequisites
✅ Ollama running: `ollama serve` (Terminal must stay open)
✅ Model loaded: `deepseek-r1:32b` (19GB)

## Step 1: Fresh VS Code Setup

**IMPORTANT:** Close VS Code completely if open.

```bash
# Reset Continue cache
rm -rf ~/.continue/dev_data
rm -rf ~/.continue/index

# Close all VS Code windows
killall "Electron" 2>/dev/null || true
```

## Step 2: Open Workspace Correctly

1. Click **File → Open Folder**
2. Select: `/Users/rachitgupta/Library/CloudStorage/OneDrive-KPMG/Apps/agentic-platform/agentic-platform`
3. Click **Open**
4. VS Code will show this as your workspace root

**CRITICAL:** The folder must appear at top of Explorer sidebar as the workspace

## Step 3: Install Continue Extension

1. Click **Extensions** (Ctrl+Shift+X)
2. Search: `Continue`
3. Install the official **Continue** extension (>1.5M downloads)
4. Click **Enable** when prompted
5. Reload VS Code (Cmd+R)

## Step 4: Verify Configuration

1. Click **Continue** icon on left sidebar (looks like ">_")
2. Should open a chat panel on right
3. At bottom, click **Settings** ⚙️
4. Verify it shows:
   - Model: DeepSeek-R1 (Ollama)
   - API Base: http://localhost:11434
   - Status: Connected ✓

## Step 5: Enable Inline Code Suggestions

1. In Continue settings, find **"Tab Autocomplete"**
2. Toggle: **ON**
3. Find **"Auto-suggest on keystroke"**
4. Toggle: **ON**

## Step 6: Index Your Codebase

1. Open any Python or JS file in editor
2. Continue should show: "Indexing your repository..."
3. Wait for indexing to complete (~1-2 min)
4. Status will show: "Indexed: 44 files"

## Step 7: Test It Works

**Chat Test:**
1. Click Continue icon (left sidebar)
2. Type: `@codebase what does agent-service do?`
3. Press Enter
4. DeepSeek should respond with analysis

**Inline Autocomplete Test:**
1. Open any Python file (e.g., services/agent/main.py)
2. Type: `def ` and press Tab
3. Continue should suggest function names
4. Type function name and it auto-completes

**Edit Test:**
1. Select any code block
2. Click **Edit with Continue**
3. Describe the change you want
4. DeepSeek will show code diff

## Troubleshooting

**Q: Chat panel appears but says "No model selected"**
- Fix: Settings → DeepSeek-R1 → Set as Default

**Q: Indexing doesn't start**
- Fix: Close and reopen VS Code with workspace as root

**Q: "Cannot connect to Ollama"**
- Fix: Make sure `ollama serve` is running in separate terminal

**Q: Autocomplete not triggering**
- Fix: Enable in Settings → Tab Autocomplete → ON

## Usage Tips

### In Chat (Seamless like Copilot)
```
@codebase Explain the authentication flow
/edit Refactor this function to be cleaner
/docs Search documentation for rate limiting
```

### Inline While Coding
- **Autocomplete:** Start typing → Tab to accept
- **Selection + Right-click:** "Ask Continue"
- **Cmd+K:** Open inline edit dialog

### Full Integration
- Green checkmark = Code accepted
- Red X = Reject suggestion
- Both work seamlessly in editor flow

## Performance Notes
- First load: 30-60 seconds (indexing)
- Subsequent queries: 5-15 seconds (local inference)
- No internet required after setup

---

**You're all set!** Now use DeepSeek-R1 exactly like GitHub Copilot:
- Inline suggestions while typing
- Chat for questions
- Right-click context menu
- Full editor integration

**Start coding with:** Cmd+Shift+; to open Continue chat anytime
