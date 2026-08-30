import React, { Component, ErrorInfo, ReactNode, useEffect, useRef } from 'react';
import {
  PredictiveArcCanvas,
  DotMatrixBackground,
  ConstellationField,
  CrtBackground,
  FlowField,
} from '@designcodeio/threeui';
import { BackgroundStyle } from '../types';
import { cn } from '../utils/cn';

interface ErrorBoundaryProps {
  fallback: ReactNode;
  children: ReactNode;
  resetKey?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class BackgroundErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.warn('ThreeUI background render failed, falling back to classic grid:', error, info);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export interface ThreeBackgroundProps {
  style: BackgroundStyle;
  ambient?: 'full' | 'dim';
  className?: string;
}

/**
 * Classic JARVIS perspective grid floor & horizon glow fallback.
 */
const ClassicGrid: React.FC<{ ambient?: 'full' | 'dim' }> = ({ ambient }) => (
  <div
    className={cn(
      'absolute inset-0 z-0 overflow-hidden transition-opacity duration-700',
      ambient === 'dim' && 'ambient-dim'
    )}
  >
    <div className="perspective-container absolute inset-0 overflow-hidden">
      <div className="grid-floor" />
    </div>
    <div className="horizon-glow" />
    <div className="fog-right" />
  </div>
);

export const ThreeBackground: React.FC<ThreeBackgroundProps> = ({
  style,
  ambient = 'full',
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Forward pointer movements from window so the WebGL canvas smoothly tracks cursor anywhere on screen
  useEffect(() => {
    if (style === 'classic') return;

    const onPointerMove = (e: PointerEvent) => {
      // Ignore synthetic events to prevent infinite dispatch loops
      if (!e.isTrusted) return;

      const target =
        containerRef.current?.querySelector<HTMLElement>('.threeui-background canvas') ||
        containerRef.current?.querySelector<HTMLElement>('.threeui-background');

      if (target && e.target !== target) {
        target.dispatchEvent(
          new PointerEvent('pointermove', {
            clientX: e.clientX,
            clientY: e.clientY,
            bubbles: false,
            cancelable: false,
          })
        );
      }
    };

    window.addEventListener('pointermove', onPointerMove, { passive: true });
    return () => window.removeEventListener('pointermove', onPointerMove);
  }, [style]);

  const renderContent = () => {
    switch (style) {
      case 'ribbon-field':
        return (
          <PredictiveArcCanvas
            variant="ribbon-field"
            speed={1.0}
            pointerAmount={1.15}
            brightness={1.05}
            opacity={1.0}
          />
        );
      case 'amber-halftone':
        return <PredictiveArcCanvas variant="amber-halftone" />;
      case 'void-field':
        return <PredictiveArcCanvas variant="void-field" />;
      case 'halftone-flow':
        return <PredictiveArcCanvas variant="halftone-flow" />;
      case 'data-pixel':
        return <PredictiveArcCanvas variant="data-pixel" />;
      case 'dot-matrix':
        return <DotMatrixBackground />;
      case 'constellation':
        return <ConstellationField />;
      case 'crt':
        return <CrtBackground />;
      case 'flow-field':
        return <FlowField />;
      case 'classic':
      default:
        return <ClassicGrid ambient={ambient} />;
    }
  };

  return (
    <div
      ref={containerRef}
      className={cn('relative h-full w-full overflow-hidden bg-void', className)}
    >
      <BackgroundErrorBoundary fallback={<ClassicGrid ambient={ambient} />} resetKey={style}>
        {renderContent()}
      </BackgroundErrorBoundary>

      {/* Subtle vignette & bottom gradient to keep content perfectly legible */}
      <div
        className={cn(
          'pointer-events-none absolute inset-0 z-10 transition-opacity duration-700',
          ambient === 'dim'
            ? 'bg-gradient-to-t from-bg-void via-bg-void/45 to-transparent'
            : 'bg-gradient-to-t from-bg-void/80 via-transparent to-transparent'
        )}
      />
    </div>
  );
};
