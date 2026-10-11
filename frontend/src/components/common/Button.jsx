import React from 'react';

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  type = 'button',
  icon: Icon,
  className = '',
  onClick,
  ...props
}) {
  const variantClass = {
    primary: 'btn-primary',
    accent: 'btn-accent',
    outline: 'btn-outline',
    danger: 'btn-danger'
  }[variant] || 'btn-primary';

  const sizeStyle = {
    sm: { minHeight: '36px', padding: '0.25rem 0.75rem', fontSize: 'var(--font-size-sm)' },
    md: { minHeight: 'var(--touch-target-min)', padding: '0.5rem 1rem', fontSize: 'var(--font-size-base)' },
    lg: { minHeight: 'var(--touch-target-large)', padding: '0.75rem 1.5rem', fontSize: 'var(--font-size-lg)' }
  }[size];

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`btn ${variantClass} ${className}`}
      style={sizeStyle}
      aria-busy={isLoading}
      {...props}
    >
      {isLoading ? (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          <svg
            style={{ width: '1.25rem', height: '1.25rem', animation: 'spin 1s linear infinite' }}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              style={{ opacity: 0.25 }}
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              style={{ opacity: 0.75 }}
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8z"
            />
          </svg>
          <span>{children}</span>
        </span>
      ) : (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          {Icon && <Icon size={size === 'lg' ? 22 : 18} />}
          <span>{children}</span>
        </span>
      )}
    </button>
  );
}
