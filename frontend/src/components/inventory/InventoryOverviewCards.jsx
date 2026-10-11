import React from 'react';
import { useI18n } from '../../context/I18nContext';
import { Package, TrendingUp, AlertTriangle, AlertCircle } from 'lucide-react';

export function InventoryOverviewCards({ overview, currencySymbol = '₹', activeFilter, onSelectFilter }) {
  const { t } = useI18n();

  if (!overview) return null;

  const cards = [
    {
      id: 'all',
      title: t('total_products'),
      value: overview.total_products || 0,
      subtext: `${overview.active_products || 0} ${t('active_status').toLowerCase()}`,
      icon: Package,
      color: 'var(--color-primary)',
      bg: 'var(--color-primary-soft)',
    },
    {
      id: 'valuation',
      title: t('total_stock_value'),
      value: `${currencySymbol}${Number(overview.total_stock_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      subtext: t('overview'),
      icon: TrendingUp,
      color: 'var(--color-accent)',
      bg: 'var(--color-accent-soft)',
    },
    {
      id: 'low_stock',
      title: t('low_stock_count'),
      value: overview.low_stock_products || 0,
      subtext: t('filter_low_stock'),
      icon: AlertTriangle,
      color: '#d97706',
      bg: '#fef3c7',
      isFilter: true,
      filterKey: 'low_stock'
    },
    {
      id: 'out_of_stock',
      title: t('out_of_stock_count'),
      value: overview.out_of_stock_products || 0,
      subtext: t('filter_out_of_stock'),
      icon: AlertCircle,
      color: 'var(--color-danger)',
      bg: 'var(--color-danger-soft)',
      isFilter: true,
      filterKey: 'out_of_stock'
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: '1rem',
      marginBottom: '1.5rem'
    }}>
      {cards.map((c) => {
        const Icon = c.icon;
        const isSelected = c.filterKey && activeFilter === c.filterKey;
        return (
          <div
            key={c.id}
            onClick={() => c.isFilter && onSelectFilter && onSelectFilter(c.filterKey === activeFilter ? 'all' : c.filterKey)}
            style={{
              padding: '1.25rem',
              borderRadius: 'var(--radius-lg)',
              backgroundColor: 'var(--color-bg-surface)',
              border: `1px solid ${isSelected ? c.color : 'var(--color-border)'}`,
              boxShadow: isSelected ? '0 0 0 2px var(--color-primary-soft)' : 'var(--shadow-sm)',
              cursor: c.isFilter ? 'pointer' : 'default',
              transition: 'all 0.15s ease'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {c.title}
              </span>
              <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-md)', backgroundColor: c.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', color: c.color }}>
                <Icon size={18} />
              </div>
            </div>
            <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--color-text-main)', marginBottom: '0.25rem' }}>
              {c.value}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              {c.subtext}
            </div>
          </div>
        );
      })}
    </div>
  );
}
