import React, { useState } from 'react';
import { I18nProvider } from './context/I18nContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Header } from './components/layout/Header';
import { Sidebar, BottomNav } from './components/layout/Navigation';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { OnboardingWizard } from './components/onboarding/OnboardingWizard';
import { SettingsPage } from './pages/SettingsPage';
import { InventoryPage } from './pages/InventoryPage';
import { POSPage } from './pages/POSPage';
import { CustomersPage } from './pages/CustomersPage';
import { PurchasesPage } from './pages/PurchasesPage';
import { SuppliersPage } from './pages/SuppliersPage';
import { ExpensesPage } from './pages/ExpensesPage';
import { CashbookPage } from './pages/CashbookPage';
import { ReportsPage } from './pages/ReportsPage';
import { CashClosingPage } from './pages/CashClosingPage';
import { LoadingSpinner } from './components/common/Feedback';

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();
  const [currentTab, setCurrentTab] = useState('dashboard');

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <LoadingSpinner label="Loading Kanakku..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="app-layout">
      <Header />
      <div className="app-layout-main">
        <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />
        <main className="app-content" id="main-content">
          {currentTab === 'pos' ? (
            <POSPage />
          ) : currentTab === 'reports' ? (
            <ReportsPage />
          ) : currentTab === 'cash_closing' ? (
            <CashClosingPage />
          ) : currentTab === 'customers' ? (
            <CustomersPage />
          ) : currentTab === 'purchases' ? (
            <PurchasesPage />
          ) : currentTab === 'suppliers' ? (
            <SuppliersPage />
          ) : currentTab === 'expenses' ? (
            <ExpensesPage />
          ) : currentTab === 'cashbook' ? (
            <CashbookPage />
          ) : currentTab === 'inventory' ? (
            <InventoryPage />
          ) : currentTab === 'onboarding' ? (
            <OnboardingWizard
              onComplete={() => setCurrentTab('dashboard')}
              onExit={() => setCurrentTab('dashboard')}
            />
          ) : currentTab === 'settings' ? (
            <SettingsPage
              onRevisitOnboarding={() => setCurrentTab('onboarding')}
            />
          ) : (
            <DashboardPage onNavigateTab={setCurrentTab} />
          )}
        </main>
      </div>
      <BottomNav currentTab={currentTab} onSelectTab={setCurrentTab} />
    </div>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </I18nProvider>
  );
}
