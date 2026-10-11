import React, { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../context/I18nContext';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Badge, LoadingSpinner, Alert, Toast } from '../components/common/Feedback';
import { Button } from '../components/common/Button';
import {
  LockKeyhole,
  LockOpen,
  Banknote,
  CheckCircle2,
  AlertTriangle,
  History,
  Calendar,
  ArrowDownLeft,
  ArrowUpRight,
  ShieldAlert,
  RefreshCw
} from 'lucide-react';

export function CashClosingPage() {
  const { t, formatCurrency } = useI18n();

  // Active Tab: 'closing' | 'history'
  const [activeTab, setActiveTab] = useState('closing');

  // Selected date (defaults to today's local date YYYY-MM-DD)
  const [closingDate, setClosingDate] = useState(() => {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  });

  // State
  const [drawerData, setDrawerData] = useState(null);
  const [historyList, setHistoryList] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [toastMsg, setToastMsg] = useState(null);

  // Form Input
  const [openingCashInput, setOpeningCashInput] = useState('');
  const [actualCashInput, setActualCashInput] = useState('');
  const [notesInput, setNotesInput] = useState('');

  // Confirmation Modal
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // Reopen Modal
  const [showReopenModal, setShowReopenModal] = useState(false);
  const [reopenReason, setReopenReason] = useState('');

  const loadDrawerStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.getCurrentCashDrawer({ closing_date: closingDate });
      const data = res.data;
      setDrawerData(data);
      setOpeningCashInput(data.opening_cash ? String(data.opening_cash) : '0');
      if (data.is_already_closed && data.closed_session) {
        setActualCashInput(String(data.closed_session.actual_cash));
        setNotesInput(data.closed_session.notes || '');
      } else {
        setActualCashInput('');
        setNotesInput('');
      }
    } catch (err) {
      console.error('Failed to load cash drawer status:', err);
      setError(err.message || 'Failed to load drawer state');
    } finally {
      setIsLoading(false);
    }
  }, [closingDate]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.getCashClosingHistory({ limit: 30 });
      setHistoryList(res.data || []);
    } catch (err) {
      console.error('Failed to load cash closing history:', err);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'closing') {
      loadDrawerStatus();
    } else {
      loadHistory();
    }
  }, [activeTab, loadDrawerStatus, loadHistory]);

  // Compute live expected cash and difference
  const openingNum = parseFloat(openingCashInput) || 0;
  const inflowsNum = parseFloat(drawerData?.cash_inflows || 0);
  const outflowsNum = parseFloat(drawerData?.cash_outflows || 0);
  const liveExpectedCash = openingNum + inflowsNum - outflowsNum;

  const actualNum = parseFloat(actualCashInput) || 0;
  const liveDifference = actualCashInput !== '' ? actualNum - liveExpectedCash : 0;

  const handleConfirmClose = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      await api.closeCashDrawer({
        closing_date: closingDate,
        opening_cash: openingNum,
        actual_cash: actualNum,
        notes: notesInput.trim() || undefined
      });
      setShowConfirmModal(false);
      setToastMsg('Daily physical cash drawer reconciled and closed successfully.');
      await loadDrawerStatus();
    } catch (err) {
      console.error('Failed to close cash drawer:', err);
      setError(err.message || 'Failed to close cash drawer');
      setShowConfirmModal(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReopen = async () => {
    if (!reopenReason.trim()) {
      alert(t('reopen_reason_prompt'));
      return;
    }
    try {
      setIsSubmitting(true);
      setError(null);
      const closingId = drawerData?.existing_closing_id;
      if (!closingId) return;
      await api.reopenCashClosing(closingId, {
        reason: reopenReason.trim()
      });
      setShowReopenModal(false);
      setReopenReason('');
      setToastMsg('Drawer reopened for correction.');
      await loadDrawerStatus();
    } catch (err) {
      console.error('Failed to reopen cash closing session:', err);
      setError(err.message || 'Failed to reopen drawer');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isClosed = drawerData?.is_already_closed;
  const breakdown = drawerData?.breakdown;
  const closedSession = drawerData?.closed_session;

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {toastMsg && <Toast message={toastMsg} onClose={() => setToastMsg(null)} />}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.25rem' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)', margin: 0 }}>
              {t('cash_closing_title')}
            </h1>
            {isClosed ? (
              <Badge variant="success">CLOSED & SEALED</Badge>
            ) : (
              <Badge variant="warning">DRAWER OPEN</Badge>
            )}
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
            {t('cash_closing_subtitle')}
          </p>
        </div>

        {/* Tab Toggle */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Button
            variant={activeTab === 'closing' ? 'primary' : 'outline'}
            onClick={() => setActiveTab('closing')}
          >
            <Banknote size={16} />
            Daily Reconcile
          </Button>
          <Button
            variant={activeTab === 'history' ? 'primary' : 'outline'}
            onClick={() => setActiveTab('history')}
          >
            <History size={16} />
            {t('closing_history')}
          </Button>
        </div>
      </div>

      {error && <Alert type="danger" title="Cash Drawer Error" message={error} />}

      {/* TAB 1: DAILY RECONCILIATION */}
      {activeTab === 'closing' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Date Selector Card */}
          <div className="card" style={{ padding: '0.875rem 1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Calendar size={18} color="var(--color-primary)" />
              <label style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700 }}>
                Closing Date:
              </label>
              <input
                type="date"
                value={closingDate}
                onChange={(e) => setClosingDate(e.target.value)}
                style={{
                  padding: '0.375rem 0.625rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  fontSize: 'var(--font-size-sm)'
                }}
              />
            </div>

            <Button variant="ghost" size="sm" onClick={loadDrawerStatus} disabled={isLoading}>
              <RefreshCw size={14} className={isLoading ? 'spin' : ''} /> Refresh Drawer
            </Button>
          </div>

          {isLoading ? (
            <div style={{ padding: '3rem 0' }}>
              <LoadingSpinner label="Auditing physical cash movements..." />
            </div>
          ) : (
            <>
              {/* Status Banner */}
              {isClosed ? (
                <div
                  style={{
                    padding: '1rem 1.25rem',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--color-accent-soft)',
                    border: '1px solid var(--color-accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '1rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <LockKeyhole size={22} color="var(--color-accent)" />
                    <div>
                      <div style={{ fontWeight: 800, fontSize: 'var(--font-size-sm)', color: '#065f46' }}>
                        {t('drawer_already_closed')}
                      </div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                        {t('closed_by')}: {closedSession?.closed_by_user_name || 'Authorized Cashier'} &bull; Status: {closedSession?.reconciliation_status?.toUpperCase()}
                      </div>
                    </div>
                  </div>

                  <Button variant="outline" size="sm" onClick={() => setShowReopenModal(true)}>
                    <LockOpen size={14} />
                    {t('reopen_btn')}
                  </Button>
                </div>
              ) : (
                <div
                  style={{
                    padding: '0.875rem 1.25rem',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: '#fffbeb',
                    border: '1px solid #fde68a',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem'
                  }}
                >
                  <AlertTriangle size={18} color="#b45309" />
                  <span style={{ fontSize: 'var(--font-size-xs)', color: '#92400e', fontWeight: 600 }}>
                    {t('drawer_open_active')}
                  </span>
                </div>
              )}

              {/* Step 1 & 2: Movements & Expected Cash Overview */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '1.25rem'
                }}
              >
                {/* Eligible Physical Inflows Card */}
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <ArrowDownLeft size={18} color="#16a34a" />
                      <span style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)' }}>
                        {t('physical_cash_inflows')}
                      </span>
                    </div>
                    <span style={{ fontWeight: 800, fontSize: 'var(--font-size-lg)', color: '#16a34a' }}>
                      +{formatCurrency(drawerData?.cash_inflows || 0)}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', fontSize: 'var(--font-size-xs)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.25rem' }}>
                      <span style={{ color: 'var(--color-text-muted)' }}>Sales Cash Tender:</span>
                      <span style={{ fontWeight: 600 }}>{formatCurrency(breakdown?.sales_cash_inflows || 0)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.25rem' }}>
                      <span style={{ color: 'var(--color-text-muted)' }}>Khata Collections (Cash):</span>
                      <span style={{ fontWeight: 600 }}>{formatCurrency(breakdown?.customer_khata_cash_inflows || 0)}</span>
                    </div>
                    <div style={{ color: 'var(--color-text-muted)', fontStyle: 'italic', marginTop: '0.25rem' }}>
                      Note: UPI, card and bank payments are strictly excluded from physical drawer.
                    </div>
                  </div>
                </div>

                {/* Eligible Physical Outflows Card */}
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <ArrowUpRight size={18} color="#dc2626" />
                      <span style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)' }}>
                        {t('physical_cash_outflows')}
                      </span>
                    </div>
                    <span style={{ fontWeight: 800, fontSize: 'var(--font-size-lg)', color: '#dc2626' }}>
                      &minus;{formatCurrency(drawerData?.cash_outflows || 0)}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', fontSize: 'var(--font-size-xs)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.25rem' }}>
                      <span style={{ color: 'var(--color-text-muted)' }}>Purchase Cash Payments:</span>
                      <span style={{ fontWeight: 600 }}>{formatCurrency(breakdown?.purchase_cash_outflows || 0)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.25rem' }}>
                      <span style={{ color: 'var(--color-text-muted)' }}>Supplier AP Cash Payments:</span>
                      <span style={{ fontWeight: 600 }}>{formatCurrency(breakdown?.supplier_settlement_cash_outflows || 0)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.25rem' }}>
                      <span style={{ color: 'var(--color-text-muted)' }}>Paid Cash Expenses:</span>
                      <span style={{ fontWeight: 600 }}>{formatCurrency(breakdown?.expense_cash_outflows || 0)}</span>
                    </div>
                  </div>
                </div>

                {/* Expected Cash Drawer Balance Card */}
                <div className="card" style={{ backgroundColor: 'var(--color-primary-soft)', border: '2px solid var(--color-primary)' }}>
                  <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase' }}>
                    {t('expected_closing_cash')}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 800, color: 'var(--color-primary-dark)', margin: '0.5rem 0' }}>
                    {formatCurrency(liveExpectedCash)}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                    Opening Float ({formatCurrency(openingNum)}) + Inflows ({formatCurrency(inflowsNum)}) &minus; Outflows ({formatCurrency(outflowsNum)})
                  </div>
                </div>
              </div>

              {/* Step 3 & 4: Physical Count Entry & Reconciliation Engine */}
              <div className="card" style={{ padding: '1.5rem' }}>
                <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 800, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Banknote size={20} color="var(--color-primary)" />
                  Physical Cash Count & Reconciliation
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
                  {/* Opening Float Input */}
                  <div>
                    <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, marginBottom: '0.375rem', color: 'var(--color-text-muted)' }}>
                      {t('opening_float')} ({business?.currency_symbol || '₹'})
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      disabled={isClosed}
                      value={openingCashInput}
                      onChange={(e) => setOpeningCashInput(e.target.value)}
                      placeholder="0.00"
                      style={{
                        width: '100%',
                        padding: '0.625rem 0.875rem',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--color-border)',
                        fontSize: 'var(--font-size-base)',
                        fontWeight: 600,
                        backgroundColor: isClosed ? 'var(--color-bg-subtle)' : 'var(--color-bg-surface)'
                      }}
                    />
                  </div>

                  {/* Counted Cash Input */}
                  <div>
                    <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, marginBottom: '0.375rem', color: 'var(--color-primary)' }}>
                      {t('counted_cash')} ({business?.currency_symbol || '₹'}) *
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      disabled={isClosed}
                      value={actualCashInput}
                      onChange={(e) => setActualCashInput(e.target.value)}
                      placeholder="Enter counted cash in drawer"
                      style={{
                        width: '100%',
                        padding: '0.625rem 0.875rem',
                        borderRadius: 'var(--radius-md)',
                        border: '2px solid var(--color-primary)',
                        fontSize: 'var(--font-size-lg)',
                        fontWeight: 800,
                        backgroundColor: isClosed ? 'var(--color-bg-subtle)' : 'var(--color-bg-surface)'
                      }}
                    />
                  </div>

                  {/* Difference & Reconciliation Result Box */}
                  <div
                    style={{
                      padding: '0.75rem 1rem',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: isClosed
                        ? 'var(--color-bg-subtle)'
                        : liveDifference === 0
                        ? '#f0fdf4'
                        : liveDifference > 0
                        ? '#ecfdf5'
                        : '#fef2f2',
                      border: `1px solid ${
                        liveDifference === 0 ? '#bbf7d0' : liveDifference > 0 ? '#a7f3d0' : '#fecaca'
                      }`,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center'
                    }}
                  >
                    <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
                      {t('drawer_difference')}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                      <span
                        style={{
                          fontSize: 'var(--font-size-xl)',
                          fontWeight: 800,
                          color:
                            liveDifference === 0
                              ? '#16a34a'
                              : liveDifference > 0
                              ? '#059669'
                              : '#dc2626'
                        }}
                      >
                        {liveDifference > 0 ? `+${formatCurrency(liveDifference)}` : formatCurrency(liveDifference)}
                      </span>
                      <Badge
                        variant={
                          liveDifference === 0
                            ? 'success'
                            : liveDifference > 0
                            ? 'success'
                            : 'warning'
                        }
                      >
                        {liveDifference === 0
                          ? t('reconciled')
                          : liveDifference > 0
                          ? t('drawer_over')
                          : t('drawer_short')}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Notes Input */}
                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, marginBottom: '0.375rem', color: 'var(--color-text-muted)' }}>
                    {t('closing_notes')}
                  </label>
                  <input
                    type="text"
                    disabled={isClosed}
                    value={notesInput}
                    onChange={(e) => setNotesInput(e.target.value)}
                    placeholder="Optional cashier notes or discrepancy justification..."
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.75rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border)',
                      fontSize: 'var(--font-size-sm)',
                      backgroundColor: isClosed ? 'var(--color-bg-subtle)' : 'var(--color-bg-surface)'
                    }}
                  />
                </div>

                {/* Action Buttons */}
                {!isClosed && (
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                    <Button
                      variant="primary"
                      size="lg"
                      disabled={actualCashInput === '' || isSubmitting}
                      onClick={() => setShowConfirmModal(true)}
                    >
                      <CheckCircle2 size={18} />
                      {t('confirm_close_btn')}
                    </Button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* TAB 2: CLOSING HISTORY */}
      {activeTab === 'history' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, margin: 0 }}>
              {t('closing_history')}
            </h3>
            <Button variant="ghost" size="sm" onClick={loadHistory}>
              <RefreshCw size={14} /> Refresh
            </Button>
          </div>

          {historyList.length === 0 ? (
            <div style={{ padding: '2rem 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
              No historical closing sessions recorded yet.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                    <th style={{ padding: '0.625rem' }}>DATE</th>
                    <th style={{ padding: '0.625rem', textAlign: 'right' }}>OPENING</th>
                    <th style={{ padding: '0.625rem', textAlign: 'right' }}>INFLOWS</th>
                    <th style={{ padding: '0.625rem', textAlign: 'right' }}>OUTFLOWS</th>
                    <th style={{ padding: '0.625rem', textAlign: 'right' }}>EXPECTED</th>
                    <th style={{ padding: '0.625rem', textAlign: 'right' }}>ACTUAL COUNT</th>
                    <th style={{ padding: '0.625rem', textAlign: 'right' }}>DIFF</th>
                    <th style={{ padding: '0.625rem', textAlign: 'center' }}>STATUS</th>
                    <th style={{ padding: '0.625rem' }}>CLOSED BY</th>
                  </tr>
                </thead>
                <tbody>
                  {historyList.map((item) => (
                    <tr key={item.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td style={{ padding: '0.625rem', fontWeight: 700 }}>{item.closing_date}</td>
                      <td style={{ padding: '0.625rem', textAlign: 'right' }}>{formatCurrency(item.opening_cash)}</td>
                      <td style={{ padding: '0.625rem', textAlign: 'right', color: '#16a34a' }}>+{formatCurrency(item.cash_inflows)}</td>
                      <td style={{ padding: '0.625rem', textAlign: 'right', color: '#dc2626' }}>&minus;{formatCurrency(item.cash_outflows)}</td>
                      <td style={{ padding: '0.625rem', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(item.expected_cash)}</td>
                      <td style={{ padding: '0.625rem', textAlign: 'right', fontWeight: 700 }}>{formatCurrency(item.actual_cash)}</td>
                      <td
                        style={{
                          padding: '0.625rem',
                          textAlign: 'right',
                          fontWeight: 700,
                          color:
                            Number(item.difference) === 0
                              ? '#16a34a'
                              : Number(item.difference) > 0
                              ? '#059669'
                              : '#dc2626'
                        }}
                      >
                        {Number(item.difference) > 0 ? `+${formatCurrency(item.difference)}` : formatCurrency(item.difference)}
                      </td>
                      <td style={{ padding: '0.625rem', textAlign: 'center' }}>
                        <Badge
                          variant={
                            item.reconciliation_status === 'reconciled'
                              ? 'success'
                              : item.reconciliation_status === 'over'
                              ? 'success'
                              : 'warning'
                          }
                        >
                          {item.reconciliation_status?.toUpperCase()}
                        </Badge>
                      </td>
                      <td style={{ padding: '0.625rem', color: 'var(--color-text-muted)' }}>
                        {item.closed_by_user_name || 'Staff'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* CONFIRMATION MODAL */}
      {showConfirmModal && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem'
          }}
        >
          <div className="card" style={{ maxWidth: '480px', width: '100%', padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <ShieldAlert size={24} color="var(--color-primary)" />
              <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 800, margin: 0 }}>
                {t('confirm_close_dialog_title')}
              </h3>
            </div>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', lineHeight: 1.5, marginBottom: '1.25rem' }}>
              {t('confirm_close_dialog_desc')}
            </p>

            <div style={{ backgroundColor: 'var(--color-bg-subtle)', padding: '0.875rem', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', fontSize: 'var(--font-size-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
                <span>Expected Cash:</span>
                <span style={{ fontWeight: 700 }}>{formatCurrency(liveExpectedCash)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
                <span>Physically Counted:</span>
                <span style={{ fontWeight: 700 }}>{formatCurrency(actualNum)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--color-border)', paddingTop: '0.375rem' }}>
                <span>Discrepancy (Diff):</span>
                <span style={{ fontWeight: 800, color: liveDifference >= 0 ? '#059669' : '#dc2626' }}>
                  {liveDifference > 0 ? `+${formatCurrency(liveDifference)}` : formatCurrency(liveDifference)}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <Button variant="outline" onClick={() => setShowConfirmModal(false)} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleConfirmClose} disabled={isSubmitting}>
                {isSubmitting ? 'Closing Drawer...' : 'Confirm & Close'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* REOPEN MODAL */}
      {showReopenModal && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem'
          }}
        >
          <div className="card" style={{ maxWidth: '480px', width: '100%', padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <LockOpen size={24} color="#d97706" />
              <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 800, margin: 0 }}>
                {t('reopen_btn')}
              </h3>
            </div>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', lineHeight: 1.5, marginBottom: '1rem' }}>
              {t('reopen_reason_prompt')}
            </p>

            <textarea
              rows={3}
              value={reopenReason}
              onChange={(e) => setReopenReason(e.target.value)}
              placeholder="e.g. Discovered missed cash receipt or misplaced physical drawer bills..."
              style={{
                width: '100%',
                padding: '0.625rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                fontSize: 'var(--font-size-sm)',
                marginBottom: '1.5rem',
                fontFamily: 'inherit'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <Button variant="outline" onClick={() => setShowReopenModal(false)} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleReopen} disabled={!reopenReason.trim() || isSubmitting}>
                {isSubmitting ? 'Reopening...' : 'Confirm Reopen'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
