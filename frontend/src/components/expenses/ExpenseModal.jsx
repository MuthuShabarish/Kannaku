import React, { useState } from 'react';
import { useI18n } from '../../context/I18nContext';
import { api } from '../../services/api';
import { Button } from '../common/Button';
import { AlertCircle, X, Banknote, QrCode, CreditCard, Building } from 'lucide-react';

export function ExpenseModal({ isOpen, onClose, onSuccess, categories = [] }) {
  const { t } = useI18n();

  const [categoryId, setCategoryId] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [payee, setPayee] = useState('');
  const [description, setDescription] = useState('');
  const [referenceNumber, setReferenceNumber] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!categoryId) {
      setError('Please select an expense category');
      return;
    }
    const parsedAmount = parseFloat(amount);
    if (!parsedAmount || parsedAmount <= 0) {
      setError('Please enter a valid expense amount greater than zero');
      return;
    }
    if (!description.trim()) {
      setError('Please enter a description or purpose for the expense');
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await api.createExpense({
        category_id: categoryId,
        amount: parsedAmount.toFixed(4),
        payment_method: paymentMethod,
        payment_status: 'paid',
        payee: payee.trim() || undefined,
        description: description.trim(),
        reference_number: referenceNumber.trim() || undefined,
      });

      if (res.success) {
        onSuccess(res.data);
        onClose();
      } else {
        setError(res.error?.message || 'Failed to record expense');
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  const paymentMethods = [
    { id: 'cash', label: t('pay_cash'), icon: Banknote },
    { id: 'upi', label: t('pay_upi'), icon: QrCode },
    { id: 'card', label: t('pay_card'), icon: CreditCard },
    { id: 'bank_transfer', label: t('pay_bank_transfer'), icon: Building },
  ];

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
          maxWidth: '520px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '1.75rem',
          backgroundColor: 'var(--color-bg-surface)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-xl)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h2 style={{ margin: 0, fontSize: 'var(--font-size-xl)', fontWeight: 800, color: 'var(--color-primary-dark)' }}>
            {t('add_expense_btn')}
          </h2>
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

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Category Dropdown */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 700, marginBottom: '0.375rem' }}>
              {t('category')} *
            </label>
            <select
              className="input"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              required
              style={{ width: '100%', padding: '0.625rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
            >
              <option value="">-- {t('category')} --</option>
              {categories.filter((c) => c.is_active).map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Amount Input */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 700, marginBottom: '0.375rem' }}>
              {t('amount')} (₹) *
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              className="input"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '0.625rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                fontSize: 'var(--font-size-lg)',
                fontWeight: 700,
              }}
            />
          </div>

          {/* Payment Method Selector */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 700, marginBottom: '0.375rem' }}>
              {t('payment_method')} *
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
              {paymentMethods.map((pm) => {
                const Icon = pm.icon;
                const isSelected = paymentMethod === pm.id;
                return (
                  <button
                    key={pm.id}
                    type="button"
                    onClick={() => setPaymentMethod(pm.id)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.25rem',
                      padding: '0.5rem',
                      borderRadius: 'var(--radius-md)',
                      border: `2px solid ${isSelected ? 'var(--color-primary)' : 'var(--color-border)'}`,
                      backgroundColor: isSelected ? 'var(--color-primary-soft)' : 'var(--color-bg-surface)',
                      color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)',
                      cursor: 'pointer',
                      fontSize: 'var(--font-size-xs)',
                      fontWeight: 600,
                    }}
                  >
                    <Icon size={18} />
                    <span>{pm.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Description */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 700, marginBottom: '0.375rem' }}>
              {t('purpose_desc')} *
            </label>
            <textarea
              className="input"
              rows={2}
              placeholder="e.g. October shop rent or EB electricity bill"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              style={{ width: '100%', padding: '0.625rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
            />
          </div>

          {/* Payee / Vendor */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 700, marginBottom: '0.375rem' }}>
              {t('payee')} (Optional)
            </label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Building Owner or Electricity Board"
              value={payee}
              onChange={(e) => setPayee(e.target.value)}
              style={{ width: '100%', padding: '0.625rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
            />
          </div>

          {/* Receipt / Voucher / UTR Ref */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 700, marginBottom: '0.375rem' }}>
              {t('voucher_ref')} (Optional)
            </label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Receipt #, UTR #, or Cheque #"
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
              style={{ width: '100%', padding: '0.625rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
            />
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
              {t('close_receipt')}
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? t('saving_expense') : t('save_expense_btn')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
