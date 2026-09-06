# Dynamic Content Architecture Guide

## Overview

This document explains the dynamic content system that automatically loads content from files (markdown, JSON, etc.) without requiring manual synchronization or application restarts.

## Problem This Solves

Previously, when documentation markdown files were updated:
- Browser would show old cached/hardcoded content
- Required manual script runs to regenerate EJS templates
- Similar issues occurred with any hardcoded feature content
- Updates didn't propagate until application restart

## Solution: Dynamic Content System

The system consists of three layers:

### 1. Server-Side Loader (`lib/doc-loader.js`)

**Purpose**: Load and cache file content with automatic invalidation

**Key Features**:
- Reads markdown/JSON files on demand
- Caches content for performance
- Watches files for changes and auto-invalidates cache
- Provides parsing/transformation (markdown to HTML)
- Generates derived data (table of contents, etc.)

**Usage Example**:
```javascript
const DocLoader = require('./lib/doc-loader');
const loader = new DocLoader('/path/to/docs');

// Load raw content
const content = loader.loadRaw('principles');

// Load parsed content
const html = loader.loadParsed('principles');

// Get with both formats + TOC
const doc = loader.load('principles', { format: 'both' });

// List all available docs
const allDocs = loader.listDocs();

// Force refresh cache
loader.cache.delete('parsed:principles');
```

### 2. API Routes (`routes/docs-api.js`)

**Purpose**: Expose content via REST API

**Endpoints**:

```
GET /api/docs
  Returns: { count, docs: ['principles', 'architecture', ...] }

GET /api/docs/:docname
  Query params:
    - format: 'raw' | 'html' (default: 'raw')
    - toc: 'true' | 'false' (include table of contents)
    - refresh: 'true' (force cache refresh)
  Returns: { name, content, format, timestamp, toc, path }

GET /api/docs/:docname/toc
  Returns: { docname, toc: [{level, title, id}, ...], count }

POST /api/docs/:docname/refresh
  Returns: { status, docname, timestamp }

POST /api/docs/refresh-all
  Returns: { status, count, docs, timestamp }
```

### 3. Client-Side Loader (`public/js/docs-client.js`)

**Purpose**: Fetch and render content in the browser

**Key Features**:
- Fetches content from API
- Client-side markdown rendering (fallback)
- Automatic hash-based routing
- Mermaid diagram support
- Async loading with error handling

**Usage Example**:
```javascript
// Basic usage
await DocsClient.loadIntoElement('principles', '#content-div');

// With options
await DocsClient.loadIntoElement('principles', '#content-div', {
  showToc: true,           // Show table of contents
  format: 'raw',           // Use raw markdown (default)
  forceRefresh: true       // Bypass cache
});

// Auto-routing on hash change
DocsClient.setupHashListener('#content-div');
// Now #principles, #architecture, etc. load automatically

// Refresh cache programmatically
await DocsClient.refresh('principles');        // Refresh one doc
await DocsClient.refresh();                    // Refresh all
```

## Implementing Dynamic Content for New Features

### Step 1: Create Your Content Files

```
docs/
  my-feature.md
  my-feature-details.md
```

Content in markdown, JSON, or any format your loader supports.

### Step 2: Create a Loader (if needed)

For most cases, use the existing `DocLoader` class. For custom content:

```javascript
// lib/custom-loader.js
const DocLoader = require('./doc-loader');

class CustomLoader extends DocLoader {
  loadParsed(name, forceRefresh) {
    const raw = this.loadRaw(name);
    // Custom parsing logic
    return this.customParse(raw);
  }
}

module.exports = CustomLoader;
```

### Step 3: Register API Routes

In `server.js`, the docs-api router is already registered:

```javascript
const createDocsRouter = require("./routes/docs-api");
const docsPath = path.join(__dirname, "../../..", "docs");
const docsRouter = createDocsRouter(app, docsPath);
app.use(docsRouter);
```

For custom content, create a new router:

```javascript
// routes/features-api.js
module.exports = function createFeaturesRouter(app, contentPath) {
  const router = express.Router();
  const loader = new CustomLoader(contentPath);

  router.get('/api/features/:name', (req, res) => {
    try {
      const content = loader.load(req.params.name);
      res.json(content);
    } catch (e) {
      res.status(404).json({ error: e.message });
    }
  });

  return router;
};

// Register in server.js
const createFeaturesRouter = require('./routes/features-api');
const featuresRouter = createFeaturesRouter(app, './features');
app.use(featuresRouter);
```

### Step 4: Use in Frontend

In your EJS template:

```html
<div id="feature-content"></div>

<script src="/js/docs-client.js"></script>
<script>
  // Load feature documentation
  DocsClient.loadIntoElement('my-feature', '#feature-content', {
    showToc: true
  });
</script>
```

Or for custom content:

