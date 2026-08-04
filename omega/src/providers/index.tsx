import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { AppRegistry, Platform } from 'react-native';
import { useColorScheme } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { NavigationContainer } from '@react-navigation/native';
import { useStore } from '@stores/useStore';
import { apiService } from '@services/api';
import { notificationService } from '@services/notifications';
import { socketService } from '@services/socket';
import { theme } from '@utils/theme';

// Types
interface ProvidersContextValue {
  isReady: boolean;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const ProvidersContext = createContext<ProvidersContextValue | null>(null);

export const useProviders = () => {
  const context = useContext(ProvidersContext);
  if (!context) throw new Error('useProviders must be used within Providers');
  return context;
};

// Theme Provider
const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isReady, setIsReady] = useState(false);
  const colorScheme = useColorScheme();
  const { setTheme, theme: currentTheme } = useStore();

  useEffect(() => {
    const initTheme = async () => {
      try {
        const stored = await SecureStore.getItemAsync('ownex-theme');
        if (stored) {
          setTheme(stored as 'light' | 'dark');
        } else if (colorScheme) {
          setTheme(colorScheme);
        }
        setIsReady(true);
      } catch {
        setTheme('dark');
        setIsReady(true);
      }
    };
    initTheme();
  }, [colorScheme, setTheme]);

  const toggleTheme = async () => {
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    await SecureStore.setItemAsync('ownex-theme', newTheme);
  };

  if (!isReady) {
    return (
      <theme.Provider value={theme}>
        <SplashScreen />
      </theme.Provider>
    );
  }

  return (
    <theme.Provider value={theme}>
      {children}
    </theme.Provider>
  );
};

// Auth Provider
const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { setAuth, auth, refreshAuth } = useStore();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = await SecureStore.getItemAsync('ownex-auth-token');
        const refresh = await SecureStore.getItemAsync('ownex-refresh-token');
        const user = await SecureStore.getItemAsync('ownex-user');
        
        if (token && refresh && user) {
          setAuth({ token, refresh, user: JSON.parse(user) });
          // Validate token
          const valid = await apiService.validateToken(token);
          if (!valid) {
            await refreshAuth();
          }
        }
      } catch (e) {
        console.log('Auth init:', e);
      } finally {
        setIsLoading(false);
      }
    };
    initAuth();
  }, [setAuth, refreshAuth]);

  if (isLoading) return null;

  return <>{children}</>;
};

// Services Provider
const ServicesProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { auth } = useStore();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const initServices = async () => {
      if (auth.token) {
        await socketService.connect(auth.token);
        await notificationService.registerForPushNotifications();
      }
      setInitialized(true);
    };
    initServices();

    return () => {
      socketService.disconnect();
    };
  }, [auth.token]);

  if (!initialized) return null;

  return <>{children}</>;
};

// Main Providers Component
export const Providers: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ServicesProvider>
          <NavigationContainer>
            {children}
          </NavigationContainer>
        </ServicesProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};

// Splash Screen
const SplashScreen: React.FC = () => {
  return (
    <theme.View className="flex-1 items-center justify-center bg-ownex-black">
      <theme.View className="animate-breathing">
        <theme.Text className="text-display-md font-display text-ownex-cyan">
          OWNEX
        </theme.Text>
        <theme.Text className="text-caption text-ownex-white-200 mt-2 tracking-wider">
          OMEGA
        </theme.Text>
      </theme.View>
      <theme.View className="mt-8 w-32 h-2 bg-ownex-graphite-100 rounded-full overflow-hidden">
        <theme.View className="animate-shimmer h-full bg-gradient-to-r from-transparent via-ownex-cyan to-transparent" />
      </theme.View>
    </theme.View>
  );
};

// Register for React Native
AppRegistry.registerComponent('OWEXOmega', () => App);