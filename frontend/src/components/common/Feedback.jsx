import React from 'react';
import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';

export function Alert({ type = 'info', title, message, children }) {
  const styles = {
    danger: {
      bg: 'var(--color-danger-soft)',
      border: 'var(--color-danger)',
      text: '#991b1b',
      icon: AlertCircle
    },
    warning: {
      bg: '#fffbeb',
      border: 'var(--color-warning)',
      text: '#92400e',
      icon: AlertTriangle
    },
    success: {
      bg: 'var(--color-accent-soft)',
      border: 'var(--color-accent)',
      text: '#065f46',
      icon: CheckCircle
    },
    info: {
      bg: 'var(--color-primary-soft)',
      border: 'var(--color-primary-light)',
      text: '#1e40af',
      icon: Info
    }
  }[type] || styles.info;

  const IconComponent = styles.icon;

  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        gap: '0.75rem',
        padding: '0.875rem 1rem',
        borderRadius: 'var(--radius-md)',
        backgroundColor: styles.bg,
        border: `1px solid ${styles.border}`,
        color: styles.text,
        marginBottom: '1rem',
        alignItems: 'flex-start'
      }}
    >
      <IconComponent size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
      <div style={{ flex: 1, fontSize: 'var(--font-size-sm)' }}>
        {title && <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{title}</div>}
        {message && <div>{message}</div>}
        {children}
      </div>
    </div>
  );
}

export function Badge({ variant = 'neutral', children }) {
  const styles = {
    primary: { bg: 'var(--color-primary-soft)', color: 'var(--color-primary)', border: 'var(--color-primary-light)' },
    success: { bg: 'var(--color-accent-soft)', color: 'var(--color-accent)', border: 'var(--color-accent)' },
    warning: { bg: '#fffbeb', color: '#b45309', border: '#f59e0b' },
    neutral: { bg: 'var(--color-bg-subtle)', color: 'var(--color-text-muted)', border: 'var(--color-border)' }
  }[variant] || styles.neutral;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '0.2rem 0.6rem',
        borderRadius: 'var(--radius-full)',
        fontSize: 'var(--font-size-xs)',
        fontWeight: 600,
        backgroundColor: styles.bg,
        color: styles.color,
        border: `1px solid ${styles.border}`
      }}
    >
      {children}
    </span>
  );
}

export function LoadingSpinner({ label = 'Loading...' }) {
  return (
    <div
      role="status"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem',
        gap: '1rem'
      }}
    >
      <div
        style={{
          width: '2.5rem',
          height: '2.5rem',
          borderRadius: '50%',
          border: '3px solid var(--color-border)',
          borderTopColor: 'var(--color-primary)',
          animation: 'spin 0.8s linear infinite'
        }}
      />
      <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
        {label}
      </span>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
