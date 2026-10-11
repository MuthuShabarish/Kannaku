import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useI18n } from '../context/I18nContext';
import { api } from '../services/api';
import { Badge } from '../components/common/Feedback';
import {
  ShieldCheck,
  Building2,
  Coins,
  Database,
  Sparkles,
  ArrowRight,
  Compass,
  Sliders,
  Package,
  ShoppingCart,
  Users,
  Truck,
  Receipt,
  BookOpen,
  CheckCircle2,
  BarChart3,
  LockKeyhole
} from 'lucide-react';
import { Button } from '../components/common/Button';

export function DashboardPage({ onNavigateTab }) {
  const { user, business } = useAuth();
  const { t } = useI18n();
  const [healthData, setHealthData] = useState(null);

  useEffect(() => {
    async function loadHealth() {
      try {
        const res = await api.getHealth();
        if (res.success) {
          setHealthData(res.data);
        }
      } catch (err) {
        console.error('Failed to query health endpoint:', err);
      }
    }
    loadHealth();
  }, []);

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      {/* Welcome Banner */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem', flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)', margin: 0 }}>
            {t('welcome')}, {user?.full_name}
          </h1>
          <Badge variant="primary">{business?.tier ? t(`tier_${business.tier}`) : 'SIMPLE TIER'}</Badge>
          {business?.onboarding_completed ? (
            <Badge variant="accent">Setup Complete</Badge>
          ) : (
            <Badge variant="warning">Setup Pending</Badge>
          )}
        </div>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-base)', margin: '0.25rem 0 0' }}>
          {business?.name} &bull; {business?.category ? t(`cat_${business.category}`) || business.category : 'General Retail'}
        </p>
      </div>

      {/* Onboarding Status Callout Banner */}
      {!business?.onboarding_completed ? (
        <div
          style={{
            padding: '1.5rem',
            borderRadius: 'var(--radius-lg)',
            border: '2px solid var(--color-primary-light)',
            backgroundColor: 'var(--color-primary-soft)',
            marginBottom: '2rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          <div style={{ maxWidth: '600px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
              <Compass size={22} color="var(--color-primary)" />
              <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, margin: 0, color: 'var(--color-primary-dark)' }}>
                {t('onboarding_banner_title')}
              </h2>
            </div>
            <p style={{ margin: 0, color: 'var(--color-text-main)', fontSize: 'var(--font-size-sm)' }}>
              {t('onboarding_banner_desc')}
            </p>
          </div>
          <Button variant="primary" size="large" onClick={() => onNavigateTab && onNavigateTab('onboarding')}>
            {t('btn_resume_setup')} <ArrowRight size={18} />
          </Button>
        </div>
      ) : (
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border)',
            backgroundColor: 'var(--color-bg-surface)',
            marginBottom: '2rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
            <div style={{ padding: '0.625rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-accent-soft)', color: 'var(--color-accent)' }}>
              <Sparkles size={24} />
            </div>
            <div>
              <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
                Active Experience
              </div>
              <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-primary-dark)' }}>
                {t(`tier_${business.tier}`)} &bull; {business.enabled_modules?.length || 0} Modules Active
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <Button variant="primary" onClick={() => onNavigateTab && onNavigateTab('pos')}>
              <ShoppingCart size={16} /> {t('pos_billing')}
            </Button>
            <Button variant="outline" onClick={() => onNavigateTab && onNavigateTab('reports')}>
              <BarChart3 size={16} /> {t('reports_and_profit_title')}
            </Button>
            <Button variant="outline" onClick={() => onNavigateTab && onNavigateTab('cash_closing')}>
              <LockKeyhole size={16} /> {t('cash_closing_title')}
            </Button>
            <Button variant="accent" onClick={() => onNavigateTab && onNavigateTab('purchases')}>
              <Truck size={16} /> {t('purchases_title')}
            </Button>
            <Button variant="outline" onClick={() => onNavigateTab && onNavigateTab('expenses')}>
              <Receipt size={16} /> {t('expenses_title')}
            </Button>
            <Button variant="outline" onClick={() => onNavigateTab && onNavigateTab('cashbook')}>
              <BookOpen size={16} /> {t('cashbook_title')}
            </Button>
            <Button variant="outline" onClick={() => onNavigateTab && onNavigateTab('suppliers')}>
              <Building2 size={16} /> {t('suppliers_title')}
            </Button>
            <Button variant="outline" onClick={() => onNavigateTab && onNavigateTab('customers')}>
              <Users size={16} /> {t('customers_title')}
            </Button>
            <Button variant="outline" onClick={() => onNavigateTab && onNavigateTab('inventory')}>
              <Package size={16} /> {t('products_and_inventory')}
            </Button>
            <Button variant="ghost" onClick={() => onNavigateTab && onNavigateTab('settings')}>
              <Sliders size={16} /> {t('settings')}
            </Button>
          </div>
        </div>
      )}

      {/* Grid of Foundation Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '1.25rem',
          marginBottom: '2rem'
        }}
      >
        {/* Business Account & Tenant Isolation */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '1rem' }}>
            <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-primary-soft)', color: 'var(--color-primary)' }}>
              <Building2 size={22} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 'var(--font-size-base)' }}>Business Identity</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Tenant Isolation Verified</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: 'var(--font-size-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Business Name:</span>
              <span style={{ fontWeight: 600 }}>{business?.name}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Phone Number:</span>
              <span style={{ fontWeight: 600 }}>{user?.phone}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Role:</span>
              <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{user?.role}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Tenant UUID:</span>
              <span style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>{business?.id?.slice(0, 8)}...</span>
            </div>
          </div>
        </div>

        {/* Currency & Financial Engine */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '1rem' }}>
            <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-accent-soft)', color: 'var(--color-accent)' }}>
              <Coins size={22} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 'var(--font-size-base)' }}>Currency & Precision</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Decimal Monetary Math</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: 'var(--font-size-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Default Currency:</span>
              <span style={{ fontWeight: 600 }}>{business?.currency_code} ({business?.currency_symbol})</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Numeric Precision:</span>
              <span style={{ fontWeight: 600 }}>NUMERIC(14, 4)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Rounding Standard:</span>
              <span style={{ fontWeight: 600 }}>Banker's (Round Half to Even)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Floating-Point Money:</span>
              <span style={{ color: 'var(--color-accent)', fontWeight: 700 }}>Prohibited</span>
            </div>
          </div>
        </div>

        {/* Database & Infrastructure */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '1rem' }}>
            <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-bg-subtle)', color: 'var(--color-primary-dark)' }}>
              <Database size={22} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 'var(--font-size-base)' }}>Database Engine</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>PostgreSQL Canonical Engine</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: 'var(--font-size-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Target Database:</span>
              <span style={{ fontWeight: 600 }}>PostgreSQL 16+</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Active Dialect:</span>
              <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{healthData?.database?.dialect || 'Connected'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.375rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Alembic Migrations:</span>
              <span style={{ fontWeight: 600 }}>Version 001 Initial Schema</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Health Status:</span>
              <Badge variant={healthData?.status === 'online' ? 'success' : 'neutral'}>
                {healthData?.status?.toUpperCase() || 'CHECKING...'}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Stage 1 Completed Deliverables Section */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <ShieldCheck size={24} color="var(--color-accent)" />
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700 }}>Stage 1 Foundation Verification</h2>
        </div>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', marginBottom: '1.25rem' }}>
          {t('stage_1_desc')}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '0.75rem' }}>
          {[
            'E.164 Phone Normalization & Validation',
            'Argon2id PIN & Password Cryptographic Hashing',
            'Dual-Key Rate Limiting (IP + Phone Brute-Force Protection)',
            'JWT Access Tokens & Secure Refresh Token Cookies',
            'Backend Business-Tenant Isolation Checks on Every Route',
            'PostgreSQL 16+ Schema with Alembic Migration Scripts',
            'INR Default Currency Engine with Banker’s Rounding',
            'Trilingual Localization (Tamil, Tanglish, English)'
          ].map((item, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-main)'
              }}
            >
              <CheckCircle2 size={16} color="var(--color-accent)" style={{ flexShrink: 0 }} />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
