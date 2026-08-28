/**
 * Docker Image Management Admin Panel
 * Handles version updates, security scanning, and vulnerability management
 */

// Global state
let dockerImageState = {
  images: [],
  securitySummary: null,
  updates: null,
  lastScan: null,
  autoRefreshInterval: null,
};

/**
 * Load all Docker images and their information
 */
async function loadDockerImages() {
  try {
    document.getElementById('docker-loading')?.classList.add('hidden');
    const container = document.getElementById('docker-images-table');
    if (!container) return;
    
    const response = await fetch('/admin/docker/images', {
      headers: {
        'x-workspace-id': window.currentWorkspace?.id || 'default',
        'x-user-id': window.currentUser?.id || 'system',
        'x-user-role': window.currentUser?.role || 'admin',
      }
    });

    if (!response.ok) throw new Error('Failed to load Docker images');
    
    const images = await response.json();
    dockerImageState.images = images;

    renderDockerImagesTable(images, container);
  } catch (error) {
    console.error('Error loading Docker images:', error);
    const container = document.getElementById('docker-images-table');
    if (container) {
      container.innerHTML = `<div class="error-message">Error loading images: ${error.message}</div>`;
    }
  }
}

/**
 * Render Docker images table
 */
function renderDockerImagesTable(images, container) {
  if (!images || images.length === 0) {
    container.innerHTML = '<p style="color: var(--text-3);">No Docker images found</p>';
    return;
  }

  const html = `
    <div style="overflow-x: auto">
      <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem">
        <thead>
          <tr style="border-bottom: 2px solid var(--border);">
            <th style="text-align: left; padding: 0.75rem; font-weight: 600;">Image</th>
            <th style="text-align: left; padding: 0.75rem; font-weight: 600;">Registry</th>
            <th style="text-align: left; padding: 0.75rem; font-weight: 600;">Current</th>
            <th style="text-align: left; padding: 0.75rem; font-weight: 600;">Latest</th>
            <th style="text-align: left; padding: 0.75rem; font-weight: 600;">Security</th>
            <th style="text-align: center; padding: 0.75rem; font-weight: 600;">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${images.map(img => `
            <tr style="border-bottom: 1px solid var(--border); transition: background 0.18s;">
              <td style="padding: 0.75rem; font-weight: 500;">${img.name}</td>
              <td style="padding: 0.75rem; font-family: monospace; font-size: 0.85rem; color: var(--text-2);">${img.registry}</td>
              <td style="padding: 0.75rem; font-family: monospace; font-size: 0.85rem;">${img.current_version}</td>
              <td style="padding: 0.75rem; font-family: monospace; font-size: 0.85rem;">${img.latest_version || '—'}</td>
              <td style="padding: 0.75rem;">
                <span style="
                  display: inline-block;
                  padding: 0.25rem 0.75rem;
                  border-radius: 0.25rem;
                  font-size: 0.75rem;
                  font-weight: 600;
                  text-transform: uppercase;
                  background: ${getSecurityStatusColor(img.security_status)};
                  color: white;
                ">
                  ${img.security_status}
                </span>
              </td>
              <td style="padding: 0.75rem; text-align: center;">
                <div style="display: flex; gap: 0.5rem; justify-content: center;">
                  <button class="btn btn-sm" onclick="scanDockerImage('${img.name}')" title="Scan for vulnerabilities">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                    Scan
                  </button>
                  ${img.latest_version && img.latest_version !== img.current_version ? `
                    <button class="btn btn-sm" onclick="showUpdateImageModal('${img.name}', '${img.current_version}', '${img.latest_version}')" title="Update to latest version">
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="23 4 23 10 17 10"></polyline>
                        <path d="M20.49 15A9 9 0 1 1 21 12"></path>
                      </svg>
                      Update
                    </button>
                  ` : ''}
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  container.innerHTML = html;
}

/**
 * Get color for security status
 */
