/**
 * Applies theme tokens to the document root.
 *
 * All app colours read through CSS custom properties, so switching a theme is a
 * single write to `documentElement.style` — no re-render of the tree required.
 */

import { UITheme } from '../types';
import { DEFAULT_THEME, SEMANTIC_TOKENS, THEMES } from './themes';

export interface ApplyThemeOptions {
  /** When false, sets `data-animations="off"`, which CSS uses to kill transitions. */
  animations?: boolean;
}

export function applyTheme(theme: UITheme, opts: ApplyThemeOptions = {}): void {
  const def = THEMES[theme] ?? THEMES[DEFAULT_THEME];
  const root = document.documentElement;

  for (const [name, value] of Object.entries(def.tokens)) {
    root.style.setProperty(`--${name}`, value);
  }
  for (const [name, value] of Object.entries(SEMANTIC_TOKENS)) {
    root.style.setProperty(`--${name}`, value);
  }

  root.dataset.theme = def.id;
  root.dataset.animations = opts.animations === false ? 'off' : 'on';

  // Keep the native UI (scrollbars, form controls, autofill) in sync.
  root.style.colorScheme = 'dark';
}
