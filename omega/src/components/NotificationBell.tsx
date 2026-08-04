import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useStore } from '@stores/useStore';
import { theme, css, styled } from '@utils/theme';

export const NotificationBell: React.FC<{ count: number }> = ({ count }) => {
  const colors = theme.colors;
  const { navigation } = useStore();

  const handlePress = () => {
    navigation.navigate('Notifications');
  };

  return (
    <TouchableOpacity onPress={handlePress} className="p-2 rounded-lg" activeOpacity={0.8}>
      <View className="relative">
        <Ionicons name="notifications-sharp" size={28} color={colors.white} />
        {count > 0 && (
          <View className="absolute -top-1 -right-1 min-w-5 h-5 bg-ownex-critical rounded-full items-center justify-center px-1.5">
            <Text className="text-caption-sm font-bold text-ownex-white">
              {count > 9 ? '9+' : count}
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
};