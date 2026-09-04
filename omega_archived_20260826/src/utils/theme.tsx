import { createContext, useContext, ReactNode } from 'react';
import { View, Text, StyleSheet, ViewStyle, TextStyle, ImageStyle } from 'react-native';
import { Theme } from '@types/theme';

interface ThemeContextValue {
  theme: Theme;
  colors: Theme['colors'];
  spacing: Theme['spacing'];
  typography: Theme['typography'];
  shadows: Theme['shadows'];
  borderRadius: Theme['borderRadius'];
  animations: Theme['animations'];
  zIndex: Theme['zIndex'];
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};

// Theme object matching tailwind config
export const theme: Theme = {
  colors: {
    // Deep blacks
    black: '#000000',
    black50: '#050505',
    black100: '#0a0a0a',
    black200: '#111111',
    black300: '#1a1a1a',
    
    // Graphite grays
    graphite: '#18181b',
    graphite50: '#1f1f23',
    graphite100: '#27272a',
    graphite200: '#333336',
    
    // Clean whites
    white: '#ffffff',
    white50: '#fafafa',
    white100: '#f5f5f5',
    white200: '#e5e5e5',
    
    // Cyan accent
    cyan: '#00d4ff',
    cyan50: '#0ae0ff',
    cyan100: '#33dbff',
    cyan200: '#66e5ff',
    cyan300: '#99efff',
    cyanDim: '#00a3cc',
    cyanDim50: '#007a99',
    
    // Electric blue
    electric: '#0066ff',
    electric50: '#1a7aff',
    electric100: '#338fff',
    electricDim: '#0052cc',
    
    // Success green
    success: '#10b981',
    success50: '#34d399',
    success100: '#6ee7b7',
    successDim: '#059669',
    
    // Warning orange
    warning: '#f59e0b',
    warning50: '#fbbf24',
    warning100: '#fcd34d',
    warningDim: '#d97706',
    
    // Critical red
    critical: '#ef4444',
    critical50: '#f87171',
    critical100: '#fca5a5',
    criticalDim: '#dc2626',
    
    // MERLIN
    merlin: '#8b5cf6',
    merlin50: '#a78bfa',
    merlinDim: '#7c3aed',
  },
  spacing: {
    0: 0,
    1: 4,
    2: 8,
    3: 12,
    4: 16,
    5: 20,
    6: 24,
    8: 32,
    10: 40,
    12: 48,
    16: 64,
    20: 80,
    24: 96,
  },
  typography: {
    fontFamilies: {
      sans: 'Inter',
      mono: 'JetBrainsMono',
      display: 'SpaceGrotesk',
    },
    fontSizes: {
      displayXL: 72,
      displayLG: 60,
      displayMD: 48,
      displaySM: 36,
      headingXL: 30,
      headingLG: 24,
      headingMD: 20,
      headingSM: 18,
      bodyLG: 18,
      body: 16,
      bodySM: 14,
      caption: 12,
      captionSM: 11,
    },
    lineHeights: {
      tight: 1.1,
      normal: 1.4,
      relaxed: 1.6,
    },
    letterSpacings: {
      tight: -0.02,
      normal: 0,
      wide: 0.02,
    },
  },
  shadows: {
    sm: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.3,
      shadowRadius: 2,
      elevation: 2,
    },
    md: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.4,
      shadowRadius: 6,
      elevation: 4,
    },
    lg: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 10 },
      shadowOpacity: 0.4,
      shadowRadius: 15,
      elevation: 8,
    },
    xl: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 20 },
      shadowOpacity: 0.5,
      shadowRadius: 25,
      elevation: 12,
    },
    glow: {
      shadowColor: '#00d4ff',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.3,
      shadowRadius: 20,
      elevation: 8,
    },
    glowLG: {
      shadowColor: '#00d4ff',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.4,
      shadowRadius: 40,
      elevation: 12,
    },
    merlinGlow: {
      shadowColor: '#8b5cf6',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.3,
      shadowRadius: 20,
      elevation: 8,
    },
  },
  borderRadius: {
    none: 0,
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    '2xl': 24,
    full: 9999,
  },
  animations: {
    durations: {
      instant: 0,
      fast: 100,
      normal: 200,
      medium: 300,
      slow: 400,
      slower: 500,
      slowest: 700,
    },
    easings: {
      spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      springSlow: 'cubic-bezier(0.25, 1.2, 0.5, 1)',
      easeOutQuart: 'cubic-bezier(0.25, 1, 0.5, 1)',
      easeInQuart: 'cubic-bezier(0.5, 0, 0.75, 0)',
    },
  },
  zIndex: {
    dropdown: 100,
    sticky: 200,
    modal: 300,
    popover: 400,
    tooltip: 500,
    toast: 600,
  },
};

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  );
};

// Styled components using theme
export const styled = {
  View: ({ style, children, ...props }: { style?: ViewStyle | ViewStyle[]; children: ReactNode } & Omit<React.ComponentProps<typeof View>, 'style'>) => (
    <View style={style} {...props}>{children}</View>
  ),
  Text: ({ style, children, ...props }: { style?: TextStyle | TextStyle[]; children: ReactNode } & Omit<React.ComponentProps<typeof Text>, 'style'>) => (
    <Text style={style} {...props}>{children}</Text>
  ),
};

// Helper to merge styles
export const css = (...styles: (ViewStyle | TextStyle | ImageStyle | undefined | false | null)[]) => {
  return styles.filter(Boolean) as (ViewStyle | TextStyle | ImageStyle)[];
};