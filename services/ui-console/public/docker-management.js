/**
 * Docker Image Management Admin Panel
 * Handles version updates, security scanning, and vulnerability management
 */

// CSS for modals and notifications
const style = document.createElement('style');
style.textContent = `
  .modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  .modal-content {
    background: var(--modal-bg, #1e293b);
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
    border: 1px solid var(--modal-border, #334155);
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem;
    border-bottom: 1px solid var(--modal-border, #334155);
  }
  .modal-header h3 {
    margin: 0;
    font-size: 1.25rem;
    color: var(--text-1, #f1f5f9);
  }
  .modal-body {
    padding: 1.5rem;
    color: var(--text-1, #f1f5f9);
  }
  .modal-footer {
    padding: 1rem 1.5rem;
    border-top: 1px solid var(--modal-border, #334155);
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
  }
  .btn-close {
    background: transparent;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--text-2, #cbd5e1);
  }
  .btn-close:hover {
    color: var(--text-1, #f1f5f9);
  }
  .notification {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    background: var(--success, #10b981);
    color: white;
    z-index: 1001;
    animation: slideIn 0.3s ease-out;
  }
  .notification.error {
    background: var(--danger, #ef4444);
  }
  .btn-danger {
    background: #ef4444 !important;
    border-color: #ef4444 !important;
    color: white !important;
  }
  .btn-danger:hover {
    background: #dc2626 !important;
    border-color: #dc2626 !important;
  }
  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

/**
 * Show notification toast message
 */
function showNotification(message, type = 'success') {
  const notification = document.createElement('div');
  notification.className = `notification ${type === 'error' ? 'error' : ''}`;
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-out forwards';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}


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
    if (!container) {
      console.warn('Docker images table container not found');
      return;
    }
    
    const response = await fetch('/api/admin/docker/images');

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const images = await response.json();
    console.log('Docker images loaded:', images);
    
    if (!Array.isArray(images)) {
      console.error('Expected array of images, got:', typeof images);
      throw new Error('Invalid response format from Docker images API');
    }
    
    dockerImageState.images = images;
    renderDockerImagesTable(images, container);
  } catch (error) {
    console.error('Error loading Docker images:', error);
    const container = document.getElementById('docker-images-table');
    if (container) {
      container.innerHTML = `<div style="padding: 1.5rem; background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; color: #ef4444;">
        <strong>Error loading images:</strong> ${error.message}
        <p style="margin: 0.5rem 0 0; font-size: 0.85rem; color: #cbd5e1;">Check console for details</p>
      </div>`;
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

    const response = await fetch('/api/admin/docker/scan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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

    const response = await fetch(`/api/admin/docker/scan/${imageName}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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
    const response = await fetch('/api/admin/docker/security-summary');

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to load security summary`);
    }
    
    const summary = await response.json();
    console.log('Security summary loaded:', summary);
    
    dockerImageState.securitySummary = summary;
    renderDockerSecuritySummary(summary);
  } catch (error) {
    console.error('Error loading security summary:', error);
    const container = document.getElementById('docker-security-cards');
    if (container) {
      container.innerHTML = `<div style="padding: 1rem; background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; color: #ef4444;">
        Failed to load security summary: ${error.message}
      </div>`;
    }
  }
}

/**
 * Render security summary cards
 */
function renderDockerSecuritySummary(summary) {
  const container = document.getElementById('docker-security-cards');
  if (!container) return;

  // Handle various data formats
  const safe = (summary.security_status?.safe || summary.safe || 0);
  const warning = (summary.security_status?.warning || summary.warning || 0);
  const critical = (summary.security_status?.critical || summary.critical || 0);
  const total = (summary.total_vulnerabilities || (safe + warning + critical) || 0);
  
  const html = `
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
      <div class="card" style="
        text-align: center;
        padding: 1.5rem;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 8px;
      ">
        <div style="font-size: 2.2rem; font-weight: 700; color: #10b981; line-height: 1;">${safe}</div>
        <div style="font-size: 0.7rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.5rem;">✓ Safe</div>
      </div>
      <div class="card" style="
        text-align: center;
        padding: 1.5rem;
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 8px;
      ">
        <div style="font-size: 2.2rem; font-weight: 700; color: #f59e0b; line-height: 1;">${warning}</div>
        <div style="font-size: 0.7rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.5rem;">⚠ Warning</div>
      </div>
      <div class="card" style="
        text-align: center;
        padding: 1.5rem;
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 8px;
      ">
        <div style="font-size: 2.2rem; font-weight: 700; color: #ef4444; line-height: 1;">${critical}</div>
        <div style="font-size: 0.7rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.5rem;">🔴 Critical</div>
      </div>
      <div class="card" style="
        text-align: center;
        padding: 1.5rem;
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 8px;
      ">
        <div style="font-size: 2.2rem; font-weight: 700; color: #3b82f6; line-height: 1;">${total}</div>
        <div style="font-size: 0.7rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.5rem;">📊 Total CVEs</div>
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
    const response = await fetch('/api/admin/docker/update-version', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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
    ? results.vulnerabilities.map(v => {
        const severityColor = getSecurityStatusColor(v.severity || v.level || 'unknown');
        return `
          <div style="
            margin: 1rem 0;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-left: 4px solid ${severityColor};
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.1);
          ">
            <div style="display: flex; align-items: start; gap: 1rem;">
              <div style="
                flex-shrink: 0;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: ${severityColor};
                margin-top: 4px;
              "></div>
              <div style="flex: 1;">
                <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 0.25rem;">
                  ${v.id || 'Unknown Vulnerability'}
                  <span style="
                    display: inline-block;
                    padding: 0.1rem 0.5rem;
                    margin-left: 0.5rem;
                    font-size: 0.75rem;
                    background: ${severityColor};
                    color: white;
                    border-radius: 3px;
                    font-weight: 600;
                  ">${(v.severity || v.level || 'unknown').toUpperCase()}</span>
                </div>
                <p style="margin: 0.5rem 0 0; color: #cbd5e1; font-size: 0.9rem; line-height: 1.5;">
                  ${v.description || v.title || 'No description available'}
                </p>
                ${v.fixed_in ? `
                  <p style="margin: 0.5rem 0 0; color: var(--success); font-size: 0.85rem;">
                    ✓ Fixed in: ${v.fixed_in}
                  </p>
                ` : '<p style="margin: 0.5rem 0 0; color: #f59e0b; font-size: 0.85rem;">⚠ No fix available</p>'}
              </div>
            </div>
          </div>
        `;
      }).join('')
    : '<div style="padding: 2rem; text-align: center; color: var(--success); font-size: 1.1rem;">✓ No known vulnerabilities found</div>';

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 700px;">
      <div class="modal-header">
        <h3>🔍 ${imageName} - Security Scan Results</h3>
        <button class="btn-close" onclick="this.closest('.modal').remove()">×</button>
      </div>
      <div class="modal-body">
        <div style="
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
          margin-bottom: 1.5rem;
        ">
          <div style="
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
          ">
            <div style="font-size: 1.5rem; font-weight: 600; color: ${getSecurityStatusColor(results.status || 'unknown')};">
              ${results.status || 'UNKNOWN'}
            </div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">
              Overall Status
            </div>
          </div>
          <div style="
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
          ">
            <div style="font-size: 1.5rem; font-weight: 600; color: ${results.vulnerability_count > 0 ? '#ef4444' : '#10b981'};">
              ${results.vulnerability_count || 0}
            </div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">
              Vulnerabilities
            </div>
          </div>
          <div style="
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
          ">
            <div style="font-size: 0.85rem; font-weight: 600; color: #94a3b8;">
              ${results.last_checked ? new Date(results.last_checked).toLocaleString() : 'Never'}
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">
              Last Checked
            </div>
          </div>
        </div>
        <div style="
          padding: 1rem;
          background: rgba(0, 0, 0, 0.3);
          border-radius: 8px;
          border-left: 3px solid #3b82f6;
          margin-bottom: 1.5rem;
        ">
          <p style="margin: 0; font-size: 0.9rem; color: #cbd5e1;">
            💡 <strong>Tip:</strong> Update to the latest stable version to patch known vulnerabilities.
          </p>
        </div>
        <h4 style="margin: 0 0 1rem; color: var(--text-1); font-size: 0.95rem;">Detected Issues:</h4>
        <div style="max-height: 400px; overflow-y: auto;">
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
async function checkDockerUpdates(evt) {
  try {
    let button = null;
    if (evt && evt.target) {
      button = evt.target.closest('button');
      if (button) {
        button.disabled = true;
        button.textContent = 'Checking...';
      }
    }

    const response = await fetch('/api/admin/docker/check-updates', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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
    if (evt && evt.target) {
      const button = evt.target.closest('button');
      if (button) {
        button.disabled = false;
        button.textContent = 'Check for Updates';
      }
    }
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
/**
 * Show warning modal before provisioning
 */
function showProvisioningWarningModal(changedVars) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  
  const varsList = Object.entries(changedVars).map(([key, value]) => 
    `<li style="margin: 0.5rem 0; font-family: monospace; font-size: 0.85rem;"><strong>${key}</strong> = ${value.includes('PASSWORD') || value.includes('SECRET') ? '••••••••' : value}</li>`
  ).join('');
  
  modal.innerHTML = `
    <div class="modal-content" style="max-width: 600px;">
      <div class="modal-header">
        <h3>⚠️ Provision Docker Images - Confirm Changes</h3>
        <button class="btn-close" onclick="this.closest('.modal').remove()">×</button>
      </div>
      <div class="modal-body">
        <div style="
          padding: 1rem;
          background: rgba(239, 68, 68, 0.1);
          border-left: 3px solid #ef4444;
          border-radius: 6px;
          margin-bottom: 1.5rem;
        ">
          <p style="margin: 0; font-weight: 600; color: #ef4444; font-size: 0.95rem;">
            🚨 CRITICAL: Point of No Return
          </p>
          <p style="margin: 0.5rem 0 0; color: #cbd5e1; font-size: 0.9rem; line-height: 1.5;">
            This operation will:
          </p>
          <ul style="margin: 0.5rem 0 0; padding-left: 1.5rem; color: #cbd5e1; font-size: 0.9rem;">
            <li>Stop the current Docker container</li>
            <li>Update environment variables</li>
            <li>Start a new container with new configuration</li>
            <li><strong style="color: #ef4444;">Any uncommitted data will be LOST</strong></li>
          </ul>
        </div>
        
        <h4 style="margin: 1rem 0 0.75rem; color: var(--text-1); font-size: 0.95rem;">Variables to Update:</h4>
        <ul style="
          list-style: none;
          margin: 0;
          padding: 0.75rem;
          background: rgba(0, 0, 0, 0.2);
          border-radius: 6px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          max-height: 200px;
          overflow-y: auto;
        ">
          ${varsList}
        </ul>
        
        <div style="
          padding: 1rem;
          background: rgba(59, 130, 246, 0.1);
          border-left: 3px solid #3b82f6;
          border-radius: 6px;
          margin-top: 1.5rem;
        ">
          <p style="margin: 0; font-size: 0.9rem; color: #cbd5e1;">
            💾 <strong>Data Persistence:</strong> Check your .env file and docker-compose.yml for volume configurations. 
            Only data in mounted volumes will be preserved.
          </p>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
        <button class="btn btn-danger" onclick="provisionDockerImages(${JSON.stringify(changedVars).replace(/"/g, '&quot;')}); this.closest('.modal').remove();" style="background: #ef4444; border-color: #ef4444;">
          Confirm & Provision
        </button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

/**
 * Provision Docker images with new environment variables
 */
async function provisionDockerImages(updatedVars) {
  try {
    showNotification('Provisioning Docker images... This may take a few moments', 'success');
    
    const response = await fetch('/api/admin/docker/provision', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ env_vars: updatedVars })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('Provisioning result:', result);
    
    showNotification('✓ Docker images provisioned successfully!', 'success');
    
    // Reload environment variables to show updated state
    setTimeout(() => loadEnvVars(), 2000);
  } catch (error) {
    console.error('Error provisioning Docker images:', error);
    showNotification('Provisioning failed: ' + error.message, 'error');
  }
}

/**
 * Load and display editable environment variables
 */
async function loadEnvVars() {
  try {
    const container = document.getElementById('docker-env-vars');
    if (!container) {
      console.warn('Environment variables container not found');
      return;
    }

    const response = await fetch('/api/admin/docker/env-vars');
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to load environment variables`);
    }
    
    const envVars = await response.json();
    console.log('Environment variables loaded:', envVars);
    
    if (!envVars || Object.keys(envVars).length === 0) {
      container.innerHTML = '<p style="color: var(--text-3); padding: 1rem;">No environment variables found</p>';
      return;
    }
    
    // Store original values for tracking changes
    window.envVarsOriginal = JSON.parse(JSON.stringify(envVars));
    
    const html = `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        ${Object.entries(envVars).map(([key, value], idx) => {
          const isSecret = key.includes('PASSWORD') || key.includes('SECRET') || key.includes('TOKEN') || key.includes('KEY');
          const displayValue = isSecret ? '••••••••' : value;
          return `
            <div style="
              padding: 1rem;
              background: var(--input-bg);
              border-radius: 8px;
              border: 1px solid var(--border);
              transition: all 0.2s;
            " id="env-var-${idx}" data-key="${key}">
              <div style="display: grid; grid-template-columns: 200px 1fr auto; gap: 1rem; align-items: flex-start;">
                <div>
                  <label style="font-size: 0.75rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 0.25rem;">Variable Name</label>
                  <code style="font-size: 0.9rem; color: var(--accent-text);">${key}</code>
                </div>
                <div>
                  <label style="font-size: 0.75rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 0.25rem;">
                    Value ${isSecret ? '(Masked)' : ''}
                  </label>
                  <input 
                    type="${isSecret ? 'password' : 'text'}"
                    class="input env-input"
                    data-key="${key}"
                    value="${value}"
                    style="width: 100%; padding: 0.5rem; border-radius: 4px; border: 1px solid var(--border); background: rgba(0,0,0,0.2); color: var(--text-1);"
                    onchange="trackEnvVarChange('${key}', this.value)"
                  />
                </div>
                <div style="display: flex; gap: 0.5rem; flex-direction: column;">
                  <button 
                    class="btn btn-sm" 
                    title="Show/Hide value"
                    onclick="toggleEnvVarVisibility('${idx}', '${key}')"
                    style="padding: 0.4rem 0.8rem;"
                  >
                    ${isSecret ? '👁️ Show' : '👁️ Hide'}
                  </button>
                  <button 
                    class="btn btn-sm" 
                    onclick="copyToClipboard('${key}=' + document.querySelector('[data-key=&quot;${key}&quot;]').value)"
                    style="padding: 0.4rem 0.8rem;"
                  >
                    Copy
                  </button>
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
      
      <div style="margin-top: 1.5rem; padding: 1rem; background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; border-radius: 6px;">
        <p style="margin: 0; font-size: 0.9rem; color: #cbd5e1;">
          💾 <strong>Before provisioning:</strong> Backup your data and ensure you have volume mounts configured in docker-compose.yml if you want to persist data.
        </p>
      </div>
      
      <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
        <button 
          class="btn btn-primary"
          id="provision-btn"
          onclick="handleProvisionClick()"
          style="flex: 1; padding: 0.75rem; font-weight: 600; disabled: true; opacity: 0.5; cursor: not-allowed;"
          disabled
        >
          💾 Save & Provision
        </button>
        <button 
          class="btn btn-secondary"
          onclick="resetEnvVars()"
          style="padding: 0.75rem 1.5rem;"
        >
          ↺ Reset
        </button>
      </div>
    `;
    
    container.innerHTML = html;
  } catch (error) {
    console.error('Error loading env vars:', error);
    const container = document.getElementById('docker-env-vars');
    if (container) {
      container.innerHTML = `<div style="padding: 1.5rem; background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; color: #ef4444;">
        <strong>Failed to load environment variables:</strong> ${error.message}
        <p style="margin: 0.5rem 0 0; font-size: 0.85rem; color: #cbd5e1;">Check console for details</p>
      </div>`;
    }
  }
}

/**
 * Track environment variable changes
 */
function trackEnvVarChange(key, newValue) {
  if (!window.envVarsModified) {
    window.envVarsModified = {};
  }
  
  const originalValue = window.envVarsOriginal?.[key] || '';
  if (newValue === originalValue) {
    delete window.envVarsModified[key];
  } else {
    window.envVarsModified[key] = newValue;
  }
  
  // Enable/disable provision button based on changes
  const provisionBtn = document.getElementById('provision-btn');
  const hasChanges = Object.keys(window.envVarsModified || {}).length > 0;
  
  if (provisionBtn) {
    provisionBtn.disabled = !hasChanges;
    provisionBtn.style.opacity = hasChanges ? '1' : '0.5';
    provisionBtn.style.cursor = hasChanges ? 'pointer' : 'not-allowed';
  }
}

/**
 * Toggle environment variable visibility (show/hide)
 */
function toggleEnvVarVisibility(idx, key) {
  const input = document.querySelector(`[data-key="${key}"]`);
  const btn = event.target.closest('button');
  
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '👁️ Hide';
  } else {
    input.type = 'password';
    btn.textContent = '👁️ Show';
  }
}

/**
 * Handle provision button click - show warning modal
 */
function handleProvisionClick() {
  if (!window.envVarsModified || Object.keys(window.envVarsModified).length === 0) {
    showNotification('No changes to provision', 'error');
    return;
  }
  
  showProvisioningWarningModal(window.envVarsModified);
}

/**
 * Reset environment variables to original values
 */
function resetEnvVars() {
  if (confirm('Reset all environment variables to their original values?')) {
    window.envVarsModified = {};
    loadEnvVars();
    showNotification('Environment variables reset', 'success');
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
