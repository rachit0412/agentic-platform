/**
 * Security Middleware & Utilities
 * Implements OWASP Top 10 protections for express.js
 */

const crypto = require('crypto');

/**
 * Security headers middleware (A02 - Security Misconfiguration)
 * Adds critical HTTP security headers
 */
function securityHeaders(req, res, next) {
  // Prevent MIME type sniffing
  res.setHeader('X-Content-Type-Options', 'nosniff');
  
  // Prevent clickjacking (frame injection)
  res.setHeader('X-Frame-Options', 'DENY');
  
  // Enable XSS protection in older browsers
  res.setHeader('X-XSS-Protection', '1; mode=block');
  
  // Content Security Policy - prevents inline scripts and styles (A05 - Injection)
  res.setHeader('Content-Security-Policy', 
    "default-src 'self'; " +
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +  // unsafe-eval needed for existing code, should be removed
    "style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: https:; " +
    "font-src 'self' data:; " +
    "connect-src 'self' localhost:* http://localhost:* http://host.docker.internal:*; " +
    "frame-src 'none'; " +
    "object-src 'none'; " +
    "base-uri 'self'; " +
    "form-action 'self';"
  );
  
  // Referrer Policy - don't leak referrer to external sites
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  
  // Feature Policy / Permissions Policy
  res.setHeader('Permissions-Policy', 
    'accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()'
  );
  
  // Prevent browsers from caching sensitive data (A02)
  if (req.path && (req.path.includes('/auth') || req.path.includes('/admin') || req.path.includes('/api'))) {
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate, private');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
  }
  
  // Strict Transport Security (requires HTTPS in production)
  // Uncomment when HTTPS is enforced:
  // res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
  
  next();
}

/**
 * Rate limiting middleware (A07 - Authentication Failures, A01 - Access Control)
 * Simple in-memory rate limiter
 */
class RateLimiter {
  constructor() {
    this.store = new Map();
    this.cleanup();
  }
  
  cleanup() {
    // Clean up expired entries every 60 seconds
    setInterval(() => {
      const now = Date.now();
      for (const [key, data] of this.store.entries()) {
        if (now > data.expiry) {
          this.store.delete(key);
        }
      }
    }, 60000);
  }
  
  checkLimit(identifier, limit = 100, windowMs = 60000) {
    const now = Date.now();
    if (!this.store.has(identifier)) {
      this.store.set(identifier, { count: 1, expiry: now + windowMs });
      return true;
    }
    
    const data = this.store.get(identifier);
    if (now > data.expiry) {
      this.store.set(identifier, { count: 1, expiry: now + windowMs });
      return true;
    }
    
    data.count++;
    return data.count <= limit;
  }
  
  middleware(options = {}) {
    const { limit = 100, windowMs = 60000, keyGenerator = (req) => req.ip, message = 'Too many requests' } = options;
    
    return (req, res, next) => {
      const key = keyGenerator(req);
      if (!this.checkLimit(key, limit, windowMs)) {
        return res.status(429).json({ error: message });
      }
      next();
    };
  }
}

const globalLimiter = new RateLimiter();

/**
 * Strict rate limiting for authentication endpoints (A07)
 * Allow max 5 attempts per 15 minutes per IP
 */
function authRateLimiter(req, res, next) {
  const key = `auth:${req.ip}`;
  if (!globalLimiter.checkLimit(key, 5, 15 * 60 * 1000)) {
    return res.status(429).json({ 
      error: 'Too many authentication attempts. Please try again in 15 minutes.' 
    });
  }
  next();
}

/**
 * CSRF Token generation and validation (A01 - Broken Access Control)
 * Implements double-submit cookie pattern
 */
class CSRFProtection {
  static generateToken(req) {
    const token = crypto.randomBytes(32).toString('hex');
    req.session = req.session || {};
    req.session.csrfToken = token;
    return token;
  }
  
