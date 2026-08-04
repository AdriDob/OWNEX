import React from 'react';
import { View, Text, ProgressBar, TouchableOpacity } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { theme, css, styled } from '@utils/theme';
import { SystemState } from '@types';

interface SystemStatusCardProps {
  system: SystemState['system'];
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({ system }) => {
  const colors = theme.colors;
  const statusColors: Record<string, string> = {
    online: colors.success,
    connecting: colors.warning,
    offline: colors.critical,
    error: colors.critical,
    maintenance: colors.warning,
  };
  const statusText: Record<string, string> = {
    online: 'ONLINE',
    connecting: 'CONNECTING',
    offline: 'OFFLINE',
    error: 'ERROR',
    maintenance: 'MAINTENANCE',
  };

  const statusColor = statusColors[system.status] || colors.warning;
  const statusLabel = statusText[system.status] || 'UNKNOWN';

  return (
    <styled.View className="bg-ownex-black-100 rounded-2xl p-5 border border-ownex-graphite-200 overflow-hidden">
      {/* Header */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <View className="w-12 h-12 rounded-xl bg-ownex-graphite-100 items-center justify-center">
            <Ionicons name="server-sharp" size={24} color={colors.cyan} />
          </View>
          <View>
            <Text className="text-heading-sm font-display text-ownex-white">OWNEX Alpha</Text>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 }}>
              <View
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: statusColor }}
              />
              <Text className="text-caption-sm font-medium" style={{ color: statusColor }}>
                {statusLabel}
              </Text>
            </View>
          </View>
        </View>
        <View style={{ alignItems: 'flex-end' }}>
          <Text className="text-caption-sm text-ownex-white-200">Last Sync</Text>
          <Text className="text-body-sm font-mono text-ownex-cyan">
            {system.lastSync ? new Date(system.lastSync).toLocaleTimeString() : 'Never'}
          </Text>
        </View>
      </View>

      {/* Metrics Grid */}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
        <MetricCard
          label="CPU"
          value={`${system.cpu}%`}
          icon="cpu-64-bit"
          color={system.cpu > 80 ? colors.critical : system.cpu > 60 ? colors.warning : colors.success}
          progress={system.cpu / 100}
        />
        <MetricCard
          label="RAM"
          value={`${system.memory}%`}
          icon="memory"
          color={system.memory > 85 ? colors.critical : system.memory > 70 ? colors.warning : colors.success}
          progress={system.memory / 100}
        />
        <MetricCard
          label="Disk"
          value={`${system.disk}%`}
          icon="harddisk"
          color={system.disk > 90 ? colors.critical : system.disk > 75 ? colors.warning : colors.success}
          progress={system.disk / 100}
        />
        <MetricCard
          label="AI Runtime"
          value={system.aiRuntime.charAt(0).toUpperCase() + system.aiRuntime.slice(1)}
          icon="brain"
          color={
            system.aiRuntime === 'healthy' ? colors.success :
            system.aiRuntime === 'degraded' ? colors.warning : colors.critical
          }
        />
      </View>

      {/* Connected Devices */}
      {system.connectedDevices.length > 0 && (
        <View style={{ borderTopWidth: 1, borderColor: colors.graphite200, paddingTop: 16 }}>
          <Text className="text-caption-sm text-ownex-white-200 uppercase tracking-wider mb-3">
            Connected Devices
          </Text>
          <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
            {system.connectedDevices.map((device) => (
              <TouchableOpacity
                key={device.id}
                className="flex-row items-center gap-2 px-3 py-1.5 rounded-full bg-ownex-graphite-50"
              >
                <View
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: device.status === 'online' ? colors.success : colors.critical }}
                />
                <Text className="text-caption-sm text-ownex-white">{device.name}</Text>
                <Ionicons
                  name={device.type === 'desktop' ? 'desktop-sharp' : device.type === 'watch' ? 'watch-sharp' : 'phone-portrait-sharp'}
                  size={14}
                  color={colors.white200}
                />
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}
    </styled.View>
  );
};

interface MetricCardProps {
  label: string;
  value: string;
  icon: string;
  color: string;
  progress?: number;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon, color, progress }) => {
  const colors = theme.colors;

  return (
    <View style={{ flex: 1, minWidth: '45%', ...css(theme.shadows.sm) }} className="bg-ownex-graphite-50 rounded-xl p-4">
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <View>
          <Text className="text-caption-sm text-ownex-white-200 uppercase tracking-wider">{label}</Text>
          <Text className="text-heading-sm font-display text-ownex-white mt-1">{value}</Text>
        </View>
        <View className="w-10 h-10 rounded-lg items-center justify-center" style={{ backgroundColor: `${color}20` }}>
          <MaterialCommunityIcons name={icon} size={20} color={color} />
        </View>
      </View>
      {progress !== undefined && (
        <View className="mt-3 h-1.5 bg-ownex-graphite-200 rounded-full overflow-hidden">
          <View
            className="h-full rounded-full"
            style={{ backgroundColor: color, width: `${progress * 100}%` }}
          />
        </View>
      )}
    </View>
  );
};