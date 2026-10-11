import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useI18n } from '../../context/I18nContext';
import { api } from '../../services/api';
import { LogOut, Globe, Circle, Store } from 'lucide-react';

export function Header() {
  const { user, business, logout } = useAuth();
  const { lang, setLanguage, t } = useI18n();
  const [isBackendOnline, setIsBackendOnline] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function checkStatus() {
      try {
        const res = await api.getHealth();
        if (isMounted) {
          setIsBackendOnline(res?.success === true);
        }
      } catch {
        if (isMounted) setIsBackendOnline(false);
      }
    }
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header
      style={{
        height: '64px',
        backgroundColor: 'var(--color-bg-surface)',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.5rem',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        boxShadow: 'var(--shadow-sm)'
      }}
    >
      {/* Brand Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--color-primary)',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '1.25rem',
            letterSpacing: '-0.5px'
          }}
        >
          க
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: '1.2rem', color: 'var(--color-primary-dark)', lineHeight: 1.1 }}>
            Kanakku <span style={{ color: 'var(--color-primary-light)', fontSize: '0.95rem', fontWeight: 600 }}>கணக்கு</span>
          </div>
          {business?.name && (
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <Store size={12} />
              <span>{business.name}</span>
            </div>
          )}
        </div>
      </div>

      {/* Right Controls: Backend Status, Language Switcher, User & Logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Connection Status Indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.375rem',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 600,
            padding: '0.25rem 0.6rem',
            borderRadius: 'var(--radius-full)',
            backgroundColor: isBackendOnline ? 'var(--color-accent-soft)' : 'var(--color-danger-soft)',
            color: isBackendOnline ? 'var(--color-accent)' : 'var(--color-danger)'
          }}
          title={isBackendOnline ? 'Backend API connected' : 'Backend offline or connecting'}
        >
          <Circle size={8} fill="currentColor" />
          <span className="hidden-mobile">{isBackendOnline ? t('online') : t('offline')}</span>
        </div>

        {/* Language Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <Globe size={16} color="var(--color-text-muted)" />
          <select
            value={lang}
            onChange={(e) => setLanguage(e.target.value)}
            aria-label={t('language')}
            style={{
              padding: '0.35rem 0.5rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-bg-subtle)',
              color: 'var(--color-text-main)',
              fontSize: 'var(--font-size-xs)',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <option value="ta">தமிழ் (Tamil)</option>
            <option value="tanglish">Tanglish</option>
            <option value="en">English</option>
          </select>
        </div>

        {/* User Info & Logout */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div className="hidden-mobile" style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>{user.full_name}</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>{user.phone}</div>
            </div>
            <button
              onClick={logout}
              className="btn btn-outline"
              style={{ padding: '0.4rem', minHeight: '36px', borderRadius: 'var(--radius-md)' }}
              title={t('logout')}
              aria-label={t('logout')}
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>

      <style>{`
        @media (max-width: 640px) {
          .hidden-mobile { display: none !important; }
        }
      `}</style>
    </header>
  );
}
