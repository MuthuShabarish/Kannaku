import React from 'react';
import { useI18n } from '../../context/I18nContext';
import { LayoutDashboard, Settings, Compass, Package, ShoppingCart, Users, Truck, Building2, Receipt, BookOpen, BarChart3, LockKeyhole } from 'lucide-react';

export function Sidebar({ currentTab, onSelectTab }) {
  const { t } = useI18n();

  const navItems = [
    { id: 'dashboard', label: t('dashboard'), icon: LayoutDashboard },
    { id: 'pos', label: t('pos_billing'), icon: ShoppingCart },
    { id: 'reports', label: t('reports_and_profit_title'), icon: BarChart3 },
    { id: 'cash_closing', label: t('cash_closing_title'), icon: LockKeyhole },
    { id: 'cashbook', label: t('cashbook_title'), icon: BookOpen },
    { id: 'expenses', label: t('expenses_title'), icon: Receipt },
    { id: 'purchases', label: t('purchases_title'), icon: Truck },
    { id: 'suppliers', label: t('suppliers_title'), icon: Building2 },
    { id: 'customers', label: t('customers_title'), icon: Users },
    { id: 'inventory', label: t('products_and_inventory'), icon: Package },
    { id: 'onboarding', label: t('onboarding_title'), icon: Compass },
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
    { id: 'pos', label: 'POS', icon: ShoppingCart },
    { id: 'purchases', label: 'Purchase', icon: Truck },
    { id: 'suppliers', label: 'Suppliers', icon: Building2 },
    { id: 'inventory', label: t('inventory'), icon: Package }
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
