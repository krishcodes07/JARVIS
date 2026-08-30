/**
 * JARVIS Theme Tokens
 *
 * Every colour in the app resolves through a CSS custom property declared here.
 * Values are space-separated RGB triplets ("139 92 246") so Tailwind can apply
 * its own alpha channel via `rgb(var(--accent) / <alpha-value>)`.
 */

import { BackgroundStyle, BlobStyle, UITheme } from '../types';

export interface ThemeTokens {
  /** Page backdrop, darkest layer. */
  'bg-void': string;
  /** Elevated panels (sidebar, cards). */
  'bg-surface-1': string;
  /** Inputs, hover states. */
  'bg-surface-2': string;
  /** Deepest inset wells (code blocks, tracks). */
  'bg-surface-3': string;

  'border-subtle': string;
  'border-strong': string;

  'text-primary': string;
  'text-secondary': string;
  'text-muted': string;

  /** Primary brand/interaction colour. */
  accent: string;
  /** Lighter accent for text-on-dark and glows. */
  'accent-soft': string;
  /** Secondary hue used by ambient effects (fog, grid). */
  'accent-glow': string;
}

export interface ThemeDefinition {
  id: UITheme;
  label: string;
  description: string;
  tokens: ThemeTokens;
}

/** Semantic colours are intentionally theme-independent. */
export const SEMANTIC_TOKENS = {
  success: '52 211 153',
  warning: '251 191 36',
  danger: '248 113 113',
  info: '56 189 248',
} as const;

export const THEMES: Record<UITheme, ThemeDefinition> = {
  jarvis: {
    id: 'jarvis',
    label: 'JARVIS',
    description: 'Signature violet on deep void',
    tokens: {
      'bg-void': '3 2 13',
      'bg-surface-1': '14 11 31',
      'bg-surface-2': '21 17 42',
      'bg-surface-3': '9 7 28',
      'border-subtle': '148 130 255',
      'border-strong': '167 139 250',
      'text-primary': '248 250 252',
      'text-secondary': '203 213 225',
      'text-muted': '148 163 184',
      accent: '139 92 246',
      'accent-soft': '192 132 252',
      'accent-glow': '124 58 237',
    },
  },
  obsidian: {
    id: 'obsidian',
    label: 'Obsidian',
    description: 'Deep charcoal, minimal and refined',
    tokens: {
      'bg-void': '5 6 8',
      'bg-surface-1': '12 14 18',
      'bg-surface-2': '19 22 28',
      'bg-surface-3': '9 11 14',
      'border-subtle': '63 69 79',
      'border-strong': '94 102 115',
      'text-primary': '245 247 250',
      'text-secondary': '203 208 217',
      'text-muted': '126 135 148',
      accent: '161 161 170',
      'accent-soft': '212 212 216',
      'accent-glow': '82 82 91',
    },
  },
  arc: {
    id: 'arc',
    label: 'Arc Reactor',
    description: 'Cool cyan, Stark Industries',
    tokens: {
      'bg-void': '2 8 16',
      'bg-surface-1': '9 20 33',
      'bg-surface-2': '14 30 46',
      'bg-surface-3': '6 16 27',
      'border-subtle': '125 211 252',
      'border-strong': '56 189 248',
      'text-primary': '241 249 255',
      'text-secondary': '191 214 231',
      'text-muted': '134 163 184',
      accent: '56 189 248',
      'accent-soft': '125 211 252',
      'accent-glow': '14 165 233',
    },
  },
  cyberpunk: {
    id: 'cyberpunk',
    label: 'Cyberpunk',
    description: 'Magenta neon over amber haze',
    tokens: {
      'bg-void': '13 2 12',
      'bg-surface-1': '28 8 26',
      'bg-surface-2': '40 13 37',
      'bg-surface-3': '20 5 19',
      'border-subtle': '244 114 182',
      'border-strong': '236 72 153',
      'text-primary': '253 244 255',
      'text-secondary': '231 200 226',
      'text-muted': '186 148 180',
      accent: '236 72 153',
      'accent-soft': '249 168 212',
      'accent-glow': '245 158 11',
    },
  },
  matrix: {
    id: 'matrix',
    label: 'Matrix',
    description: 'Phosphor green terminal',
    tokens: {
      'bg-void': '2 10 6',
      'bg-surface-1': '7 23 15',
      'bg-surface-2': '11 33 22',
      'bg-surface-3': '4 17 11',
      'border-subtle': '110 231 183',
      'border-strong': '52 211 153',
      'text-primary': '236 253 245',
      'text-secondary': '187 224 206',
      'text-muted': '134 175 154',
      accent: '52 211 153',
      'accent-soft': '110 231 183',
      'accent-glow': '16 185 129',
    },
  },
  stealth: {
    id: 'stealth',
    label: 'Stealth',
    description: 'Neutral slate, zero glow',
    tokens: {
      'bg-void': '8 10 14',
      'bg-surface-1': '17 21 28',
      'bg-surface-2': '26 32 42',
      'bg-surface-3': '12 15 21',
      'border-subtle': '148 163 184',
      'border-strong': '203 213 225',
      'text-primary': '248 250 252',
      'text-secondary': '203 213 225',
      'text-muted': '148 163 184',
      accent: '148 163 184',
      'accent-soft': '203 213 225',
      'accent-glow': '100 116 139',
    },
  },
};

