import React, { useState, useEffect } from 'react';
import { useI18n } from '../../context/I18nContext';
import { X, Building2, Phone, Mail, MapPin, FileText } from 'lucide-react';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Feedback';

export function SupplierModal({ supplier, isOpen, onClose, onSave }) {
  const { t } = useI18n();

  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
    notes: '',
  });

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (supplier) {
      setFormData({
        name: supplier.name || '',
        phone: supplier.phone || '',
        email: supplier.email || '',
        address: supplier.address || '',
        notes: supplier.notes || '',
      });
    } else {
      setFormData({
        name: '',
        phone: '',
        email: '',
        address: '',
        notes: '',
      });
    }
    setError(null);
  }, [supplier, isOpen]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.name.trim()) {
      setError('Supplier name is required.');
      return;
    }

    try {
      setLoading(true);
      await onSave({
        name: formData.name.trim(),
        phone: formData.phone.trim() || null,
        email: formData.email.trim() || null,
        address: formData.address.trim() || null,
        notes: formData.notes.trim() || null,
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save supplier.');
    } finally {
      setLoading(false);
    }
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
          maxWidth: '520px',
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Building2 size={22} color="var(--color-primary)" />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 700, color: 'var(--color-text-main)' }}>
              {supplier ? t('edit_supplier') : t('add_supplier')}
            </h3>
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {error && <Alert type="danger" message={error} />}

          <Input
            label={t('supplier_name')}
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="e.g. Tata Steel Mills / Lakshmi Traders"
            required
            autoFocus
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label={t('supplier_phone')}
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              placeholder="e.g. 9876543210"
              icon={Phone}
            />

            <Input
              label={t('supplier_email')}
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="vendor@company.com"
              icon={Mail}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            <label style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-text-main)' }}>
              {t('supplier_address')}
            </label>
            <textarea
              name="address"
              value={formData.address}
              onChange={handleChange}
              rows={2}
              placeholder="Street, City, Pincode"
              style={{
                width: '100%',
                padding: '0.625rem 0.875rem',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--font-size-sm)',
                fontFamily: 'inherit',
                outline: 'none',
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            <label style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-text-main)' }}>
              {t('supplier_notes')}
            </label>
            <input
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              placeholder="e.g. Net 30 payment terms, 2% cash discount"
              style={{
                width: '100%',
                padding: '0.625rem 0.875rem',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--font-size-sm)',
                fontFamily: 'inherit',
                outline: 'none',
              }}
            />
          </div>

          {/* Actions */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '0.75rem',
              marginTop: '1rem',
              paddingTop: '1rem',
              borderTop: '1px solid var(--color-border)',
            }}
          >
            <Button variant="secondary" onClick={onClose} type="button">
              {t('btn_cancel')}
            </Button>
            <Button variant="primary" type="submit" loading={loading}>
              {t('btn_save')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
