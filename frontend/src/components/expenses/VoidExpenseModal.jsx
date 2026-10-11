import React, { useState } from 'react';
import { useI18n } from '../../context/I18nContext';
import { api } from '../../services/api';
import { Button } from '../common/Button';
import { AlertCircle, X, Trash2 } from 'lucide-react';

export function VoidExpenseModal({ isOpen, onClose, onSuccess, expense }) {
  const { t, formatCurrency } = useI18n();

  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !expense) return null;

  const handleVoid = async (e) => {
    e.preventDefault();
    setError(null);

    if (!reason.trim()) {
      setError('Please provide an audit reason for voiding this expense');
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await api.voidExpense(expense.id, {
        reason: reason.trim(),
      });

      if (res.success) {
        onSuccess(res.data);
        onClose();
      } else {
        setError(res.error?.message || 'Failed to void expense');
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '480px',
          padding: '1.75rem',
          backgroundColor: 'var(--color-bg-surface)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-xl)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-danger)' }}>
            <Trash2 size={22} />
            <h2 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 800 }}>
              {t('void_expense_title')}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div
            style={{
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--color-danger-soft)',
              color: 'var(--color-danger)',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: 'var(--font-size-sm)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Voucher:</span>
            <span style={{ fontWeight: 700 }}>{expense.expense_number}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Amount:</span>
            <span style={{ fontWeight: 800, color: 'var(--color-danger)' }}>{formatCurrency(expense.amount)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Description:</span>
            <span style={{ fontWeight: 600 }}>{expense.description}</span>
          </div>
        </div>

        <p style={{ margin: '0 0 1rem', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
          {t('void_confirm_desc')}
        </p>

        <form onSubmit={handleVoid} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 700, marginBottom: '0.375rem' }}>
              {t('void_reason')} *
            </label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Duplicate entry or incorrect amount recorded"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              style={{ width: '100%', padding: '0.625rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
              {t('close_receipt')}
            </Button>
            <Button variant="danger" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Voiding...' : t('void_btn')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
