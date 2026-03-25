import React, { useEffect, useState } from 'react';
import { useUser, UserButton, SignInButton } from '@clerk/react';
import { Link } from 'react-router-dom';
import { ThemeToggle } from './theme-toggle';
import { Sparkles } from 'lucide-react';

const Header: React.FC<{ forceSolid?: boolean }> = ({ forceSolid = false }) => {
  const { isSignedIn } = useUser();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 12);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 w-full transition-all duration-300 ${scrolled || forceSolid
          ? 'bg-white/90 dark:bg-neutral-950/90 backdrop-blur-md shadow-sm border-b border-neutral-200/60 dark:border-neutral-800/60'
          : 'bg-transparent'
        }`}
    >
      <div className="container flex h-16 items-center justify-between mx-auto px-6">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span
            className="text-xl font-bold text-neutral-950 dark:text-neutral-50"
            style={{ fontFamily: 'Sora, sans-serif' }}
          >
            internshipmatcher
          </span>
          <span className="text-xs font-bold text-cyan-500 align-super tracking-wide -ml-0.5">
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
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {isSignedIn ? (
            <UserButton />
          ) : (
            <SignInButton mode="modal">
              <button className="bg-violet-600 hover:bg-violet-700 text-white rounded-full px-5 py-2 text-sm font-semibold shadow-md shadow-violet-500/25 hover:shadow-violet-500/40 hover:-translate-y-0.5 transition-all">
                Sign In
              </button>
            </SignInButton>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
