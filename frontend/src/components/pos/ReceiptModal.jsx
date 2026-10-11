import React from 'react';
import { useI18n } from '../../context/I18nContext';
import { useAuth } from '../../context/AuthContext';
import { Printer, X, CheckCircle, Clock } from 'lucide-react';
import { Button } from '../common/Button';

export function ReceiptModal({ sale, onClose }) {
  const { t, formatCurrency } = useI18n();
  const { business } = useAuth();

  if (!sale) return null;

  const handlePrint = () => {
    window.print();
  };

  const formattedDate = new Date(sale.created_at).toLocaleString();

  return (
    <div
      className="receipt-modal-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="receipt-modal-container"
        style={{
          backgroundColor: '#ffffff',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)',
          width: '100%',
          maxWidth: '480px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--color-bg-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={20} color="var(--color-accent)" />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 700, color: 'var(--color-text-main)' }}>
              {t('view_receipt')} — {sale.invoice_number}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              display: 'flex',
              padding: '0.25rem',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Printable Receipt Body */}
        <div
          className="printable-receipt"
          style={{
            padding: '1.5rem',
            overflowY: 'auto',
            flex: 1,
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-main)',
            fontFamily: 'var(--font-family-base)',
          }}
        >
          {/* Shop Header */}
          <div style={{ textAlign: 'center', marginBottom: '1.25rem', borderBottom: '2px dashed var(--color-border)', paddingBottom: '1rem' }}>
            <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 800, color: 'var(--color-primary)' }}>
              {business?.name || 'Kanakku Store'}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
              {business?.category ? `${business.category.toUpperCase()} • ` : ''}Retail Billing
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)', marginTop: '0.25rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}>
              <Clock size={12} /> {formattedDate}
            </div>
          </div>

          {/* Invoice Meta */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', fontSize: 'var(--font-size-xs)' }}>
            <div>
              <span style={{ color: 'var(--color-text-muted)' }}>{t('invoice_number')}: </span>
              <strong>{sale.invoice_number}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--color-text-muted)' }}>Payment: </span>
              <strong style={{ textTransform: 'uppercase', color: 'var(--color-primary)' }}>{sale.payment_method}</strong>
            </div>
          </div>

          {sale.customer_name && (
            <div style={{ backgroundColor: 'var(--color-primary-soft)', padding: '0.625rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: 'var(--font-size-xs)' }}>
              <div style={{ fontWeight: 700, color: 'var(--color-primary)' }}>
                {t('billed_to')}: {sale.customer_name}
              </div>
              {sale.customer_phone && <div style={{ color: 'var(--color-text-muted)' }}>Phone: {sale.customer_phone}</div>}
            </div>
          )}

          {/* Itemized Table */}
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1.25rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', textAlign: 'left' }}>
                <th style={{ paddingBottom: '0.5rem' }}>{t('item')}</th>
                <th style={{ paddingBottom: '0.5rem', textAlign: 'center' }}>{t('qty')}</th>
                <th style={{ paddingBottom: '0.5rem', textAlign: 'right' }}>{t('rate')}</th>
                <th style={{ paddingBottom: '0.5rem', textAlign: 'right' }}>{t('amount')}</th>
              </tr>
            </thead>
            <tbody>
              {sale.items?.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: '1px dotted #f1f5f9' }}>
                  <td style={{ padding: '0.5rem 0' }}>
                    <div style={{ fontWeight: 600 }}>{item.product_name}</div>
                    {item.discount_amount > 0 && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--color-accent)' }}>
                        Disc: -{formatCurrency(item.discount_amount)}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '0.5rem 0', textAlign: 'center' }}>
                    {parseFloat(item.quantity).toFixed(2)} {item.unit}
                  </td>
                  <td style={{ padding: '0.5rem 0', textAlign: 'right' }}>
                    {formatCurrency(item.unit_price)}
                  </td>
                  <td style={{ padding: '0.5rem 0', textAlign: 'right', fontWeight: 600 }}>
                    {formatCurrency(item.total_price)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pricing Summary */}
          <div style={{ borderTop: '2px dashed var(--color-border)', paddingTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-muted)' }}>
              <span>{t('subtotal')}:</span>
              <span>{formatCurrency(sale.subtotal_amount)}</span>
            </div>

            {parseFloat(sale.discount_amount) > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-accent)' }}>
                <span>{t('discount')}:</span>
                <span>-{formatCurrency(sale.discount_amount)}</span>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-base)', fontWeight: 800, color: 'var(--color-text-main)', borderTop: '1px solid var(--color-border)', paddingTop: '0.5rem', marginTop: '0.25rem' }}>
              <span>{t('total')}:</span>
              <span style={{ color: 'var(--color-primary)' }}>{formatCurrency(sale.total_amount)}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              <span>{t('paid_amount')}:</span>
              <span>{formatCurrency(sale.paid_amount)}</span>
            </div>

            {parseFloat(sale.credit_amount) > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-warning)' }}>
                <span>{t('credit_amount')}:</span>
                <span>{formatCurrency(sale.credit_amount)}</span>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', marginTop: '0.25rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Status:</span>
              <span
                style={{
                  padding: '0.125rem 0.5rem',
                  borderRadius: 'var(--radius-full)',
                  fontWeight: 700,
                  fontSize: '0.7rem',
                  backgroundColor: sale.payment_status === 'paid' ? 'var(--color-accent-soft)' : 'var(--color-danger-soft)',
                  color: sale.payment_status === 'paid' ? 'var(--color-accent)' : 'var(--color-danger)',
                  textTransform: 'uppercase'
                }}
              >
                {sale.payment_status}
              </span>
            </div>
          </div>

          {/* Footer Thank You */}
          <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
            <div>நன்றி! மீண்டும் வருக! / Thank you, visit again!</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)', marginTop: '0.25rem' }}>
              Powered by Kanakku (கணக்கு)
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderTop: '1px solid var(--color-border)',
            display: 'flex',
            gap: '0.75rem',
            justifyContent: 'flex-end',
            backgroundColor: 'var(--color-bg-subtle)',
          }}
        >
          <Button variant="secondary" onClick={onClose}>
            {t('close_receipt')}
          </Button>
          <Button variant="primary" onClick={handlePrint} icon={Printer}>
            {t('print_receipt')}
          </Button>
        </div>
      </div>

      {/* Print Specific Styling */}
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .printable-receipt, .printable-receipt * {
            visibility: visible;
          }
          .printable-receipt {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            padding: 0;
          }
          .receipt-modal-overlay {
            background: none !important;
            padding: 0 !important;
          }
        }
      `}</style>
    </div>
  );
}
