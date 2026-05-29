import React from 'react';
import Header from '../components/Header';
import Logo from '../components/Logo';
import { Hero } from '../components/ui/animated-hero';
import { HonestStats } from '../components/HonestStats';
import { HowItActuallyWorks } from '../components/HowItActuallyWorks';
import { BuilderBlock } from '../components/BuilderBlock';
import { ClosingCTA } from '../components/ClosingCTA';

function Footer() {
  return (
    <footer className="border-t border-lp-border py-6">
      <div className="max-w-[860px] mx-auto px-6">
        <p className="font-mono text-[10px] text-text-tertiary text-center tracking-wide flex items-center justify-center gap-1.5 flex-wrap">
          <Logo size={14} className="inline-block shrink-0" />
          © 2026 internshipmatcher · set in Source Serif 4 &amp; JetBrains Mono ·{' '}
          <button type="button" className="hover:text-text-secondary transition-colors">
            privacy
          </button>{' '}
          ·{' '}
          <button type="button" className="hover:text-text-secondary transition-colors">
            terms
          </button>{' '}
          ·{' '}
          <a
            href="https://github.com/Sujan30/jobbot"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-secondary transition-colors"
          >
            github ↗
          </a>
        </p>
      </div>
    </footer>
  );
}

const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <Header />
      <main className="max-w-[860px] mx-auto px-6">
        <Hero />
        <HonestStats />
        <HowItActuallyWorks />
        <BuilderBlock />
        <ClosingCTA />
      </main>
      <Footer />
    </div>
  );
};

export default LandingPage;
