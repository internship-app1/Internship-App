const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Proxy for SSE streaming endpoints - must NOT buffer
  app.use(
    '/api/match-stream',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      // Critical for SSE: disable response buffering
      onProxyRes: function (proxyRes, req, res) {
        // Remove any buffering headers
        proxyRes.headers['cache-control'] = 'no-cache';
        proxyRes.headers['connection'] = 'keep-alive';
      },
      // Don't buffer the response
      selfHandleResponse: false,
    })
  );

  // Proxy for all other API calls
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  );
};

