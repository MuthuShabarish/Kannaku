import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useI18n } from '../context/I18nContext';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Button } from '../components/common/Button';
import { Badge, LoadingSpinner, Toast } from '../components/common/Feedback';
import { ExpenseModal } from '../components/expenses/ExpenseModal';
import { CategoryModal } from '../components/expenses/CategoryModal';
import { VoidExpenseModal } from '../components/expenses/VoidExpenseModal';
import {
  Plus,
  Search,
  Receipt,
  Banknote,
  QrCode,
  CreditCard,
  Building,
  Tag,
  Trash2,
  Calendar,
  Layers
} from 'lucide-react';

export function ExpensesPage() {
  const { t, formatCurrency } = useI18n();
  const { business } = useAuth();
  const isSimpleTier = business?.tier === 'simple';

  // Data State
  const [expenses, setExpenses] = useState([]);
  const [categories, setCategories] = useState([]);
  const [overview, setOverview] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedMode, setSelectedMode] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  // Modals
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [voidingExpense, setVoidingExpense] = useState(null);

  // Feedback
  const [toastMessage, setToastMessage] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [expRes, catRes, ovRes] = await Promise.all([
        api.getExpenses({
          search: search.trim() || undefined,
          category_id: selectedCategory || undefined,
          payment_method: selectedMode || undefined,
          payment_status: selectedStatus || undefined,
          limit: 100,
        }),
        api.getExpenseCategories(),
        api.getExpensesOverview(),
      ]);

      setExpenses(expRes.data || []);
      setCategories(catRes.data || []);
      setOverview(ovRes.data || null);
    } catch (err) {
      console.error('Failed to load expenses data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [search, selectedCategory, selectedMode, selectedStatus]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Payment Mode Icon Helper
  const getModeIcon = (mode) => {
    switch (mode) {
      case 'upi':
        return <QrCode size={14} color="#7c3aed" />;
      case 'card':
        return <CreditCard size={14} color="#2563eb" />;
      case 'bank_transfer':
        return <Building size={14} color="#0d9488" />;
      case 'cash':
      default:
        return <Banknote size={14} color="#16a34a" />;
    }
  };

  const cashOutflow = useMemo(() => {
    if (!overview?.by_payment_method) return 0;
    return parseFloat(overview.by_payment_method.cash || 0);
  }, [overview]);

  const digitalOutflow = useMemo(() => {
    if (!overview?.by_payment_method) return 0;
    const upi = parseFloat(overview.by_payment_method.upi || 0);
    const card = parseFloat(overview.by_payment_method.card || 0);
    const bank = parseFloat(overview.by_payment_method.bank_transfer || 0);
    return upi + card + bank;
  }, [overview]);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '3rem' }}>
      {toastMessage && (
        <Toast
          message={toastMessage}
          type="success"
          onClose={() => setToastMessage(null)}
        />
      )}

      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)', margin: 0 }}>
            {t('expenses_title')}
          </h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: '0.25rem 0 0' }}>
            {t('expenses_subtitle')}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Button variant="outline" onClick={() => setShowCategoryModal(true)}>
            <Layers size={16} /> {t('manage_categories_btn')}
          </Button>
          <Button variant="primary" onClick={() => setShowExpenseModal(true)}>
            <Plus size={16} /> {t('add_expense_btn')}
          </Button>
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--color-text-muted)' }}>
            <Receipt size={18} color="var(--color-primary)" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase' }}>
              {t('total_expenses')}
            </span>
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)' }}>
            {formatCurrency(overview?.total_expenses || 0)}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            {overview?.total_count || 0} active operating vouchers
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--color-text-muted)' }}>
            <Banknote size={18} color="#16a34a" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase' }}>
              Cash Expenses
            </span>
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: '#16a34a' }}>
            {formatCurrency(cashOutflow)}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            Paid from cash drawer
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--color-text-muted)' }}>
            <QrCode size={18} color="#7c3aed" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase' }}>
              Digital / Bank Expenses
            </span>
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: '#7c3aed' }}>
            {formatCurrency(digitalOutflow)}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            UPI, Card & Bank transfers
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--color-text-muted)' }}>
            <Tag size={18} color="var(--color-accent)" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase' }}>
              Active Categories
            </span>
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)' }}>
            {categories.filter((c) => c.is_active).length}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            Configured operating categories
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className="card"
        style={{
          padding: '1rem',
          marginBottom: '1.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.75rem',
          alignItems: 'center',
        }}
      >
        <div style={{ position: 'relative', flex: '1 1 200px' }}>
          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
          <input
            type="text"
            className="input"
            placeholder="Search description, payee, voucher #..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: '100%', paddingLeft: '2.25rem', paddingRight: '0.75rem', height: '38px', borderRadius: 'var(--radius-md)' }}
          />
        </div>

        <select
          className="input"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          style={{ height: '38px', padding: '0 0.75rem', borderRadius: 'var(--radius-md)', flex: '0 1 180px' }}
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        <select
          className="input"
          value={selectedMode}
          onChange={(e) => setSelectedMode(e.target.value)}
          style={{ height: '38px', padding: '0 0.75rem', borderRadius: 'var(--radius-md)', flex: '0 1 140px' }}
        >
          <option value="">All Modes</option>
          <option value="cash">Cash</option>
          <option value="upi">UPI</option>
          <option value="card">Card</option>
          <option value="bank_transfer">Bank Transfer</option>
        </select>

        <select
          className="input"
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          style={{ height: '38px', padding: '0 0.75rem', borderRadius: 'var(--radius-md)', flex: '0 1 130px' }}
        >
          <option value="">All Statuses</option>
          <option value="paid">Paid</option>
          <option value="voided">Voided</option>
        </select>
      </div>

      {/* Expenses Table / Cards */}
      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
          <LoadingSpinner size="large" />
        </div>
      ) : expenses.length === 0 ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <Receipt size={40} color="var(--color-text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
          <h3 style={{ margin: '0 0 0.5rem', fontWeight: 700 }}>No Operating Expenses Found</h3>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: '0 0 1.25rem' }}>
            Record operational overheads such as rent, electricity, wages, or supplies to track business spending.
          </p>
          <Button variant="primary" onClick={() => setShowExpenseModal(true)}>
            <Plus size={16} /> {t('add_expense_btn')}
          </Button>
        </div>
      ) : isSimpleTier ? (
        /* Simple Mode: Touch Cards */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {expenses.map((exp) => (
            <div
              key={exp.id}
              className="card"
              style={{
                padding: '1.25rem',
                borderLeft: `4px solid ${exp.payment_status === 'voided' ? 'var(--color-text-muted)' : 'var(--color-danger)'}`,
                opacity: exp.payment_status === 'voided' ? 0.6 : 1,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <div>
                  <div style={{ fontWeight: 800, fontSize: 'var(--font-size-base)', color: 'var(--color-primary-dark)' }}>
                    {exp.description}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    {exp.category_name} &bull; {exp.expense_number}
                  </div>
                </div>
                <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: exp.payment_status === 'voided' ? 'var(--color-text-muted)' : 'var(--color-danger)' }}>
                  {formatCurrency(exp.amount)}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.75rem', borderTop: '1px solid var(--color-border)', paddingTop: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  {getModeIcon(exp.payment_method)}
                  <span style={{ textTransform: 'capitalize' }}>{exp.payment_method.replace('_', ' ')}</span>
                  {exp.payee && <span>&bull; {exp.payee}</span>}
                </div>
                {exp.payment_status === 'voided' ? (
                  <Badge variant="neutral">{t('status_voided')}</Badge>
                ) : (
                  <button
                    onClick={() => setVoidingExpense(exp)}
                    style={{ background: 'none', border: 'none', color: 'var(--color-danger)', cursor: 'pointer', padding: 0 }}
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Growth & Enterprise: Dense Table */
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 'var(--font-size-sm)' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-bg-subtle)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>{t('expense_date')}</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>{t('expense_number')}</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>{t('category')}</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>{t('purpose_desc')}</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>{t('payee')}</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>{t('payment_method')}</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700, textAlign: 'right' }}>{t('amount')}</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>Status</th>
                  <th style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((exp) => {
                  const isVoided = exp.payment_status === 'voided';
                  return (
                    <tr
                      key={exp.id}
                      style={{
                        borderBottom: '1px solid var(--color-border)',
                        backgroundColor: isVoided ? 'var(--color-bg-subtle)' : 'transparent',
                        opacity: isVoided ? 0.6 : 1,
                      }}
                    >
                      <td style={{ padding: '0.75rem 1rem', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Calendar size={14} color="var(--color-text-muted)" />
                          <span>{new Date(exp.expense_date).toLocaleDateString()}</span>
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem 1rem', fontWeight: 600, fontFamily: 'monospace' }}>
                        {exp.expense_number}
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <Badge variant="neutral">{exp.category_name || 'General'}</Badge>
                      </td>
                      <td style={{ padding: '0.75rem 1rem', maxWidth: '240px', wordBreak: 'break-word' }}>
                        <div style={{ fontWeight: 600 }}>{exp.description}</div>
                        {exp.reference_number && (
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                            Ref: {exp.reference_number}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--color-text-muted)' }}>
                        {exp.payee || '—'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          {getModeIcon(exp.payment_method)}
                          <span style={{ textTransform: 'capitalize' }}>
                            {exp.payment_method.replace('_', ' ')}
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 800, color: isVoided ? 'var(--color-text-muted)' : 'var(--color-danger)' }}>
                        {formatCurrency(exp.amount)}
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        {isVoided ? (
                          <Badge variant="neutral">{t('status_voided')}</Badge>
                        ) : (
                          <Badge variant="primary">{t('status_paid')}</Badge>
                        )}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                        {!isVoided && (
                          <button
                            title="Void Expense"
                            onClick={() => setVoidingExpense(exp)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: 'var(--color-danger)',
                              cursor: 'pointer',
                              padding: '0.25rem',
                            }}
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      <ExpenseModal
        isOpen={showExpenseModal}
        onClose={() => setShowExpenseModal(false)}
        categories={categories}
        onSuccess={() => {
          setToastMessage(t('expense_success'));
          loadData();
        }}
      />

      <CategoryModal
        isOpen={showCategoryModal}
        onClose={() => setShowCategoryModal(false)}
        categories={categories}
        onRefresh={loadData}
      />

      <VoidExpenseModal
        isOpen={Boolean(voidingExpense)}
        onClose={() => setVoidingExpense(null)}
        expense={voidingExpense}
        onSuccess={() => {
          setToastMessage(t('void_success'));
          loadData();
        }}
      />
    </div>
  );
}
