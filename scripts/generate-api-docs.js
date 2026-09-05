/**
 * API Endpoint Extractor
 * Automatically discovers and documents all API endpoints
 * Generates API reference documentation dynamically
 */

const fs = require('fs');
const path = require('path');

class APIDocGenerator {
  constructor(serverFilePath) {
    this.serverFilePath = serverFilePath;
    this.endpoints = [];
  }

  /**
   * Extract endpoints from Express server file
   */
  extractEndpoints() {
    const fileContent = fs.readFileSync(this.serverFilePath, 'utf-8');
    const lines = fileContent.split('\n');

    // Regex patterns to match API endpoints
    const patterns = [
      /app\.(get|post|put|delete|patch)\s*\(\s*["'`]([^"'`]+)["'`]/g,
      /router\.(get|post|put|delete|patch)\s*\(\s*["'`]([^"'`]+)["'`]/g,
    ];

    const foundEndpoints = new Map();

    // Extract from file
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      for (const pattern of patterns) {
        let match;
        pattern.lastIndex = 0;
        while ((match = pattern.exec(line)) !== null) {
          const method = match[1].toUpperCase();
          const path = match[2];

          if (path.includes('/api/')) {
            const key = `${method}:${path}`;
            if (!foundEndpoints.has(key)) {
              // Try to find comments above this endpoint
              let description = '';
              for (let j = Math.max(0, i - 5); j < i; j++) {
                if (lines[j].includes('//') && lines[j].includes('GET|POST|PUT|DELETE|PATCH')) {
                  description = lines[j].replace(/.*\/\/\s*/, '').trim();
                  break;
                }
              }

              foundEndpoints.set(key, {
                method,
                path,
                line: i + 1,
                description: description || 'No description available'
              });
            }
          }
        }
      }
    }

    // Convert to array and sort by path
    this.endpoints = Array.from(foundEndpoints.values()).sort((a, b) => {
      if (a.path !== b.path) return a.path.localeCompare(b.path);
      return a.method.localeCompare(b.method);
    });

    return this.endpoints;
  }

  /**
   * Group endpoints by category
   */
  groupByCategory() {
    const groups = {};

    this.endpoints.forEach(endpoint => {
      // Extract category from path (e.g., /api/docs → docs)
      const match = endpoint.path.match(/\/api\/([^\/]+)/);
      const category = match ? match[1] : 'other';

      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(endpoint);
    });

    return groups;
  }

  /**
   * Generate markdown documentation
   */
  generateMarkdown() {
    const groups = this.groupByCategory();
    const categoryOrder = [
      'auth',
      'docs',
      'health',
      'users',
      'workspaces',
      'agents',
      'skills',
      'tools',
      'documents',
      'workflows',
      'personas',
      'guardrails',
      'prompts',
      'db',
      'export',
      'import',
      'admin',
    ];

    let markdown = `# API Reference

> **Auto-generated API endpoint documentation**
> Generated from: \`services/ui-console/server.js\`
> Total Endpoints: ${this.endpoints.length}

## Quick Navigation

`;

    // Generate table of contents
    Object.keys(groups).sort((a, b) => {
      const aIdx = categoryOrder.indexOf(a);
      const bIdx = categoryOrder.indexOf(b);
      if (aIdx === -1 && bIdx === -1) return a.localeCompare(b);
      if (aIdx === -1) return 1;
      if (bIdx === -1) return -1;
      return aIdx - bIdx;
    }).forEach(category => {
      const count = groups[category].length;
      markdown += `- [${category.toUpperCase()} (${count} endpoints)](#${category})\n`;
    });

    markdown += '\n---\n\n';

    // Generate sections for each category
    Object.keys(groups).sort((a, b) => {
      const aIdx = categoryOrder.indexOf(a);
      const bIdx = categoryOrder.indexOf(b);
      if (aIdx === -1 && bIdx === -1) return a.localeCompare(b);
      if (aIdx === -1) return 1;
      if (bIdx === -1) return -1;
      return aIdx - bIdx;
    }).forEach(category => {
      const endpoints = groups[category];

      markdown += `## ${category.toUpperCase()}\n\n`;
      markdown += `**${endpoints.length} endpoint${endpoints.length !== 1 ? 's' : ''}**\n\n`;

      // Create table of endpoints
      markdown += '| Method | Path | Description |\n';
      markdown += '|--------|------|-------------|\n';

      endpoints.forEach(endpoint => {
        const methodBadge = this.getMethodBadge(endpoint.method);
        markdown += `| ${methodBadge} | \`${endpoint.path}\` | ${endpoint.description} |\n`;
      });

      markdown += '\n';
    });

    // Add usage guide
    markdown += `---

## API Usage Guide

### Authentication

All endpoints (except \`/auth/\*\` and \`/health\`) require a valid session cookie:

\`\`\`bash
# Login first
curl -X POST http://localhost:3005/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"admin","password":"password"}' \\
  -c cookies.txt

# Then use the session cookie
curl http://localhost:3005/api/users \\
  -b cookies.txt
\`\`\`

### Response Format

All API responses are JSON:

\`\`\`json
{
  "status": "success|error",
  "data": {...},
  "timestamp": "2025-09-06T14:32:15Z"
}
\`\`\`

### Error Handling

- **400**: Bad Request - Invalid input
- **401**: Unauthorized - Not authenticated
- **403**: Forbidden - Insufficient permissions
- **404**: Not Found - Resource doesn't exist
- **500**: Internal Server Error

### Rate Limiting

- Authentication endpoints: 5 attempts per 5 minutes per IP
- General endpoints: No limit (session-based)

### Documentation API

Special endpoints for dynamic content:

\`\`\`bash
# List all documentation
GET /api/docs

# Get specific documentation
GET /api/docs/{docname}?format=raw&toc=true

# Refresh cache
POST /api/docs/{docname}/refresh
POST /api/docs/refresh-all
\`\`\`

---

## Statistics

**Total Endpoints**: ${this.endpoints.length}

**By Method**:
\`\`\`
${this.getMethodStats()}
\`\`\`

**By Category**:
\`\`\`
${this.getCategoryStats(groups)}
\`\`\`

---

## Common Patterns

### Create Resource
\`\`\`bash
curl -X POST http://localhost:3005/api/{resource} \\
  -H "Content-Type: application/json" \\
  -d '{"name":"example"}' \\
  -b cookies.txt
\`\`\`

### Read Resource
\`\`\`bash
curl http://localhost:3005/api/{resource}/{id} \\
  -b cookies.txt
\`\`\`

### Update Resource
\`\`\`bash
curl -X PUT http://localhost:3005/api/{resource}/{id} \\
  -H "Content-Type: application/json" \\
  -d '{"name":"updated"}' \\
  -b cookies.txt
\`\`\`

### Delete Resource
\`\`\`bash
curl -X DELETE http://localhost:3005/api/{resource}/{id} \\
  -b cookies.txt
\`\`\`

---

Generated: ${new Date().toISOString()}
`;

    return markdown;
  }

  /**
   * Get method badge for markdown
   */
  getMethodBadge(method) {
    const badges = {
      'GET': '🔍 GET',
      'POST': '✏️ POST',
      'PUT': '🔄 PUT',
      'DELETE': '🗑️ DELETE',
      'PATCH': '📝 PATCH'
    };
    return badges[method] || method;
  }

  /**
   * Get statistics by method
   */
  getMethodStats() {
    const stats = {};
    this.endpoints.forEach(endpoint => {
      stats[endpoint.method] = (stats[endpoint.method] || 0) + 1;
    });

    return Object.entries(stats)
      .sort((a, b) => b[1] - a[1])
      .map(([method, count]) => `  ${method}: ${count}`)
      .join('\n');
  }

  /**
   * Get statistics by category
   */
  getCategoryStats(groups) {
    return Object.entries(groups)
      .sort((a, b) => b[1].length - a[1].length)
      .map(([category, endpoints]) => `  ${category}: ${endpoints.length}`)
      .join('\n');
  }

  /**
   * Generate and save documentation
   */
  generateAndSave(outputPath) {
    this.extractEndpoints();
    const markdown = this.generateMarkdown();

    fs.writeFileSync(outputPath, markdown, 'utf-8');
    console.log(`✅ API documentation generated: ${outputPath}`);
    console.log(`📊 Found ${this.endpoints.length} endpoints`);

    return {
      count: this.endpoints.length,
      path: outputPath,
      timestamp: new Date()
    };
  }
}

module.exports = APIDocGenerator;
