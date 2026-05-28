export const API_BASE_URL = (() => {
  if (typeof window !== 'undefined') {
    const { hostname } = window.location;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
    if (isLocalhost) {
      return (process.env.REACT_APP_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '');
    }
    return '';
  }
  return process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '';
})();