export const THEME_LIST: ThemeDefinition[] = Object.values(THEMES);

export const DEFAULT_THEME: UITheme = 'jarvis';
export const DEFAULT_BLOB_STYLE: BlobStyle = 'hologram';

export interface BlobStyleDefinition {
  id: BlobStyle;
  label: string;
  description: string;
}

export const BLOB_STYLES: BlobStyleDefinition[] = [
  { id: 'hologram', label: 'Hologram', description: 'Woven spherical streamlines' },
  { id: 'arc_reactor', label: 'Arc Reactor', description: 'Concentric rings with a hot core' },
  { id: 'particle', label: 'Particle', description: 'Orbiting point cloud' },
  { id: 'pulse', label: 'Pulse', description: 'Expanding concentric shells' },
];

export const DEFAULT_BACKGROUND_STYLE: BackgroundStyle = 'ribbon-field';

export interface BackgroundStyleDefinition {
  id: BackgroundStyle;
  label: string;
  family: string;
  description: string;
  badge?: string;
}

export const BACKGROUND_STYLES: BackgroundStyleDefinition[] = [
  {
    id: 'ribbon-field',
    label: 'Ribbon Field',
    family: 'Predictive Arc',
    description: 'Cyan, indigo & purple ribbons resolved through an animated dot matrix',
    badge: 'ThreeUI',
  },
  {
    id: 'amber-halftone',
    label: 'Amber Halftone',
    family: 'Predictive Arc',
    description: 'Warm amber and gold energy currents across a halftone matrix',
    badge: 'ThreeUI',
  },
  {
    id: 'void-field',
    label: 'Void Field',
    family: 'Predictive Arc',
    description: 'Deep cosmic void with subtle luminous particle currents',
    badge: 'ThreeUI',
  },
  {
    id: 'halftone-flow',
    label: 'Halftone Flow',
    family: 'Predictive Arc',
    description: 'Fluid undulating waveforms rendered through rasterized dot arrays',
    badge: 'ThreeUI',
  },
  {
    id: 'data-pixel',
    label: 'Data Pixel',
    family: 'Predictive Arc',
    description: 'Algorithmic cybernetic pixel coordinates & predictive telemetry',
    badge: 'ThreeUI',
  },
  {
    id: 'dot-matrix',
    label: 'Dot Matrix',
    family: 'Signal',
    description: 'Dynamic reactive dot matrix grid with ambient particle drift',
    badge: 'ThreeUI',
  },
  {
    id: 'constellation',
    label: 'Constellation',
    family: 'Network',
    description: 'Interactive neural node network with connecting energy lines',
    badge: 'ThreeUI',
  },
  {
    id: 'crt',
    label: 'CRT Terminal',
    family: 'Retro',
    description: 'Curved retro cathode-ray monitor with scanlines & phosphor bloom',
    badge: 'ThreeUI',
  },
  {
    id: 'flow-field',
    label: 'Flow Field',
    family: 'Fluid',
    description: 'Smooth vector flow trajectories curving across 3D space',
    badge: 'ThreeUI',
  },
  {
    id: 'classic',
    label: 'Classic Grid',
    family: 'Minimal',
    description: 'Original perspective wireframe floor with horizon glow',
  },
];

export function isUITheme(value: unknown): value is UITheme {
  return typeof value === 'string' && value in THEMES;
}

export function isBlobStyle(value: unknown): value is BlobStyle {
  return BLOB_STYLES.some((s) => s.id === value);
}

export function isBackgroundStyle(value: unknown): value is BackgroundStyle {
  return BACKGROUND_STYLES.some((b) => b.id === value);
}

/** Resolve a token to a `rgb(r g b)` string — for canvas work, which can't use Tailwind. */
export function tokenToRgb(theme: UITheme, token: keyof ThemeTokens, alpha = 1): string {
  const triplet = THEMES[theme]?.tokens[token] ?? THEMES[DEFAULT_THEME].tokens[token];
  const [r, g, b] = triplet.split(' ');
  return alpha >= 1 ? `rgb(${r} ${g} ${b})` : `rgb(${r} ${g} ${b} / ${alpha})`;
}
