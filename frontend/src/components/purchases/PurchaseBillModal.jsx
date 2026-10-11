import React from 'react';
import { useI18n } from '../../context/I18nContext';
import { useAuth } from '../../context/AuthContext';
import { Printer, X, CheckCircle, Clock } from 'lucide-react';
import { Button } from '../common/Button';

export function PurchaseBillModal({ purchase, onClose }) {
  const { t, formatCurrency } = useI18n();
  const { business } = useAuth();

  if (!purchase) return null;

  const handlePrint = () => {
    window.print();
  };

  const formattedDate = new Date(purchase.purchase_date || purchase.created_at).toLocaleString();

  return (
    <div
      className="purchase-modal-overlay"
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
        className="purchase-modal-container"
        style={{
          backgroundColor: '#ffffff',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)',
          width: '100%',
          maxWidth: '520px',
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
              {t('view_bill')} — {purchase.invoice_number}
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

        {/* Printable Purchase Voucher Body */}
        <div
          className="printable-purchase"
          style={{
            padding: '1.5rem',
            overflowY: 'auto',
            flex: 1,
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-main)',
            fontFamily: 'var(--font-family-base)',
          }}
        >
          {/* Voucher Header */}
          <div style={{ textAlign: 'center', marginBottom: '1.25rem', borderBottom: '2px dashed var(--color-border)', paddingBottom: '1rem' }}>
            <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 800, color: 'var(--color-primary)' }}>
              {business?.name || 'Kanakku Store'}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-accent)', marginTop: '0.25rem', textTransform: 'uppercase' }}>
              Goods Received Voucher (கொள்முதல் ரசீது)
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)', marginTop: '0.25rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}>
              <Clock size={12} /> {formattedDate}
            </div>
          </div>

          {/* Invoice Meta */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', fontSize: 'var(--font-size-xs)' }}>
            <div>
              <span style={{ color: 'var(--color-text-muted)' }}>Voucher No: </span>
              <strong>{purchase.invoice_number}</strong>
              {purchase.supplier_invoice_ref && (
                <div style={{ color: 'var(--color-text-muted)', marginTop: '0.125rem' }}>
                  Supplier Ref: <strong>{purchase.supplier_invoice_ref}</strong>
                </div>
              )}
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Payment Mode: </span>
              <strong style={{ textTransform: 'uppercase', color: 'var(--color-primary)' }}>{purchase.payment_method}</strong>
            </div>
          </div>

          {purchase.supplier_name && (
            <div style={{ backgroundColor: 'var(--color-bg-subtle)', padding: '0.625rem 0.875rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: 'var(--font-size-xs)' }}>
              <div style={{ fontWeight: 700, color: 'var(--color-text-main)' }}>
                Supplier: {purchase.supplier_name}
              </div>
              {purchase.supplier_phone && <div style={{ color: 'var(--color-text-muted)' }}>Phone: {purchase.supplier_phone}</div>}
            </div>
          )}

          {/* Itemized Table */}
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1.25rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', textAlign: 'left' }}>
                <th style={{ paddingBottom: '0.5rem' }}>{t('item')}</th>
                <th style={{ paddingBottom: '0.5rem', textAlign: 'center' }}>{t('qty')}</th>
                <th style={{ paddingBottom: '0.5rem', textAlign: 'right' }}>Unit Cost</th>
                <th style={{ paddingBottom: '0.5rem', textAlign: 'right' }}>Landed Cost</th>
                <th style={{ paddingBottom: '0.5rem', textAlign: 'right' }}>Total</th>
              </tr>
            </thead>
            <tbody>
              {purchase.items?.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: '1px dotted #f1f5f9' }}>
                  <td style={{ padding: '0.5rem 0' }}>
                    <div style={{ fontWeight: 600 }}>{item.product_name}</div>
                    {item.discount_amount > 0 && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--color-accent)' }}>
                        Line Disc: -{formatCurrency(item.discount_amount)}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '0.5rem 0', textAlign: 'center' }}>
                    {parseFloat(item.quantity).toFixed(2)} {item.unit}
                  </td>
                  <td style={{ padding: '0.5rem 0', textAlign: 'right' }}>
                    {formatCurrency(item.unit_cost)}
                  </td>
                  <td style={{ padding: '0.5rem 0', textAlign: 'right', color: 'var(--color-primary)', fontWeight: 600 }}>
                    {formatCurrency(item.effective_unit_cost)}
                  </td>
                  <td style={{ padding: '0.5rem 0', textAlign: 'right', fontWeight: 600 }}>
                    {formatCurrency(item.total_cost)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pricing Summary */}
          <div style={{ borderTop: '2px dashed var(--color-border)', paddingTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-muted)' }}>
              <span>{t('subtotal')}:</span>
              <span>{formatCurrency(purchase.subtotal_amount)}</span>
            </div>

            {parseFloat(purchase.discount_amount) > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-accent)' }}>
                <span>Bill Discount:</span>
                <span>-{formatCurrency(purchase.discount_amount)}</span>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-base)', fontWeight: 800, color: 'var(--color-text-main)', borderTop: '1px solid var(--color-border)', paddingTop: '0.5rem', marginTop: '0.25rem' }}>
              <span>{t('purchase_total')}:</span>
              <span style={{ color: 'var(--color-primary)' }}>{formatCurrency(purchase.total_amount)}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              <span>Amount Paid:</span>
              <span>{formatCurrency(purchase.paid_amount)}</span>
            </div>

            {parseFloat(purchase.credit_amount) > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-warning)' }}>
                <span>Remaining Payable (Dues):</span>
                <span>{formatCurrency(purchase.credit_amount)}</span>
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
                  backgroundColor: purchase.payment_status === 'paid' ? 'var(--color-accent-soft)' : 'var(--color-warning-soft)',
                  color: purchase.payment_status === 'paid' ? 'var(--color-accent)' : '#b45309',
                  textTransform: 'uppercase'
                }}
              >
                {purchase.payment_status}
              </span>
            </div>
          </div>

          {/* Footer Note */}
          <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
            <div>Stock received and updated into moving-average inventory.</div>
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
            {t('btn_close')}
          </Button>
          <Button variant="primary" onClick={handlePrint} icon={Printer}>
            Print Voucher
          </Button>
        </div>
      </div>

      {/* Print Specific Styling */}
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .printable-purchase, .printable-purchase * {
            visibility: visible;
          }
          .printable-purchase {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            padding: 0;
          }
          .purchase-modal-overlay {
            background: none !important;
            padding: 0 !important;
          }
        }
      `}</style>
    </div>
  );
}
