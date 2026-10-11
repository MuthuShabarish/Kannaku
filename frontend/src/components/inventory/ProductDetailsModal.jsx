import React, { useState, useEffect } from 'react';
import { useI18n } from '../../context/I18nContext';
import { Button } from '../common/Button';
import { Badge, LoadingSpinner, Alert } from '../common/Feedback';
import { X, Sliders, Edit, History, ArrowUpRight, ArrowDownRight, Package } from 'lucide-react';
import { api } from '../../services/api';

export function ProductDetailsModal({
  isOpen,
  onClose,
  productId,
  currencySymbol = '₹',
  onOpenAdjustment,
  onOpenEdit
}) {
  const { t } = useI18n();
  const [product, setProduct] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadDetail = useCallback(async () => {
    if (!productId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getProduct(productId);
      setProduct(res.data);
    } catch (err) {
      setError(err.message || 'Failed to load product details');
    } finally {
      setIsLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    if (isOpen && productId) {
      loadDetail();
    }
  }, [isOpen, productId, loadDetail]);

  if (!isOpen) return null;

  const cost = parseFloat(product?.purchase_cost) || 0;
  const price = parseFloat(product?.selling_price) || 0;
  const margin = price > 0 ? (((price - cost) / price) * 100).toFixed(1) : 0;
  const stock = parseFloat(product?.current_stock) || 0;

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
        maxWidth: '720px',
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
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          backgroundColor: 'var(--color-bg-surface)',
          zIndex: 2
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <div style={{ width: '38px', height: '38px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-primary-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-primary)' }}>
              <Package size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: 0, color: 'var(--color-text-main)' }}>
                {product?.name || t('product_details')}
              </h2>
              {product?.tamil_name && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  {product.tamil_name}
                </div>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
          >
            <X size={20} />
          </button>
        </div>

        {isLoading ? (
          <LoadingSpinner label="Loading product specifications & history..." />
        ) : error ? (
          <div style={{ padding: '1.5rem' }}>
            <Alert type="danger" message={error} />
          </div>
        ) : product ? (
          <div style={{ padding: '1.5rem' }}>
            {/* Top Status & Metrics Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: '1rem',
              padding: '1rem',
              backgroundColor: 'var(--color-bg-subtle)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
              marginBottom: '1.5rem'
            }}>
              <div>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                  {t('stock_balance')}
                </span>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--color-text-main)', marginTop: '2px' }}>
                  {stock} <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 500 }}>{product.unit}</span>
                </div>
                <div style={{ marginTop: '4px' }}>
                  <Badge variant={product.stock_status === 'out_of_stock' ? 'neutral' : product.stock_status === 'low_stock' ? 'warning' : 'success'}>
                    {product.stock_status === 'out_of_stock'
                      ? t('status_out_of_stock')
                      : product.stock_status === 'low_stock'
                      ? t('status_low_stock')
                      : t('status_in_stock')}
                  </Badge>
                </div>
              </div>

              <div>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                  {t('selling_price')}
                </span>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--color-accent)', marginTop: '2px' }}>
                  {currencySymbol}{Number(price).toFixed(2)}
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  Cost: {currencySymbol}{Number(cost).toFixed(2)}
                </div>
              </div>

              <div>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                  Gross Margin
                </span>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: margin > 0 ? 'var(--color-primary)' : 'var(--color-text-muted)', marginTop: '2px' }}>
                  {margin}%
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  Profit: {currencySymbol}{(price - cost).toFixed(2)}
                </div>
              </div>

              <div>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                  {t('sku')}
                </span>
                <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-text-main)', marginTop: '4px', fontFamily: 'monospace' }}>
                  {product.sku || '—'}
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  {product.category_name || 'Uncategorized'}
                </div>
              </div>
            </div>

            {/* Quick Actions Bar */}
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
              <Button
                variant="primary"
                icon={Sliders}
                onClick={() => {
                  if (onOpenAdjustment) onOpenAdjustment(product);
                }}
              >
                {t('adjust_stock')}
              </Button>
              <Button
                variant="outline"
                icon={Edit}
                onClick={() => {
                  if (onOpenEdit) onOpenEdit(product);
                }}
              >
                {t('edit_product')}
              </Button>
            </div>

            {/* Product Metadata Table */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
                Specifications
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.5rem', fontSize: 'var(--font-size-sm)' }}>
                <div><span style={{ color: 'var(--color-text-muted)' }}>Low Stock Alert:</span> <strong>{product.low_stock_threshold} {product.unit}</strong></div>
                <div><span style={{ color: 'var(--color-text-muted)' }}>Status:</span> <strong>{product.is_active ? t('active_status') : t('inactive_status')}</strong></div>
                {product.description && (
                  <div style={{ gridColumn: '1 / -1', marginTop: '0.25rem' }}>
                    <span style={{ color: 'var(--color-text-muted)' }}>Description:</span> {product.description}
                  </div>
                )}
              </div>
            </div>

            {/* Stock Movement Audit Ledger */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <History size={16} color="var(--color-primary)" />
                <h3 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                  {t('recent_movements')}
                </h3>
              </div>

              {(!product.recent_movements || product.recent_movements.length === 0) ? (
                <div style={{ textAlign: 'center', padding: '1.5rem', backgroundColor: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                  {t('no_movements_yet')}
                </div>
              ) : (
                <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
                    <thead>
                      <tr style={{ backgroundColor: 'var(--color-bg-subtle)', borderBottom: '1px solid var(--color-border)', textAlign: 'left' }}>
                        <th style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>{t('movement_date')}</th>
                        <th style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>{t('movement_type')}</th>
                        <th style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textAlign: 'right' }}>{t('quantity_delta')}</th>
                        <th style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textAlign: 'right' }}>{t('balance_after')}</th>
                        <th style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>{t('adjustment_reason')}</th>
                        <th style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>{t('responsible_user')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {product.recent_movements.map((m) => {
                        const isPos = parseFloat(m.quantity_delta) >= 0;
                        return (
                          <tr key={m.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                            <td style={{ padding: '0.625rem 0.75rem', whiteSpace: 'nowrap', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                              {new Date(m.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem' }}>
                              <Badge variant={m.movement_type === 'opening' ? 'primary' : isPos ? 'success' : 'neutral'}>
                                {m.movement_type.replace('_', ' ')}
                              </Badge>
                            </td>
                            <td style={{
                              padding: '0.625rem 0.75rem',
                              textAlign: 'right',
                              fontWeight: 700,
                              color: isPos ? 'var(--color-accent)' : 'var(--color-danger)'
                            }}>
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                                {isPos ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                                {isPos ? `+${m.quantity_delta}` : m.quantity_delta}
                              </span>
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem', textAlign: 'right', fontWeight: 600 }}>
                              {m.balance_after}
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-text-main)', maxWidth: '200px' }}>
                              {m.reason || '—'}
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                              {m.created_by_user_name || 'System / Owner'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : null}

        <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'flex-end' }}>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
