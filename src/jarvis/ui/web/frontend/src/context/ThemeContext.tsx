import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { ConfigApi } from '../services/api';
import { BackgroundStyle, BlobStyle, UITheme } from '../types';
import { applyTheme } from '../theme/applyTheme';
import {
  DEFAULT_BACKGROUND_STYLE,
  DEFAULT_BLOB_STYLE,
  DEFAULT_THEME,
  isBackgroundStyle,
  isBlobStyle,
  isUITheme,
} from '../theme/themes';

interface ThemeContextType {
  theme: UITheme;
  setTheme: (theme: UITheme) => void;
  blobStyle: BlobStyle;
  setBlobStyle: (style: BlobStyle) => void;
  backgroundStyle: BackgroundStyle;
  setBackgroundStyle: (style: BackgroundStyle) => void;
  backgroundOpacity: number;
  setBackgroundOpacity: (opacity: number) => void;
  enableAnimations: boolean;
  setEnableAnimations: (enabled: boolean) => void;
  soundEffects: boolean;
  setSoundEffects: (enabled: boolean) => void;
  sidebarExpanded: boolean;
  setSidebarExpanded: (expanded: boolean) => void;
  /** True until the backend config has been read once. */
  isHydrating: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const LS = {
  theme: 'jarvis_theme',
  blob: 'jarvis_blob_style',
  background: 'jarvis_background_style',
  backgroundOpacity: 'jarvis_background_opacity',
  animations: 'jarvis_animations',
  sound: 'jarvis_sound_fx',
  sidebar: 'jarvis_sidebar_expanded',
} as const;

function readLocal<T>(key: string, guard: (v: unknown) => v is T, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return guard(raw) ? raw : fallback;
  } catch {
    return fallback;
  }
}

function readLocalBool(key: string, fallback: boolean): boolean {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return raw === 'true';
  } catch {
    return fallback;
  }
}

function writeLocal(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Private browsing / quota — the backend copy is authoritative anyway.
  }
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // localStorage is the fast path so the first paint is correct; the backend
  // config is the source of truth and overwrites it once loaded.
  const [theme, setThemeState] = useState<UITheme>(() =>
    readLocal(LS.theme, isUITheme, DEFAULT_THEME)
  );
  const [blobStyle, setBlobStyleState] = useState<BlobStyle>(() =>
    readLocal(LS.blob, isBlobStyle, DEFAULT_BLOB_STYLE)
  );
  const [backgroundStyle, setBackgroundStyleState] = useState<BackgroundStyle>(() =>
    readLocal(LS.background, isBackgroundStyle, DEFAULT_BACKGROUND_STYLE)
  );
  const [backgroundOpacity, setBackgroundOpacityState] = useState<number>(() => {
    try {
      const raw = localStorage.getItem(LS.backgroundOpacity);
      if (raw !== null) {
        const parsed = parseFloat(raw);
        if (!isNaN(parsed) && parsed >= 0.05 && parsed <= 1.0) return parsed;
      }
    } catch {}
    return 0.5;
  });
  const [enableAnimations, setEnableAnimationsState] = useState<boolean>(() =>
    readLocalBool(LS.animations, true)
  );
  const [soundEffects, setSoundEffectsState] = useState<boolean>(() =>
    readLocalBool(LS.sound, false)
  );
  const [sidebarExpanded, setSidebarExpandedState] = useState<boolean>(() =>
    readLocalBool(LS.sidebar, true)
  );
  const [isHydrating, setIsHydrating] = useState<boolean>(true);

  // Suppress the persist-on-change effect while we're applying server values.
  const hydratedRef = useRef(false);

  // Paint tokens immediately, and on every subsequent change.
  useEffect(() => {
    applyTheme(theme, { animations: enableAnimations });
  }, [theme, enableAnimations]);

  // ─── Hydrate from backend ───────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const cfg = await ConfigApi.get();
        const web = cfg?.ui?.web ?? {};
        if (cancelled) return;

        if (isUITheme(web.theme)) setThemeState(web.theme);
        if (isBlobStyle(web.blob_style)) setBlobStyleState(web.blob_style);
        if (isBackgroundStyle(web.background_style)) setBackgroundStyleState(web.background_style);
        if (typeof web.background_opacity === 'number') {
          const clamped = Math.max(0.05, Math.min(1.0, web.background_opacity));
          setBackgroundOpacityState(clamped);
        }
        if (typeof web.animations === 'boolean') setEnableAnimationsState(web.animations);
        if (typeof web.sound_effects === 'boolean') setSoundEffectsState(web.sound_effects);
        if (typeof web.sidebar_expanded === 'boolean') setSidebarExpandedState(web.sidebar_expanded);
      } catch {
        // Offline or engine not ready — keep the localStorage values.
      } finally {
        if (!cancelled) {
          hydratedRef.current = true;
          setIsHydrating(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const persist = useCallback((patch: Record<string, unknown>) => {
    if (!hydratedRef.current) return;
    ConfigApi.update({ ui: { web: patch } }).catch((e) => {
      console.warn('Failed to persist appearance settings:', e);
    });
  }, []);

  const setTheme = useCallback(
    (next: UITheme) => {
      setThemeState(next);
      writeLocal(LS.theme, next);
      persist({ theme: next });
    },
    [persist]
  );

  const setBlobStyle = useCallback(
    (next: BlobStyle) => {
      setBlobStyleState(next);
      writeLocal(LS.blob, next);
      persist({ blob_style: next });
    },
    [persist]
  );

  const setBackgroundStyle = useCallback(
    (next: BackgroundStyle) => {
      setBackgroundStyleState(next);
      writeLocal(LS.background, next);
      persist({ background_style: next });
    },
    [persist]
  );

  const setBackgroundOpacity = useCallback(
    (next: number) => {
      const clamped = Math.max(0.05, Math.min(1.0, next));
      setBackgroundOpacityState(clamped);
      writeLocal(LS.backgroundOpacity, String(clamped));
      persist({ background_opacity: clamped });
    },
    [persist]
  );

  const setEnableAnimations = useCallback(
    (next: boolean) => {
      setEnableAnimationsState(next);
      writeLocal(LS.animations, String(next));
      persist({ animations: next });
    },
    [persist]
  );

  const setSoundEffects = useCallback(
    (next: boolean) => {
      setSoundEffectsState(next);
      writeLocal(LS.sound, String(next));
      persist({ sound_effects: next });
    },
    [persist]
  );

  const setSidebarExpanded = useCallback(
    (next: boolean) => {
      setSidebarExpandedState(next);
      writeLocal(LS.sidebar, String(next));
      persist({ sidebar_expanded: next });
    },
    [persist]
  );

  return (
    <ThemeContext.Provider
      value={{
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
        isHydrating,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
