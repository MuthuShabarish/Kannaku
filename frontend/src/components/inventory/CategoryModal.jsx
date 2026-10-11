import React, { useState } from 'react';
import { useI18n } from '../../context/I18nContext';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Alert } from '../common/Feedback';
import { X, Plus, FolderPlus, Tag } from 'lucide-react';
import { api } from '../../services/api';

export function CategoryModal({ isOpen, onClose, categories = [], onCategoryCreated }) {
  const { t } = useI18n();
  const [name, setName] = useState('');
  const [tamilName, setTamilName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) {
      setError('Category name is required.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const res = await api.createCategory({
        name: name.trim(),
        tamil_name: tamilName.trim() || undefined,
        display_order: categories.length + 1
      });
      setName('');
      setTamilName('');
      if (onCategoryCreated) {
        onCategoryCreated(res.data);
      }
    } catch (err) {
      setError(err.message || 'Failed to create category');
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
      zIndex: 1050,
      padding: '1rem'
    }}>
      <div style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderRadius: 'var(--radius-xl)',
        width: '100%',
        maxWidth: '480px',
        maxHeight: '90vh',
        overflowY: 'auto',
        boxShadow: 'var(--shadow-xl)',
        border: '1px solid var(--color-border)'
      }}>
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FolderPlus size={20} color="var(--color-primary)" />
            <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: 0, color: 'var(--color-text-main)' }}>
              {t('manage_categories')}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ padding: '1.5rem' }}>
          {error && <Alert type="danger" message={error} />}

          <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
            <Input
              label={t('new_category_name')}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Dairy, Spices, Hardware..."
              required
            />
            <Input
              label={t('tamil_name')}
              value={tamilName}
              onChange={(e) => setTamilName(e.target.value)}
              placeholder="e.g., மளிகை பொருட்கள்..."
            />
            <Button type="submit" variant="primary" isLoading={isSubmitting} icon={Plus}>
              {t('add_category')}
            </Button>
          </form>

          <div>
            <h3 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.75rem' }}>
              {t('all_categories')} ({categories.length})
            </h3>
            {categories.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                No categories yet. Add one above!
              </div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {categories.map((c) => (
                  <div
                    key={c.id}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.375rem',
                      padding: '0.375rem 0.75rem',
                      borderRadius: 'var(--radius-full)',
                      backgroundColor: 'var(--color-bg-subtle)',
                      border: '1px solid var(--color-border)',
                      fontSize: 'var(--font-size-sm)',
                      color: 'var(--color-text-main)'
                    }}
                  >
                    <Tag size={14} color="var(--color-text-muted)" />
                    <span style={{ fontWeight: 600 }}>{c.name}</span>
                    {c.tamil_name && <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>({c.tamil_name})</span>}
                    <span style={{
                      backgroundColor: 'var(--color-primary-soft)',
                      color: 'var(--color-primary)',
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: '8px'
                    }}>
                      {c.product_count || 0}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'flex-end' }}>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
