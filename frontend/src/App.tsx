import React, { Suspense } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { ClerkProvider } from '@clerk/react';
import { ThemeProvider } from './components/theme-provider';
import LandingPage from './pages/LandingPage';
import FindPage from './pages/FindPage';
import LoginPage from './pages/LoginPage';
import TestJobDisplay from './components/TestJobDisplay';

function App() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Loading...</div>}>
      <ClerkProvider publishableKey={process.env.REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY as string}>
        <BrowserRouter>
          <ThemeProvider defaultTheme="system" storageKey="internship-ui-theme">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/find" element={<FindPage />} />
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
