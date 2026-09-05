import React from 'react';
import { View, Text, TouchableOpacity, FlatList } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { theme, css, styled } from '@utils/theme';
import { Agent } from '@types';

interface AgentsOverviewCardProps {
  agents: Agent[];
}

export const AgentsOverviewCard: React.FC<AgentsOverviewCardProps> = ({ agents }) => {
  const colors = theme.colors;
  
  const activeAgents = agents.filter(a => a.status === 'running').length;
  const idleAgents = agents.filter(a => a.status === 'idle').length;
  const errorAgents = agents.filter(a => a.status === 'error').length;
  const offlineAgents = agents.filter(a => a.status === 'offline').length;

  const statusConfig = {
    running: { color: colors.success, icon: 'play-circle', label: 'Running' },
    idle: { color: colors.cyan, icon: 'pause-circle', label: 'Idle' },
    paused: { color: colors.warning, icon: 'pause', label: 'Paused' },
    error: { color: colors.critical, icon: 'alert-circle', label: 'Error' },
    offline: { color: colors.white200, icon: 'power-off', label: 'Offline' },
  };

  const typeIcons: Record<string, string> = {
    scanner: 'radar',
    analyzer: 'magnify',
    validator: 'check-circle',
    reporter: 'file-document',
    learning: 'brain',
    custom: 'puzzle',
  };

  if (agents.length === 0) {
    return (
      <styled.View className="bg-ownex-black-100 rounded-2xl p-5 border border-ownex-graphite-200">
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View className="w-12 h-12 rounded-xl bg-ownex-graphite-100 items-center justify-center">
              <Ionicons name="construct-sharp" size={24} color={colors.cyan} />
            </View>
            <Text className="text-heading-sm font-display text-ownex-white">Agents</Text>
          </View>
          <Text className="text-caption text-ownex-white-200">0 active</Text>
        </View>
        <View className="py-8 items-center">
          <Ionicons name="construct-outline" size={48} color={colors.graphite200} />
          <Text className="text-body-sm text-ownex-white-200 mt-3 text-center px-4">
            No agents configured. Connect OWNEX Alpha to see agents.
          </Text>
        </View>
      </styled.View>
    );
  }

  return (
    <styled.View className="bg-ownex-black-100 rounded-2xl p-5 border border-ownex-graphite-200">
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <View style={{ flex-direction: 'row', alignItems: 'center', gap: 10 }}>
          <View className="w-12 h-12 rounded-xl bg-ownex-graphite-100 items-center justify-center">
            <Ionicons name="construct-sharp" size={24} color={colors.cyan} />
          </View>
          <Text className="text-heading-sm font-display text-ownex-white">Agents</Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Text className="text-body-sm font-mono text-ownex-cyan">{activeAgents}</Text>
          <Text className="text-caption text-ownex-white-200">Active</Text>
        </View>
      </View>

      {/* Status Summary */}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {[
          { key: 'running', count: activeAgents },
          { key: 'idle', count: idleAgents },
          { key: 'error', count: errorAgents },
          { key: 'offline', count: offlineAgents },
        ].map(({ key, count }) => (
          count > 0 && (
            <View
              key={key}
              className="flex-row items-center gap-2 px-3 py-1.5 rounded-full"
              style={{ backgroundColor: `${statusConfig[key as keyof typeof statusConfig].color}20` }}
            >
              <Ionicons
                name={statusConfig[key as keyof typeof statusConfig].icon}
                size={14}
                color={statusConfig[key as keyof typeof statusConfig].color}
              />
              <Text className="text-caption-sm font-medium" style={{ color: statusConfig[key as keyof typeof statusConfig].color }}>
                {count}
              </Text>
            </View>
          )
        ))}
      </View>

      {/* Agent List */}
      <FlatList
        data={agents.slice(0, 5)}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <AgentRow agent={item} />}
        ListHeaderComponent={() => (
          <Text className="text-caption-sm text-ownex-white-200 uppercase tracking-wider mb-2">
            Recent Agents
          </Text>
        )}
        ListFooterComponent={() => agents.length > 5 && (
          <TouchableOpacity className="mt-3 py-2 items-center">
            <Text className="text-caption-sm text-ownex-cyan">View all {agents.length} agents</Text>
          </TouchableOpacity>
        )}
      />
    </styled.View>
  );
};

interface AgentRowProps {
  agent: Agent;
}

const AgentRow: React.FC<AgentRowProps> = ({ agent }) => {
  const colors = theme.colors;
  const statusConfig = {
    running: { color: colors.success, icon: 'play-circle' },
    idle: { color: colors.cyan, icon: 'pause-circle' },
    paused: { color: colors.warning, icon: 'pause' },
    error: { color: colors.critical, icon: 'alert-circle' },
    offline: { color: colors.white200, icon: 'power-off' },
  };
  const config = statusConfig[agent.status];
  const typeIcon = {
    scanner: 'radar',
    analyzer: 'magnify',
    validator: 'check-circle',
    reporter: 'file-document',
    learning: 'brain',
    custom: 'puzzle',
  }[agent.type] || 'construct';

  return (
    <TouchableOpacity
      className="flex-row items-center gap-3 p-3 rounded-xl bg-ownex-graphite-50"
      activeOpacity={0.8}
    >
      <View className="w-10 h-10 rounded-lg items-center justify-center" style={{ backgroundColor: `${colors.cyan}15` }}>
        <MaterialCommunityIcons name={typeIcon} size={20} color={colors.cyan} />
      </View>
      <View className="flex-1 min-w-0">
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text className="text-body-sm font-medium text-ownex-white truncate pr-2">{agent.name}</Text>
          <View className="flex-row items-center gap-1">
            <View className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: config.color }} />
            <Text className="text-caption-sm" style={{ color: config.color }}>{config.label}</Text>
          </View>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 2 }}>
          <Text className="text-caption-sm text-ownex-white-200 truncate">{agent.currentTask || 'No task'}</Text>
          {agent.progress > 0 && (
            <View style={{ flex: 1, maxWidth: 80, height: 3 }}>
              <View
                className="h-full rounded-full bg-ownex-graphite-200"
                style={{ backgroundColor: `${config.color}30` }}
              >
                <View
                  className="h-full rounded-full"
                  style={{ backgroundColor: config.color, width: `${agent.progress}%` }}
                />
              </View>
            </View>
          )}
        </View>
      </View>
      <Ionicons name="chevron-forward-sharp" size={18} color={colors.white200} />
    </TouchableOpacity>
  );
};