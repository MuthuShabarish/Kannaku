import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useI18n } from '../context/I18nContext';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { Alert } from '../components/common/Feedback';
import { KeyRound, ShieldAlert, Copy, Check, Store, Phone, User as UserIcon } from 'lucide-react';

export function LoginPage() {
  const { login, register, lastRecoveryKey, clearLastRecoveryKey } = useAuth();
  const { t } = useI18n();

  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [fullName, setFullName] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [category, setCategory] = useState('');
  const [currencyCode] = useState('INR');

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isCopied, setIsCopied] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setIsLoading(true);

    try {
      if (mode === 'login') {
        await login(phone, pin);
      } else {
        await register({
          phone,
          pin_or_password: pin,
          full_name: fullName,
          business_name: businessName,
          category: category || null,
          currency_code: currencyCode,
          currency_symbol: '₹',
          default_language: 'ta'
        });
      }
    } catch (err) {
      setErrorMessage(err.message || 'Operation failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyKey = () => {
    if (lastRecoveryKey) {
      navigator.clipboard.writeText(lastRecoveryKey);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
        backgroundColor: 'var(--color-bg-app)'
      }}
    >
      <div style={{ width: '100%', maxWidth: '440px' }}>
        {/* Brand Banner */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: 'var(--radius-lg)',
              backgroundColor: 'var(--color-primary)',
              color: '#ffffff',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '1.75rem',
              marginBottom: '0.75rem',
              boxShadow: 'var(--shadow-md)'
            }}
          >
            க
          </div>
          <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)' }}>
            Kanakku (கணக்கு)
          </h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', marginTop: '0.25rem' }}>
            {t('app_tagline')}
          </p>
        </div>

        {/* Emergency Recovery Key Notice Banner */}
        {lastRecoveryKey && (
          <div
            role="dialog"
            aria-labelledby="recovery-key-title"
            style={{
              backgroundColor: '#fffbeb',
              border: '2px solid var(--color-warning)',
              borderRadius: 'var(--radius-lg)',
              padding: '1.25rem',
              marginBottom: '1.5rem',
              boxShadow: 'var(--shadow-md)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#92400e', marginBottom: '0.5rem' }}>
              <ShieldAlert size={20} />
              <strong id="recovery-key-title">{t('emergency_key')}</strong>
            </div>
            <p style={{ fontSize: 'var(--font-size-xs)', color: '#78350f', marginBottom: '0.75rem' }}>
              {t('emergency_key_notice')}
            </p>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.625rem 0.875rem',
                backgroundColor: '#ffffff',
                border: '1px dashed var(--color-warning)',
                borderRadius: 'var(--radius-md)',
                fontFamily: 'monospace',
                fontWeight: 700,
                fontSize: 'var(--font-size-base)',
                letterSpacing: '0.1em',
                marginBottom: '0.75rem'
              }}
            >
              <span>{lastRecoveryKey}</span>
              <button
                type="button"
                onClick={handleCopyKey}
                className="btn btn-outline"
                style={{ minHeight: '32px', padding: '0.2rem 0.5rem', fontSize: 'var(--font-size-xs)' }}
              >
                {isCopied ? <Check size={14} color="green" /> : <Copy size={14} />}
                <span style={{ marginLeft: '4px' }}>{isCopied ? t('copied') : t('copy_key')}</span>
              </button>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={clearLastRecoveryKey}
              style={{ width: '100%' }}
            >
              I have saved my key securely
            </Button>
          </div>
        )}

        {/* Auth Form Card */}
        <div className="card">
          {/* Mode Switch Tabs */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '0.5rem',
              backgroundColor: 'var(--color-bg-subtle)',
              padding: '0.375rem',
              borderRadius: 'var(--radius-md)',
              marginBottom: '1.5rem'
            }}
          >
            <button
              type="button"
              onClick={() => { setMode('login'); setErrorMessage(''); }}
              style={{
                padding: '0.5rem',
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                fontWeight: 700,
                fontSize: 'var(--font-size-sm)',
                cursor: 'pointer',
                backgroundColor: mode === 'login' ? 'var(--color-bg-surface)' : 'transparent',
                color: mode === 'login' ? 'var(--color-primary)' : 'var(--color-text-muted)',
                boxShadow: mode === 'login' ? 'var(--shadow-sm)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              {t('login')}
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setErrorMessage(''); }}
              style={{
                padding: '0.5rem',
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                fontWeight: 700,
                fontSize: 'var(--font-size-sm)',
                cursor: 'pointer',
                backgroundColor: mode === 'register' ? 'var(--color-bg-surface)' : 'transparent',
                color: mode === 'register' ? 'var(--color-primary)' : 'var(--color-text-muted)',
                boxShadow: mode === 'register' ? 'var(--shadow-sm)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              {t('register')}
            </button>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <Alert type="danger" message={errorMessage} />
          )}

          <form onSubmit={handleSubmit} noValidate>
            {mode === 'register' && (
              <>
                <Input
                  label={t('business_name')}
                  name="businessName"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  placeholder={t('business_name_placeholder')}
                  required
                />
                <Input
                  label={t('full_name')}
                  name="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder={t('full_name_placeholder')}
                  required
                />
                <Input
                  label={t('category')}
                  name="category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder={t('category_placeholder')}
                />
              </>
            )}

            <Input
              label={t('phone_number')}
              name="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder={t('phone_placeholder')}
              helperText="E.g. 9876543210 (India +91 is applied automatically)"
              required
            />

            <Input
              label={t('pin_or_password')}
              name="pin"
              type="password"
              inputMode="numeric"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder={t('pin_placeholder')}
              helperText={mode === 'register' ? 'Minimum 4 numeric digits. Plaintext is never saved.' : undefined}
              required
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              style={{ width: '100%', marginTop: '0.75rem' }}
            >
              {mode === 'login' ? t('submit_login') : t('submit_register')}
            </Button>
          </form>

          {/* Quick Switch Link */}
          <div style={{ textAlign: 'center', marginTop: '1.25rem' }}>
            <button
              type="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setErrorMessage(''); }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-primary-light)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {mode === 'login' ? t('no_account') : t('have_account')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
