import React from 'react';
import { useUser, UserButton, SignInButton } from '@clerk/react';
import { ThemeToggle } from './theme-toggle';
import { Button } from './ui/button';
import { Briefcase, LogIn } from 'lucide-react';

const Header: React.FC = () => {
  const { isSignedIn } = useUser();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-2">
          <Briefcase className="h-6 w-6" />
          <span className="text-xl font-bold">InternMatch AI</span>
        </div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          {isSignedIn ? (
            <UserButton />
          ) : (
            <SignInButton mode="modal">
              <Button size="sm">
                <LogIn className="h-4 w-4 mr-2" />
                Sign In
              </Button>
            </SignInButton>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
