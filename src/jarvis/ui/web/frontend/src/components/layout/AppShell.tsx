import React from 'react';
import { useTheme } from '../../context/ThemeContext';
import { ThreeBackground } from '../ThreeBackground';
import { cn } from '../../utils/cn';

export interface AppShellProps {
  sidebar: React.ReactNode;
  topBar: React.ReactNode;
  children: React.ReactNode;
  /**
   * Full-strength ambient background. The hero empty state wants the background
   * at full power; a running conversation dims it so prose stays readable.
   */
  ambient?: 'full' | 'dim';
}

/**
 * Two-column application frame. The ThreeUI ambient background lives here (behind
 * everything, `pointer-events-none`) rather than in the chat view, so it stays
 * put while the transcript scrolls.
 */
export const AppShell: React.FC<AppShellProps> = ({
  sidebar,
  topBar,
  children,
  ambient = 'full',
}) => {
  const { backgroundStyle, backgroundOpacity, sidebarExpanded } = useTheme();

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-void text-content">
      {/* Ambient background layer with user-configured opacity */}
      <div
        aria-hidden
        style={{
          left: sidebarExpanded ? 'var(--sidebar-width, 264px)' : '0px',
          opacity: backgroundOpacity,
        }}
        className="pointer-events-none absolute inset-y-0 right-0 z-0 overflow-hidden transition-[left,opacity] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
      >
        <ThreeBackground style={backgroundStyle} ambient={ambient} />
      </div>

      {sidebar}

      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        {topBar}
        <main className="relative flex min-h-0 flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
};

