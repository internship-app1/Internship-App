import React from 'react';

const BrowserRouter = ({ children }: { children: React.ReactNode }) => <>{children}</>;
const Routes = ({ children }: { children: React.ReactNode }) => <>{children}</>;
const Route = ({ element }: { element?: React.ReactNode }) => <>{element}</>;
const Link = ({ children, to }: { children: React.ReactNode; to: string }) => (
  <a href={to}>{children}</a>
);
const Navigate = ({ to }: { to: string }) => <a href={to}>Navigate</a>;
const Outlet = () => <></>;
const useNavigate = () => jest.fn();
const useLocation = () => ({ pathname: '/', search: '', hash: '', state: null, key: 'default' });
const useParams = () => ({});
const useSearchParams = () => [new URLSearchParams(), jest.fn()];

export {
  BrowserRouter,
  Routes,
  Route,
  Link,
  Navigate,
  Outlet,
  useNavigate,
  useLocation,
  useParams,
  useSearchParams,
};
