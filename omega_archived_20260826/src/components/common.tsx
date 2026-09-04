import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme, css, styled } from '@utils/theme';

interface WatchActionButtonProps {
  label: string;
  icon: string;
  color: string;
  onPress: () => void;
  disabled?: boolean;
}

export const WatchActionButton: React.FC<WatchActionButtonProps> = ({ 
  label, 
  icon, 
  color, 
  onPress, 
  disabled = false 
}) => {
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      className="flex-1 flex-row items-center justify-center gap-2 px-4 py-3 rounded-xl"
      style={{ 
        backgroundColor: disabled ? 'rgba(255,255,255,0.05)' : `rgba(${hexToRgb(color)}, 0.15)`,
        borderColor: disabled ? 'rgba(255,255,255,0.05)' : `rgba(${hexToRgb(color)}, 0.3)`,
        borderWidth: 1,
      }}
      activeOpacity={0.7}
    >
      <Ionicons name={icon} size={22} color={disabled ? '#666' : color} />
      <Text className="text-body-sm font-medium" style={{ color: disabled ? '#666' : color }}>
        {label}
      </Text>
    </TouchableOpacity>
  );
};

function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r}, ${g}, ${b}`;
}

interface CardProps {
  children: React.ReactNode;
  className?: string;
  style?: any;
}

export const Card: React.FC<CardProps> = ({ children, className = '', style }) => {
  return (
    <styled.View className={`bg-ownex-black-100 rounded-2xl border border-ownex-graphite-200 ${className}`} style={style}>
      {children}
    </styled.View>
  );
};

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({ title, subtitle, action }) => {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
      <View>
        <Text className="text-heading-sm font-display text-ownex-white">{title}</Text>
        {subtitle && <Text className="text-caption text-ownex-white-200 mt-1">{subtitle}</Text>}
      </View>
      {action}
    </View>
  );
};

interface EmptyStateProps {
  icon: string;
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, message, actionLabel, onAction }) => {
  const colors = theme.colors;
  
  return (
    <View className="py-12 items-center px-8">
      <Ionicons name={icon} size={64} color={colors.graphite200} />
      <Text className="text-heading-sm font-display text-ownex-white mt-4 text-center">{title}</Text>
      <Text className="text-body-sm text-ownex-white-200 mt-2 text-center px-4">{message}</Text>
      {actionLabel && onAction && (
        <TouchableOpacity onPress={onAction} className="mt-4 px-6 py-3 rounded-xl" style={{ backgroundColor: colors.cyan }}>
          <Text className="text-body-sm font-medium text-ownex-black">{actionLabel}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

interface LoadingStateProps {
  size?: 'sm' | 'md' | 'lg';
  color?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ size = 'md', color }) => {
  const colors = theme.colors;
  const sizes = { sm: 20, md: 32, lg: 48 };
  
  return (
    <View className="items-center justify-center py-8">
      <Ionicons name="refresh-sharp" size={sizes[size]} color={color || colors.cyan} style={{ animation: 'spin 1s linear infinite' }} />
    </View>
  );
};

interface DividerProps {
  className?: string;
}

export const Divider: React.FC<DividerProps> = ({ className = '' }) => {
  return <View className={`h-px bg-ownex-graphite-200 ${className}`} />;
};

interface BadgeProps {
  children: React.ReactNode;
  color?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const Badge: React.FC<BadgeProps> = ({ children, color, size = 'md' }) => {
  const colors = theme.colors;
  const sizes = {
    sm: { px: 6, py: 1, text: 'text-caption-sm' },
    md: { px: 8, py: 2, text: 'text-caption' },
    lg: { px: 10, py: 3, text: 'text-body-sm' },
  };
  const s = sizes[size];
  
  return (
    <View
      className={`flex-row items-center justify-center rounded-full ${s.text} font-medium`}
      style={{ 
        backgroundColor: `${color || colors.cyan}20`,
        paddingHorizontal: s.px,
        paddingVertical: s.py,
      }}
    >
      <Text style={{ color: color || colors.cyan }}>{children}</Text>
    </View>
  );
};