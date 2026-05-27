import React from 'react';
import { Link } from 'react-router-dom';
import { useUser, UserButton, SignInButton } from '@clerk/react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from './theme-provider';

const Header: React.FC<{ forceSolid?: boolean }> = () => {
  const { isSignedIn } = useUser();
  const { theme, setTheme } = useTheme();

  const isDark =
    theme === 'dark' ||
    (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  const toggleTheme = () => setTheme(isDark ? 'light' : 'dark');

  return (
    <header className="border-b border-lp-border bg-bg">
      <div className="max-w-[860px] mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Masthead */}
          <Link to="/" className="no-underline">
            <div className="font-serif text-xl text-text-primary leading-none">
              internshipmatcher
              <em className="not-italic text-text-secondary">.</em>
            </div>
          </Link>

          {/* Nav links + controls */}
          <nav className="flex items-center gap-5">
            <Link
              to="/find"
              className="font-mono text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              Find
            </Link>
            {isSignedIn && (
              <Link
                to="/history"
                className="font-mono text-xs text-text-secondary hover:text-text-primary transition-colors"
              >
                History
              </Link>
            )}
            {isSignedIn && (
              <Link
                to="/usage"
                className="font-mono text-xs text-text-secondary hover:text-text-primary transition-colors"
              >
                Usage
              </Link>
            )}

            <button
              onClick={toggleTheme}
              className="text-text-tertiary hover:text-text-primary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary rounded-sm"
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            </button>

            {isSignedIn ? (
              <UserButton />
            ) : (
              <SignInButton mode="modal">
                <button className="font-mono text-xs text-text-secondary hover:text-text-primary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary rounded-sm">
                  Sign in →
                </button>
              </SignInButton>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;
