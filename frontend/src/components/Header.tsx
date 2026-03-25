import React, { useEffect, useState } from 'react';
import { useUser, UserButton, SignInButton } from '@clerk/react';
import { Link } from 'react-router-dom';
import { ThemeToggle } from './theme-toggle';
import { Sparkles, Menu, X } from 'lucide-react';

const Header: React.FC<{ forceSolid?: boolean }> = ({ forceSolid = false }) => {
  const { isSignedIn } = useUser();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 12);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <header
      className={`sticky top-0 z-50 w-full transition-all duration-300 ${
        scrolled || forceSolid || mobileMenuOpen
          ? 'bg-white/90 dark:bg-neutral-950/90 backdrop-blur-md shadow-sm border-b border-neutral-200/60 dark:border-neutral-800/60'
          : 'bg-transparent'
      }`}
    >
      <div className="container flex h-16 items-center justify-between mx-auto px-4 sm:px-6">
        {/* Logo */}
        <div className="flex items-center gap-2 min-w-0">
          <div className="h-7 w-7 flex-shrink-0 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span
            className="text-lg sm:text-xl font-bold text-neutral-950 dark:text-neutral-50 truncate"
            style={{ fontFamily: 'Sora, sans-serif' }}
          >
            internshipmatcher
          </span>
          <span className="text-xs font-bold text-cyan-500 align-super tracking-wide -ml-0.5 flex-shrink-0">
            AI
          </span>
        </div>

        {/* Desktop nav links */}
        <nav className="hidden md:flex items-center gap-6">
          <a
            href="#how-it-works"
            onClick={(e) => {
              e.preventDefault();
              document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-950 dark:hover:text-neutral-50 transition-colors"
          >
            How It Works
          </a>
          <a
            href="#features"
            onClick={(e) => {
              e.preventDefault();
              document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-950 dark:hover:text-neutral-50 transition-colors"
          >
            Features
          </a>
          {isSignedIn && (
            <Link
              to="/history"
              className="text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-950 dark:hover:text-neutral-50 transition-colors"
            >
              My History
            </Link>
          )}
        </nav>

        {/* Right side actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />
          {isSignedIn ? (
            <UserButton />
          ) : (
            <SignInButton mode="modal">
              <button className="bg-violet-600 hover:bg-violet-700 text-white rounded-full px-4 sm:px-5 py-2 text-sm font-semibold shadow-md shadow-violet-500/25 hover:shadow-violet-500/40 hover:-translate-y-0.5 transition-all min-h-[44px]">
                Sign In
              </button>
            </SignInButton>
          )}
          {/* Hamburger button — mobile only */}
          <button
            className="md:hidden flex items-center justify-center rounded-lg p-2 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors min-h-[44px] min-w-[44px]"
            onClick={() => setMobileMenuOpen((o) => !o)}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile nav drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-neutral-200/60 dark:border-neutral-800/60 bg-white/95 dark:bg-neutral-950/95 backdrop-blur-md px-4 py-4 space-y-1">
          <a
            href="#how-it-works"
            onClick={(e) => {
              e.preventDefault();
              closeMobileMenu();
              document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="flex items-center py-3 px-3 rounded-xl text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors min-h-[44px]"
          >
            How It Works
          </a>
          <a
            href="#features"
            onClick={(e) => {
              e.preventDefault();
              closeMobileMenu();
              document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="flex items-center py-3 px-3 rounded-xl text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors min-h-[44px]"
          >
            Features
          </a>
          {isSignedIn && (
            <Link
              to="/history"
              onClick={closeMobileMenu}
              className="flex items-center py-3 px-3 rounded-xl text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors min-h-[44px]"
            >
              My History
            </Link>
          )}
        </div>
      )}
    </header>
  );
};

export default Header;
