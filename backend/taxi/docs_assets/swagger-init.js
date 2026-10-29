'use strict';
window.ui = SwaggerUIBundle({
  url: '/openapi.json', dom_id: '#swagger-ui', layout: 'BaseLayout',
  presets: [SwaggerUIBundle.presets.apis], deepLinking: true, filter: true,
  docExpansion: 'list', displayRequestDuration: true, validatorUrl: null,
  persistAuthorization: false, withCredentials: true,
  requestInterceptor: async request => {
    const target = new URL(request.url, window.location.origin);
    if (target.origin !== window.location.origin) throw new Error('Use the same-origin Campus Taxi API.');
    request.credentials = 'same-origin';
    const mutation = !['GET','HEAD','OPTIONS'].includes((request.method || 'GET').toUpperCase());
    const bearer = Object.keys(request.headers || {}).some(key => key.toLowerCase() === 'authorization' && request.headers[key]);
    if (mutation && target.pathname !== '/api/auth/login' && !bearer) {
      const response = await fetch('/api/auth/me', {credentials:'same-origin',cache:'no-store'});
      if (response.ok) {
        const session = await response.json();
        if (session.csrf_token) {
          request.headers ||= {};
          request.headers['X-Taxi-CSRF'] = session.csrf_token;
        }
      }
    }
    return request;
  }
});
