import { AlertTriangle } from "lucide-react";
import { Component, ReactNode } from "react";

type ErrorBoundaryProps = {
  children: ReactNode;
};

type ErrorBoundaryState = {
  error: Error | null;
};

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="error-boundary">
          <AlertTriangle size={28} />
          <h1>Something went wrong.</h1>
          <p>{this.state.error.message}</p>
        </main>
      );
    }
    return this.props.children;
  }
}
