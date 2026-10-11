import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useI18n } from '../context/I18nContext';
import { api } from '../services/api';
import { Button } from '../components/common/Button';
import { Alert, Badge, LoadingSpinner } from '../components/common/Feedback';
import {
  Settings,
  Sparkles,
  Save,
  CheckCircle2,
  RefreshCw,
  Compass,
  Sliders,
  Layers
} from 'lucide-react';

export function SettingsPage({ onRevisitOnboarding }) {
  const { business, updateBusiness, refreshBusiness } = useAuth();
  const { t, setLanguage, currentLanguage } = useI18n();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const [tier, setTier] = useState('simple');
  const [preferredLang, setPreferredLang] = useState('ta');
  const [enabledModules, setEnabledModules] = useState([]);
  const [accessibility, setAccessibility] = useState({
    high_contrast: false,
    large_font: false,
    simplified_ui: true
  });
  const [availableModules, setAvailableModules] = useState([]);

  useEffect(() => {
    async function loadProfile() {
      try {
        setLoading(true);
        const [profRes, onbRes] = await Promise.all([
          api.getBusinessProfile(),
          api.getOnboardingState()
        ]);

        if (profRes.success && profRes.data) {
          const p = profRes.data;
          setTier(p.tier || 'simple');
          setPreferredLang(p.default_language || 'ta');
          setEnabledModules(p.enabled_modules || []);
          if (p.accessibility_settings) {
            setAccessibility(p.accessibility_settings);
          }
        }

        // Fetch available module list for toggling
        if (onbRes.success && onbRes.data) {
          const recRes = await api.getRecommendation(onbRes.data.answers || {});
          if (recRes.success && recRes.data?.available_modules) {
            setAvailableModules(recRes.data.available_modules);
          }
        }
      } catch (err) {
        console.warn('Could not load preferences:', err);
      } finally {
        setLoading(false);
      }
    }
    loadProfile();
  }, []);

  const toggleModule = (modId) => {
    setEnabledModules(prev =>
      prev.includes(modId) ? prev.filter(x => x !== modId) : [...prev, modId]
    );
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setErrorMsg(null);
      setSuccessMsg(null);

      const res = await api.updateBusinessPreferences({
        tier,
        default_language: preferredLang,
        enabled_modules: enabledModules,
        accessibility_settings: accessibility
      });

      if (res.success && res.data) {
        updateBusiness(res.data);
        await refreshBusiness();
        setLanguage(preferredLang);
        setSuccessMsg(t('preferences_saved'));
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem 1rem', display: 'flex', justifyContent: 'center' }}>
        <LoadingSpinner label="Loading settings..." />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, margin: 0, color: 'var(--color-primary-dark)' }}>
              {t('profile_settings_title')}
            </h1>
            <Badge variant="primary">{tier.toUpperCase()}</Badge>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-base)', margin: 0 }}>
            {t('profile_settings_desc')}
          </p>
        </div>

        <Button variant="outline" onClick={onRevisitOnboarding}>
          <Compass size={16} /> {t('btn_revisit_onboarding')}
        </Button>
      </div>

      {successMsg && (
        <div style={{ marginBottom: '1.25rem' }}>
          <Alert variant="accent">{successMsg}</Alert>
        </div>
      )}

      {errorMsg && (
        <div style={{ marginBottom: '1.25rem' }}>
          <Alert variant="danger">{errorMsg}</Alert>
        </div>
      )}

      {/* Experience Tier Selector */}
      <div className="card" style={{ padding: '1.75rem', marginBottom: '1.5rem', boxShadow: 'var(--shadow-sm)' }}>
        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: '0 0 0.5rem', color: 'var(--color-text-main)' }}>
          {t('current_tier')}
        </h2>
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
          Kanakku adapts screens and speed to your operational complexity.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          {[
            { id: 'simple', title: t('tier_simple'), desc: t('tier_simple_tagline') },
            { id: 'growth', title: t('tier_growth'), desc: t('tier_growth_tagline') },
            { id: 'enterprise', title: t('tier_enterprise'), desc: t('tier_enterprise_tagline') }
          ].map(opt => {
            const isSelected = tier === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => setTier(opt.id)}
                style={{
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  border: isSelected ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                  backgroundColor: isSelected ? 'var(--color-primary-soft)' : 'var(--color-bg-surface)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ fontWeight: 800, fontSize: 'var(--font-size-base)', color: isSelected ? 'var(--color-primary)' : 'inherit', marginBottom: '0.25rem' }}>
                  {opt.title}
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  {opt.desc}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Language Preference */}
      <div className="card" style={{ padding: '1.75rem', marginBottom: '1.5rem', boxShadow: 'var(--shadow-sm)' }}>
        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: '0 0 1rem', color: 'var(--color-text-main)' }}>
          {t('step9_title')}
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
          {[
            { id: 'ta', label: t('lang_ta') },
            { id: 'tanglish', label: t('lang_tanglish') },
            { id: 'en', label: t('lang_en') }
          ].map(lang => (
            <button
              key={lang.id}
              type="button"
              onClick={() => setPreferredLang(lang.id)}
              style={{
                padding: '1rem',
                borderRadius: 'var(--radius-md)',
                border: preferredLang === lang.id ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                backgroundColor: preferredLang === lang.id ? 'var(--color-primary-soft)' : 'transparent',
                fontWeight: 600,
                fontSize: 'var(--font-size-sm)',
                cursor: 'pointer',
                textAlign: 'left'
              }}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </div>

      {/* Accessibility & Interface Simplicity */}
      <div className="card" style={{ padding: '1.75rem', marginBottom: '1.5rem', boxShadow: 'var(--shadow-sm)' }}>
        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: '0 0 1rem', color: 'var(--color-text-main)' }}>
          {t('step10_title')}
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
            <input
              type="checkbox"
              checked={!!accessibility.high_contrast}
              onChange={(e) => setAccessibility(prev => ({ ...prev, high_contrast: e.target.checked }))}
              style={{ width: '18px', height: '18px' }}
            />
            <span>{t('label_high_contrast')}</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
            <input
              type="checkbox"
              checked={!!accessibility.large_font}
              onChange={(e) => setAccessibility(prev => ({ ...prev, large_font: e.target.checked }))}
              style={{ width: '18px', height: '18px' }}
            />
            <span>{t('label_large_font')}</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
            <input
              type="checkbox"
              checked={!!accessibility.simplified_ui}
              onChange={(e) => setAccessibility(prev => ({ ...prev, simplified_ui: e.target.checked }))}
              style={{ width: '18px', height: '18px' }}
            />
            <span>{t('label_simplified_ui')}</span>
          </label>
        </div>
      </div>

      {/* Active Modules Toggle */}
      <div className="card" style={{ padding: '1.75rem', marginBottom: '2rem', boxShadow: 'var(--shadow-sm)' }}>
        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: '0 0 0.5rem', color: 'var(--color-text-main)' }}>
          {t('active_modules', { count: enabledModules.length })}
        </h2>
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
          Toggle features active in your current navigation bar and operational screens.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
          {availableModules.map(mod => {
            const isChecked = enabledModules.includes(mod.id);
            const modName = currentLanguage === 'ta' ? mod.name_ta : currentLanguage === 'tanglish' ? mod.name_tanglish : mod.name_en;
            return (
              <label
                key={mod.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.875rem 1rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: isChecked ? 'var(--color-bg-subtle)' : 'transparent',
                  cursor: 'pointer',
                  fontSize: 'var(--font-size-sm)'
                }}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggleModule(mod.id)}
                  style={{ width: '18px', height: '18px' }}
                />
                <span style={{ fontWeight: 600 }}>{modName}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Save Action */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
        <Button variant="primary" size="large" onClick={handleSave} disabled={saving}>
          <Save size={18} /> {saving ? t('btn_saving') : t('btn_save_preferences')}
        </Button>
      </div>
    </div>
  );
}
