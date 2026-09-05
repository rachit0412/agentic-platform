/**
 * Client-side Dynamic Documentation Loader
 * Loads markdown documentation from API and renders it dynamically
 */

class DocsClient {
  constructor(apiBase = '/api/docs') {
    this.apiBase = apiBase;
    this.cache = new Map();
    this.currentDoc = null;
  }

  /**
   * Fetch documentation from API
   */
  async fetchDoc(docname, options = {}) {
    const cacheKey = `${docname}:${options.format || 'raw'}`;

    if (!options.forceRefresh && this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    const params = new URLSearchParams({
      format: options.format || 'raw',
      toc: options.toc ? 'true' : 'false',
      ...options.params
    });

    try {
      const response = await fetch(`${this.apiBase}/${docname}?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      this.cache.set(cacheKey, data);
      return data;
    } catch (e) {
      console.error(`Error loading documentation ${docname}:`, e);
      throw e;
    }
  }

  /**
   * List all available documentation
   */
  async listDocs() {
    try {
      const response = await fetch(`${this.apiBase}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (e) {
      console.error('Error listing docs:', e);
      return { count: 0, docs: [] };
    }
  }

  /**
   * Get table of contents
   */
  async getTableOfContents(docname) {
    try {
      const response = await fetch(`${this.apiBase}/${docname}/toc`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (e) {
      console.error(`Error loading TOC for ${docname}:`, e);
      return { toc: [], count: 0 };
    }
  }

  /**
   * Render markdown content to HTML (client-side fallback)
   */
  renderMarkdown(markdown) {
    let html = markdown
      // Escape HTML
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Code blocks (restore HTML after escape)
      .replace(/&lt;pre&gt;&lt;code[^&]*&gt;([\s\S]*?)&lt;\/code&gt;&lt;\/pre&gt;/g,
        '<pre><code>$1</code></pre>')
      // Re-allow < and > in regular content for readability
      .replace(/&lt;(\/?[\w]+[^&]*?)&gt;/g, '<$1>')
      // Headers
      .replace(/^### (.*?)$/gm, '<h3>$1</h3>')
      .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
      .replace(/^# (.*?)$/gm, '<h1>$1</h1>')
      // Horizontal rules
      .replace(/^---$/gm, '<hr>')
      // Blockquotes
      .replace(/^> (.*?)$/gm, '<blockquote>$1</blockquote>')
      // Unordered lists
      .replace(/^\s*[-*+] (.*?)$/gm, '<li>$1</li>')
      .replace(/(<li>.*?<\/li>)/s, (match) => {
        return match.includes('<ul>') ? match : `<ul>${match}</ul>`;
      })
      // Code inline
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // Bold
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      // Links
      .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>')
      // Paragraphs
      .replace(/\n\n/g, '</p><p>')
      .replace(/^([^<])/gm, (match) => !match.includes('<') ? '<p>' + match : match);

    return html.includes('<p>') ? html : `<p>${html}</p>`;
  }

  /**
   * Load and display documentation in an element
   */
  async loadIntoElement(docname, elementSelector, options = {}) {
    try {
      const element = document.querySelector(elementSelector);
      if (!element) {
        console.error(`Element not found: ${elementSelector}`);
        return;
      }

      element.innerHTML = '<div style="text-align: center; padding: 2rem;"><p>Loading documentation...</p></div>';

      // Fetch documentation
      const doc = await this.fetchDoc(docname, {
        format: options.format || 'raw',
        toc: options.showToc,
        forceRefresh: options.forceRefresh
      });

      // Render content
      let html = options.format === 'html' ? doc.content : this.renderMarkdown(doc.content);

      // Add table of contents if available and requested
      let tocHtml = '';
      if (options.showToc && doc.toc) {
        tocHtml = '<nav class="docs-toc"><ul>';
        doc.toc.forEach(item => {
          const padding = `${(item.level - 1) * 20}px`;
          tocHtml += `<li style="padding-left: ${padding}"><a href="#${item.id}">${item.title}</a></li>`;
        });
        tocHtml += '</ul></nav>';
      }

      element.innerHTML = tocHtml + html;
      this.currentDoc = docname;

      // Trigger mermaid rendering if available
      if (window.mermaid && !options.skipMermaid) {
        try {
          mermaid.run({ nodes: element.querySelectorAll('.mermaid') });
        } catch (e) {
          console.warn('Mermaid rendering skipped:', e.message);
        }
      }

    } catch (e) {
      const element = document.querySelector(elementSelector);
      if (element) {
        element.innerHTML = `<div style="color: red; padding: 1rem;"><strong>Error loading documentation:</strong> ${e.message}</div>`;
      }
    }
  }

  /**
   * Refresh documentation cache
   */
  async refresh(docname = null) {
    try {
      if (docname) {
        const response = await fetch(`${this.apiBase}/${docname}/refresh`, {
          method: 'POST'
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        this.cache.delete(`${docname}:raw`);
        this.cache.delete(`${docname}:html`);
        console.log(`✅ Refreshed documentation: ${docname}`);
      } else {
        const response = await fetch(`${this.apiBase}/refresh-all`, {
          method: 'POST'
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        this.cache.clear();
        console.log('✅ Refreshed all documentation');
      }
    } catch (e) {
      console.error('Error refreshing documentation:', e);
    }
  }

  /**
   * Setup auto-refresh on hash change
   */
  setupHashListener(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const loadFromHash = async () => {
      const hash = window.location.hash.replace('#', '');
      if (hash) {
        await this.loadIntoElement(hash, containerSelector, { showToc: true });
      }
    };

    window.addEventListener('hashchange', loadFromHash);
    loadFromHash(); // Initial load
  }
}

// Global instance
window.DocsClient = window.DocsClient || new DocsClient();
