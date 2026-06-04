/* eslint-disable react-refresh/only-export-components --
 * This is a test-only mock for `@clerk/react`: it must export the auth hooks and
 * state helpers alongside the stub components, and Fast Refresh does not apply to
 * test mocks. */
/**
 * Controllable mock for `@clerk/react` used by component tests.
 *
 * The real Clerk provider needs a live publishable key + network, so tests mock
 * it (wired in `src/test/setup.ts` via `vi.mock`). `setClerkState` lets a test
 * flip between signed-in / signed-out / still-loading to exercise the
 * `ProtectedRoute` and auth flows (FE-019).
 */
import type { ReactNode } from 'react';

export interface ClerkState {
  isLoaded: boolean;
  isSignedIn: boolean;
  user: { id: string } | null;
}

export const clerkState: ClerkState = {
  isLoaded: true,
  isSignedIn: true,
  user: { id: 'user_test' },
};

export function setClerkState(next: Partial<ClerkState>): void {
  Object.assign(clerkState, next);
}

export function resetClerkState(): void {
  setClerkState({
    isLoaded: true,
    isSignedIn: true,
    user: { id: 'user_test' },
  });
}

export function useUser() {
  return {
    isLoaded: clerkState.isLoaded,
    isSignedIn: clerkState.isSignedIn,
    user: clerkState.user,
  };
}

export function useAuth() {
  return {
    isLoaded: clerkState.isLoaded,
    isSignedIn: clerkState.isSignedIn,
    userId: clerkState.user?.id ?? null,
    getToken: () => Promise.resolve('test-token'),
  };
}

export function ClerkProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

export function UserButton() {
  return <button type="button">user</button>;
}

export function SignIn() {
  return <div data-testid="clerk-sign-in">Sign in</div>;
}
