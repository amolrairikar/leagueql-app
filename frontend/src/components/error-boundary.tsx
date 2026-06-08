import { Component, type ErrorInfo, type ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import { logger } from '@/lib/logger';

interface Props {
  children: ReactNode;
  /** Rendered instead of the default fallback when provided. */
  fallback?: ReactNode;
  /**
   * When any value in this array changes (shallow compare), a currently-caught
   * error is cleared so the children re-render. Use this to reset the boundary
   * on navigation (e.g. `resetKeys={[location.pathname]}`) — otherwise the
   * error state persists across route changes since the boundary instance is
   * reused rather than remounted.
   */
  resetKeys?: unknown[];
}

interface State {
  error: Error | null;
}

const resetKeysChanged = (prev: unknown[] = [], next: unknown[] = []) =>
  prev.length !== next.length ||
  prev.some((key, i) => !Object.is(key, next[i]));

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    logger.error('Uncaught render error', error, info.componentStack);
  }

  componentDidUpdate(prevProps: Props) {
    if (
      this.state.error &&
      resetKeysChanged(prevProps.resetKeys, this.props.resetKeys)
    ) {
      this.reset();
    }
  }

  reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center gap-4 p-12 text-center">
          <p className="text-lg font-semibold text-foreground">
            Something went wrong
          </p>
          <p className="text-sm text-muted-foreground max-w-sm">
            {this.state.error.message || 'An unexpected error occurred.'}
          </p>
          <Button variant="outline" onClick={this.reset}>
            Try again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
