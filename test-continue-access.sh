#!/bin/bash
# Continue.dev Access Test for Agentic-Platform

echo "═══════════════════════════════════════════════════════════"
echo "CONTINUE.DEV AGENTIC-PLATFORM ACCESS TEST"
echo "═══════════════════════════════════════════════════════════"
echo ""

PLATFORM_PATH="/Users/rachitgupta/Library/CloudStorage/OneDrive-KPMG/Apps/agentic-platform/agentic-platform"

echo "✓ Testing agentic-platform folder access..."
if [ -d "$PLATFORM_PATH" ]; then
    echo "  ✅ Folder is accessible: $PLATFORM_PATH"
else
    echo "  ❌ Folder NOT accessible"
    exit 1
fi

echo ""
echo "✓ Counting Python files..."
PY_COUNT=$(find "$PLATFORM_PATH" -type f -name "*.py" -not -path "*/node_modules/*" | wc -l)
echo "  ✅ Found $PY_COUNT Python files"

echo ""
echo "✓ Counting JavaScript/TypeScript files..."
JS_COUNT=$(find "$PLATFORM_PATH" -type f \( -name "*.js" -o -name "*.ts" \) -not -path "*/node_modules/*" | wc -l)
echo "  ✅ Found $JS_COUNT JS/TS files"

echo ""
echo "✓ Key source files accessible:"
find "$PLATFORM_PATH/services" -type f -name "main.py" -o -name "server.js" -o -name "app.py" | head -5 | sed 's/^/  ✅ /'

echo ""
echo "✓ Continue config status:"
if [ -f ~/.continue/config.yaml ]; then
    echo "  ✅ config.yaml exists"
    grep -q "contextProviders:" ~/.continue/config.yaml && echo "  ✅ contextProviders enabled"
fi

echo ""
echo "✓ Continue index status:"
if [ -f ~/.continue/index/index.sqlite ]; then
    INDEX_SIZE=$(du -h ~/.continue/index/index.sqlite | cut -f1)
    echo "  ✅ Index file exists (size: $INDEX_SIZE)"
else
    echo "  ⚠️  Index not yet built - will be created on first Continue.dev use"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "NEXT STEPS:"
echo "═══════════════════════════════════════════════════════════"
echo "1. Open VS Code with agentic-platform as workspace root"
echo "2. Open Continue.dev sidebar (Ctrl+Shift+; or Cmd+Shift+;)"
echo "3. In chat, type: @codebase What is the architecture?"
echo "4. DeepSeek-R1 will search and analyze your codebase"
echo ""
echo "✅ READY TO USE!"
