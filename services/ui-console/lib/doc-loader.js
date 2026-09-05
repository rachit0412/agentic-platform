/**
 * Dynamic Documentation Loader
 *
 * Loads and caches markdown documentation files dynamically
 * Watch for file changes and invalidate cache automatically
 * Provides both raw markdown and parsed content
 */

const fs = require('fs');
const path = require('path');
const { watch } = require('fs');

class DocLoader {
  constructor(docsPath) {
    this.docsPath = docsPath || path.join(__dirname, '../../..', 'docs');
    this.cache = new Map();
    this.fileWatchers = new Map();
    this.mdToHtml = null;

    // Try to load markdown parser
    try {
      const { marked } = require('marked');
      this.mdToHtml = marked;
    } catch (e) {
      console.warn('marked not available, using fallback markdown parsing');
      this.mdToHtml = this.fallbackMarkdownParse;
    }
  }

  /**
   * Fallback markdown parser (basic, without marked dependency)
   */
  fallbackMarkdownParse(markdown) {
    let html = markdown
      // Code blocks
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
      // Headers
      .replace(/^### (.*?)$/gm, '<h3>$1</h3>')
      .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
      .replace(/^# (.*?)$/gm, '<h1>$1</h1>')
      // Bold
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      // Links
      .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2">$1</a>')
      // Line breaks
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');

    return `<p>${html}</p>`;
  }

  /**
   * Load markdown file and return raw content
   */
  loadRaw(docName) {
    const filePath = path.join(this.docsPath, `${docName}.md`);

    // Check if file exists
    if (!fs.existsSync(filePath)) {
      throw new Error(`Documentation file not found: ${docName}`);
    }

    // Return raw markdown
    return fs.readFileSync(filePath, 'utf-8');
  }

  /**
   * Load markdown file and return parsed HTML
   */
  loadParsed(docName, forceRefresh = false) {
    const cacheKey = `parsed:${docName}`;

    // Return from cache if available
    if (!forceRefresh && this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    // Load raw markdown
    const raw = this.loadRaw(docName);

    // Parse to HTML
    let html;
    try {
      if (typeof this.mdToHtml === 'function') {
        html = this.mdToHtml(raw);
      } else {
        // If marked is object with async parse, use sync if available
        html = this.mdToHtml.parse ? this.mdToHtml.parse(raw) : this.fallbackMarkdownParse(raw);
      }
    } catch (e) {
      console.error(`Error parsing markdown for ${docName}:`, e);
      html = this.fallbackMarkdownParse(raw);
    }

    // Cache result
    this.cache.set(cacheKey, html);

    // Watch for file changes and invalidate cache
    this.watchFile(docName);

    return html;
  }

  /**
   * Get both raw and parsed content
   */
  load(docName, options = {}) {
    const raw = this.loadRaw(docName);
    const parsed = this.loadParsed(docName, options.forceRefresh);

    return {
      name: docName,
      raw,
      parsed,
      timestamp: new Date(),
      path: path.join(this.docsPath, `${docName}.md`)
    };
  }

  /**
   * List all available documentation files
   */
  listDocs() {
    try {
      const files = fs.readdirSync(this.docsPath);
      return files
        .filter(f => f.endsWith('.md'))
        .map(f => f.replace(/\.md$/, ''))
        .sort();
    } catch (e) {
      console.error('Error listing docs:', e);
      return [];
    }
  }

  /**
   * Watch file for changes and invalidate cache
   */
  watchFile(docName) {
    const filePath = path.join(this.docsPath, `${docName}.md`);

    // Already watching
    if (this.fileWatchers.has(filePath)) {
      return;
    }

    // Set up file watcher
    const watcher = watch(filePath, { persistent: false }, (eventType, filename) => {
      if (eventType === 'change') {
        console.log(`📝 Documentation changed: ${docName}`);
        // Invalidate cache for this document and derived caches
        this.cache.delete(`parsed:${docName}`);
        this.cache.delete(`raw:${docName}`);
      }
    });

    this.fileWatchers.set(filePath, watcher);
  }

  /**
   * Get table of contents from markdown
   */
  getTableOfContents(docName) {
    const raw = this.loadRaw(docName);
    const lines = raw.split('\n');
    const toc = [];

    lines.forEach(line => {
      const match = line.match(/^(#{1,6})\s+(.+)$/);
      if (match) {
        const level = match[1].length;
        const title = match[2];
        const id = title
          .toLowerCase()
          .replace(/[^\w\s-]/g, '')
          .replace(/\s+/g, '-');

        toc.push({
          level,
          title,
          id
        });
      }
    });

    return toc;
  }

  /**
   * Clear all caches
   */
  clearCache() {
    this.cache.clear();
    console.log('📦 Documentation cache cleared');
  }

  /**
   * Destroy all watchers
   */
  destroy() {
    this.fileWatchers.forEach(watcher => {
      watcher.close();
    });
    this.fileWatchers.clear();
  }
}

module.exports = DocLoader;
