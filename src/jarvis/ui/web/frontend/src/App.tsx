import React from 'react';
import { JarvisProvider } from './context/JarvisContext';
import { ThemeProvider } from './context/ThemeContext';
import { useRouter } from './hooks/useRouter';
import { ChatView } from './views/ChatView';

const AppRoutes: React.FC = () => {
  const router = useRouter();

  // '/settings' is handled as overlay state inside ChatView,
  // so we always render ChatView. The settings overlay reads the URL.
  return (
    <ChatView
      chatId={router.chatId}
      navigate={router.navigate}
      currentRoute={router.route}
    />
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <JarvisProvider>
        <AppRoutes />
      </JarvisProvider>
    </ThemeProvider>
  );
};
