import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useI18n } from '../../context/I18nContext';
import { api } from '../../services/api';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Alert, Badge, LoadingSpinner } from '../common/Feedback';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Save,
  CheckCircle2,
  Building,
  Users,
  Store,
  Layers,
  Boxes,
  Factory,
  CreditCard,
  ShieldAlert,
  Languages,
  Eye,
  Check,
  ChevronRight,
  AlertCircle
} from 'lucide-react';

export function OnboardingWizard({ onComplete, onExit }) {
  const { business, user, updateBusiness, refreshBusiness } = useAuth();
  const { t, setLanguage, currentLanguage } = useI18n();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState(null);

  // Stepper state
  // Steps: 1..10 (questions), 11 (Review & Recommendation), 12 (Completed)
  const [currentStep, setCurrentStep] = useState(1);
  const [recommendation, setRecommendation] = useState(null);
  const [selectedTier, setSelectedTier] = useState('simple');
  const [enabledModules, setEnabledModules] = useState([]);

  // Form answers state
  const [answers, setAnswers] = useState({
    business_name: business?.name || '',
    category: business?.category || 'grocery',
    workforce_count: 1,
    app_users_count: 1,
    branch_count: 1,
    warehouse_count: 1,
    operations: ['retail'],
    tracks_inventory: true,
    purchase_orders: false,
    has_manufacturing: false,
    raw_materials: false,
    production_batches: false,
    scrap_wastage: false,
    track_customer_credit: false,
    track_supplier_payments: false,
    need_staff_permissions: false,
    need_approval_workflows: false,
    preferred_language: currentLanguage || 'ta',
    accessibility: {
      high_contrast: false,
      large_font: false,
      simplified_ui: true
    }
  });

  // Load saved draft on mount
  useEffect(() => {
    async function loadDraft() {
      try {
        setLoading(true);
        const res = await api.getOnboardingState();
        if (res.success && res.data) {
          const data = res.data;
          if (data.answers) {
            setAnswers(prev => ({
              ...prev,
              ...data.answers,
              business_name: data.answers.business_name || business?.name || prev.business_name,
            }));
          }
          if (data.current_step && data.current_step <= 11) {
            setCurrentStep(data.current_step);
          }
          if (data.selected_tier) {
            setSelectedTier(data.selected_tier);
          }
          if (data.enabled_modules && data.enabled_modules.length > 0) {
            setEnabledModules(data.enabled_modules);
          }
        }
      } catch (err) {
        console.warn('Could not load onboarding draft, starting fresh:', err);
      } finally {
        setLoading(false);
      }
    }
    loadDraft();
  }, [business]);

  const updateAnswer = (key, value) => {
    setAnswers(prev => ({ ...prev, [key]: value }));
    setError(null);
  };

  const updateAccessibility = (key, value) => {
    setAnswers(prev => ({
      ...prev,
      accessibility: {
        ...prev.accessibility,
        [key]: value
      }
    }));
  };

  const toggleOperation = (op) => {
    setAnswers(prev => {
      const exists = prev.operations.includes(op);
      let nextOps = exists ? prev.operations.filter(x => x !== op) : [...prev.operations, op];
      if (nextOps.length === 0) nextOps = ['retail'];
      const hasMfg = nextOps.includes('manufacturing');
      return {
        ...prev,
        operations: nextOps,
        has_manufacturing: hasMfg
      };
    });
  };

  // Skip Step 6 (Manufacturing) if business does NOT have manufacturing
  const isMfgStepActive = () => {
    return answers.operations.includes('manufacturing') || answers.has_manufacturing;
  };

  // Determine effective total question steps (excluding review)
  const totalQuestionSteps = 10;

  // Save draft to backend as user progresses
  const persistDraft = async (nextStep) => {
    try {
      setSaving(true);
      await api.saveOnboardingDraft({
        step: nextStep,
        answers
      });
    } catch (err) {
      console.warn('Failed to save draft:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleNext = async () => {
    setError(null);

    // Validation per step
    if (currentStep === 1) {
      if (!answers.business_name || !answers.business_name.trim()) {
        setError(t('label_business_name') + ' is required.');
        return;
      }
    }

    let nextStep = currentStep + 1;
    // Conditional step skipping
    if (currentStep === 5 && !isMfgStepActive()) {
      nextStep = 7; // Skip step 6 (Manufacturing)
    }

    if (nextStep === 11) {
      // Reached review / recommendation trigger
      await fetchRecommendation();
    } else {
      await persistDraft(nextStep);
    }

    setCurrentStep(nextStep);
  };

  const handleBack = () => {
    setError(null);
    let prevStep = currentStep - 1;
    if (currentStep === 7 && !isMfgStepActive()) {
      prevStep = 5; // Step back past manufacturing
    }
    if (prevStep < 1) prevStep = 1;
    setCurrentStep(prevStep);
  };

  const handleSaveAndExit = async () => {
    await persistDraft(currentStep);
    if (onExit) onExit();
  };

  const fetchRecommendation = async () => {
    try {
      setSaving(true);
      const res = await api.getRecommendation(answers);
      if (res.success && res.data) {
        setRecommendation(res.data);
        setSelectedTier(res.data.recommended_tier);
        setEnabledModules(res.data.recommended_modules);
      }
    } catch (err) {
      setError(err.message || 'Failed to calculate recommendation');
    } finally {
      setSaving(false);
    }
  };

  const toggleModule = (modId) => {
    setEnabledModules(prev =>
      prev.includes(modId) ? prev.filter(x => x !== modId) : [...prev, modId]
    );
  };

  const handleComplete = async () => {
    try {
      setCompleting(true);
      setError(null);
      const res = await api.completeOnboarding({
        selected_tier: selectedTier,
        enabled_modules: enabledModules,
        answers
      });
      if (res.success && res.data) {
        updateBusiness(res.data);
        await refreshBusiness();
        setCurrentStep(12); // Completed screen
      }
    } catch (err) {
      setError(err.message || 'Failed to complete onboarding');
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '4rem 1rem', display: 'flex', justifyContent: 'center' }}>
        <LoadingSpinner label="Loading setup questions..." />
      </div>
    );
  }

  // Calculate progress percentage
  const progressPercent = Math.min(Math.round(((Math.min(currentStep, 11) - 1) / 10) * 100), 100);

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* Wizard Header & Progress Bar */}
      {currentStep <= 11 && (
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {t('onboarding_title')}
              </span>
              <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, margin: '0.25rem 0 0', color: 'var(--color-text-main)' }}>
                {currentStep === 11 ? t('review_title') : t(`step${currentStep}_title`)}
              </h1>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-subtle)' }}>
                {currentStep <= 10 ? t('step_indicator', { current: currentStep, total: totalQuestionSteps }) : 'Final Step'}
              </span>
              <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-accent)' }}>
                {progressPercent}%
              </div>
            </div>
          </div>

          {/* Accessible Animated Progress Bar */}
          <div
            role="progressbar"
            aria-valuenow={progressPercent}
            aria-valuemin="0"
            aria-valuemax="100"
            style={{
              height: '8px',
              backgroundColor: 'var(--color-border)',
              borderRadius: 'var(--radius-full)',
              overflow: 'hidden'
            }}
          >
            <div
              style={{
                width: `${progressPercent}%`,
                height: '100%',
                backgroundColor: 'var(--color-primary)',
                transition: 'width 0.3s ease'
              }}
            />
          </div>
        </div>
      )}

      {error && (
        <div style={{ marginBottom: '1.25rem' }}>
          <Alert variant="danger">{error}</Alert>
        </div>
      )}

      {/* Main Question Card Surface */}
      <div className="card" style={{ padding: '2rem', marginBottom: '1.5rem', boxShadow: 'var(--shadow-md)' }}>
        {/* STEP 1: Business Identity & Category */}
        {currentStep === 1 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step1_desc')}
            </p>

            <div style={{ marginBottom: '1.5rem' }}>
              <Input
                label={t('label_business_name')}
                value={answers.business_name}
                onChange={(e) => updateAnswer('business_name', e.target.value)}
                placeholder="e.g. Sri Murugan Store"
                required
                autoFocus
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
                {t('label_category')}
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
                {[
                  { id: 'grocery', label: t('cat_grocery') },
                  { id: 'textile', label: t('cat_textile') },
                  { id: 'fruits', label: t('cat_fruits') },
                  { id: 'hardware', label: t('cat_hardware') },
                  { id: 'pharmacy', label: t('cat_pharmacy') },
                  { id: 'restaurant', label: t('cat_restaurant') },
                  { id: 'manufacturing', label: t('cat_manufacturing') },
                  { id: 'services', label: t('cat_services') },
                  { id: 'other', label: t('cat_other') },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => updateAnswer('category', cat.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0.875rem 1rem',
                      borderRadius: 'var(--radius-md)',
                      border: answers.category === cat.id ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                      backgroundColor: answers.category === cat.id ? 'var(--color-primary-soft)' : 'var(--color-bg-surface)',
                      color: answers.category === cat.id ? 'var(--color-primary)' : 'var(--color-text-main)',
                      fontWeight: answers.category === cat.id ? 700 : 500,
                      cursor: 'pointer',
                      textAlign: 'left',
                      minHeight: 'var(--touch-target-min)',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <span>{cat.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Workforce & Users */}
        {currentStep === 2 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step2_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div>
                <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {t('label_workforce')}
                </label>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)', marginBottom: '0.5rem' }}>
                  {t('hint_workforce')}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    value={answers.workforce_count}
                    onChange={(e) => updateAnswer('workforce_count', Math.max(1, parseInt(e.target.value) || 1))}
                    style={{
                      width: '120px',
                      padding: '0.75rem',
                      fontSize: 'var(--font-size-lg)',
                      fontWeight: 700,
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border)',
                      textAlign: 'center'
                    }}
                  />
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {[1, 5, 10, 25, 50].map(val => (
                      <button
                        key={val}
                        type="button"
                        onClick={() => updateAnswer('workforce_count', val)}
                        style={{
                          padding: '0.5rem 0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          border: answers.workforce_count === val ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                          backgroundColor: answers.workforce_count === val ? 'var(--color-primary-soft)' : 'transparent',
                          cursor: 'pointer',
                          fontWeight: 600
                        }}
                      >
                        {val}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {t('label_app_users')}
                </label>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)', marginBottom: '0.5rem' }}>
                  {t('hint_app_users')}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <input
                    type="number"
                    min="1"
                    max="500"
                    value={answers.app_users_count}
                    onChange={(e) => updateAnswer('app_users_count', Math.max(1, parseInt(e.target.value) || 1))}
                    style={{
                      width: '120px',
                      padding: '0.75rem',
                      fontSize: 'var(--font-size-lg)',
                      fontWeight: 700,
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border)',
                      textAlign: 'center'
                    }}
                  />
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {[1, 2, 3, 5, 10].map(val => (
                      <button
                        key={val}
                        type="button"
                        onClick={() => updateAnswer('app_users_count', val)}
                        style={{
                          padding: '0.5rem 0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          border: answers.app_users_count === val ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                          backgroundColor: answers.app_users_count === val ? 'var(--color-primary-soft)' : 'transparent',
                          cursor: 'pointer',
                          fontWeight: 600
                        }}
                      >
                        {val}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Outlets & Warehouses */}
        {currentStep === 3 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step3_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div>
                <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.5rem' }}>
                  {t('label_branch_count')}
                </label>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  {[
                    { val: 1, label: '1 Outlet (Single Shop)' },
                    { val: 2, label: '2 Outlets' },
                    { val: 3, label: '3-4 Outlets' },
                    { val: 5, label: '5+ Outlets (Chain)' }
                  ].map(item => (
                    <button
                      key={item.val}
                      type="button"
                      onClick={() => updateAnswer('branch_count', item.val)}
                      style={{
                        padding: '1rem',
                        borderRadius: 'var(--radius-md)',
                        border: answers.branch_count === item.val ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                        backgroundColor: answers.branch_count === item.val ? 'var(--color-primary-soft)' : 'transparent',
                        color: answers.branch_count === item.val ? 'var(--color-primary)' : 'var(--color-text-main)',
                        fontWeight: 600,
                        cursor: 'pointer',
                        minWidth: '150px'
                      }}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.5rem' }}>
                  {t('label_warehouse_count')}
                </label>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  {[
                    { val: 0, label: 'No separate godown (Stock in shop)' },
                    { val: 1, label: '1 Central Godown' },
                    { val: 2, label: '2 or more Godowns' }
                  ].map(item => (
                    <button
                      key={item.val}
                      type="button"
                      onClick={() => updateAnswer('warehouse_count', item.val)}
                      style={{
                        padding: '1rem',
                        borderRadius: 'var(--radius-md)',
                        border: answers.warehouse_count === item.val ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                        backgroundColor: answers.warehouse_count === item.val ? 'var(--color-primary-soft)' : 'transparent',
                        color: answers.warehouse_count === item.val ? 'var(--color-primary)' : 'var(--color-text-main)',
                        fontWeight: 600,
                        cursor: 'pointer',
                        minWidth: '160px'
                      }}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Operational Model */}
        {currentStep === 4 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step4_desc')}
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              {[
                { id: 'retail', title: t('op_retail'), icon: Store },
                { id: 'wholesale', title: t('op_wholesale'), icon: Boxes },
                { id: 'services', title: t('op_services'), icon: Users },
                { id: 'manufacturing', title: t('op_manufacturing'), icon: Factory },
              ].map(item => {
                const isSelected = answers.operations.includes(item.id);
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => toggleOperation(item.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      padding: '1.25rem',
                      borderRadius: 'var(--radius-md)',
                      border: isSelected ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                      backgroundColor: isSelected ? 'var(--color-primary-soft)' : 'var(--color-bg-surface)',
                      color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textAlign: 'left',
                      minHeight: 'var(--touch-target-large)',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: isSelected ? 'var(--color-primary)' : 'var(--color-bg-subtle)', color: isSelected ? '#fff' : 'var(--color-text-muted)' }}>
                      <Icon size={22} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 'var(--font-size-base)', fontWeight: isSelected ? 700 : 600 }}>{item.title}</div>
                    </div>
                    {isSelected && <Check size={20} color="var(--color-primary)" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* STEP 5: Inventory & Purchases */}
        {currentStep === 5 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step5_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div>
                <label style={{ display: 'block', fontWeight: 700, marginBottom: '0.75rem', fontSize: 'var(--font-size-base)' }}>
                  {t('label_tracks_inventory')}
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
                  <button
                    type="button"
                    onClick={() => updateAnswer('tracks_inventory', true)}
                    style={{
                      padding: '1rem',
                      borderRadius: 'var(--radius-md)',
                      border: answers.tracks_inventory ? '2px solid var(--color-accent)' : '1px solid var(--color-border)',
                      backgroundColor: answers.tracks_inventory ? 'var(--color-accent-soft)' : 'transparent',
                      cursor: 'pointer',
                      fontWeight: 600,
                      textAlign: 'left'
                    }}
                  >
                    <div style={{ color: answers.tracks_inventory ? 'var(--color-accent)' : 'inherit' }}>
                      {t('yes_tracks_inventory')}
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => updateAnswer('tracks_inventory', false)}
                    style={{
                      padding: '1rem',
                      borderRadius: 'var(--radius-md)',
                      border: !answers.tracks_inventory ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                      backgroundColor: !answers.tracks_inventory ? 'var(--color-primary-soft)' : 'transparent',
                      cursor: 'pointer',
                      fontWeight: 600,
                      textAlign: 'left'
                    }}
                  >
                    <div style={{ color: !answers.tracks_inventory ? 'var(--color-primary)' : 'inherit' }}>
                      {t('no_tracks_inventory')}
                    </div>
                  </button>
                </div>
              </div>

              {answers.tracks_inventory && (
                <div style={{ paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '0.75rem', fontSize: 'var(--font-size-base)' }}>
                    {t('label_purchase_orders')}
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
                    <button
                      type="button"
                      onClick={() => updateAnswer('purchase_orders', true)}
                      style={{
                        padding: '1rem',
                        borderRadius: 'var(--radius-md)',
                        border: answers.purchase_orders ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                        backgroundColor: answers.purchase_orders ? 'var(--color-primary-soft)' : 'transparent',
                        cursor: 'pointer',
                        fontWeight: 600,
                        textAlign: 'left'
                      }}
                    >
                      {t('yes_purchase_orders')}
                    </button>
                    <button
                      type="button"
                      onClick={() => updateAnswer('purchase_orders', false)}
                      style={{
                        padding: '1rem',
                        borderRadius: 'var(--radius-md)',
                        border: !answers.purchase_orders ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                        backgroundColor: !answers.purchase_orders ? 'var(--color-primary-soft)' : 'transparent',
                        cursor: 'pointer',
                        fontWeight: 600,
                        textAlign: 'left'
                      }}
                    >
                      {t('no_purchase_orders')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* STEP 6: Manufacturing & Raw Materials (Conditional) */}
        {currentStep === 6 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step6_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[
                { id: 'raw_materials', label: t('label_raw_materials') },
                { id: 'production_batches', label: t('label_production_batches') },
                { id: 'scrap_wastage', label: t('label_scrap_wastage') }
              ].map(item => (
                <label
                  key={item.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '1rem 1.25rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border)',
                    backgroundColor: answers[item.id] ? 'var(--color-primary-soft)' : 'transparent',
                    cursor: 'pointer',
                    minHeight: 'var(--touch-target-min)'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={answers[item.id]}
                    onChange={(e) => updateAnswer(item.id, e.target.checked)}
                    style={{ width: '20px', height: '20px', cursor: 'pointer' }}
                  />
                  <span style={{ fontWeight: 600, fontSize: 'var(--font-size-base)' }}>{item.label}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* STEP 7: Credit & Khata Tracking */}
        {currentStep === 7 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step7_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '1rem',
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: answers.track_customer_credit ? 'var(--color-primary-soft)' : 'transparent',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={answers.track_customer_credit}
                  onChange={(e) => updateAnswer('track_customer_credit', e.target.checked)}
                  style={{ width: '22px', height: '22px', marginTop: '3px', cursor: 'pointer' }}
                />
                <div>
                  <div style={{ fontWeight: 700, fontSize: 'var(--font-size-base)', marginBottom: '0.25rem' }}>
                    {t('label_customer_credit')}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    {t('hint_customer_credit')}
                  </div>
                </div>
              </label>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '1rem',
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: answers.track_supplier_payments ? 'var(--color-primary-soft)' : 'transparent',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={answers.track_supplier_payments}
                  onChange={(e) => updateAnswer('track_supplier_payments', e.target.checked)}
                  style={{ width: '22px', height: '22px', marginTop: '3px', cursor: 'pointer' }}
                />
                <div>
                  <div style={{ fontWeight: 700, fontSize: 'var(--font-size-base)', marginBottom: '0.25rem' }}>
                    {t('label_supplier_payments')}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    {t('hint_supplier_payments')}
                  </div>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* STEP 8: Governance & Team Roles */}
        {currentStep === 8 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step8_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '1rem',
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: answers.need_staff_permissions ? 'var(--color-primary-soft)' : 'transparent',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={answers.need_staff_permissions}
                  onChange={(e) => updateAnswer('need_staff_permissions', e.target.checked)}
                  style={{ width: '22px', height: '22px', marginTop: '3px', cursor: 'pointer' }}
                />
                <div>
                  <div style={{ fontWeight: 700, fontSize: 'var(--font-size-base)', marginBottom: '0.25rem' }}>
                    {t('label_staff_permissions')}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    {t('hint_staff_permissions')}
                  </div>
                </div>
              </label>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '1rem',
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: answers.need_approval_workflows ? 'var(--color-primary-soft)' : 'transparent',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={answers.need_approval_workflows}
                  onChange={(e) => updateAnswer('need_approval_workflows', e.target.checked)}
                  style={{ width: '22px', height: '22px', marginTop: '3px', cursor: 'pointer' }}
                />
                <div>
                  <div style={{ fontWeight: 700, fontSize: 'var(--font-size-base)', marginBottom: '0.25rem' }}>
                    {t('label_approval_workflows')}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    Require supervisor PIN/approval before cancelling bills or giving custom discounts.
                  </div>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* STEP 9: Preferred UI Language */}
        {currentStep === 9 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step9_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              {[
                { id: 'ta', label: t('lang_ta') },
                { id: 'tanglish', label: t('lang_tanglish') },
                { id: 'en', label: t('lang_en') }
              ].map(lang => (
                <button
                  key={lang.id}
                  type="button"
                  onClick={() => {
                    updateAnswer('preferred_language', lang.id);
                    setLanguage(lang.id);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '1.25rem',
                    borderRadius: 'var(--radius-md)',
                    border: answers.preferred_language === lang.id ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                    backgroundColor: answers.preferred_language === lang.id ? 'var(--color-primary-soft)' : 'transparent',
                    color: answers.preferred_language === lang.id ? 'var(--color-primary)' : 'var(--color-text-main)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  <span style={{ fontSize: 'var(--font-size-base)' }}>{lang.label}</span>
                  {answers.preferred_language === lang.id && <Check size={20} color="var(--color-primary)" />}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* STEP 10: Interface Simplicity & Accessibility */}
        {currentStep === 10 && (
          <div>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1.5rem', fontSize: 'var(--font-size-base)' }}>
              {t('step10_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: answers.accessibility?.high_contrast ? 'var(--color-primary-soft)' : 'transparent',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={!!answers.accessibility?.high_contrast}
                  onChange={(e) => updateAccessibility('high_contrast', e.target.checked)}
                  style={{ width: '22px', height: '22px', cursor: 'pointer' }}
                />
                <span style={{ fontWeight: 600, fontSize: 'var(--font-size-base)' }}>{t('label_high_contrast')}</span>
              </label>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: answers.accessibility?.large_font ? 'var(--color-primary-soft)' : 'transparent',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={!!answers.accessibility?.large_font}
                  onChange={(e) => updateAccessibility('large_font', e.target.checked)}
                  style={{ width: '22px', height: '22px', cursor: 'pointer' }}
                />
                <span style={{ fontWeight: 600, fontSize: 'var(--font-size-base)' }}>{t('label_large_font')}</span>
              </label>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: answers.accessibility?.simplified_ui ? 'var(--color-primary-soft)' : 'transparent',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={!!answers.accessibility?.simplified_ui}
                  onChange={(e) => updateAccessibility('simplified_ui', e.target.checked)}
                  style={{ width: '22px', height: '22px', cursor: 'pointer' }}
                />
                <span style={{ fontWeight: 600, fontSize: 'var(--font-size-base)' }}>{t('label_simplified_ui')}</span>
              </label>
            </div>
          </div>
        )}

        {/* STEP 11: Review, Deterministic Recommendation & Owner Choice */}
        {currentStep === 11 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-accent-soft)', color: 'var(--color-accent)' }}>
                <Sparkles size={24} />
              </div>
              <div>
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 800, margin: 0, color: 'var(--color-primary-dark)' }}>
                  {t('recommendation_title')}
                </h2>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  {t('recommendation_desc')}
                </div>
              </div>
            </div>

            {/* Recommendation Explanation Card */}
            {recommendation && (
              <div
                style={{
                  padding: '1.5rem',
                  borderRadius: 'var(--radius-md)',
                  border: '2px solid var(--color-accent)',
                  backgroundColor: 'var(--color-accent-soft)',
                  marginBottom: '2rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <Badge variant="accent">{t('recommended_tag')}</Badge>
                  <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-accent)' }}>
                    {t('complexity_badge', { score: recommendation.complexity_score })}
                  </span>
                </div>

                <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 900, color: 'var(--color-primary-dark)', marginBottom: '0.25rem' }}>
                  {t(`tier_${recommendation.recommended_tier}`)}
                </div>
                <p style={{ color: 'var(--color-text-main)', fontSize: 'var(--font-size-sm)', margin: '0 0 1.25rem' }}>
                  {t(`tier_${recommendation.recommended_tier}_desc`)}
                </p>

                {/* Explainable Reasons List */}
                <div style={{ borderTop: '1px solid rgba(5, 150, 105, 0.2)', paddingTop: '1rem' }}>
                  <div style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)', color: 'var(--color-primary-dark)', marginBottom: '0.5rem' }}>
                    {t('why_this_recommended')}:
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                    {recommendation.reasons?.map((reason, idx) => (
                      <li key={idx} style={{ marginBottom: '0.375rem' }}>
                        <strong>{currentLanguage === 'ta' ? reason.title_ta : currentLanguage === 'tanglish' ? reason.title_tanglish : reason.title_en}:</strong>{' '}
                        {currentLanguage === 'ta' ? reason.desc_ta : currentLanguage === 'tanglish' ? reason.desc_tanglish : reason.desc_en}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Owner Tier Override Selector */}
            <div style={{ marginBottom: '2rem' }}>
              <label style={{ display: 'block', fontWeight: 700, fontSize: 'var(--font-size-base)', marginBottom: '0.75rem' }}>
                {t('owner_choice_prompt')}
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                {[
                  {
                    id: 'simple',
                    title: t('tier_simple'),
                    tagline: t('tier_simple_tagline'),
                  },
                  {
                    id: 'growth',
                    title: t('tier_growth'),
                    tagline: t('tier_growth_tagline'),
                  },
                  {
                    id: 'enterprise',
                    title: t('tier_enterprise'),
                    tagline: t('tier_enterprise_tagline'),
                  }
                ].map(tierOption => {
                  const isSelected = selectedTier === tierOption.id;
                  const isRec = recommendation?.recommended_tier === tierOption.id;
                  return (
                    <button
                      key={tierOption.id}
                      type="button"
                      onClick={() => setSelectedTier(tierOption.id)}
                      style={{
                        padding: '1.25rem',
                        borderRadius: 'var(--radius-md)',
                        border: isSelected ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                        backgroundColor: isSelected ? 'var(--color-primary-soft)' : 'var(--color-bg-surface)',
                        cursor: 'pointer',
                        textAlign: 'left',
                        position: 'relative',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {isRec && (
                        <div style={{ position: 'absolute', top: '10px', right: '10px' }}>
                          <Badge variant="accent">Best Match</Badge>
                        </div>
                      )}
                      <div style={{ fontWeight: 800, fontSize: 'var(--font-size-base)', color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)', marginBottom: '0.25rem' }}>
                        {tierOption.title}
                      </div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                        {tierOption.tagline}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Module Toggles */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.5rem' }}>
                <label style={{ fontWeight: 700, fontSize: 'var(--font-size-base)' }}>
                  {t('modules_included')} ({enabledModules.length})
                </label>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)' }}>
                  {t('toggle_module_hint')}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                {recommendation?.available_modules?.map(mod => {
                  const isChecked = enabledModules.includes(mod.id);
                  const modName = currentLanguage === 'ta' ? mod.name_ta : currentLanguage === 'tanglish' ? mod.name_tanglish : mod.name_en;
                  const modDesc = currentLanguage === 'ta' ? mod.description_ta : currentLanguage === 'tanglish' ? mod.description_tanglish : mod.description_en;
                  return (
                    <label
                      key={mod.id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
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
                        style={{ marginTop: '2px', cursor: 'pointer' }}
                      />
                      <div>
                        <div style={{ fontWeight: 600 }}>{modName}</div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)' }}>{modDesc}</div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* STEP 12: Completion Celebratory Screen */}
        {currentStep === 12 && (
          <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
            <div style={{ width: '64px', height: '64px', borderRadius: '50%', backgroundColor: 'var(--color-accent-soft)', color: 'var(--color-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
              <CheckCircle2 size={40} />
            </div>
            <h2 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 900, color: 'var(--color-primary-dark)', marginBottom: '0.5rem' }}>
              {t('completion_title')}
            </h2>
            <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-base)', maxWidth: '500px', margin: '0 auto 2rem' }}>
              {t('completion_desc', { tier: t(`tier_${selectedTier}`) })}
            </p>

            <div style={{ display: 'inline-flex', gap: '1rem', padding: '1rem 2rem', backgroundColor: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', marginBottom: '2.5rem', textAlign: 'left' }}>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)' }}>Active Experience:</div>
                <div style={{ fontWeight: 800, fontSize: 'var(--font-size-lg)', color: 'var(--color-primary)' }}>{t(`tier_${selectedTier}`)}</div>
              </div>
              <div style={{ width: '1px', backgroundColor: 'var(--color-border)' }} />
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)' }}>Modules Enabled:</div>
                <div style={{ fontWeight: 800, fontSize: 'var(--font-size-lg)', color: 'var(--color-accent)' }}>{enabledModules.length} Modules</div>
              </div>
            </div>

            <div>
              <Button
                variant="accent"
                size="large"
                onClick={() => {
                  if (onComplete) onComplete();
                }}
              >
                {t('btn_go_dashboard')} &rarr;
              </Button>
            </div>
          </div>
        )}

        {/* Wizard Footer Navigation Controls */}
        {currentStep <= 11 && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '2.5rem',
              paddingTop: '1.5rem',
              borderTop: '1px solid var(--color-border)'
            }}
          >
            <div>
              {currentStep > 1 && (
                <Button variant="outline" onClick={handleBack} disabled={saving || completing}>
                  <ArrowLeft size={16} /> {t('btn_back')}
                </Button>
              )}
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <Button variant="ghost" onClick={handleSaveAndExit} disabled={saving || completing}>
                <Save size={16} /> {t('btn_save_exit')}
              </Button>

              {currentStep < 11 && (
                <Button variant="primary" onClick={handleNext} disabled={saving}>
                  {t('btn_continue')} <ArrowRight size={16} />
                </Button>
              )}

              {currentStep === 11 && (
                <Button variant="accent" onClick={handleComplete} disabled={completing}>
                  {completing ? t('logging_in') : t('btn_complete')} <Check size={18} />
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
