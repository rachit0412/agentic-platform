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
    let html = markdown;

    // Protect code blocks first
    const codeBlocks = [];
    html = html.replace(/```([^\n]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const idx = codeBlocks.length;
      codeBlocks.push(`<pre><code class="language-${lang || 'text'}">${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`);
      return `__CODE_BLOCK_${idx}__`;
    });

    // Protect tables
    const tables = [];
    html = html.replace(/\|.+\n\|[-:\s|]+\n((?:\|.+\n)*)/g, (match) => {
      const idx = tables.length;
      const rows = match.trim().split('\n');
      let table = '<table><tbody>';
      rows.forEach((row, i) => {
        table += '<tr>';
        row.split('|').filter(c => c.trim()).forEach(cell => {
          const tag = i === 0 ? 'th' : 'td';
          table += `<${tag}>${cell.trim()}</${tag}>`;
        });
        table += '</tr>';
        if (i === 0) table += '</tbody><tbody>';
      });
      table += '</tbody></table>';
      tables.push(table);
      return `__TABLE_${idx}__`;
    });

    // HTML escape remaining content
    html = html
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Headers
    html = html
      .replace(/^##### (.*?)$/gm, '<h5>$1</h5>')
      .replace(/^#### (.*?)$/gm, '<h4>$1</h4>')
      .replace(/^### (.*?)$/gm, '<h3>$1</h3>')
      .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
      .replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // Horizontal rules
    html = html.replace(/^---$/gm, '<hr>');

    // Blockquotes
    html = html.replace(/^&gt; (.*?)$/gm, '<blockquote>$1</blockquote>');

    // Lists - ordered
    html = html.replace(/^\d+\. (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>)/s, (match) => 
      !match.includes('<ol>') && !match.includes('<ul>') && match.match(/^\d+/) ? `<ol>${match}</ol>` : match
    );

    // Lists - unordered
    html = html.replace(/^[-*+] (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>)/s, (match) => {
      if (match.includes('<ol>') || match.includes('<ul>')) return match;
      return `<ul>${match}</ul>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/__(.+?)__/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>').replace(/_(.+?)_/g, '<em>$1</em>');

    // Links
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2">$1</a>');

    // Paragraphs
    html = html.replace(/\n\n+/g, '</p><p>');
    if (!html.startsWith('<')) html = `<p>${html}`;
    if (!html.endsWith('>')) html += '</p>';

    // Restore code blocks
    codeBlocks.forEach((block, i) => {
      html = html.replace(`__CODE_BLOCK_${i}__`, block);
    });

    // Restore tables
    tables.forEach((table, i) => {
      html = html.replace(`__TABLE_${i}__`, table);
    });

    return html;
  }

  slugify(text) {
    return String(text || '')
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-');
  }

  enhanceRenderedContent(element) {
    if (!element) return;

    // Add stable ids to headings for in-page anchor links.
    const seen = new Map();
    element.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach((h) => {
      if (h.id) return;
      const base = this.slugify(h.textContent);
      if (!base) return;
      const count = seen.get(base) || 0;
      seen.set(base, count + 1);
      h.id = count === 0 ? base : `${base}-${count}`;
    });

    // Rewrite markdown doc links to in-app docs route.
    element.querySelectorAll('a[href]').forEach((a) => {
      const href = a.getAttribute('href') || '';
      const mdMatch = href.match(/^\.?\/?([A-Za-z0-9._-]+)\.md(#.*)?$/i);
      if (mdMatch) {
        const stem = mdMatch[1].replace(/\.[^.]+$/, '');
        const slug = this.slugify(stem);
        const suffix = mdMatch[2] || '';
        a.setAttribute('href', `/docs#${slug}${suffix}`);
      }
    });
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
      this.enhanceRenderedContent(element);
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

// Backward compatibility:
// Some pages call DocsClient.method(...) (class-style) instead of window.DocsClient.method(...)
// Expose static shims so both invocation styles work safely.
if (typeof globalThis.DocsClient === 'function') {
  const staticMethods = [
    'fetchDoc',
    'listDocs',
    'getTableOfContents',
    'renderMarkdown',
    'loadIntoElement',
    'refresh',
    'setupHashListener'
  ];
  staticMethods.forEach((methodName) => {
    if (typeof globalThis.DocsClient[methodName] !== 'function') {
      globalThis.DocsClient[methodName] = (...args) => window.DocsClient[methodName](...args);
    }
  });
}
