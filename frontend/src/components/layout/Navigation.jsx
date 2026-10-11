import React from 'react';
import { useI18n } from '../../context/I18nContext';
import { LayoutDashboard, Settings, ShieldCheck, Compass } from 'lucide-react';

export function Sidebar({ currentTab, onSelectTab }) {
  const { t } = useI18n();

  const navItems = [
    { id: 'dashboard', label: t('dashboard'), icon: LayoutDashboard },
    { id: 'onboarding', label: t('onboarding_title'), icon: Compass },
    { id: 'foundation', label: 'Stage 1 Core', icon: ShieldCheck },
    { id: 'settings', label: t('settings'), icon: Settings }
  ];

  return (
    <aside className="app-sidebar" aria-label="Desktop Navigation">
      <div style={{ padding: '1.25rem 1rem', borderBottom: '1px solid var(--color-border)' }}>
        <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Navigation
        </div>
      </div>
      <nav style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.625rem 0.875rem',
                borderRadius: 'var(--radius-md)',
                backgroundColor: isActive ? 'var(--color-primary-soft)' : 'transparent',
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-main)',
                fontWeight: isActive ? 600 : 500,
                fontSize: 'var(--font-size-sm)',
                border: 'none',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
                transition: 'background-color 0.15s ease'
              }}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

export function BottomNav({ currentTab, onSelectTab }) {
  const { t } = useI18n();

  const navItems = [
    { id: 'dashboard', label: t('dashboard'), icon: LayoutDashboard },
    { id: 'onboarding', label: 'Setup', icon: Compass },
    { id: 'settings', label: t('settings'), icon: Settings }
  ];

  return (
    <nav className="app-bottom-nav" aria-label="Mobile Navigation">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = currentTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onSelectTab(item.id)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.125rem',
              backgroundColor: 'transparent',
              border: 'none',
              color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
              fontSize: 'var(--font-size-xs)',
              fontWeight: isActive ? 700 : 500,
              minWidth: '60px',
              height: '100%',
              cursor: 'pointer'
            }}
          >
            <Icon size={20} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
