import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { HeroEmptyState } from '../components/chat/HeroEmptyState';
import { PromptBox } from '../components/chat/PromptBox';
import { Transcript } from '../components/chat/Transcript';
import { AppShell } from '../components/layout/AppShell';
import { Sidebar, SidebarDrawer } from '../components/layout/Sidebar';
import { TopBar } from '../components/layout/TopBar';
import { VoiceOverlay } from '../components/VoiceOverlay';
import { JarvisBlob } from '../components/JarvisBlob';
import { useJarvis } from '../context/JarvisContext';
import { SettingsTab } from '../types';
import { cn } from '../utils/cn';
import { SettingsView } from './settings/SettingsView';

/** Slash commands that open a settings panel rather than doing something. */
const SETTINGS_ROUTES: Record<string, SettingsTab> = {
  '/models': 'model',
  '/effort': 'model',
  '/mcp': 'mcp',
  '/skills': 'skills',
  '/theme': 'appearance',
  '/tools': 'tools',
};

export interface ChatViewProps {
  chatId?: string;
  navigate: (to: string, opts?: { replace?: boolean }) => void;
  currentRoute: 'chat' | 'settings' | 'home';
}

export const ChatView: React.FC<ChatViewProps> = ({
  chatId,
  navigate,
  currentRoute,
}) => {
  const {
    messages,
    isVoiceChatActive,
    isVoiceMode,
    startVoiceChat,
    createNewSession,
    clearActiveChat,
    isDrawerOpen,
    setDrawerOpen,
    sendMessage,
    selectSession,
    currentSessionId,
  } = useJarvis();

  const [settingsTab, setSettingsTab] = useState<SettingsTab>('model');

  // Settings overlay is driven by the URL: /settings opens it.
  const settingsOpen = currentRoute === 'settings';

  // When the route has a chatId and it differs from the current session, load it.
  // When on / without a chatId, ensure the session is cleared so it's a clean new chat.
  useEffect(() => {
    if (chatId) {
      if (chatId !== currentSessionId) {
        void selectSession(chatId);
      }
    } else {
      if (currentSessionId) {
        clearActiveChat();
      }
    }
  }, [chatId]); // eslint-disable-line react-hooks/exhaustive-deps

  const openSettings = useCallback((tab: SettingsTab = 'model') => {
    setSettingsTab(tab);
    navigate('/settings');
    setDrawerOpen(false);
  }, [navigate, setDrawerOpen]);

  const closeSettings = useCallback(() => {
    // Go back to chat route
    if (chatId) {
      navigate(`/chat/${chatId}`);
    } else if (currentSessionId && currentSessionId !== 'default') {
      navigate(`/chat/${currentSessionId}`);
    } else {
      navigate('/');
    }
  }, [navigate, chatId, currentSessionId]);

  const handleSlashAction = useCallback(
    (cmd: string) => {
      const clean = cmd.toLowerCase().trim().split(/\s+/)[0];

      const tab = SETTINGS_ROUTES[clean];
      if (tab) {
        openSettings(tab);
        return;
      }
      if (clean === '/new') {
        clearActiveChat();
        navigate('/');
      } else if (clean === '/clear') {
        clearActiveChat();
      }
    },
    [openSettings, clearActiveChat, navigate]
  );

  /**
   * Intercept send: on the very first message (home route, no messages),
   * create a session first, navigate to /chat/{id}, then send.
   */
  const handleSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      // If there is no active session yet, create one now and navigate
      if (!currentSessionId) {
        const sid = await createNewSession();
        navigate(`/chat/${sid}`, { replace: true });
        await sendMessage(trimmed);
      } else {
        await sendMessage(trimmed);
      }
    },
    [currentSessionId, createNewSession, navigate, sendMessage]
  );

  // When user clicks New chat from sidebar: reset state and navigate to / (do NOT create session yet)
  const handleNewSession = useCallback(async () => {
    clearActiveChat();
    navigate('/');
  }, [clearActiveChat, navigate]);

  // When a session is selected from sidebar, navigate
  const handleSelectSession = useCallback(
    async (sid: string) => {
      await selectSession(sid);
      navigate(`/chat/${sid}`);
    },
    [selectSession, navigate]
  );

  const hasMessages = messages.length > 0;

  return (
    <>
      <AppShell
        ambient={hasMessages ? 'dim' : 'full'}
        sidebar={
          <Sidebar
            onOpenSettings={openSettings}
            onSelectSession={handleSelectSession}
            onNewSession={handleNewSession}
          />
        }
        topBar={
          <TopBar
            onOpenSettings={openSettings}
            onOpenDrawer={() => setDrawerOpen(true)}
            onNewChat={handleNewSession}
          />
        }
      >
        {hasMessages ? <Transcript /> : <HeroEmptyState />}

        {/* Composer. Fades when voice chat is active. */}
        <div
          className={cn(
            'relative z-20 shrink-0 px-4 pb-5 pt-2 sm:px-6',
            'transition-all duration-300',
            isVoiceChatActive
              ? 'pointer-events-none translate-y-6 opacity-0'
              : 'translate-y-0 opacity-100'
          )}
        >
          <div className="mx-auto w-full max-w-3xl">
            <PromptBox onSlashAction={handleSlashAction} onSend={handleSend} autoFocus />
          </div>
        </div>

        {/* Persistent corner blob — visible only when there are messages and voice chat is NOT active */}
        <AnimatePresence>
          {hasMessages && !isVoiceChatActive && (
            <motion.div
              className="absolute bottom-5 left-6 z-30 pointer-events-auto"
              initial={{ opacity: 0, scale: 0.5, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.5, y: 20 }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            >
              <JarvisBlob
                size={80}
                label="Start voice chat"
                onClick={() => void startVoiceChat().catch((e) => console.warn(e))}
                hideFloor
              />
            </motion.div>
          )}
        </AnimatePresence>
      </AppShell>

      <SidebarDrawer
        open={isDrawerOpen}
        onClose={() => setDrawerOpen(false)}
        onOpenSettings={openSettings}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
      />

      <VoiceOverlay />

      <SettingsView
        isOpen={settingsOpen}
        onClose={closeSettings}
        initialTab={settingsTab}
      />
    </>
  );
};
