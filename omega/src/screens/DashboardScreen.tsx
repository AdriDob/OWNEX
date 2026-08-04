import React, { useEffect, useCallback } from 'react';
import { View, Text, ScrollView, RefreshControl, Animated, Easing } from 'react-native';
import { Ionicons, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { useStore } from '@stores/useStore';
import { apiService } from '@services/api';
import { socketService } from '@services/socket';
import { theme, css, styled } from '@utils/theme';
import { SystemStatusCard } from '@components/SystemStatusCard';
import { MerlinCard } from '@components/MerlinCard';
import { AgentsOverviewCard } from '@components/AgentsOverviewCard';
import { WorkflowsOverviewCard } from '@components/WorkflowsOverviewCard';
import { OpportunitiesOverviewCard } from '@components/OpportunitiesOverviewCard';
import { QuickActionsCard } from '@components/QuickActionsCard';
import { NotificationBell } from '@components/NotificationBell';

export const DashboardScreen = () => {
  const {
    system,
    agents,
    workflows,
    opportunities,
    notifications,
    unreadCount,
    updateSystemStatus,
    setAgents,
    setWorkflows,
    setOpportunities,
    addNotification,
    merlin,
  } = useStore();

  const [refreshing, setRefreshing] = React.useState(false);
  const [animValues] = React.useState({
    fade: new Animated.Value(0),
    slide: new Animated.Value(50),
  });

  const fetchData = useCallback(async () => {
    try {
      const [systemRes, agentsRes, workflowsRes, oppsRes, notifRes] = await Promise.allSettled([
        apiService.getSystemStatus(),
        apiService.getAgents(),
        apiService.getWorkflows({ limit: 10 }),
        apiService.getOpportunities({ limit: 10, status: 'new' }),
        apiService.getNotifications({ unreadOnly: true, limit: 5 }),
      ]);

      if (systemRes.status === 'fulfilled') {
        updateSystemStatus(systemRes.value.data);
      }
      if (agentsRes.status === 'fulfilled') {
        setAgents(agentsRes.value.data);
      }
      if (workflowsRes.status === 'fulfilled') {
        setWorkflows(workflowsRes.value.data);
      }
      if (oppsRes.status === 'fulfilled') {
        setOpportunities(oppsRes.value.data);
      }
      if (notifRes.status === 'fulfilled') {
        notifRes.value.data.forEach((n: any) => addNotification(n));
      }
    } catch (e) {
      console.error('[Dashboard] Fetch error:', e);
    } finally {
      setRefreshing(false);
    }
  }, [updateSystemStatus, setAgents, setWorkflows, setOpportunities, addNotification]);

  useEffect(() => {
    fetchData();
    
    // Animate entrance
    Animated.parallel([
      Animated.timing(animValues.fade, {
        toValue: 1,
        duration: 600,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(animValues.slide, {
        toValue: 0,
        duration: 500,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();

    // Socket listeners
    const unsubSystem = socketService.onEvent('system:status', (event) => {
      updateSystemStatus(event.data);
    });
    const unsubAgent = socketService.onEvent('agent:update', (event) => {
      // Handled by agent store
    });
    const unsubWorkflow = socketService.onEvent('workflow:update', (event) => {
      // Handled by workflow store
    });
    const unsubNotif = socketService.onEvent('notification:new', (event) => {
      addNotification(event.data);
    });

    return () => {
      unsubSystem();
      unsubAgent();
      unsubWorkflow();
      unsubNotif();
    };
  }, [fetchData, updateSystemStatus, addNotification]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const renderHeader = () => (
    <View style={css(theme.shadows.md, { paddingHorizontal: 20, paddingTop: 10, paddingBottom: 16 })}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View>
          <Text className="text-display-sm font-display text-ownex-white">OWNEX</Text>
          <Text className="text-caption text-ownex-cyan tracking-wider">OMEGA</Text>
        </View>
        <NotificationBell count={unreadCount} />
      </View>
    </View>
  );

  return (
    <styled.View className="flex-1 bg-ownex-black">
      <Animated.View
        style={{
          opacity: animValues.fade,
          transform: [{ translateY: animValues.slide }],
        }}
      >
        <ScrollView
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#00d4ff']} />}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingBottom: 100 }}
          ListHeaderComponent={renderHeader}
        >
          <View style={{ paddingHorizontal: 16, gap: 16 }}>
            {/* System Status Card */}
            <SystemStatusCard system={system} />
            
            {/* MERLIN Card */}
            <MerlinCard merlin={merlin} />
            
            {/* Quick Actions */}
            <QuickActionsCard />
            
            {/* Agents Overview */}
            <AgentsOverviewCard agents={agents} />
            
            {/* Workflows Overview */}
            <WorkflowsOverviewCard workflows={workflows} />
            
            {/* Opportunities Overview */}
            <OpportunitiesOverviewCard opportunities={opportunities} />
          </View>
        </ScrollView>
      </Animated.View>
    </styled.View>
  );
};