```html
<script>
  class FeaturesClient {
    async load(name, element) {
      const response = await fetch(`/api/features/${name}`);
      const data = await response.json();
      document.querySelector(element).innerHTML = data.content;
    }
  }

  const features = new FeaturesClient();
  features.load('my-feature', '#feature-content');
</script>
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│         User Browser                             │
│  ┌──────────────────────────────────────┐       │
│  │  DocsClient (docs-client.js)         │       │
│  │  - Fetch from API                    │       │
│  │  - Render markdown                   │       │
│  │  - Hash routing (#principles, etc.)  │       │
│  └──────────────────────────────────────┘       │
│                     │                           │
└─────────────────────┼───────────────────────────┘
                      │ HTTP
                      ▼
┌─────────────────────────────────────────────────┐
│         Express.js Server                       │
│  ┌──────────────────────────────────────┐       │
│  │  API Routes (docs-api.js)            │       │
│  │  - GET /api/docs                     │       │
│  │  - GET /api/docs/:name               │       │
│  │  - POST /api/docs/refresh            │       │
│  └──────────────────────────────────────┘       │
│                     │                           │
│  ┌──────────────────────────────────────┐       │
│  │  DocLoader (doc-loader.js)           │       │
│  │  - Load files                        │       │
│  │  - Cache + auto-invalidate           │       │
│  │  - File watchers                     │       │
│  │  - Parse/transform content           │       │
│  └──────────────────────────────────────┘       │
│                     │                           │
└─────────────────────┼───────────────────────────┘
                      │ File System
                      ▼
            ┌──────────────────┐
            │  Markdown Files  │
            │  - docs/         │
            │  - features/     │
            │  - etc.          │
            └──────────────────┘
```

## Key Benefits

1. **Automatic Updates**: Changes to content files are immediately reflected
2. **No Cache Staleness**: File watchers invalidate cache on changes
3. **Performance**: Server-side caching + client-side caching
4. **Flexibility**: Works with any content format
5. **Reusable**: Apply to any dynamic content (admin panels, features, etc.)
6. **Fallback Support**: Client-side markdown rendering if server unreachable
7. **SEO Friendly**: Server can render initial HTML for search engines
8. **Real-time Updates**: Multiple users see changes without reload

## Advanced Usage

### Custom Parsing

```javascript
// Override parse method in loader
class MyLoader extends DocLoader {
  loadParsed(name, forceRefresh) {
    const raw = this.loadRaw(name);
    
    // Custom transformations
    const transformed = raw
      .replace(/{{variable}}/g, process.env.MY_VAR)
      .replace(/<!--include-file:(.*?)-->/g, (match, file) => {
        return fs.readFileSync(file, 'utf-8');
      });
    
    return this.mdToHtml(transformed);
  }
}
```

### Watch Multiple Directories

```javascript
const loader = new DocLoader('/docs');

// Watch additional directory
loader.watchFile('../features/admin.md');
loader.watchFile('../configs/settings.json');
```

### Populate Metadata

```javascript
// Generate index of all docs with metadata
async function buildDocsIndex() {
  const docs = loader.listDocs();
  const index = [];

  for (const doc of docs) {
    const toc = loader.getTableOfContents(doc);
    index.push({
      name: doc,
      sections: toc.length,
      path: path.join(loader.docsPath, `${doc}.md`),
      lastModified: fs.statSync(path.join(loader.docsPath, `${doc}.md`)).mtime
    });
  }

  return index;
}
```

## Migration Path

### Before (Hardcoded Content)

```html
<div id="principles">
  <h1>Principles</h1>
  <p>Hardcoded content here...</p>
  <!-- Requires EJS template update to see new content -->
</div>
```

### After (Dynamic Content)

```html
<div id="principles"></div>
<script src="/js/docs-client.js"></script>
<script>
  DocsClient.loadIntoElement('principles', '#principles');
</script>
```

Update markdown file → Changes appear immediately ✅

## Testing

```javascript
// Test that content updates are reflected
async function testDynamicUpdate() {
  // Load initial content
  const v1 = await DocsClient.fetchDoc('test-doc');
  console.log(v1.content);

  // Modify file on disk
  fs.writeFileSync('docs/test-doc.md', '# Updated Content');

  // Refresh cache
  await DocsClient.refresh('test-doc');

  // Load again
  const v2 = await DocsClient.fetchDoc('test-doc', { forceRefresh: true });
  console.log(v2.content); // Should show "Updated Content"
}
```

## Summary

The dynamic content system eliminates the synchronization gap between source files and rendered output. Any feature using this pattern will automatically reflect updates without requiring:
- Manual regeneration scripts
- Application restarts
- Cache invalidation commands
- Template synchronization

This makes the platform more maintainable and ensures documentation and feature content are always up-to-date.
