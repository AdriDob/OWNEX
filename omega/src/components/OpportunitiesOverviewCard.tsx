import React from 'react';
import { View, Text, TouchableOpacity, FlatList } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { theme, css, styled } from '@utils/theme';
import { Opportunity } from '@types';

interface OpportunitiesOverviewCardProps {
  opportunities: Opportunity[];
}

export const OpportunitiesOverviewCard: React.FC<OpportunitiesOverviewCardProps> = ({ opportunities }) => {
  const colors = theme.colors;
  
  const newOpps = opportunities.filter(o => o.status === 'new').length;
  const readyOpps = opportunities.filter(o => o.status === 'ready').length;
  const inProgressOpps = opportunities.filter(o => o.status === 'in_progress').length;
  const submittedOpps = opportunities.filter(o => o.status === 'submitted').length;
  const acceptedOpps = opportunities.filter(o => o.status === 'accepted').length;

  const typeIcons: Record<string, string> = {
    bounty: 'bug',
    freelance: 'briefcase',
    dev: 'code-braces',
    data: 'database',
    investment: 'trending-up',
    trading: 'chart-line',
    crypto: 'currency-btc',
  };

  const typeColors: Record<string, string> = {
    bounty: colors.critical,
    freelance: colors.cyan,
    dev: colors.electric,
    data: colors.merlin,
    investment: colors.success,
    trading: colors.warning,
    crypto: colors.warning,
  };

  if (opportunities.length === 0) {
    return (
      <styled.View className="bg-ownex-black-100 rounded-2xl p-5 border border-ownex-graphite-200">
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View className="w-12 h-12 rounded-xl bg-ownex-graphite-100 items-center justify-center">
              <Ionicons name="diamond-sharp" size={24} color={colors.cyan} />
            </View>
            <Text className="text-heading-sm font-display text-ownex-white">Opportunities</Text>
          </View>
          <Text className="text-caption text-ownex-white-200">0 new</Text>
        </View>
        <View className="py-8 items-center">
          <Ionicons name="diamond-outline" size={48} color={colors.graphite200} />
          <Text className="text-body-sm text-ownex-white-200 mt-3 text-center px-4">
            No opportunities found. Run discovery workflow.
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
            <Ionicons name="diamond-sharp" size={24} color={colors.cyan} />
          </View>
          <Text className="text-heading-sm font-display text-ownex-white">Opportunities</Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Text className="text-body-sm font-mono text-ownex-cyan">{newOpps + readyOpps}</Text>
          <Text className="text-caption text-ownex-white-200">Actionable</Text>
        </View>
      </View>

      {/* Status Summary */}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {[
          { key: 'new', count: newOpps, color: colors.cyan },
          { key: 'ready', count: readyOpps, color: colors.success },
          { key: 'in_progress', count: inProgressOpps, color: colors.warning },
          { key: 'submitted', count: submittedOpps, color: colors.merlin },
          { key: 'accepted', count: acceptedOpps, color: colors.success },
        ].map(({ key, count, color }) => (
          count > 0 && (
            <View
              key={key}
              className="flex-row items-center gap-2 px-3 py-1.5 rounded-full"
              style={{ backgroundColor: `${color}20` }}
            >
              <View className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
              <Text className="text-caption-sm font-medium" style={{ color }}>
                {count}
              </Text>
            </View>
          )
        ))}
      </View>

      {/* Opportunity List */}
      <FlatList
        data={opportunities.slice(0, 5)}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <OpportunityRow opportunity={item} />}
        ListHeaderComponent={() => (
          <Text className="text-caption-sm text-ownex-white-200 uppercase tracking-wider mb-2">
            Top Opportunities
          </Text>
        )}
        ListFooterComponent={() => opportunities.length > 5 && (
          <TouchableOpacity className="mt-3 py-2 items-center">
            <Text className="text-caption-sm text-ownex-cyan">View all {opportunities.length} opportunities</Text>
          </TouchableOpacity>
        )}
      />
    </styled.View>
  );
};

interface OpportunityRowProps {
  opportunity: Opportunity;
}

const OpportunityRow: React.FC<OpportunityRowProps> = ({ opportunity }) => {
  const colors = theme.colors;
  const typeIcon = {
    bounty: 'bug',
    freelance: 'briefcase',
    dev: 'code-braces',
    data: 'database',
    investment: 'trending-up',
    trading: 'chart-line',
    crypto: 'currency-btc',
  }[opportunity.type] || 'diamond';
  const typeColor = {
    bounty: colors.critical,
    freelance: colors.cyan,
    dev: colors.electric,
    data: colors.merlin,
    investment: colors.success,
    trading: colors.warning,
    crypto: colors.warning,
  }[opportunity.type] || colors.cyan;

  const statusColors: Record<string, string> = {
    new: colors.cyan,
    analyzing: colors.warning,
    ready: colors.success,
    in_progress: colors.electric,
    submitted: colors.merlin,
    accepted: colors.success,
    rejected: colors.critical,
    expired: colors.white200,
  };

  const formatReward = (opp: Opportunity) => {
    if (opp.reward.type === 'range') {
      return `$${opp.reward.min.toLocaleString()} - $${opp.reward.max.toLocaleString()}`;
    }
    if (opp.reward.type === 'fixed') {
      return `$${opp.reward.min.toLocaleString()}`;
    }
    return 'TBD';
  };

  return (
    <TouchableOpacity
      className="flex-row items-center gap-3 p-3 rounded-xl bg-ownex-graphite-50"
      activeOpacity={0.8}
    >
      <View className="w-10 h-10 rounded-lg items-center justify-center" style={{ backgroundColor: `${typeColor}15` }}>
        <MaterialCommunityIcons name={typeIcon} size={20} color={typeColor} />
      </View>
      <View className="flex-1 min-w-0">
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text className="text-body-sm font-medium text-ownex-white truncate pr-2">{opportunity.title}</Text>
          <View className="flex-row items-center gap-1">
            <View className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: statusColors[opportunity.status] }} />
            <Text className="text-caption-sm" style={{ color: statusColors[opportunity.status] }}>
              {opportunity.status.replace('_', ' ')}
            </Text>
          </View>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 2 }}>
          <Text className="text-caption-sm text-ownex-white-200">{opportunity.platform}</Text>
          <View className="w-1 h-1 rounded-full bg-ownex-white-200" />
          <Text className="text-caption-sm font-mono" style={{ color: typeColor }}>{formatReward(opportunity)}</Text>
          <View className="w-1 h-1 rounded-full bg-ownex-white-200" />
          <Text className="text-caption-sm" style={{ color: typeColor }}>
            {opportunity.confidence}% confidence
          </Text>
        </View>
      </View>
      <Ionicons name="chevron-forward-sharp" size={18} color={colors.white200} />
    </TouchableOpacity>
  );
};