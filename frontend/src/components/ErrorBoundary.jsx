import { Component } from "react";
import ServerError from "./ServerError.jsx";

/**
 * Catches any unhandled React render/lifecycle errors and shows the
 * ServerError page instead of a blank white crash screen.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Log to console so developers can still see the stack trace
    console.error("[ErrorBoundary] Uncaught render error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <ServerError
          onGoHome={() => {
            // Clear the error state and reload cleanly
            this.setState({ hasError: false });
            window.location.replace("/");
          }}
        />
      );
    }
    return this.props.children;
  }
}