function getSecurityStatusColor(status) {
  const colors = {
    'safe': '#10b981',      // Green
    'warning': '#f59e0b',   // Amber
    'critical': '#ef4444',  // Red
    'unknown': '#6b7280'    // Gray
  };
  return colors[status] || '#6b7280';
}

/**
 * Scan all Docker images for vulnerabilities
 */
async function scanAllDockerImages() {
  try {
    const button = event.target.closest('button');
    const originalText = button.textContent;
    button.textContent = 'Scanning...';
    button.disabled = true;

    const response = await fetch('/admin/docker/scan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-workspace-id': window.currentWorkspace?.id || 'default',
        'x-user-id': window.currentUser?.id || 'system',
        'x-user-role': window.currentUser?.role || 'admin',
      }
    });

    if (!response.ok) throw new Error('Scan failed');
    
    const result = await response.json();
    dockerImageState.lastScan = result;

    showNotification('Scan complete', 'success');
    loadDockerSecuritySummary();
    loadDockerImages();
  } catch (error) {
    console.error('Error scanning images:', error);
    showNotification('Scan failed: ' + error.message, 'error');
  } finally {
    const button = event.target.closest('button');
    button.textContent = originalText;
    button.disabled = false;
  }
}

/**
 * Scan a specific Docker image
 */
