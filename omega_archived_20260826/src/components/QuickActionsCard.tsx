import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useStore } from '@stores/useStore';
import { theme, css, styled } from '@utils/theme';
import { apiService } from '@services/api';

export const QuickActionsCard: React.FC = () => {
  const colors = theme.colors;
  const { system } = useStore();

  const actions = [
    {
      id: 'scan',
      label: 'New Scan',
      icon: 'radar',
      color: colors.cyan,
      onPress: () => handleAction('scan'),
    },
    {
      id: 'analyze',
      label: 'Analyze Target',
      icon: 'magnify',
      color: colors.electric,
      onPress: () => handleAction('analyze'),
    },
    {
      id: 'discover',
      label: 'Discover Opps',
      icon: 'diamond',
      color: colors.merlin,
      onPress: () => handleAction('discover'),
    },
    {
      id: 'daemon',
      label: system.status === 'online' ? 'Stop Daemon' : 'Start Daemon',
      icon: system.status === 'online' ? 'stop-circle' : 'play-circle',
      color: system.status === 'online' ? colors.critical : colors.success,
      onPress: () => handleAction('daemon'),
    },
    {
      id: 'report',
      label: 'Generate Report',
      icon: 'file-document',
      color: colors.success,
      onPress: () => handleAction('report'),
    },
    {
      id: 'sync',
      label: 'Force Sync',
      icon: 'sync',
      color: colors.warning,
      onPress: () => handleAction('sync'),
    },
  ];

  const handleAction = async (action: string) => {
    try {
      switch (action) {
        case 'scan':
          // Navigate to workflows with scan type
          break;
        case 'analyze':
          break;
        case 'discover':
          break;
        case 'daemon':
          if (system.status === 'online') {
            await apiService.stopDaemon();
          } else {
            await apiService.startDaemon();
          }
          break;
        case 'report':
          break;
        case 'sync':
          break;
      }
    } catch (e) {
      console.error('[QuickActions] Error:', e);
    }
  };

  return (
    <styled.View className="bg-ownex-black-100 rounded-2xl p-5 border border-ownex-graphite-200">
      <Text className="text-heading-sm font-display text-ownex-white mb-4">Quick Actions</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
        {actions.map((action) => (
          <TouchableOpacity
            key={action.id}
            onPress={action.onPress}
            className="flex-1 min-w-[45%] flex-row items-center gap-3 p-4 rounded-xl bg-ownex-graphite-50 border border-ownex-graphite-200"
            activeOpacity={0.8}
          >
            <View className="w-12 h-12 rounded-lg items-center justify-center" style={{ backgroundColor: `${action.color}20` }}>
              <Ionicons name={action.icon} size={22} color={action.color} />
            </View>
            <Text className="text-body-sm font-medium text-ownex-white">{action.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </styled.View>
  );
};