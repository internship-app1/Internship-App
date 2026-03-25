import React, { Suspense, useEffect } from 'react';
import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom';
import { ClerkProvider } from '@clerk/react';
import { ThemeProvider } from './components/theme-provider';
import LandingPage from './pages/LandingPage';
import FindPage from './pages/FindPage';
import HistoryPage from './pages/HistoryPage';
import LoginPage from './pages/LoginPage';
import TestJobDisplay from './components/TestJobDisplay';

declare global {
  interface Window { dataLayer: Record<string, unknown>[]; }
}

function PageTracker() {
  const location = useLocation();
  useEffect(() => {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: 'page_view',
      page_path: location.pathname + location.search,
    });
  }, [location]);
  return null;
}

function App() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Loading...</div>}>
      <ClerkProvider publishableKey={process.env.REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY!}>
        <BrowserRouter>
          <ThemeProvider defaultTheme="system" storageKey="internship-ui-theme">
            <PageTracker />
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/find" element={<FindPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/test" element={<TestJobDisplay />} />
            </Routes>
          </ThemeProvider>
        </BrowserRouter>
      </ClerkProvider>
    </Suspense>
  );
}

export default App;
