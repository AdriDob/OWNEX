import React from 'react';
import { View, Text, TouchableOpacity, FlatList } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { theme, css, styled } from '@utils/theme';
import { Workflow } from '@types';

interface WorkflowsOverviewCardProps {
  workflows: Workflow[];
}

export const WorkflowsOverviewCard: React.FC<WorkflowsOverviewCardProps> = ({ workflows }) => {
  const colors = theme.colors;
  
  const runningWorkflows = workflows.filter(w => w.status === 'running').length;
  const pendingWorkflows = workflows.filter(w => w.status === 'pending').length;
  const completedWorkflows = workflows.filter(w => w.status === 'completed').length;
  const failedWorkflows = workflows.filter(w => w.status === 'failed').length;
  const pausedWorkflows = workflows.filter(w => w.status === 'paused').length;

  const statusConfig = {
    running: { color: colors.success, icon: 'play-circle', label: 'Running' },
    pending: { color: colors.cyan, icon: 'clock', label: 'Pending' },
    completed: { color: colors.success, icon: 'check-circle', label: 'Done' },
    failed: { color: colors.critical, icon: 'close-circle', label: 'Failed' },
    paused: { color: colors.warning, icon: 'pause', label: 'Paused' },
    cancelled: { color: colors.white200, icon: 'minus-circle', label: 'Cancelled' },
  };

  if (workflows.length === 0) {
    return (
      <styled.View className="bg-ownex-black-100 rounded-2xl p-5 border border-ownex-graphite-200">
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View className="w-12 h-12 rounded-xl bg-ownex-graphite-100 items-center justify-center">
              <Ionicons name="git-branch-sharp" size={24} color={colors.cyan} />
            </View>
            <Text className="text-heading-sm font-display text-ownex-white">Workflows</Text>
          </View>
          <Text className="text-caption text-ownex-white-200">0 running</Text>
        </View>
        <View className="py-8 items-center">
          <Ionicons name="git-branch-outline" size={48} color={colors.graphite200} />
          <Text className="text-body-sm text-ownex-white-200 mt-3 text-center px-4">
            No active workflows. Start one from the Workflows tab.
          </Text>
        </View>
      </styled.View>
    );
  }

  return (
    <styled.View className="bg-ownex-black-100 rounded-2xl p-5 border border-ownex-graphite-200">
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <View className="w-12 h-12 rounded-xl bg-ownex-graphite-100 items-center justify-center">
            <Ionicons name="git-branch-sharp" size={24} color={colors.cyan} />
          </View>
          <Text className="text-heading-sm font-display text-ownex-white">Workflows</Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Text className="text-body-sm font-mono text-ownex-cyan">{runningWorkflows}</Text>
          <Text className="text-caption text-ownex-white-200">Running</Text>
        </View>
      </View>

      {/* Status Summary */}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {[
          { key: 'running', count: runningWorkflows },
          { key: 'pending', count: pendingWorkflows },
          { key: 'completed', count: completedWorkflows },
          { key: 'failed', count: failedWorkflows },
          { key: 'paused', count: pausedWorkflows },
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

      {/* Workflow List */}
      <FlatList
        data={workflows.slice(0, 5)}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <WorkflowRow workflow={item} />}
        ListHeaderComponent={() => (
          <Text className="text-caption-sm text-ownex-white-200 uppercase tracking-wider mb-2">
            Recent Workflows
          </Text>
        )}
        ListFooterComponent={() => workflows.length > 5 && (
          <TouchableOpacity className="mt-3 py-2 items-center">
            <Text className="text-caption-sm text-ownex-cyan">View all {workflows.length} workflows</Text>
          </TouchableOpacity>
        )}
      />
    </styled.View>
  );
};

interface WorkflowRowProps {
  workflow: Workflow;
}

const WorkflowRow: React.FC<WorkflowRowProps> = ({ workflow }) => {
  const colors = theme.colors;
  const statusConfig = {
    running: { color: colors.success, icon: 'play-circle' },
    pending: { color: colors.cyan, icon: 'clock' },
    completed: { color: colors.success, icon: 'check-circle' },
    failed: { color: colors.critical, icon: 'close-circle' },
    paused: { color: colors.warning, icon: 'pause' },
    cancelled: { color: colors.white200, icon: 'minus-circle' },
  };
  const config = statusConfig[workflow.status];

  return (
    <TouchableOpacity
      className="flex-row items-center gap-3 p-3 rounded-xl bg-ownex-graphite-50"
      activeOpacity={0.8}
    >
      <View className="w-10 h-10 rounded-lg items-center justify-center" style={{ backgroundColor: `${config.color}15` }}>
        <Ionicons name={config.icon} size={20} color={config.color} />
      </View>
      <View className="flex-1 min-w-0">
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text className="text-body-sm font-medium text-ownex-white truncate pr-2">{workflow.name}</Text>
          <View className="flex-row items-center gap-1">
            <View className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: config.color }} />
            <Text className="text-caption-sm" style={{ color: config.color }}>{config.label}</Text>
          </View>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 2 }}>
          <Text className="text-caption-sm text-ownex-white-200 truncate">{workflow.currentStep || 'Initializing...'}</Text>
          {workflow.progress > 0 && (
            <View style={{ flex: 1, maxWidth: 80, height: 3 }}>
              <View className="h-full rounded-full bg-ownex-graphite-200" style={{ backgroundColor: `${config.color}30` }}>
                <View className="h-full rounded-full" style={{ backgroundColor: config.color, width: `${workflow.progress}%` }} />
              </View>
            </View>
          )}
        </View>
      </View>
      <Ionicons name="chevron-forward-sharp" size={18} color={colors.white200} />
    </TouchableOpacity>
  );
};