import React, { useEffect, useRef } from 'react';
import { useJarvis } from '../context/JarvisContext';
import { useTheme } from '../context/ThemeContext';
import { BlobStyle } from '../types';
import { cn } from '../utils/cn';
import { buildPalette, ORB_RENDERERS, OrbFrame } from './orb/orbRenderers';

export interface JarvisBlobProps {
  size?: number;
  className?: string;
  /** Larger presentation used by the voice overlay. */
  isExpanded?: boolean;
  onClick?: () => void;
  /** Override the user's configured orb style (used by the style picker). */
  styleOverride?: BlobStyle;
  /** Suppress the reflective floor (avatars, picker tiles). */
  hideFloor?: boolean;
  /** Ignore audio reactivity even during voice mode. */
  staticLevels?: boolean;
  /**
   * Draw one frame and stop. Used for avatars and picker tiles — a transcript
   * with 40 messages must not spin up 40 animation loops.
   */
  paused?: boolean;
  label?: string;
}

/**
 * Canvas-rendered JARVIS orb.
 *
 * The animation loop is deliberately insulated from React: audio levels arrive
 * through a ref subscription and the palette lives in a ref, so neither a 60 fps
 * microphone stream nor a theme switch re-creates the canvas. Only structural
 * props (size, style, animation preference) re-run the effect.
 */
export const JarvisBlob: React.FC<JarvisBlobProps> = ({
  size = 200,
  className,
  isExpanded = false,
  onClick,
  styleOverride,
  hideFloor,
  staticLevels,
  paused,
  label = 'JARVIS',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { isVoiceMode, subscribeToAudioLevels } = useJarvis();
  const { theme, blobStyle, enableAnimations } = useTheme();

  const activeStyle = styleOverride ?? blobStyle;
  const dimension = isExpanded ? Math.round(size * 1.6) : size;

  // Smoothed amplitude, written by the audio subscription and read per frame.
  const ampRef = useRef(0);
  const paletteRef = useRef(buildPalette(theme));

  useEffect(() => {
    paletteRef.current = buildPalette(theme);
  }, [theme]);

  // Reactivity is only meaningful while the mic is live.
  const reactive = isVoiceMode && !staticLevels && !paused;
  const animated = enableAnimations && !paused;

  useEffect(() => {
    if (!reactive) {
      ampRef.current = 0;
      return;
    }
    return subscribeToAudioLevels((data) => {
      if (!data.length) return;
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i];
      const next = sum / data.length / 255;
      // Low-pass the level so the orb glides instead of jittering.
      ampRef.current = ampRef.current * 0.7 + next * 0.3;
    });
  }, [reactive, subscribeToAudioLevels]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = dimension * dpr;
    canvas.height = dimension * dpr;
    canvas.style.width = `${dimension}px`;
    canvas.style.height = `${dimension}px`;

    const render = ORB_RENDERERS[activeStyle] ?? ORB_RENDERERS.hologram;

    let frameId: number | null = null;
    let time = 0;
    let rotation = 0;

    const paint = () => {
      const amp = ampRef.current;
      const pulse = 1 + Math.sin(time * 2.5) * 0.025 + amp * 0.25;

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, dimension, dimension);

      const frame: OrbFrame = {
        ctx,
        width: dimension,
        height: dimension,
        cx: dimension / 2,
        cy: dimension / 2,
        radius: dimension * 0.42 * pulse,
        time,
        rotation,
        amp,
        palette: paletteRef.current,
        showFloor: false,
      };

      render(frame);
      ctx.restore();
    };

    if (!animated) {
      // Honour the motion preference with a single representative frame.
      time = 1.2;
      rotation = 0.8;
      paint();
      return;
    }

    const loop = () => {
      time += 0.018;
      rotation += 0.015;
      paint();
      frameId = requestAnimationFrame(loop);
    };
    frameId = requestAnimationFrame(loop);

    return () => {
      if (frameId !== null) cancelAnimationFrame(frameId);
    };
    // `theme` is a dependency so a paused/static orb repaints on a theme switch;
    // the animated loop reads the palette from a ref and would repaint anyway.
  }, [dimension, activeStyle, animated, hideFloor, isExpanded, theme]);

  const interactive = !!onClick;

  return (
    <div
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-label={interactive ? label : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={cn(
        'relative inline-flex items-center justify-center select-none',
        interactive &&
          'cursor-pointer transition-transform duration-200 hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-full',
        className
      )}
    >
      <canvas ref={canvasRef} aria-hidden />
    </div>
  );
};

/** Small non-interactive orb used as the assistant avatar in the transcript. */
export const OrbAvatar: React.FC<{ size?: number; className?: string }> = ({
  size = 28,
  className,
}) => (
  <JarvisBlob
    size={size}
    hideFloor
    staticLevels
    paused
    className={cn('shrink-0', className)}
  />
);
