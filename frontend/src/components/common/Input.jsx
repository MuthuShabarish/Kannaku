import React from 'react';

export function Input({
  label,
  id,
  error,
  helperText,
  required = false,
  className = '',
  ...props
}) {
  const inputId = id || props.name;
  const errorId = error ? `${inputId}-error` : undefined;
  const helperId = helperText ? `${inputId}-helper` : undefined;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }}>
      {label && (
        <label
          htmlFor={inputId}
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 600,
            color: 'var(--color-text-main)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}
        >
          {label}
          {required && <span style={{ color: 'var(--color-danger)' }}>*</span>}
        </label>
      )}

      <input
        id={inputId}
        required={required}
        aria-invalid={!!error}
        aria-describedby={[errorId, helperId].filter(Boolean).join(' ') || undefined}
        className={`input-field ${error ? 'input-error' : ''} ${className}`}
        {...props}
      />

      {helperText && !error && (
        <span
          id={helperId}
          style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}
        >
          {helperText}
        </span>
      )}

      {error && (
        <span
          id={errorId}
          role="alert"
          style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-danger)', fontWeight: 500 }}
        >
          {error}
        </span>
      )}
    </div>
  );
}
