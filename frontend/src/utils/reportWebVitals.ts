/**
 * Web Vitals performance monitoring
 * Reports Core Web Vitals metrics to the console (can be extended to send to analytics)
 */

import { onCLS, onFCP, onINP, onLCP, onTTFB, type Metric } from 'web-vitals';

type ReportHandler = (metric: Metric) => void;

/**
 * Report Web Vitals metrics
 * @param onPerfEntry - Callback function to handle metrics
 */
export function reportWebVitals(onPerfEntry?: ReportHandler): void {
  if (onPerfEntry && typeof onPerfEntry === 'function') {
    // Core Web Vitals
    onCLS(onPerfEntry); // Cumulative Layout Shift
    onFCP(onPerfEntry); // First Contentful Paint
    onINP(onPerfEntry); // Interaction to Next Paint
    onLCP(onPerfEntry); // Largest Contentful Paint
    onTTFB(onPerfEntry); // Time to First Byte
  }
}

/**
 * Default handler that logs metrics to console
 */
export function logWebVitals(): void {
  reportWebVitals((metric) => {
    const { name, value, rating, delta } = metric;

    console.group(`⚡ ${name}`);
    console.log('Value:', value.toFixed(2), 'ms');
    console.log('Rating:', rating);
    console.log('Delta:', delta.toFixed(2), 'ms');
    console.groupEnd();

    // You can send to analytics here
    // Example: gtag('event', name, { value: Math.round(value), metric_id: id });
  });
}

/**
 * Get performance rating thresholds
 */
export function getPerformanceRating(name: string, value: number): 'good' | 'needs-improvement' | 'poor' {
  const thresholds: Record<string, { good: number; poor: number }> = {
    CLS: { good: 0.1, poor: 0.25 },
    FCP: { good: 1800, poor: 3000 },
    FID: { good: 100, poor: 300 },
    INP: { good: 200, poor: 500 },
    LCP: { good: 2500, poor: 4000 },
    TTFB: { good: 800, poor: 1800 },
  };

  const threshold = thresholds[name];
  if (!threshold) return 'needs-improvement';

  if (value <= threshold.good) return 'good';
  if (value <= threshold.poor) return 'needs-improvement';
  return 'poor';
}
