/**
 * Documentation API Routes
 * Serves markdown documentation dynamically
 */

const express = require('express');
const DocLoader = require('../lib/doc-loader');

module.exports = function createDocsRouter(app, docsPath) {
  const router = express.Router();
  const docLoader = new DocLoader(docsPath);

  /**
   * GET /api/docs/:docname
   * Get documentation content (raw markdown by default, html if ?format=html)
   */
  router.get('/api/docs/:docname', (req, res) => {
    try {
      const { docname } = req.params;
      const { format = 'raw', toc = 'false' } = req.query;

      const doc = docLoader.load(docname, {
        forceRefresh: req.query.refresh === 'true'
      });

      const result = {
        name: doc.name,
        timestamp: doc.timestamp,
        content: format === 'html' ? doc.parsed : doc.raw,
        format: format,
        path: doc.path
      };

      // Add table of contents if requested
      if (toc === 'true') {
        result.toc = docLoader.getTableOfContents(docname);
      }

      res.json(result);
    } catch (e) {
      res.status(404).json({
        error: e.message,
        status: 'not_found'
      });
    }
  });

  /**
   * GET /api/docs
   * List all available documentation files
   */
  router.get('/api/docs', (req, res) => {
    try {
      const docs = docLoader.listDocs();
      res.json({
        count: docs.length,
        docs,
        timestamp: new Date()
      });
    } catch (e) {
      res.status(500).json({
        error: e.message,
        status: 'error'
      });
    }
  });

  /**
   * GET /api/docs/:docname/toc
   * Get table of contents for a document
   */
  router.get('/api/docs/:docname/toc', (req, res) => {
    try {
      const { docname } = req.params;
      const toc = docLoader.getTableOfContents(docname);
      res.json({
        docname,
        toc,
        count: toc.length
      });
    } catch (e) {
      res.status(404).json({
        error: e.message,
        status: 'not_found'
      });
    }
  });

  /**
   * POST /api/docs/:docname/refresh
   * Force refresh cache for a document
   */
  router.post('/api/docs/:docname/refresh', (req, res) => {
    try {
      const { docname } = req.params;
      const doc = docLoader.load(docname, { forceRefresh: true });
      res.json({
        status: 'refreshed',
        docname,
        timestamp: doc.timestamp
      });
    } catch (e) {
      res.status(404).json({
        error: e.message,
        status: 'not_found'
      });
    }
  });

  /**
   * POST /api/docs/refresh-all
   * Refresh all documentation cache
   */
  router.post('/api/docs/refresh-all', (req, res) => {
    try {
      docLoader.clearCache();
      const docs = docLoader.listDocs();
      res.json({
        status: 'refreshed',
        count: docs.length,
        docs,
        timestamp: new Date()
      });
    } catch (e) {
      res.status(500).json({
        error: e.message,
        status: 'error'
      });
    }
  });

  // Attach loader to app for use in other routes
  app.locals.docLoader = docLoader;

  return router;
};
