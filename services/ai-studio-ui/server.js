/**
 * AI Studio UI Server — Simple Express proxy for frontend
 * Serves HTML and proxies API calls to ai-studio-server
 */

const express = require('express');
const path = require('path');
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

const app = express();
const PORT = process.env.PORT || 4000;
const STUDIO_API = process.env.STUDIO_API || 'http://ai-studio-server:8020';

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname)));

// Proxy API calls
app.all('/api/*', async (req, res) => {
    const endpoint = req.originalUrl.replace('/api', '');
    const url = `${STUDIO_API}${endpoint}`;

    try {
        const options = {
            method: req.method,
            headers: {
                ...req.headers,
                'host': new URL(STUDIO_API).host,
            },
        };

        if (req.method !== 'GET' && req.method !== 'HEAD') {
            options.body = JSON.stringify(req.body);
        }

        const response = await fetch(url, options);
        
        // Forward headers
        response.headers.forEach((value, name) => {
            if (name !== 'content-encoding') {
                res.setHeader(name, value);
            }
        });

        // Stream response for SSE
        if (response.headers.get('content-type')?.includes('event-stream')) {
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');
            response.body.pipe(res);
        } else {
            res.status(response.status);
            res.send(await response.text());
        }
    } catch (error) {
        console.error(`Proxy error: ${error.message}`);
        res.status(502).json({ error: 'Backend service unavailable', details: error.message });
    }
});

// Serve index.html for all other routes (SPA)
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'ai-studio-ui', timestamp: new Date().toISOString() });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`\n🎨 AI Studio UI listening on http://0.0.0.0:${PORT}`);
    console.log(`📡 API Backend: ${STUDIO_API}\n`);
});
