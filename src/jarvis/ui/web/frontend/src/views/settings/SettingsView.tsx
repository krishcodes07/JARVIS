import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Bot,
  Database,
  Info,
  Layers,
  Palette,
  Plug,
  Send,
  Volume2,
  Wrench,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { SettingsTab } from '../../types';
import { cn } from '../../utils/cn';
import { IconButton } from '../../components/ui';
import { AboutSettings } from './AboutSettings';
import { AppearanceSettings } from './AppearanceSettings';
import { ConnectorsSettings } from './ConnectorsSettings';
import { MCPSettings } from './MCPSettings';
import { MemorySettings } from './MemorySettings';
import { ModelSettings } from './ModelSettings';
import { SkillsSettings } from './SkillsSettings';
import { ToolsSettings } from './ToolsSettings';
import { VoiceSettings } from './VoiceSettings';

interface NavItem {
  id: SettingsTab;
  label: string;
  hint: string;
  Icon: LucideIcon;
}

const NAV: NavItem[] = [
  { id: 'model', label: 'Model', hint: 'Providers, models, reasoning', Icon: Bot },
  { id: 'appearance', label: 'Appearance', hint: 'Theme, orb, motion', Icon: Palette },
  { id: 'voice', label: 'Voice', hint: 'Speech in and out', Icon: Volume2 },
  { id: 'memory', label: 'Memory & Safety', hint: 'Context window, guardrails', Icon: Database },
  { id: 'skills', label: 'Skills', hint: 'Loadable playbooks', Icon: Layers },
  { id: 'mcp', label: 'MCP Servers', hint: 'External tool servers', Icon: Plug },
  { id: 'connectors', label: 'Connectors', hint: 'Telegram, Discord', Icon: Send },
  { id: 'tools', label: 'Tools', hint: 'Built-in capabilities', Icon: Wrench },
  { id: 'about', label: 'About', hint: 'Version and health', Icon: Info },
];

const PANELS: Record<SettingsTab, React.FC> = {
  model: ModelSettings,
  appearance: AppearanceSettings,
  voice: VoiceSettings,
  memory: MemorySettings,
  skills: SkillsSettings,
  mcp: MCPSettings,
  connectors: ConnectorsSettings,
  tools: ToolsSettings,
  about: AboutSettings,
};

export interface SettingsViewProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: SettingsTab;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  isOpen,
  onClose,
  initialTab = 'model',
}) => {
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const { enableAnimations } = useTheme();

  // Re-open on whichever tab the caller deep-linked to.
  useEffect(() => {
    if (isOpen) setActiveTab(initialTab);
  }, [isOpen, initialTab]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  const active = NAV.find((n) => n.id === activeTab) ?? NAV[0];
  const Panel = PANELS[activeTab];
  const transition = enableAnimations ? { duration: 0.2, ease: [0.22, 1, 0.36, 1] } : { duration: 0 };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Settings"
          className="fixed inset-0 z-[80] flex flex-col bg-void"
          initial={{ opacity: 0, scale: 0.99 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.99 }}
          transition={transition}
        >
          {/* Header */}
          <header
            data-chrome
            className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-subtle/8 bg-surface-1/70 px-4 backdrop-blur-xl sm:px-6"
          >
            <div className="flex min-w-0 items-center gap-3">
              <h2 className="font-display text-sm font-bold uppercase tracking-[0.18em] text-content">
                Settings
              </h2>
              <span className="hidden truncate text-xs text-content-muted sm:block">
                {active.hint}
              </span>
            </div>
            <IconButton label="Close settings (Esc)" size="sm" tooltip="left" onClick={onClose}>
              <X />
            </IconButton>
          </header>

          {/* Mobile section scroller */}
          <div
            data-chrome
            className="scroll-area flex shrink-0 gap-1.5 overflow-x-auto border-b border-subtle/8 px-3 py-2 md:hidden"
          >
            {NAV.map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={cn(
                  'flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors',
                  activeTab === id
                    ? 'border-accent/30 bg-accent/12 text-accent'
                    : 'border-subtle/10 bg-surface-2/50 text-content-muted'
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </div>

          <div className="flex min-h-0 flex-1">
            {/* Desktop nav rail */}
            <nav
              data-chrome
              aria-label="Settings sections"
              className="scroll-area hidden w-60 shrink-0 overflow-y-auto border-r border-subtle/8 bg-surface-1/40 p-3 md:block"
            >
              {NAV.map(({ id, label, hint, Icon }) => {
                const isActive = activeTab === id;
                return (
                  <button
                    key={id}
                    onClick={() => setActiveTab(id)}
                    aria-current={isActive ? 'page' : undefined}
                    className={cn(
                      'group mb-0.5 flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors',
                      isActive ? 'bg-accent/12 text-content' : 'text-content-muted hover:bg-surface-2/60'
                    )}
                  >
                    <Icon
                      className={cn(
                        'mt-0.5 h-4 w-4 shrink-0 transition-colors',
                        isActive ? 'text-accent' : 'text-content-muted group-hover:text-content-secondary'
                      )}
                    />
                    <span className="min-w-0">
                      <span
                        className={cn(
                          'block text-[13px] font-medium',
                          isActive ? 'text-content' : 'text-content-secondary'
                        )}
                      >
                        {label}
                      </span>
                      <span className="mt-0.5 block truncate text-[11px] text-content-muted">
                        {hint}
                      </span>
                    </span>
                  </button>
                );
              })}
            </nav>

            {/* Panel */}
            <div className="scroll-area min-w-0 flex-1 overflow-y-auto">
              <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-8 sm:py-8">
                <div className="mb-6">
                  <h1 className="flex items-center gap-2.5 font-display text-xl font-bold text-content">
                    <active.Icon className="h-5 w-5 text-accent" />
                    {active.label}
                  </h1>
                  <p className="mt-1 text-sm text-content-muted">{active.hint}</p>
                </div>
                <Panel />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
