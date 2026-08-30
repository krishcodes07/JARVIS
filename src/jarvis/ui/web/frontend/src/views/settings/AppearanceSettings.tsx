import React from 'react';
import { Check, Layers, Monitor, PanelLeft, Sliders, Sparkles, Volume2, Zap } from 'lucide-react';
import { JarvisBlob } from '../../components/JarvisBlob';
import { Row, Section, Toggle } from '../../components/ui';
import { useTheme } from '../../context/ThemeContext';
import { BACKGROUND_STYLES, BLOB_STYLES, THEME_LIST } from '../../theme/themes';
import { cn } from '../../utils/cn';

/**
 * Miniature swatch showing a theme's void / surface / accent triplet.
 *
 * Colours come straight from the theme table rather than from Tailwind classes,
 * because every tile has to render its *own* palette while the app is still
 * wearing the active one.
 */
const ThemeCard: React.FC<{
  label: string;
  description: string;
  tokens: Record<string, string>;
  selected: boolean;
  onSelect: () => void;
}> = ({ label, description, tokens, selected, onSelect }) => {
  const rgb = (token: string) => `rgb(${tokens[token]})`;

  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        'group relative flex flex-col rounded-2xl border p-3.5 text-left transition-all',
        selected
          ? 'border-accent/60 bg-surface-2 shadow-accent-sm ring-1 ring-accent/40'
          : 'border-subtle/10 bg-surface-2/30 hover:border-accent/30 hover:bg-surface-2/60'
      )}
    >
      {/* 3-swatch strip */}
      <div className="flex h-6 w-full overflow-hidden rounded-lg border border-subtle/15">
        <div className="flex-1" style={{ backgroundColor: rgb('bg-void') }} />
        <div className="flex-1" style={{ backgroundColor: rgb('bg-surface-1') }} />
        <div className="flex-1" style={{ backgroundColor: rgb('accent') }} />
      </div>

      <div className="mt-2.5 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-semibold text-content group-hover:text-accent-soft transition-colors">
            {label}
          </span>
          <span className="mt-0.5 block truncate text-[11px] text-content-muted">
            {description}
          </span>
        </div>
        {selected && <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" />}
      </div>
    </button>
  );
};

