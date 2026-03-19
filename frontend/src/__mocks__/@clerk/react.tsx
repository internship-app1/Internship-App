import React from 'react';

const ClerkProvider = ({ children }: { children: React.ReactNode }) => <>{children}</>;
const SignInButton = ({ children }: { children?: React.ReactNode }) => (
  <button>{children || 'Sign In'}</button>
);
const SignOutButton = ({ children }: { children?: React.ReactNode }) => (
  <button>{children || 'Sign Out'}</button>
);
const UserButton = () => <div>UserButton</div>;
const SignIn = () => <div>Sign In</div>;
const SignUp = () => <div>Sign Up</div>;
const useUser = () => ({ isSignedIn: false, user: null, isLoaded: true });
const useAuth = () => ({
  isSignedIn: false,
  isLoaded: true,
  userId: null,
  getToken: jest.fn().mockResolvedValue(null),
});
const useClerk = () => ({ signOut: jest.fn(), openSignIn: jest.fn() });

export {
  ClerkProvider,
  SignInButton,
  SignOutButton,
  UserButton,
  SignIn,
  SignUp,
  useUser,
  useAuth,
  useClerk,
};
