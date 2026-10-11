import React, { useState } from 'react';
import { useI18n } from '../../context/I18nContext';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Alert } from '../common/Feedback';
import { X, ArrowUpCircle, ArrowDownCircle, CheckCircle } from 'lucide-react';
import { api } from '../../services/api';

const QUICK_REASONS = {
  increase: [
    'Found extra inventory during stock count',
    'Received bonus goods from supplier',
    'Customer returned unused item',
    'Unrecorded spot purchase'
  ],
  decrease: [
    'Damaged or expired inventory',
    'Internal store / operational use',
    'Stock audit missing / discrepancy',
    'Returned defective item to vendor'
  ]
};

export function StockAdjustmentModal({
  isOpen,
  onClose,
  product,
  currencySymbol = '₹',
  onAdjusted
}) {
  const { t } = useI18n();

  const [adjustmentType, setAdjustmentType] = useState('increase'); // 'increase' | 'decrease'
  const [quantity, setQuantity] = useState('');
  const [reason, setReason] = useState('');
  const [unitCost, setUnitCost] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !product) return null;

  const currentStock = parseFloat(product.current_stock) || 0;
  const qty = parseFloat(quantity) || 0;
  const newBalance = adjustmentType === 'increase'
    ? currentStock + qty
    : currentStock - qty;

  const isInvalidDecrease = adjustmentType === 'decrease' && qty > currentStock;

  async function handleSubmit(e) {
    e.preventDefault();

    if (!quantity || qty <= 0) {
      setError('Please specify a quantity greater than zero.');
      return;
    }

    if (isInvalidDecrease) {
      setError(`Cannot decrease stock by ${qty}. Current balance is only ${currentStock} ${product.unit}.`);
      return;
    }

    if (!reason.trim() || reason.trim().length < 3) {
      setError('A valid reason (minimum 3 characters) is required for all stock adjustments.');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const payload = {
        product_id: product.id,
        adjustment_type: adjustmentType,
        quantity: qty,
        reason: reason.trim(),
        unit_cost: unitCost ? parseFloat(unitCost) : undefined
      };

      const res = await api.adjustStock(payload);
      if (onAdjusted) {
        onAdjusted(res.data);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to record stock adjustment');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.65)',
      backdropFilter: 'blur(3px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1045,
      padding: '1rem'
    }}>
      <div style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderRadius: 'var(--radius-xl)',
        width: '100%',
        maxWidth: '520px',
        maxHeight: '92vh',
        overflowY: 'auto',
        boxShadow: 'var(--shadow-xl)',
        border: '1px solid var(--color-border)'
      }}>
        {/* Header */}
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: 0, color: 'var(--color-text-main)' }}>
              {t('adjust_stock')}
            </h2>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
              {product.name} {product.sku ? `(${product.sku})` : ''}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '1.5rem' }}>
          {error && <Alert type="danger" message={error} />}

          {/* Current Stock Banner */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.875rem 1.25rem',
            backgroundColor: 'var(--color-bg-subtle)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border)',
            marginBottom: '1.25rem'
          }}>
            <div>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                {t('stock_balance')}
              </span>
              <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--color-text-main)' }}>
                {currentStock} <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>{product.unit}</span>
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Preview After Adjustment
              </span>
              <div style={{
                fontSize: 'var(--font-size-xl)',
                fontWeight: 700,
                color: isInvalidDecrease ? 'var(--color-danger)' : 'var(--color-accent)'
              }}>
                {qty > 0 ? `${newBalance.toFixed(2)} ${product.unit}` : '—'}
              </div>
            </div>
          </div>

          {/* Adjustment Type Selector */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text-main)' }}>
              {t('adjustment_type')}
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <button
                type="button"
                onClick={() => { setAdjustmentType('increase'); setError(null); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  borderRadius: 'var(--radius-md)',
                  border: `2px solid ${adjustmentType === 'increase' ? 'var(--color-accent)' : 'var(--color-border)'}`,
                  backgroundColor: adjustmentType === 'increase' ? 'var(--color-accent-soft)' : 'transparent',
                  color: adjustmentType === 'increase' ? 'var(--color-accent)' : 'var(--color-text-main)',
                  fontWeight: 700,
                  fontSize: 'var(--font-size-sm)',
                  cursor: 'pointer'
                }}
              >
                <ArrowUpCircle size={18} />
                {t('increase_stock')}
              </button>

              <button
                type="button"
                onClick={() => { setAdjustmentType('decrease'); setError(null); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  borderRadius: 'var(--radius-md)',
                  border: `2px solid ${adjustmentType === 'decrease' ? 'var(--color-danger)' : 'var(--color-border)'}`,
                  backgroundColor: adjustmentType === 'decrease' ? 'var(--color-danger-soft)' : 'transparent',
                  color: adjustmentType === 'decrease' ? 'var(--color-danger)' : 'var(--color-text-main)',
                  fontWeight: 700,
                  fontSize: 'var(--font-size-sm)',
                  cursor: 'pointer'
                }}
              >
                <ArrowDownCircle size={18} />
                {t('decrease_stock')}
              </button>
            </div>
          </div>

          {/* Quantity & Unit Cost */}
          <div style={{ display: 'grid', gridTemplateColumns: adjustmentType === 'increase' ? '1fr 1fr' : '1fr', gap: '1rem', marginBottom: '1.25rem' }}>
            <Input
              label={`${t('quantity_label')} (${product.unit})`}
              type="number"
              step="0.01"
              min="0.01"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="e.g., 5"
              required
            />

            {adjustmentType === 'increase' && (
              <Input
                label={`${t('unit_cost_optional')} (${currencySymbol})`}
                type="number"
                step="0.01"
                min="0"
                value={unitCost}
                onChange={(e) => setUnitCost(e.target.value)}
                placeholder={`Current: ${product.purchase_cost}`}
                helperText="Updates moving average cost"
              />
            )}
          </div>

          {/* Reason Input & Quick Chips */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: '0.375rem', color: 'var(--color-text-main)' }}>
              {t('adjustment_reason')} <span style={{ color: 'var(--color-danger)' }}>*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              required
              placeholder={t('adjustment_reason_placeholder')}
              style={{
                width: '100%',
                padding: '0.625rem 0.875rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg-surface)',
                color: 'var(--color-text-main)',
                fontSize: 'var(--font-size-sm)',
                resize: 'vertical',
                marginBottom: '0.5rem'
              }}
            />

            {/* Quick Chips */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
              {QUICK_REASONS[adjustmentType].map((qr, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setReason(qr)}
                  style={{
                    background: 'var(--color-bg-subtle)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-full)',
                    padding: '0.25rem 0.625rem',
                    fontSize: '11px',
                    color: 'var(--color-text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {qr}
                </button>
              ))}
            </div>
          </div>

          {/* Modal Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant={adjustmentType === 'increase' ? 'primary' : 'danger'}
              isLoading={isSubmitting}
              disabled={isInvalidDecrease || !qty}
              icon={CheckCircle}
            >
              {t('save_adjustment')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
