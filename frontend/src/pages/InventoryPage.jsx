import React, { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../context/I18nContext';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';
import { Badge, LoadingSpinner, Alert } from '../components/common/Feedback';
import { InventoryOverviewCards } from '../components/inventory/InventoryOverviewCards';
import { ProductModal } from '../components/inventory/ProductModal';
import { StockAdjustmentModal } from '../components/inventory/StockAdjustmentModal';
import { CategoryModal } from '../components/inventory/CategoryModal';
import { ProductDetailsModal } from '../components/inventory/ProductDetailsModal';
import {
  Package,
  Plus,
  Search,
  Sliders,
  Eye,
  Edit,
  FolderPlus,
  RefreshCw,
  PowerOff,
  Power
} from 'lucide-react';
import { api } from '../services/api';

export function InventoryPage() {
  const { t } = useI18n();
  const { business } = useAuth();
  const currencySymbol = business?.currency_symbol || '₹';
  const isSimpleTier = business?.tier === 'simple';

  // State
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [overview, setOverview] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'low_stock' | 'out_of_stock' | 'inactive'
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  // Modals state
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);

  const [isAdjustModalOpen, setIsAdjustModalOpen] = useState(false);
  const [adjustingProduct, setAdjustingProduct] = useState(null);

  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);

  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [viewingProductId, setViewingProductId] = useState(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = {};
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (selectedCategory) params.category_id = selectedCategory;

      if (activeFilter === 'low_stock') {
        params.low_stock = true;
      } else if (activeFilter === 'inactive') {
        params.is_active = false;
      } else {
        // 'all' or 'out_of_stock' (we can filter active products by default)
        params.is_active = true;
      }

      params.sort_by = sortBy;
      params.order = sortOrder;

      const [prodsRes, catsRes, ovRes] = await Promise.all([
        api.getProducts(params),
        api.getCategories(),
        api.getInventoryOverview()
      ]);

      let prodList = prodsRes.data || [];
      if (activeFilter === 'out_of_stock') {
        prodList = prodList.filter((p) => parseFloat(p.current_stock) <= 0);
      }

      setProducts(prodList);
      setCategories(catsRes.data || []);
      setOverview(ovRes.data || null);
    } catch (err) {
      setError(err.message || 'Failed to load inventory');
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, selectedCategory, activeFilter, sortBy, sortOrder]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function handleProductSaved(_savedProduct) {
    setSuccessMessage(t('product_saved_success'));
    setTimeout(() => setSuccessMessage(null), 4000);
    loadData();
  }

  function handleStockAdjusted(_movement) {
    setSuccessMessage(t('stock_adjusted_success'));
    setTimeout(() => setSuccessMessage(null), 4000);
    loadData();
  }

  async function handleToggleStatus(productId, currentActive) {
    try {
      await api.toggleProductStatus(productId, !currentActive);
      loadData();
    } catch (err) {
      setError(err.message || 'Failed to update product status');
    }
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* Page Header */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        marginBottom: '1.5rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-text-main)', margin: 0 }}>
              {t('products_and_inventory')}
            </h1>
            <Badge variant={isSimpleTier ? 'primary' : 'success'}>
              {business?.tier ? business.tier.toUpperCase() : 'TIER'}
            </Badge>
          </div>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
            Real-time stock tracking, categories, price configuration and traceable ledger movements.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Button
            variant="outline"
            icon={FolderPlus}
            onClick={() => setIsCategoryModalOpen(true)}
          >
            {t('manage_categories')}
          </Button>

          <Button
            variant="primary"
            icon={Plus}
            onClick={() => {
              setEditingProduct(null);
              setIsProductModalOpen(true);
            }}
          >
            {t('add_product')}
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <InventoryOverviewCards
        overview={overview}
        currencySymbol={currencySymbol}
        activeFilter={activeFilter}
        onSelectFilter={(filterKey) => setActiveFilter(filterKey)}
      />

      {/* Alerts & Messages */}
      {successMessage && <Alert type="success" message={successMessage} />}
      {error && <Alert type="danger" message={error} />}

      {/* Filters & Search Control Bar */}
      <div style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--color-border)',
        padding: '1rem',
        marginBottom: '1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem'
      }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Search bar */}
          <div style={{ position: 'relative', flex: '1 1 280px' }}>
            <Search
              size={18}
              style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('search_products')}
              style={{
                width: '100%',
                padding: '0.625rem 0.75rem 0.625rem 2.25rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg-subtle)',
                color: 'var(--color-text-main)',
                fontSize: 'var(--font-size-sm)'
              }}
            />
          </div>

          {/* Category Dropdown */}
          <div style={{ flex: '0 1 200px' }}>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              style={{
                width: '100%',
                padding: '0.625rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg-subtle)',
                color: 'var(--color-text-main)',
                fontSize: 'var(--font-size-sm)'
              }}
            >
              <option value="">{t('all_categories')}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.tamil_name ? `(${c.tamil_name})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Sort Control */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{
                padding: '0.625rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg-subtle)',
                color: 'var(--color-text-main)',
                fontSize: 'var(--font-size-sm)'
              }}
            >
              <option value="created_at">Date Added</option>
              <option value="name">Product Name</option>
              <option value="selling_price">Selling Price</option>
              <option value="current_stock">Stock Level</option>
            </select>

            <button
              onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
              title="Toggle sort direction"
              style={{
                minHeight: '38px',
                padding: '0 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg-subtle)',
                color: 'var(--color-text-main)',
                cursor: 'pointer',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600
              }}
            >
              {sortOrder.toUpperCase()}
            </button>

            <button
              onClick={() => loadData()}
              title="Refresh"
              style={{
                minHeight: '38px',
                padding: '0 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg-subtle)',
                color: 'var(--color-text-main)',
                cursor: 'pointer'
              }}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        {/* Quick Filter Pills */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', paddingTop: '0.5rem', borderTop: '1px solid var(--color-border)' }}>
          {[
            { id: 'all', label: t('filter_all'), count: overview?.total_products },
            { id: 'low_stock', label: t('filter_low_stock'), count: overview?.low_stock_products, warning: true },
            { id: 'out_of_stock', label: t('filter_out_of_stock'), count: overview?.out_of_stock_products, danger: true },
            { id: 'inactive', label: t('filter_inactive') }
          ].map((pill) => {
            const isActive = activeFilter === pill.id;
            return (
              <button
                key={pill.id}
                onClick={() => setActiveFilter(pill.id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                  padding: '0.375rem 0.875rem',
                  borderRadius: 'var(--radius-full)',
                  border: `1px solid ${isActive ? 'var(--color-primary)' : 'var(--color-border)'}`,
                  backgroundColor: isActive ? 'var(--color-primary-soft)' : 'transparent',
                  color: isActive ? 'var(--color-primary)' : 'var(--color-text-main)',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: 'var(--font-size-xs)',
                  cursor: 'pointer'
                }}
              >
                <span>{pill.label}</span>
                {pill.count !== undefined && (
                  <span style={{
                    padding: '1px 6px',
                    borderRadius: '10px',
                    fontSize: '11px',
                    fontWeight: 700,
                    backgroundColor: pill.danger ? 'var(--color-danger-soft)' : pill.warning ? '#fef3c7' : 'var(--color-bg-subtle)',
                    color: pill.danger ? 'var(--color-danger)' : pill.warning ? '#b45309' : 'var(--color-text-muted)'
                  }}>
                    {pill.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content: Products List / Table */}
      {isLoading ? (
        <LoadingSpinner label="Loading products and real-time inventory..." />
      ) : products.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '4rem 1.5rem',
          backgroundColor: 'var(--color-bg-surface)',
          borderRadius: 'var(--radius-xl)',
          border: '1px dashed var(--color-border)'
        }}>
          <div style={{ width: '56px', height: '56px', borderRadius: '50%', backgroundColor: 'var(--color-primary-soft)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-primary)', marginBottom: '1rem' }}>
            <Package size={28} />
          </div>
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, color: 'var(--color-text-main)', margin: '0 0 0.5rem' }}>
            {t('no_products_found')}
          </h3>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', maxWidth: '420px', margin: '0 auto 1.5rem' }}>
            Start building your catalog. Add products with prices, units, and initial stock to start tracking inventory.
          </p>
          <Button
            variant="primary"
            icon={Plus}
            onClick={() => {
              setEditingProduct(null);
              setIsProductModalOpen(true);
            }}
          >
            {t('add_product')}
          </Button>
        </div>
      ) : isSimpleTier ? (
        /* SIMPLE TIER: Clean card view with high contrast touch buttons */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: '1rem' }}>
          {products.map((p) => {
            const stock = parseFloat(p.current_stock) || 0;
            const isOutOfStock = stock <= 0;
            const isLowStock = p.stock_status === 'low_stock';

            return (
              <div
                key={p.id}
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  borderRadius: 'var(--radius-lg)',
                  border: `1px solid ${isOutOfStock ? 'var(--color-danger-soft)' : isLowStock ? '#fde68a' : 'var(--color-border)'}`,
                  padding: '1.25rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <div>
                      <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, margin: 0, color: 'var(--color-text-main)' }}>
                        {p.name}
                      </h3>
                      {p.tamil_name && (
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                          {p.tamil_name}
                        </div>
                      )}
                    </div>
                    <Badge variant={isOutOfStock ? 'neutral' : isLowStock ? 'warning' : 'success'}>
                      {isOutOfStock ? t('status_out_of_stock') : isLowStock ? t('status_low_stock') : t('status_in_stock')}
                    </Badge>
                  </div>

                  <div style={{ display: 'flex', gap: '0.75rem', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: '0.75rem' }}>
                    {p.sku && <span>SKU: <strong>{p.sku}</strong></span>}
                    {p.category_name && <span>• {p.category_name}</span>}
                  </div>

                  <div style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    backgroundColor: 'var(--color-bg-subtle)',
                    borderRadius: 'var(--radius-md)',
                    marginBottom: '1rem'
                  }}>
                    <div>
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', display: 'block' }}>
                        {t('selling_price')}
                      </span>
                      <span style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-accent)' }}>
                        {currencySymbol}{Number(p.selling_price).toFixed(2)}
                      </span>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', display: 'block' }}>
                        {t('stock_balance')}
                      </span>
                      <span style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: isOutOfStock ? 'var(--color-danger)' : 'var(--color-text-main)' }}>
                        {stock} <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 500 }}>{p.unit}</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Button
                    size="sm"
                    variant="primary"
                    icon={Sliders}
                    style={{ flex: 1 }}
                    onClick={() => {
                      setAdjustingProduct(p);
                      setIsAdjustModalOpen(true);
                    }}
                  >
                    {t('adjust_stock')}
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    icon={Eye}
                    onClick={() => {
                      setViewingProductId(p.id);
                      setIsDetailsModalOpen(true);
                    }}
                  />

                  <Button
                    size="sm"
                    variant="outline"
                    icon={Edit}
                    onClick={() => {
                      setEditingProduct(p);
                      setIsProductModalOpen(true);
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* GROWTH / ENTERPRISE TIER: High-density structured data table */
        <div style={{
          backgroundColor: 'var(--color-bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--color-border)',
          overflowX: 'auto',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--color-bg-subtle)', borderBottom: '1px solid var(--color-border)', textAlign: 'left' }}>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>{t('products')}</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>{t('sku')}</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>{t('category_label')}</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)', textAlign: 'right' }}>{t('purchase_cost')}</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)', textAlign: 'right' }}>{t('selling_price')}</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)', textAlign: 'right' }}>Margin</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)', textAlign: 'right' }}>{t('stock_balance')}</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>{t('stock_status')}</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-muted)', textAlign: 'right' }}>{t('actions')}</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => {
                const stock = parseFloat(p.current_stock) || 0;
                const cost = parseFloat(p.purchase_cost) || 0;
                const price = parseFloat(p.selling_price) || 0;
                const margin = price > 0 ? (((price - cost) / price) * 100).toFixed(0) : 0;
                const isOutOfStock = stock <= 0;
                const isLowStock = p.stock_status === 'low_stock';

                return (
                  <tr key={p.id} style={{ borderBottom: '1px solid var(--color-border)', opacity: p.is_active ? 1 : 0.6 }}>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <div style={{ fontWeight: 600, color: 'var(--color-text-main)' }}>{p.name}</div>
                      {p.tamil_name && <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>{p.tamil_name}</div>}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                      {p.sku || '—'}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', color: 'var(--color-text-muted)' }}>
                      {p.category_name || '—'}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                      {currencySymbol}{cost.toFixed(2)}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 700, color: 'var(--color-accent)' }}>
                      {currencySymbol}{price.toFixed(2)}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', color: margin > 0 ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>
                      {margin}%
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 700, color: isOutOfStock ? 'var(--color-danger)' : 'var(--color-text-main)' }}>
                      {stock} <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 400, color: 'var(--color-text-muted)' }}>{p.unit}</span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <Badge variant={isOutOfStock ? 'neutral' : isLowStock ? 'warning' : 'success'}>
                        {isOutOfStock ? t('status_out_of_stock') : isLowStock ? t('status_low_stock') : t('status_in_stock')}
                      </Badge>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '0.375rem' }}>
                        <Button
                          size="sm"
                          variant="primary"
                          icon={Sliders}
                          title={t('adjust_stock')}
                          onClick={() => {
                            setAdjustingProduct(p);
                            setIsAdjustModalOpen(true);
                          }}
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          icon={Eye}
                          title={t('product_details')}
                          onClick={() => {
                            setViewingProductId(p.id);
                            setIsDetailsModalOpen(true);
                          }}
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          icon={Edit}
                          title={t('edit_product')}
                          onClick={() => {
                            setEditingProduct(p);
                            setIsProductModalOpen(true);
                          }}
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          icon={p.is_active ? PowerOff : Power}
                          title={p.is_active ? t('deactivate') : t('activate')}
                          onClick={() => handleToggleStatus(p.id, p.is_active)}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Modals */}
      <ProductModal
        isOpen={isProductModalOpen}
        onClose={() => setIsProductModalOpen(false)}
        product={editingProduct}
        categories={categories}
        currencySymbol={currencySymbol}
        onSaved={handleProductSaved}
        onOpenCategoryManager={() => setIsCategoryModalOpen(true)}
      />

      <StockAdjustmentModal
        isOpen={isAdjustModalOpen}
        onClose={() => setIsAdjustModalOpen(false)}
        product={adjustingProduct}
        currencySymbol={currencySymbol}
        onAdjusted={handleStockAdjusted}
      />

      <CategoryModal
        isOpen={isCategoryModalOpen}
        onClose={() => setIsCategoryModalOpen(false)}
        categories={categories}
        onCategoryCreated={(newCat) => {
          setCategories((prev) => [...prev, newCat]);
          loadData();
        }}
      />

      <ProductDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => setIsDetailsModalOpen(false)}
        productId={viewingProductId}
        currencySymbol={currencySymbol}
        onOpenAdjustment={(prod) => {
          setIsDetailsModalOpen(false);
          setAdjustingProduct(prod);
          setIsAdjustModalOpen(true);
        }}
        onOpenEdit={(prod) => {
          setIsDetailsModalOpen(false);
          setEditingProduct(prod);
          setIsProductModalOpen(true);
        }}
      />
    </div>
  );
}
