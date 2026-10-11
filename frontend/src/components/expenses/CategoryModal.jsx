import React, { useState } from 'react';
import { useI18n } from '../../context/I18nContext';
import { api } from '../../services/api';
import { Button } from '../common/Button';
import { Badge } from '../common/Feedback';
import { X, Plus, AlertCircle, Check } from 'lucide-react';

export function CategoryModal({ isOpen, onClose, categories = [], onRefresh }) {
  const { t } = useI18n();

  const [isAdding, setIsAdding] = useState(false);
  const [newCatName, setNewCatName] = useState('');
  const [newCatDesc, setNewCatDesc] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(null);

    if (!newCatName.trim()) {
      setError('Please enter a category name');
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await api.createExpenseCategory({
        name: newCatName.trim(),
        description: newCatDesc.trim() || undefined,
      });

      if (res.success) {
        setNewCatName('');
        setNewCatDesc('');
        setIsAdding(false);
        onRefresh();
      } else {
        setError(res.error?.message || 'Failed to create category');
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (category) => {
    try {
      await api.updateExpenseCategory(category.id, {
        is_active: !category.is_active,
      });
      onRefresh();
    } catch (err) {
      console.error('Failed to toggle category active status:', err);
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
          maxWidth: '560px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          padding: '1.75rem',
          backgroundColor: 'var(--color-bg-surface)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-xl)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 'var(--font-size-xl)', fontWeight: 800, color: 'var(--color-primary-dark)' }}>
              {t('manage_categories_btn')}
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              Operating overhead categories tailored to your business
            </p>
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

        {/* Add Category Section */}
        {isAdding ? (
          <form
            onSubmit={handleCreate}
            style={{
              padding: '1rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-bg-subtle)',
              marginBottom: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)' }}>New Operating Category</div>
            <div>
              <input
                type="text"
                className="input"
                placeholder={t('category_name') + ' (e.g. Tea & Refreshments)'}
                value={newCatName}
                onChange={(e) => setNewCatName(e.target.value)}
                required
                style={{ width: '100%', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}
              />
            </div>
            <div>
              <input
                type="text"
                className="input"
                placeholder={t('category_desc') + ' (Optional)'}
                value={newCatDesc}
                onChange={(e) => setNewCatDesc(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <Button size="small" variant="outline" type="button" onClick={() => setIsAdding(false)}>
                Cancel
              </Button>
              <Button size="small" variant="primary" type="submit" disabled={isSubmitting}>
                <Check size={16} /> Save Category
              </Button>
            </div>
          </form>
        ) : (
          <div style={{ marginBottom: '1rem' }}>
            <Button size="small" variant="outline" onClick={() => setIsAdding(true)}>
              <Plus size={16} /> Add Custom Category
            </Button>
          </div>
        )}

        {/* Categories List */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {categories.map((cat) => (
            <div
              key={cat.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: cat.is_active ? 'var(--color-bg-surface)' : 'var(--color-bg-subtle)',
                opacity: cat.is_active ? 1 : 0.6,
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)' }}>{cat.name}</span>
                  {cat.is_system_default ? (
                    <Badge variant="neutral">{t('system_category')}</Badge>
                  ) : (
                    <Badge variant="accent">{t('custom_category')}</Badge>
                  )}
                </div>
                {cat.description && (
                  <p style={{ margin: '0.2rem 0 0', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    {cat.description}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => handleToggleActive(cat)}
                style={{
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  padding: '0.25rem 0.5rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: 'transparent',
                  cursor: 'pointer',
                  color: cat.is_active ? 'var(--color-text-muted)' : 'var(--color-primary)',
                }}
              >
                {cat.is_active ? 'Deactivate' : 'Activate'}
              </button>
            </div>
          ))}
        </div>

        <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end' }}>
          <Button variant="primary" onClick={onClose}>
            {t('close_receipt')}
          </Button>
        </div>
      </div>
    </div>
  );
}
