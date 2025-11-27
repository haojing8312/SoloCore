/**
 * Application entry point
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import { logWebVitals } from './utils/reportWebVitals';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Report Web Vitals in development
if (import.meta.env.DEV) {
  logWebVitals();
}
