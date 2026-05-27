import React from 'react';
import { Link } from 'react-router-dom';
import { useUser, UserButton, SignInButton } from '@clerk/react';
import { Sparkles } from 'lucide-react';
import { Hero } from '../components/ui/animated-hero';
import { HonestStats } from '../components/HonestStats';
import { HowItActuallyWorks } from '../components/HowItActuallyWorks';
import { BuilderBlock } from '../components/BuilderBlock';
import { ClosingCTA } from '../components/ClosingCTA';

function Nav() {
  const { isSignedIn } = useUser();

  return (
    <header className="sticky top-0 z-50 border-b border-lp-border bg-bg/90 backdrop-blur-md">
      <div className="max-w-4xl mx-auto px-6 md:px-10 flex h-14 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 no-underline">
          <div className="h-6 w-6 rounded-md bg-ia flex items-center justify-center">
            <Sparkles className="h-3.5 w-3.5 text-bg" />
          </div>
          <span className="text-sm font-semibold text-text-primary">internshipmatcher</span>
        </Link>

        <nav className="flex items-center gap-5">
          {isSignedIn && (
            <Link
              to="/history"
              className="text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              History
            </Link>
          )}
          <Link
            to="/find"
            className="text-xs text-text-secondary hover:text-text-primary transition-colors"
          >
            Find
          </Link>
          {isSignedIn ? (
            <UserButton />
          ) : (
            <SignInButton mode="modal">
              <button className="text-xs bg-ia text-bg px-3 py-1.5 rounded-md font-semibold hover:bg-ia-hover transition-colors">
                Sign in
              </button>
            </SignInButton>
          )}
        </nav>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="border-t border-lp-border py-8">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-text-tertiary">
        <span className="font-medium text-text-secondary">internshipmatcher</span>
        <p>© 2025 internshipmatcher. Free to use.</p>
        <div className="flex gap-4">
          <button type="button" className="hover:text-text-secondary transition-colors">Privacy</button>
          <button type="button" className="hover:text-text-secondary transition-colors">Terms</button>
          <a
            href="https://github.com/Sujan30/jobbot"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-secondary transition-colors"
          >
            GitHub ↗
          </a>
        </div>
      </div>
    </footer>
  );
}

const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <Nav />
      <main className="max-w-4xl mx-auto px-6 md:px-10">
        <Hero />
        <HonestStats />
        <HowItActuallyWorks />
        <BuilderBlock />
        <ClosingCTA />
      </main>
      <div className="max-w-4xl mx-auto px-6 md:px-10">
        <Footer />
      </div>
    </div>
  );
};

export default LandingPage;
