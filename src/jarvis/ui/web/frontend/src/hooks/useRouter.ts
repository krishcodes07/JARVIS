import { useCallback, useEffect, useMemo, useState } from 'react';

export interface RouteMatch {
  /** The matched pathname, e.g. '/chat/abc123' */
  path: string;
  /** The top-level route segment: 'chat' | 'settings' | '' (home) */
  route: 'chat' | 'settings' | 'home';
  /** For /chat/:id — the session id, or undefined on /chat */
  chatId?: string;
}

function parsePath(pathname: string): RouteMatch {
  const clean = pathname.replace(/\/+$/, '') || '/';
  const segments = clean.split('/').filter(Boolean);

  if (segments[0] === 'settings') {
    return { path: clean, route: 'settings' };
  }

  if (segments[0] === 'chat') {
    return {
      path: clean,
      route: 'chat',
      chatId: segments[1] || undefined,
    };
  }

  return { path: clean, route: 'home' };
}

/**
 * Minimal client-side router. No external dependencies.
 * Works with the SPA catch-all in server.py.
 */
export function useRouter() {
  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const onPop = () => setPathname(window.location.pathname);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const navigate = useCallback((to: string, opts?: { replace?: boolean }) => {
    if (to === window.location.pathname) return;
    if (opts?.replace) {
      window.history.replaceState(null, '', to);
    } else {
      window.history.pushState(null, '', to);
    }
    setPathname(to);
  }, []);

  const match = useMemo(() => parsePath(pathname), [pathname]);

  return { ...match, navigate };
}