export const AppearanceSettings: React.FC = () => {
  const {
    theme,
    setTheme,
    blobStyle,
    setBlobStyle,
    backgroundStyle,
    setBackgroundStyle,
    backgroundOpacity,
    setBackgroundOpacity,
    enableAnimations,
    setEnableAnimations,
    soundEffects,
    setSoundEffects,
    sidebarExpanded,
    setSidebarExpanded,
  } = useTheme();

  return (
    <div className="space-y-7">
      <Section
        bare
        title="Theme"
        icon={<Sparkles />}
        description="Recolours the entire interface, including the orb and ambient background. Saved to your JARVIS config."
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {THEME_LIST.map((t) => (
            <ThemeCard
              key={t.id}
              label={t.label}
              description={t.description}
              tokens={t.tokens as unknown as Record<string, string>}
              selected={theme === t.id}
              onSelect={() => setTheme(t.id)}
            />
          ))}
        </div>
      </Section>

      <Section
        bare
        title="Orb style"
        icon={<Monitor />}
        description="How the JARVIS core renders. Each tile is the real renderer, drawn as a single static frame."
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {BLOB_STYLES.map((s) => {
            const selected = blobStyle === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setBlobStyle(s.id)}
                aria-pressed={selected}
                className={cn(
                  'flex flex-col items-center rounded-2xl border p-3 transition-all',
                  selected
                    ? 'border-accent/50 bg-accent/[0.07] shadow-accent-sm'
                    : 'border-subtle/10 bg-surface-2/40 hover:border-accent/25 hover:bg-surface-2/70'
                )}
              >
                <JarvisBlob size={92} styleOverride={s.id} hideFloor staticLevels paused />
                <span className="mt-1.5 text-[12px] font-semibold text-content">{s.label}</span>
                <span className="mt-0.5 text-center text-[10.5px] leading-tight text-content-muted">
                  {s.description}
                </span>
              </button>
            );
          })}
        </div>
      </Section>

      <Section
        bare
        title="Background"
        icon={<Layers />}
        description="Procedural WebGL shaders & Three.js canvas fields inspired by ThreeUI, featuring real-time pointer interactions and fluid ribbon optics."
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {BACKGROUND_STYLES.map((bg) => {
            const selected = backgroundStyle === bg.id;
            return (
              <button
                key={bg.id}
                onClick={() => setBackgroundStyle(bg.id)}
                aria-pressed={selected}
                className={cn(
                  'group relative flex flex-col justify-between overflow-hidden rounded-2xl border p-3.5 text-left transition-all',
                  selected
                    ? 'border-accent/60 bg-accent/[0.08] shadow-accent-sm ring-1 ring-accent/30'
                    : 'border-subtle/10 bg-surface-1/50 hover:border-accent/30 hover:bg-surface-1/80 hover:-translate-y-0.5'
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10.5px] font-mono font-medium uppercase tracking-wider text-accent">
                      {bg.family}
                    </span>
                    {bg.badge && (
                      <span className="rounded border border-accent/30 bg-accent/15 px-1.5 py-0.2 text-[9px] font-semibold text-accent-soft">
                        {bg.badge}
                      </span>
                    )}
                  </div>
                  {selected && <Check className="h-4 w-4 shrink-0 text-accent" />}
                </div>

                <div className="mt-2.5">
                  <span className="block text-[13px] font-semibold text-content group-hover:text-accent-soft transition-colors">
                    {bg.label}
                  </span>
                  <span className="mt-1 block text-[11px] leading-relaxed text-content-muted">
                    {bg.description}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Background Opacity Slider */}
        <div className="mt-4 rounded-2xl border border-subtle/12 bg-surface-1/60 p-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4 text-accent" />
              <span className="text-xs font-semibold text-content">Background Opacity</span>
            </div>
            <span className="rounded-md border border-accent/30 bg-accent/15 px-2 py-0.5 font-mono text-xs font-semibold text-accent-soft">
              {Math.round(backgroundOpacity * 100)}%
            </span>
          </div>

          <p className="mt-1 text-[11px] leading-relaxed text-content-muted">
            Adjust the visibility and intensity of the ambient ThreeUI background scene.
          </p>

          <div className="mt-3 flex items-center gap-3">
            <span className="font-mono text-[11px] font-medium text-content-muted">10%</span>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={backgroundOpacity}
              onChange={(e) => setBackgroundOpacity(parseFloat(e.target.value))}
              aria-label="Background opacity"
              className="h-2 flex-1 cursor-pointer appearance-none rounded-full bg-surface-2 accent-accent transition-all focus:outline-none focus:ring-2 focus:ring-accent/40"
            />
            <span className="font-mono text-[11px] font-medium text-content-muted">100%</span>
          </div>

          <div className="mt-3 flex items-center gap-2">
            {[0.25, 0.5, 0.75, 1.0].map((preset) => {
              const active = Math.abs(backgroundOpacity - preset) < 0.02;
              return (
                <button
                  key={preset}
                  onClick={() => setBackgroundOpacity(preset)}
                  className={cn(
                    'flex-1 rounded-xl border py-1.5 text-xs font-medium transition-all',
                    active
                      ? 'border-accent/60 bg-accent/20 font-semibold text-accent-soft shadow-accent-sm ring-1 ring-accent/30'
                      : 'border-subtle/10 bg-surface-2/40 text-content-muted hover:border-accent/30 hover:bg-surface-2/80 hover:text-content'
                  )}
                >
                  {Math.round(preset * 100)}%
                </button>
              );
            })}
          </div>
        </div>
      </Section>

      <Section title="Interface" icon={<Zap />}>
        <Row
          label="Animations"
          icon={<Zap />}
          description="Orb rotation, panel transitions, and shimmer effects. Turning this off freezes the canvas on a single frame."
          control={<Toggle checked={enableAnimations} onChange={setEnableAnimations} />}
        />
        <Row
          label="Sound effects"
          icon={<Volume2 />}
          description="Audio cues when a response starts and finishes."
          control={<Toggle checked={soundEffects} onChange={setSoundEffects} />}
        />
        <Row
          label="Expand sidebar by default"
          icon={<PanelLeft />}
          description="When off, the sidebar starts as a narrow icon rail."
          control={<Toggle checked={sidebarExpanded} onChange={setSidebarExpanded} />}
        />
      </Section>
    </div>
  );
};