async function scanDockerImage(imageName) {
  try {
    const button = event.target.closest('button');
    button.disabled = true;

    const response = await fetch(`/admin/docker/scan/${imageName}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-workspace-id': window.currentWorkspace?.id || 'default',
        'x-user-id': window.currentUser?.id || 'system',
        'x-user-role': window.currentUser?.role || 'admin',
      }
    });

    if (!response.ok) throw new Error('Scan failed');
    
    const result = await response.json();
    showImageScanResults(imageName, result);
    loadDockerImages();
  } catch (error) {
    console.error('Error scanning image:', error);
    showNotification('Scan failed: ' + error.message, 'error');
  } finally {
    const button = event.target.closest('button');
    button.disabled = false;
  }
}

/**
 * Load Docker security summary
 */
async function loadDockerSecuritySummary() {
  try {
    const response = await fetch('/admin/docker/security-summary', {
      headers: {
        'x-workspace-id': window.currentWorkspace?.id || 'default',
        'x-user-id': window.currentUser?.id || 'system',
        'x-user-role': window.currentUser?.role || 'admin',
      }
    });

    if (!response.ok) throw new Error('Failed to load summary');
    
    const summary = await response.json();
    dockerImageState.securitySummary = summary;
    renderDockerSecuritySummary(summary);
  } catch (error) {
    console.error('Error loading security summary:', error);
  }
}

/**
 * Render security summary cards
 */
function renderDockerSecuritySummary(summary) {
  const container = document.getElementById('docker-security-cards');
  if (!container) return;

  const html = `
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
      <div class="card" style="text-align: center; padding: 1rem;">
        <div style="font-size: 1.8rem; font-weight: 700; color: #10b981;">${summary.security_status.safe}</div>
        <div style="font-size: 0.7rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em;">Safe</div>
      </div>
      <div class="card" style="text-align: center; padding: 1rem;">
        <div style="font-size: 1.8rem; font-weight: 700; color: #f59e0b;">${summary.security_status.warning}</div>
        <div style="font-size: 0.7rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em;">Warning</div>
      </div>
      <div class="card" style="text-align: center; padding: 1rem;">
        <div style="font-size: 1.8rem; font-weight: 700; color: #ef4444;">${summary.security_status.critical}</div>
        <div style="font-size: 0.7rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em;">Critical</div>
      </div>
      <div class="card" style="text-align: center; padding: 1rem;">
        <div style="font-size: 1.8rem; font-weight: 700; color: var(--text-1);">${summary.total_vulnerabilities}</div>
        <div style="font-size: 0.7rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em;">Total CVEs</div>
      </div>
    </div>
  `;

  container.innerHTML = html;

  // Render needs attention list
  if (summary.needs_immediate_attention.length > 0) {
    const attentionContainer = document.getElementById('docker-attention-needed');
    if (attentionContainer) {
      const attentionHtml = `
        <div class="card" style="border-left: 4px solid #ef4444; background: rgba(239, 68, 68, 0.05);">
          <h4 style="color: #ef4444; margin-top: 0;">⚠ Needs Immediate Attention</h4>
          <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
            ${summary.needs_immediate_attention.map(img => `<li>${img}</li>`).join('')}
          </ul>
        </div>
      `;
      attentionContainer.innerHTML = attentionHtml;
    }
  }
}

/**
 * Show update image modal
 */
function showUpdateImageModal(imageName, currentVersion, latestVersion) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.innerHTML = `
    <div class="modal-content" style="max-width: 500px;">
      <div class="modal-header">
        <h3>Update Docker Image</h3>
        <button class="btn btn-close" onclick="this.closest('.modal').remove()">×</button>
      </div>
      <div class="modal-body">
        <p><strong>Image:</strong> ${imageName}</p>
        <p><strong>Current:</strong> <code>${currentVersion}</code></p>
        <p><strong>Latest:</strong> <code>${latestVersion}</code></p>
        <p style="color: var(--text-3); font-size: 0.9rem;">
          This will update the environment variable and require rebuilding containers.
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
        <button class="btn btn-primary" onclick="updateDockerImage('${imageName}', '${latestVersion}'); this.closest('.modal').remove();">
          Update to ${latestVersion}
        </button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

/**
 * Update a Docker image version
 */
async function updateDockerImage(imageName, newVersion) {
  try {
    const response = await fetch('/admin/docker/update-version', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-workspace-id': window.currentWorkspace?.id || 'default',
        'x-user-id': window.currentUser?.id || 'system',
        'x-user-role': window.currentUser?.role || 'admin',
      },
      body: JSON.stringify({
        image: imageName,
        version: newVersion
      })
    });

    if (!response.ok) throw new Error('Update failed');
    
    const result = await response.json();
    
    if (result.success) {
      showNotification(`${imageName} updated to ${newVersion}. Run docker compose to apply.`, 'success');
      loadDockerImages();
      loadDockerSecuritySummary();
    } else {
      throw new Error(result.error);
    }
  } catch (error) {
    console.error('Error updating image:', error);
    showNotification('Update failed: ' + error.message, 'error');
  }
}

/**
 * Show scan results modal
 */
function showImageScanResults(imageName, results) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  const vulnHtml = results.vulnerabilities && results.vulnerabilities.length > 0
    ? results.vulnerabilities.map(v => `
        <div style="margin: 0.5rem 0; padding: 0.5rem; background: var(--card-bg); border-left: 3px solid ${getSecurityStatusColor(v.severity)};">
          <strong>${v.id}</strong> - ${v.severity.toUpperCase()}
          <p style="margin: 0.25rem 0 0; color: var(--text-2); font-size: 0.9rem;">${v.description}</p>
          <p style="margin: 0.25rem 0 0; color: var(--success); font-size: 0.85rem;">Fixed in: ${v.fixed_in}</p>
        </div>
      `).join('')
    : '<p style="color: var(--text-3);">No known vulnerabilities</p>';

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 600px;">
      <div class="modal-header">
        <h3>${imageName} Security Scan Results</h3>
        <button class="btn btn-close" onclick="this.closest('.modal').remove()">×</button>
      </div>
      <div class="modal-body">
        <p><strong>Status:</strong> <span style="color: ${getSecurityStatusColor(results.status)}">${results.status.toUpperCase()}</span></p>
        <p><strong>Vulnerabilities Found:</strong> ${results.vulnerability_count}</p>
        <p><strong>Last Checked:</strong> ${new Date(results.last_checked).toLocaleString()}</p>
        <div style="margin-top: 1rem; max-height: 300px; overflow-y: auto;">
          ${vulnHtml}
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

/**
 * Check for available updates
 */
async function checkDockerUpdates() {
  try {
    const button = event.target.closest('button');
    button.disabled = true;
    button.textContent = 'Checking...';

    const response = await fetch('/admin/docker/check-updates', {
      method: 'POST',
      headers: {
        'x-workspace-id': window.currentWorkspace?.id || 'default',
        'x-user-id': window.currentUser?.id || 'system',
        'x-user-role': window.currentUser?.role || 'admin',
      }
    });

    if (!response.ok) throw new Error('Check failed');
    
    const result = await response.json();
    dockerImageState.updates = result;
    
    const updatesContainer = document.getElementById('docker-updates-available');
    if (updatesContainer && result.updates_available > 0) {
      const html = `
        <div class="card" style="border-left: 4px solid #f59e0b; background: rgba(245, 158, 11, 0.05);">
          <h4 style="color: #f59e0b; margin-top: 0;">📦 ${result.updates_available} Update(s) Available</h4>
          <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
            ${Object.values(result.images).filter(img => img.update_available).map(img => `
              <li>${img.image}: ${img.current} → ${img.latest}</li>
            `).join('')}
          </ul>
        </div>
      `;
      updatesContainer.innerHTML = html;
    }
    
    showNotification('Update check complete', 'success');
  } catch (error) {
    console.error('Error checking updates:', error);
    showNotification('Update check failed: ' + error.message, 'error');
  } finally {
    const button = event.target.closest('button');
    button.disabled = false;
    button.textContent = 'Check for Updates';
  }
}

/**
 * Initialize Docker management panel
 */
function initDockerManagement() {
  loadDockerImages();
  loadDockerSecuritySummary();
  checkDockerUpdates();
  loadEnvVars();

  // Auto-refresh every 5 minutes
  dockerImageState.autoRefreshInterval = setInterval(() => {
    loadDockerSecuritySummary();
  }, 5 * 60 * 1000);
}

/**
 * Load and display environment variables
 */
async function loadEnvVars() {
  try {
    const container = document.getElementById('docker-env-vars');
    if (!container) return;

    const response = await fetch('/admin/docker/env-vars', {
      headers: {
        'x-workspace-id': window.currentWorkspace?.id || 'default',
        'x-user-id': window.currentUser?.id || 'system',
        'x-user-role': window.currentUser?.role || 'admin',
      }
    });
    
    if (!response.ok) throw new Error('Failed to load env vars');
    
    const envVars = await response.json();
    
    const html = Object.entries(envVars).map(function(entry) {
      const key = entry[0];
      const value = entry[1];
      const displayValue = key.includes('PASSWORD') || key.includes('SECRET') ? '••••••••' : value;
      return '<div style="padding: 0.75rem; background: var(--input-bg); border-radius: 0.25rem; border: 1px solid var(--border); margin-bottom: 0.5rem;">' +
        '<div style="display: grid; grid-template-columns: 150px 1fr auto; gap: 1rem; align-items: center;">' +
        '<code style="font-size: 0.85rem; color: var(--accent-text);">' + key + '</code>' +
        '<code style="font-size: 0.85rem; color: var(--text-2);">' + displayValue + '</code>' +
        '<button class="btn btn-sm" onclick="copyToClipboard(\'' + key + '=' + value.replace(/'/g, "\\'") + '\')">Copy</button>' +
        '</div></div>';
    }).join('');
    
    container.innerHTML = html || '<p style="color: var(--text-3);">No environment variables found</p>';
  } catch (error) {
    const container = document.getElementById('docker-env-vars');
    if (container) {
      container.innerHTML = '<div class="error-message">' + error.message + '</div>';
    }
  }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(function() {
    showNotification('Copied to clipboard', 'success');
  }).catch(function(err) {
    console.error('Failed to copy:', err);
    showNotification('Failed to copy', 'error');
  });
}

// Clean up on unload
window.addEventListener('beforeunload', () => {
  if (dockerImageState.autoRefreshInterval) {
    clearInterval(dockerImageState.autoRefreshInterval);
  }
});
