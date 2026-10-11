import React, { useState } from 'react';
import { useI18n } from '../../context/I18nContext';
import { X, CreditCard, Banknote, QrCode, Building } from 'lucide-react';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Feedback';

export function SupplierPaymentModal({ supplier, isOpen, onClose, onPaymentRecorded }) {
  const { t, formatCurrency } = useI18n();

  const [amount, setAmount] = useState('');
  const [paymentMode, setPaymentMode] = useState('cash');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !supplier) return null;

  const currentDue = parseFloat(supplier.current_balance || '0');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const payVal = parseFloat(amount);
    if (isNaN(payVal) || payVal <= 0) {
      setError('Please enter a valid positive payment amount.');
      return;
    }

    if (payVal > currentDue) {
      setError(`Payment cannot exceed outstanding payable balance of ${formatCurrency(currentDue)}.`);
      return;
    }

    try {
      setLoading(true);
      await onPaymentRecorded(supplier.id, {
        amount: payVal,
        payment_mode: paymentMode,
        notes: notes.trim() || undefined,
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to record payment.');
    } finally {
      setLoading(false);
    }
  };

  const handleFullSettlement = () => {
    setAmount(currentDue.toFixed(2));
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.6)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 999,
        padding: '1rem',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)',
          width: '100%',
          maxWidth: '460px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--color-bg-subtle)',
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 700, color: 'var(--color-text-main)' }}>
              {t('pay_supplier_title')}
            </h3>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
              {supplier.name}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              padding: '0.25rem',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Current Balance Banner */}
        <div
          style={{
            margin: '1.25rem 1.5rem 0',
            padding: '1rem',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--color-warning-soft)',
            border: '1px solid #fde68a',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <span style={{ fontSize: 'var(--font-size-xs)', color: '#92400e', fontWeight: 600 }}>
              {t('supplier_dues')}:
            </span>
            <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: '#b45309' }}>
              {formatCurrency(currentDue)}
            </div>
          </div>
          <button
            type="button"
            onClick={handleFullSettlement}
            style={{
              fontSize: 'var(--font-size-xs)',
              fontWeight: 700,
              backgroundColor: '#ffffff',
              color: '#b45309',
              border: '1px solid #f59e0b',
              borderRadius: 'var(--radius-sm)',
              padding: '0.375rem 0.625rem',
              cursor: 'pointer',
            }}
          >
            Full Pay
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '1.25rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {error && <Alert type="danger" message={error} />}

          <Input
            label={t('payment_amount')}
            type="number"
            step="0.01"
            min="0.01"
            max={currentDue}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            required
            autoFocus
          />

          {/* Payment Method Selector */}
          <div>
            <label style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '0.5rem', display: 'block' }}>
              {t('payment_method')}
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.5rem' }}>
              {[
                { mode: 'cash', label: t('pay_cash'), icon: Banknote },
                { mode: 'upi', label: t('pay_upi'), icon: QrCode },
                { mode: 'bank_transfer', label: t('pay_bank_transfer'), icon: Building },
                { mode: 'card', label: t('pay_card'), icon: CreditCard },
              ].map(({ mode, label, icon: Icon }) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setPaymentMode(mode)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '0.25rem',
                    padding: '0.5rem 0.25rem',
                    borderRadius: 'var(--radius-md)',
                    border: `1.5px solid ${paymentMode === mode ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    backgroundColor: paymentMode === mode ? 'var(--color-primary-soft)' : '#ffffff',
                    color: paymentMode === mode ? 'var(--color-primary)' : 'var(--color-text-muted)',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                  }}
                >
                  <Icon size={16} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          <Input
            label="Reference / Transaction Note"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Paid via GPay / Cheque No 88910"
          />

          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '0.75rem',
              marginTop: '0.75rem',
              paddingTop: '1rem',
              borderTop: '1px solid var(--color-border)',
            }}
          >
            <Button variant="secondary" onClick={onClose} type="button">
              {t('btn_cancel')}
            </Button>
            <Button variant="primary" type="submit" loading={loading}>
              {t('pay_dues')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
