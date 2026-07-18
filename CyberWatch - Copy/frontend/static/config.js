/**
 * config.js — CyberWatch frontend configuration.
 * Auto-switches between localhost dev and production URLs.
 */
const CONFIG = {
  WS_URL: (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  )
    ? `ws://${window.location.hostname}:8000/events/live`
    : 'wss://<your-render-project>.onrender.com/events/live',

  API_URL: (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  )
    ? `http://${window.location.hostname}:8000`
    : 'https://<your-render-project>.onrender.com',
};
