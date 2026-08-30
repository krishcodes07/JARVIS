/**
 * Canvas renderers for the JARVIS orb.
 *
 * Each renderer draws exactly one frame and is fully driven by the `OrbFrame`
 * it receives — no module state — so the same function can paint a 320px hero,
 * a 40px avatar, or a static single frame when animations are disabled.
 *
 * Colours arrive as comma-joined RGB triplets ("139, 92, 246") so they can be
 * interpolated into `rgba()` at any alpha; canvas has no access to the CSS
 * custom properties the rest of the app uses.
 */

import { BlobStyle, UITheme } from '../../types';
import { DEFAULT_THEME, THEMES, ThemeTokens } from '../../theme/themes';

export interface OrbPalette {
  accent: string;
  accentSoft: string;
  accentGlow: string;
  void: string;
  surface: string;
}

export interface OrbFrame {
  ctx: CanvasRenderingContext2D;
  width: number;
  height: number;
  /** Centre of the orb, in CSS pixels. */
  cx: number;
  cy: number;
  radius: number;
  /** Monotonically increasing seconds-ish clock. */
  time: number;
  rotation: number;
  /** Smoothed microphone amplitude, 0…1. Always 0 outside voice mode. */
  amp: number;
  palette: OrbPalette;
  /** Draw the reflective floor rings beneath the orb. */
  showFloor: boolean;
}

const tripleOf = (tokens: ThemeTokens, key: keyof ThemeTokens): string =>
  tokens[key].split(' ').join(', ');

export function buildPalette(theme: UITheme): OrbPalette {
  const tokens = (THEMES[theme] ?? THEMES[DEFAULT_THEME]).tokens;
  return {
    accent: tripleOf(tokens, 'accent'),
    accentSoft: tripleOf(tokens, 'accent-soft'),
    accentGlow: tripleOf(tokens, 'accent-glow'),
    void: tripleOf(tokens, 'bg-void'),
    surface: tripleOf(tokens, 'bg-surface-1'),
  };
}

const rgba = (triple: string, alpha: number) => `rgba(${triple}, ${alpha})`;

// ─── Shared pieces ──────────────────────────────────────────────

/** Elliptical contact glow + ripple rings (disabled to remove bottom circles). */
function drawFloor(_f: OrbFrame): void {
  // Bottom circles removed
}

/** Atmospheric bloom around the silhouette (disabled to remove outer glow from the orb). */
function drawCorona(_f: OrbFrame, _scale = 1.55): void {
  // Outer glow removed
}

/** Dark sphere body, lit from the upper left. */
function drawBody(f: OrbFrame): void {
  const { ctx, cx, cy, radius, palette } = f;
  const body = ctx.createRadialGradient(
    cx - radius * 0.3,
    cy - radius * 0.3,
    0,
    cx,
    cy,
    radius
  );
  body.addColorStop(0, rgba(palette.surface, 0.95));
  body.addColorStop(0.7, rgba(palette.void, 0.98));
  body.addColorStop(1, rgba(palette.void, 1));

  ctx.fillStyle = body;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.fill();
}

/** Bright limb around the edge, sold separately from the body fill. */
function drawRim(f: OrbFrame): void {
  const { ctx, cx, cy, radius, palette, amp } = f;
  const rim = ctx.createRadialGradient(cx, cy, radius * 0.82, cx, cy, radius);
  rim.addColorStop(0, 'rgba(0, 0, 0, 0)');
  rim.addColorStop(0.6, rgba(palette.accentGlow, 0.25));
  rim.addColorStop(0.9, rgba(palette.accent, 0.7));
  rim.addColorStop(1, rgba(palette.accentSoft, 0.95));

  ctx.fillStyle = rim;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.strokeStyle = rgba(palette.accentSoft, 0.75 + amp * 0.25);
  ctx.lineWidth = 1.4;
  ctx.stroke();
}

// ─── hologram ───────────────────────────────────────────────────

/** The signature look: 16 spherical helices woven across a dark sphere. */
function renderHologram(f: OrbFrame): void {
  const { ctx, cx, cy, radius, rotation, palette, amp } = f;

  if (f.showFloor) drawFloor(f);
  drawCorona(f);
  drawBody(f);

  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.clip();

  const streamlines = 16;
  const steps = 60;

  const stroke = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
  stroke.addColorStop(0, rgba(palette.accentGlow, 0.85));
  stroke.addColorStop(0.5, rgba(palette.accent, 0.95));
  stroke.addColorStop(1, rgba(palette.accentSoft, 0.9));

  for (let s = 0; s < streamlines; s++) {
    const phase = (s / streamlines) * Math.PI * 2 + rotation;
    ctx.beginPath();
    let started = false;

    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * Math.PI - Math.PI / 2;
      const helix = phase + t * 2.2;

      const x3 = Math.cos(t) * Math.sin(helix);
      const y3 = Math.sin(t);
      const z3 = Math.cos(t) * Math.cos(helix);

      // Hide the far side of the sphere so the weave reads as 3D.
      if (z3 > -0.2) {
        const sx = cx + x3 * radius;
        const sy = cy + y3 * radius * 0.96;
        if (started) ctx.lineTo(sx, sy);
        else {
          ctx.moveTo(sx, sy);
          started = true;
        }
      } else {
        started = false;
      }
    }

    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1.6 + amp * 1.5;
    ctx.stroke();
  }

  drawRim(f);
  ctx.restore();
}

// ─── arc_reactor ────────────────────────────────────────────────

