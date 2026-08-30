import React from 'react';
import {
  Bot,
  Brain,
  Layers,
  MessageSquare,
  Palette,
  Plug,
  Trash2,
  Wrench,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../utils/cn';

export interface SlashCommand {
  name: string;
  description: string;
  Icon: LucideIcon;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  { name: '/new', description: 'Start a new conversation', Icon: MessageSquare },
  { name: '/models', description: 'Browse and switch models', Icon: Bot },
  { name: '/effort', description: 'Set reasoning effort', Icon: Brain },
  { name: '/mcp', description: 'Manage MCP servers', Icon: Plug },
  { name: '/skills', description: 'View and toggle skill packs', Icon: Layers },
  { name: '/theme', description: 'Themes and orb styles', Icon: Palette },
  { name: '/tools', description: 'Browse available tools', Icon: Wrench },
  { name: '/clear', description: 'Clear the on-screen transcript', Icon: Trash2 },
];

export function filterSlashCommands(query: string): SlashCommand[] {
  const q = query.trim().toLowerCase();
  if (!q.startsWith('/')) return [];
  const bare = q.slice(1);
  if (!bare) return SLASH_COMMANDS;
  return SLASH_COMMANDS.filter(
    (cmd) => cmd.name.slice(1).startsWith(bare) || cmd.description.toLowerCase().includes(bare)
  );
}

export interface SlashCommandMenuProps {
  commands: SlashCommand[];
  activeIndex: number;
  onSelect: (name: string) => void;
  onHover: (index: number) => void;
}

/**
 * Command palette above the prompt box. Highlight state is owned by the prompt
 * box so arrow keys typed into the textarea drive it.
 */
export const SlashCommandMenu: React.FC<SlashCommandMenuProps> = ({
  commands,
  activeIndex,
  onSelect,
  onHover,
}) => {
  if (commands.length === 0) return null;

  return (
    <div
      role="listbox"
      aria-label="Slash commands"
      className="panel absolute bottom-full left-0 right-0 z-50 mb-2 animate-slide-up overflow-hidden rounded-2xl shadow-panel"
    >
      <div className="border-b border-subtle/8 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-content-muted">
        Commands
      </div>
      <div className="scroll-area max-h-64 overflow-y-auto p-1.5">
        {commands.map((cmd, i) => (
          <button
            key={cmd.name}
            role="option"
            aria-selected={i === activeIndex}
            onMouseEnter={() => onHover(i)}
            onClick={() => onSelect(cmd.name)}
            className={cn(
              'flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left transition-colors',
              i === activeIndex ? 'bg-accent/12' : 'hover:bg-surface-2/60'
            )}
          >
            <span
              className={cn(
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border',
                i === activeIndex
                  ? 'border-accent/30 bg-accent/15 text-accent'
                  : 'border-subtle/10 bg-surface-2/70 text-content-muted'
              )}
            >
              <cmd.Icon className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block font-mono text-xs font-semibold text-content">{cmd.name}</span>
              <span className="block truncate text-[11px] text-content-muted">
                {cmd.description}
              </span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
