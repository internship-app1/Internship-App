/**
 * Smoke tests for the top-level App component.
 *
 * Clerk and React Router are mocked so no real auth context is needed.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import App from '../App';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Clerk — stub out ClerkProvider so it just renders children
jest.mock('@clerk/react', () => ({
  ClerkProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useUser: () => ({ isSignedIn: false, user: null }),
  useAuth: () => ({ isSignedIn: false, getToken: jest.fn() }),
  SignInButton: () => <button>Sign In</button>,
  UserButton: () => <div>UserButton</div>,
}));

// React Router DOM — stub out routing primitives
jest.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Routes: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Route: ({ element }: { element: React.ReactNode }) => <>{element}</>,
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => <a href={to}>{children}</a>,
  useNavigate: () => jest.fn(),
  useLocation: () => ({ pathname: '/' }),
  useParams: () => ({}),
}));

// Pages — stub heavy pages so we only test routing wiring
jest.mock('../pages/LandingPage', () => () => <div data-testid="landing-page">Landing</div>);
jest.mock('../pages/FindPage', () => () => <div data-testid="find-page">Find</div>);
jest.mock('../pages/LoginPage', () => () => <div data-testid="login-page">Login</div>);
jest.mock('../components/TestJobDisplay', () => () => <div data-testid="test-page">Test</div>);

// ThemeProvider — pass-through
jest.mock('../components/theme-provider', () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    // Default route "/" should show the landing page mock
    expect(screen.getByTestId('landing-page')).toBeInTheDocument();
  });

  it('shows landing page at root route', () => {
    render(<App />);
    expect(screen.getByText('Landing')).toBeInTheDocument();
  });
});
