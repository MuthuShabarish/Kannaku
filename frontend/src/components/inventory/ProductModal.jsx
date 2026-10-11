import React, { useState, useEffect } from 'react';
import { useI18n } from '../../context/I18nContext';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Alert } from '../common/Feedback';
import { X, Package, Plus, Save } from 'lucide-react';
import { api } from '../../services/api';

const STANDARD_UNITS = [
  { value: 'piece', label: 'Piece (pc)' },
  { value: 'kg', label: 'Kilogram (kg)' },
  { value: 'gram', label: 'Gram (g)' },
  { value: 'litre', label: 'Litre (L)' },
  { value: 'box', label: 'Box' },
  { value: 'dozen', label: 'Dozen' },
  { value: 'meter', label: 'Meter (m)' },
];

export function ProductModal({
  isOpen,
  onClose,
  product = null, // if provided, edit mode; else create mode
  categories = [],
  currencySymbol = '₹',
  onSaved,
  onOpenCategoryManager
}) {
  const { t } = useI18n();

  const isEdit = Boolean(product && product.id);

  const [formData, setFormData] = useState({
    name: '',
    tamil_name: '',
    category_id: '',
    sku: '',
    unit: 'piece',
    purchase_cost: '0.00',
    selling_price: '0.00',
    low_stock_threshold: '0.00',
    opening_stock: '0.00',
    opening_stock_cost: '',
    description: '',
    is_active: true
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (product) {
      setFormData({
        name: product.name || '',
        tamil_name: product.tamil_name || '',
        category_id: product.category_id || '',
        sku: product.sku || '',
        unit: product.unit || 'piece',
        purchase_cost: product.purchase_cost != null ? String(product.purchase_cost) : '0.00',
        selling_price: product.selling_price != null ? String(product.selling_price) : '0.00',
        low_stock_threshold: product.low_stock_threshold != null ? String(product.low_stock_threshold) : '0.00',
        opening_stock: '0.00',
        opening_stock_cost: '',
        description: product.description || '',
        is_active: product.is_active ?? true
      });
    } else {
      setFormData({
        name: '',
        tamil_name: '',
        category_id: '',
        sku: '',
        unit: 'piece',
        purchase_cost: '0.00',
        selling_price: '0.00',
        low_stock_threshold: '0.00',
        opening_stock: '0.00',
        opening_stock_cost: '',
        description: '',
        is_active: true
      });
    }
    setError(null);
  }, [product, isOpen]);

  if (!isOpen) return null;

  function handleChange(field, value) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError(t('product_name') + ' is required.');
      return;
    }

    const pCost = parseFloat(formData.purchase_cost) || 0;
    const sPrice = parseFloat(formData.selling_price) || 0;
    const threshold = parseFloat(formData.low_stock_threshold) || 0;

    if (pCost < 0 || sPrice < 0 || threshold < 0) {
      setError('Prices and thresholds cannot be negative.');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      if (isEdit) {
        const payload = {
          name: formData.name.trim(),
          tamil_name: formData.tamil_name.trim() || undefined,
          category_id: formData.category_id || undefined,
          sku: formData.sku.trim() || undefined,
          unit: formData.unit,
          purchase_cost: pCost,
          selling_price: sPrice,
          low_stock_threshold: threshold,
          description: formData.description.trim() || undefined,
          is_active: formData.is_active
        };
        const res = await api.updateProduct(product.id, payload);
        if (onSaved) onSaved(res.data);
      } else {
        const openQty = parseFloat(formData.opening_stock) || 0;
        const openCost = formData.opening_stock_cost ? parseFloat(formData.opening_stock_cost) : undefined;
        const payload = {
          name: formData.name.trim(),
          tamil_name: formData.tamil_name.trim() || undefined,
          category_id: formData.category_id || undefined,
          sku: formData.sku.trim() || undefined,
          unit: formData.unit,
          purchase_cost: pCost,
          selling_price: sPrice,
          low_stock_threshold: threshold,
          opening_stock: openQty,
          opening_stock_cost: openCost,
          description: formData.description.trim() || undefined,
          is_active: formData.is_active
        };
        const res = await api.createProduct(payload);
        if (onSaved) onSaved(res.data);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save product');
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
      zIndex: 1040,
      padding: '1rem'
    }}>
      <div style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderRadius: 'var(--radius-xl)',
        width: '100%',
        maxWidth: '640px',
        maxHeight: '92vh',
        overflowY: 'auto',
        boxShadow: 'var(--shadow-xl)',
        border: '1px solid var(--color-border)'
      }}>
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          backgroundColor: 'var(--color-bg-surface)',
          zIndex: 2
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Package size={22} color="var(--color-primary)" />
            <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: 0, color: 'var(--color-text-main)' }}>
              {isEdit ? t('edit_product') : t('add_product')}
            </h2>
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

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            <Input
              label={t('product_name')}
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder={t('product_name_placeholder')}
              required
            />
            <Input
              label={t('tamil_name')}
              value={formData.tamil_name}
              onChange={(e) => handleChange('tamil_name', e.target.value)}
              placeholder={t('tamil_name_placeholder')}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.375rem' }}>
                <label style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-text-main)' }}>
                  {t('category_label')}
                </label>
                {onOpenCategoryManager && (
                  <button
                    type="button"
                    onClick={onOpenCategoryManager}
                    style={{
                      background: 'none',
                      border: 'none',
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--color-primary)',
                      cursor: 'pointer',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '2px'
                    }}
                  >
                    <Plus size={12} /> {t('add_category')}
                  </button>
                )}
              </div>
              <select
                value={formData.category_id}
                onChange={(e) => handleChange('category_id', e.target.value)}
                style={{
                  width: '100%',
                  minHeight: 'var(--touch-target-min)',
                  padding: '0.625rem 0.875rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: 'var(--color-bg-surface)',
                  color: 'var(--color-text-main)',
                  fontSize: 'var(--font-size-base)'
                }}
              >
                <option value="">-- {t('select_category')} --</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} {c.tamil_name ? `(${c.tamil_name})` : ''}
                  </option>
                ))}
              </select>
            </div>

            <Input
              label={t('sku')}
              value={formData.sku}
              onChange={(e) => handleChange('sku', e.target.value)}
              placeholder={t('sku_placeholder')}
              helperText="Optional, unique identifier within your shop"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: '0.375rem', color: 'var(--color-text-main)' }}>
                {t('unit_label')}
              </label>
              <select
                value={formData.unit}
                onChange={(e) => handleChange('unit', e.target.value)}
                style={{
                  width: '100%',
                  minHeight: 'var(--touch-target-min)',
                  padding: '0.625rem 0.875rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: 'var(--color-bg-surface)',
                  color: 'var(--color-text-main)',
                  fontSize: 'var(--font-size-base)'
                }}
              >
                {STANDARD_UNITS.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
            </div>

            <Input
              label={`${t('purchase_cost')} (${currencySymbol})`}
              type="number"
              step="0.01"
              min="0"
              value={formData.purchase_cost}
              onChange={(e) => handleChange('purchase_cost', e.target.value)}
              required
            />

            <Input
              label={`${t('selling_price')} (${currencySymbol})`}
              type="number"
              step="0.01"
              min="0"
              value={formData.selling_price}
              onChange={(e) => handleChange('selling_price', e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            <Input
              label={t('low_stock_threshold')}
              type="number"
              step="1"
              min="0"
              value={formData.low_stock_threshold}
              onChange={(e) => handleChange('low_stock_threshold', e.target.value)}
              helperText="Alerts you when stock falls to or below this level"
            />

            {!isEdit && (
              <Input
                label={t('opening_stock')}
                type="number"
                step="0.01"
                min="0"
                value={formData.opening_stock}
                onChange={(e) => handleChange('opening_stock', e.target.value)}
                helperText="Initial quantity currently on hand in store"
              />
            )}
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: '0.375rem', color: 'var(--color-text-main)' }}>
              {t('description_label')}
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              rows={2}
              style={{
                width: '100%',
                padding: '0.625rem 0.875rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg-surface)',
                color: 'var(--color-text-main)',
                fontSize: 'var(--font-size-base)',
                resize: 'vertical'
              }}
              placeholder="Notes on packaging, supplier details or specifications..."
            />
          </div>

          {isEdit && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <input
                type="checkbox"
                id="is_active_toggle"
                checked={formData.is_active}
                onChange={(e) => handleChange('is_active', e.target.checked)}
                style={{ width: '18px', height: '18px' }}
              />
              <label htmlFor="is_active_toggle" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-text-main)', cursor: 'pointer' }}>
                {t('active_status')} product (uncheck to deactivate)
              </label>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting} icon={Save}>
              {isEdit ? 'Update Product' : 'Create Product'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
