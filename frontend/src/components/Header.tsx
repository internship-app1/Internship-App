import React, { useEffect, useState } from 'react';
import { useUser, UserButton, SignInButton } from '@clerk/react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Sparkles, Menu, X } from 'lucide-react';

const Header: React.FC<{ forceSolid?: boolean }> = ({ forceSolid = false }) => {
  const { isSignedIn } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleSectionNav = (sectionId: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    if (location.pathname === '/') {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' });
    } else {
      navigate(`/#${sectionId}`);
    }
    setMobileMenuOpen(false);
  };

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const solid = scrolled || forceSolid || mobileMenuOpen;

  return (
    <header
      className={`sticky top-0 z-50 w-full transition-all duration-300 ${
        solid ? 'bg-bg/95 backdrop-blur-md border-b border-lp-border' : 'bg-transparent'
      }`}
    >
      <div className="max-w-4xl mx-auto flex h-14 items-center justify-between px-6 md:px-10">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 min-w-0 no-underline">
          <div className="h-7 w-7 flex-shrink-0 rounded-lg bg-ia flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-bg" />
          </div>
          <span className="text-base font-semibold text-text-primary truncate">
            internshipmatcher
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          <a
            href="/#how-it-works"
            onClick={handleSectionNav('how-it-works')}
            className="text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            How It Works
          </a>
          <a
            href="/#features"
            onClick={handleSectionNav('features')}
            className="text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            Features
          </a>
          {isSignedIn && (
            <Link
              to="/history"
              className="text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              My History
            </Link>
          )}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {isSignedIn ? (
            <UserButton />
          ) : (
            <SignInButton mode="modal">
              <button className="bg-ia text-bg px-4 py-2 rounded-lg text-sm font-semibold hover:bg-ia-hover transition-colors min-h-[44px]">
                Sign In
              </button>
            </SignInButton>
          )}
          <button
            className="md:hidden flex items-center justify-center rounded-lg p-2 text-text-secondary hover:text-text-primary hover:bg-surface transition-colors min-h-[44px] min-w-[44px]"
            onClick={() => setMobileMenuOpen((o) => !o)}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-lp-border bg-bg/95 backdrop-blur-md px-6 py-4 space-y-1">
          <a
            href="/#how-it-works"
            onClick={handleSectionNav('how-it-works')}
            className="flex items-center py-3 px-3 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-surface transition-colors min-h-[44px]"
          >
            How It Works
          </a>
          <a
            href="/#features"
            onClick={handleSectionNav('features')}
            className="flex items-center py-3 px-3 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-surface transition-colors min-h-[44px]"
          >
            Features
          </a>
          {isSignedIn && (
            <Link
              to="/history"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center py-3 px-3 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-surface transition-colors min-h-[44px]"
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