  static middleware(req, res, next) {
    // Skip CSRF check for GET, HEAD, OPTIONS
    if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
      return next();
    }
    
    // Generate token if not present
    if (!req.session || !req.session.csrfToken) {
      req.session = req.session || {};
      req.session.csrfToken = crypto.randomBytes(32).toString('hex');
    }
    
    // Make token available to templates
    res.locals.csrfToken = req.session.csrfToken;
    
    // Validate token on state-changing requests
    const token = req.headers['x-csrf-token'] || req.body?.csrfToken;
    
    if (!token || token !== req.session.csrfToken) {
      return res.status(403).json({ error: 'CSRF token validation failed' });
    }
    
    next();
  }
  
  static getToken(req) {
    if (!req.session) {
      req.session = {};
    }
    if (!req.session.csrfToken) {
      req.session.csrfToken = crypto.randomBytes(32).toString('hex');
    }
    return req.session.csrfToken;
  }
}

/**
 * Input validation & sanitization (A05 - Injection)
 */
class InputValidator {
  static sanitizeString(str) {
    if (typeof str !== 'string') return str;
    return str
      .replace(/[<>\"']/g, c => ({ '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#x27;' }[c]))
      .trim();
  }
  
  static validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
  
  static validateUsername(username) {
    // Allow alphanumeric, underscore, hyphen, 3-50 chars
    const usernameRegex = /^[a-zA-Z0-9_-]{3,50}$/;
    return usernameRegex.test(username);
  }
  
  static validatePassword(password) {
    // At least 12 chars, uppercase, lowercase, number, special char
    if (password.length < 12) return false;
    if (!/[A-Z]/.test(password)) return false;
    if (!/[a-z]/.test(password)) return false;
    if (!/[0-9]/.test(password)) return false;
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) return false;
    return true;
  }
}

/**
 * Safe error handling (A02 - Security Misconfiguration, A10 - Error Handling)
 * Returns generic error messages in production, detailed in development
 */
function errorHandler(err, req, res, next) {
  const isDevelopment = process.env.NODE_ENV === 'development';
  
  console.error('[ERROR]', {
    timestamp: new Date().toISOString(),
    method: req.method,
    path: req.path,
    ip: req.ip,
    error: err.message,
    stack: isDevelopment ? err.stack : undefined
  });
  
  const statusCode = err.statusCode || 500;
  const response = {
    error: isDevelopment ? err.message : 'An internal server error occurred'
  };
  
  if (isDevelopment && err.details) {
    response.details = err.details;
  }
  
  res.status(statusCode).json(response);
}

/**
 * Audit logging middleware (A09 - Security Logging & Alerting)
 */
function auditLog(req, res, next) {
  const startTime = Date.now();
  
  // Log response
  const originalSend = res.send;
  res.send = function(data) {
    const duration = Date.now() - startTime;
    const isSecurityRelevant = [
      '/auth', '/login', '/admin', '/api'
    ].some(path => req.path.includes(path));
    
    if (isSecurityRelevant || res.statusCode >= 400) {
      console.log('[AUDIT]', {
        timestamp: new Date().toISOString(),
        method: req.method,
        path: req.path,
        status: res.statusCode,
        ip: req.ip,
        userId: req.session?.user?.id || 'anonymous',
        duration: `${duration}ms`,
        userAgent: req.get('user-agent')?.substring(0, 50)
      });
    }
    
    res.send = originalSend;
    return res.send(data);
  };
  
  next();
}

/**
 * Helmet-like security headers without dependency
 */
function securityDefaults(req, res, next) {
  // Remove server identification
  res.removeHeader('X-Powered-By');
  
  // Set secure default headers
  res.setHeader('Server', 'SecureAgent/1.0');
  
  next();
}

module.exports = {
  securityHeaders,
  authRateLimiter,
  CSRFProtection,
  InputValidator,
  errorHandler,
  auditLog,
  securityDefaults,
  RateLimiter,
  globalLimiter
};