/** Concentric rings with segmented coils and a blown-out white core. */
function renderArcReactor(f: OrbFrame): void {
  const { ctx, cx, cy, radius, rotation, palette, amp, time } = f;

  if (f.showFloor) drawFloor(f);
  drawCorona(f, 1.45);
  drawBody(f);

  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.clip();

  // Segmented coil ring
  const coils = 10;
  const coilR = radius * 0.72;
  for (let i = 0; i < coils; i++) {
    const a0 = (i / coils) * Math.PI * 2 + rotation * 0.35;
    const a1 = a0 + (Math.PI * 2) / coils - 0.14;
    ctx.beginPath();
    ctx.arc(cx, cy, coilR, a0, a1);
    ctx.strokeStyle = rgba(palette.accentSoft, 0.55 + amp * 0.35);
    ctx.lineWidth = radius * 0.1;
    ctx.lineCap = 'butt';
    ctx.stroke();
  }

  // Static guide rings
  for (const scale of [0.86, 0.58, 0.44]) {
    ctx.beginPath();
    ctx.arc(cx, cy, radius * scale, 0, Math.PI * 2);
    ctx.strokeStyle = rgba(palette.accent, 0.35);
    ctx.lineWidth = 1.2;
    ctx.stroke();
  }

  // Triangular core cage, counter-rotating
  const cage = radius * 0.34;
  ctx.beginPath();
  for (let i = 0; i < 3; i++) {
    const a = -rotation * 0.6 + (i / 3) * Math.PI * 2;
    const px = cx + Math.cos(a) * cage;
    const py = cy + Math.sin(a) * cage;
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.strokeStyle = rgba(palette.accentSoft, 0.7);
  ctx.lineWidth = 1.6;
  ctx.stroke();

  // Hot core
  const breathe = 1 + Math.sin(time * 3) * 0.06 + amp * 0.3;
  const coreR = radius * 0.3 * breathe;
  const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR);
  core.addColorStop(0, 'rgba(255, 255, 255, 1)');
  core.addColorStop(0.35, rgba(palette.accentSoft, 0.95));
  core.addColorStop(0.72, rgba(palette.accent, 0.55));
  core.addColorStop(1, 'rgba(0, 0, 0, 0)');
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
  ctx.fill();

  drawRim(f);
  ctx.restore();
}

// ─── particle ───────────────────────────────────────────────────

const PARTICLE_COUNT = 220;

/**
 * Deterministic point cloud on a Fibonacci sphere, rotated about Y each frame.
 * Deterministic placement means a static frame (animations off) still looks
 * identical every mount.
 */
function renderParticle(f: OrbFrame): void {
  const { ctx, cx, cy, radius, rotation, palette, amp, time } = f;

  if (f.showFloor) drawFloor(f);
  drawCorona(f, 1.5);

  const golden = Math.PI * (3 - Math.sqrt(5));
  const jitter = 1 + amp * 0.35;

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const y = 1 - (i / (PARTICLE_COUNT - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = golden * i + rotation;

    // Slow per-particle breathing keeps the cloud alive without extra state.
    const wobble = 1 + Math.sin(time * 1.6 + i * 0.35) * 0.04;
    const shell = radius * 0.92 * wobble * jitter;

    const x3 = Math.cos(theta) * r;
    const z3 = Math.sin(theta) * r;

    const depth = (z3 + 1) / 2; // 0 = far, 1 = near
    const sx = cx + x3 * shell;
    const sy = cy + y * shell * 0.96;

    const size = 0.6 + depth * 1.9 + amp * 1.2;
    const alpha = 0.12 + depth * 0.72;

    ctx.beginPath();
    ctx.arc(sx, sy, size, 0, Math.PI * 2);
    ctx.fillStyle = rgba(depth > 0.62 ? palette.accentSoft : palette.accent, alpha);
    ctx.fill();
  }

  // Faint inner mass so the cloud reads as a volume, not a ring.
  const inner = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 0.8);
  inner.addColorStop(0, rgba(palette.accent, 0.22 + amp * 0.2));
  inner.addColorStop(1, 'rgba(0, 0, 0, 0)');
  ctx.fillStyle = inner;
  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.8, 0, Math.PI * 2);
  ctx.fill();
}

// ─── pulse ──────────────────────────────────────────────────────

const SHELLS = 5;

/** Expanding concentric shells radiating from a bright core. */
function renderPulse(f: OrbFrame): void {
  const { ctx, cx, cy, radius, palette, amp, time } = f;

  if (f.showFloor) drawFloor(f);
  drawCorona(f, 1.4);

  const speed = 0.28 + amp * 0.25;

  for (let s = 0; s < SHELLS; s++) {
    // Each shell's phase cycles 0→1 and restarts, offset per shell.
    const phase = (time * speed + s / SHELLS) % 1;
    const r = radius * (0.18 + phase * 1.05);
    const fade = 1 - phase;

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = rgba(palette.accent, fade * (0.5 + amp * 0.4));
    ctx.lineWidth = 1 + fade * (2 + amp * 2);
    ctx.stroke();
  }

  // Core
  const breathe = 1 + Math.sin(time * 2.4) * 0.08 + amp * 0.4;
  const coreR = radius * 0.26 * breathe;
  const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR);
  core.addColorStop(0, 'rgba(255, 255, 255, 0.98)');
  core.addColorStop(0.4, rgba(palette.accentSoft, 0.9));
  core.addColorStop(1, rgba(palette.accent, 0));
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
  ctx.fill();

  // Thin containment ring at the nominal radius
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.strokeStyle = rgba(palette.accentSoft, 0.35 + amp * 0.3);
  ctx.lineWidth = 1.2;
  ctx.stroke();
}

export const ORB_RENDERERS: Record<BlobStyle, (frame: OrbFrame) => void> = {
  hologram: renderHologram,
  arc_reactor: renderArcReactor,
  particle: renderParticle,
  pulse: renderPulse,
};
