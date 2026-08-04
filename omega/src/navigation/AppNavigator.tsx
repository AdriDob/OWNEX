import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createDrawerNavigator } from '@react-navigation/drawer';
import { Ionicons, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { useStore } from '@stores/useStore';
import { theme } from '@utils/theme';
import { css } from '@utils/theme';

// Screens (lazy loaded)
const DashboardScreen = React.lazy(() => import('@screens/DashboardScreen').then(m => ({ default: m.DashboardScreen })));
const AgentsScreen = React.lazy(() => import('@screens/AgentsScreen').then(m => ({ default: m.AgentsScreen })));
const WorkflowsScreen = React.lazy(() => import('@screens/WorkflowsScreen').then(m => ({ default: m.WorkflowsScreen })));
const OpportunitiesScreen = React.lazy(() => import('@screens/OpportunitiesScreen').then(m => ({ default: m.OpportunitiesScreen })));
const MerlinScreen = React.lazy(() => import('@screens/MerlinScreen').then(m => ({ default: m.MerlinScreen })));
const SettingsScreen = React.lazy(() => import('@screens/SettingsScreen').then(m => ({ default: m.SettingsScreen })));
const AuthScreen = React.lazy(() => import('@screens/AuthScreen').then(m => ({ default: m.AuthScreen })));
const OnboardingScreen = React.lazy(() => import('@screens/OnboardingScreen').then(m => ({ default: m.OnboardingScreen })));
const AgentDetailScreen = React.lazy(() => import('@screens/AgentDetailScreen').then(m => ({ default: m.AgentDetailScreen })));
const WorkflowDetailScreen = React.lazy(() => import('@screens/WorkflowDetailScreen').then(m => ({ default: m.WorkflowDetailScreen })));
const OpportunityDetailScreen = React.lazy(() => import('@screens/OpportunityDetailScreen').then(m => ({ default: m.OpportunityDetailScreen })));
const NotificationsScreen = React.lazy(() => import('@screens/NotificationsScreen').then(m => ({ default: m.NotificationsScreen })));
const SystemDiagnosticsScreen = React.lazy(() => import('@screens/SystemDiagnosticsScreen').then(m => ({ default: m.SystemDiagnosticsScreen })));
const ProfileScreen = React.lazy(() => import('@screens/ProfileScreen').then(m => ({ default: m.ProfileScreen })));

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();
const Drawer = createDrawerNavigator<RootStackParamList>();

// Tab Bar Icons
const TabIcon = ({ name, focused, color, size = 26 }: { name: string; focused: boolean; color: string; size?: number }) => (
  <Ionicons name={focused ? name : name.replace('sharp-', '').replace('-outline', '')} size={size} color={color} />
);

const TabBarButton = ({ route, focused, onPress, label, iconName, badgeCount }: any) => {
  const { theme: currentTheme } = useStore();
  const colors = theme.colors;
  
  return (
    <theme.View
      className="flex-1 items-center justify-center px-2 py-1.5"
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected: focused }}
    >
      <theme.View className="relative">
        <TabIcon name={iconName} focused={focused} color={focused ? colors.cyan : colors.white200} size={28} />
        {badgeCount > 0 && (
          <theme.View className="absolute -top-1 -right-1 min-w-4 h-4 bg-ownex-critical rounded-full items-center justify-center px-1">
            <theme.Text className="text-caption-sm font-bold text-ownex-white">
              {badgeCount > 9 ? '9+' : badgeCount}
            </theme.Text>
          </theme.View>
        )}
      </theme.View>
      <theme.Text
        className={`text-caption-sm mt-1 transition-colors ${focused ? 'text-ownex-cyan' : 'text-ownex-white-200'}`}
      >
        {label}
      </theme.Text>
    </theme.View>
  );
};

// Main Tab Navigator
const MainTabs = () => {
  const { system, unreadCount } = useStore();
  
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: theme.colors.cyan,
        tabBarInactiveTintColor: theme.colors.white200,
        tabBarStyle: {
          backgroundColor: theme.colors.black100,
          borderTopWidth: 0,
          height: 72,
          paddingBottom: 8,
          ...theme.shadows.xl,
        },
        tabBarItemStyle: { marginHorizontal: 4 },
      })}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          tabBarButton: (props) => <TabBarButton {...props} label="Dashboard" iconName="home-sharp" />,
        }}
      />
      <Tab.Screen
        name="Agents"
        component={AgentsScreen}
        options={{
          tabBarButton: (props) => <TabBarButton {...props} label="Agents" iconName="construct-sharp" badgeCount={system.agentsActive} />,
        }}
      />
      <Tab.Screen
        name="Workflows"
        component={WorkflowsScreen}
        options={{
          tabBarButton: (props) => <TabBarButton {...props} label="Workflows" iconName="git-branch-sharp" badgeCount={system.workflowsRunning} />,
        }}
      />
      <Tab.Screen
        name="Opportunities"
        component={OpportunitiesScreen}
        options={{
          tabBarButton: (props) => <TabBarButton {...props} label="Opps" iconName="diamond-sharp" />,
        }}
      />
      <Tab.Screen
        name="Merlin"
        component={MerlinScreen}
        options={{
          tabBarButton: (props) => <TabBarButton {...props} label="MERLIN" iconName="sparkles-sharp" />,
        }}
      />
    </Tab.Navigator>
  );
};

// Root Stack Navigator
export const AppNavigator = () => {
  const { auth, merlin } = useStore();
  
  if (!auth.isAuthenticated) {
    return (
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
          presentation: 'card',
          cardStyle: { backgroundColor: theme.colors.black },
        }}
      >
        <Stack.Screen name="Auth" component={AuthScreen} />
        <Stack.Screen name="Onboarding" component={OnboardingScreen} />
      </Stack.Navigator>
    );
  }

  return (
    <Drawer.Navigator
      initialRouteName="Main"
      screenOptions={{
        headerShown: false,
        drawerStyle: {
          backgroundColor: theme.colors.black100,
          width: 280,
        },
        drawerContentStyle: { flex: 1 },
        drawerItemStyle: { marginHorizontal: 12, borderRadius: 12 },
        drawerActiveTintColor: theme.colors.cyan,
        drawerInactiveTintColor: theme.colors.white200,
        drawerActiveBackgroundColor: theme.colors.graphite100,
        drawerInactiveBackgroundColor: 'transparent',
        drawerLabelStyle: { fontSize: 16, fontWeight: '500' },
        drawerIconStyle: { marginRight: 12 },
        cardStyle: { backgroundColor: theme.colors.black },
      }}
      drawerContent={(props) => <DrawerContent {...props} />}
    >
      <Drawer.Screen name="Main" component={MainTabs} />
      <Drawer.Screen name="Settings" component={SettingsScreen} options={{ drawerLabel: 'Settings', drawerIcon: ({ focused, color, size }) => <MaterialCommunityIcons name="cog" size={size} color={color} /> }} />
      <Drawer.Screen name="Profile" component={ProfileScreen} options={{ drawerLabel: 'Profile', drawerIcon: ({ focused, color, size }) => <Ionicons name="person-sharp" size={size} color={color} /> }} />
      <Drawer.Screen name="Notifications" component={NotificationsScreen} options={{ drawerLabel: 'Notifications', drawerIcon: ({ focused, color, size }) => <Ionicons name="notifications-sharp" size={size} color={color} /> }} />
      <Drawer.Screen name="SystemDiagnostics" component={SystemDiagnosticsScreen} options={{ drawerLabel: 'Diagnostics', drawerIcon: ({ focused, color, size }) => <MaterialCommunityIcons name="monitor-dashboard" size={size} color={color} /> }} />
      
      {/* Detail screens (stack navigation within drawer) */}
      <Drawer.Screen name="AgentDetail" component={AgentDetailScreen} options={{ drawerLabel: 'Agent Detail', drawerIcon: ({ focused, color, size }) => <Ionicons name="construct-sharp" size={size} color={color} /> }} />
      <Drawer.Screen name="WorkflowDetail" component={WorkflowDetailScreen} options={{ drawerLabel: 'Workflow Detail', drawerIcon: ({ focused, color, size }) => <Ionicons name="git-branch-sharp" size={size} color={color} /> }} />
      <Drawer.Screen name="OpportunityDetail" component={OpportunityDetailScreen} options={{ drawerLabel: 'Opportunity Detail', drawerIcon: ({ focused, color, size }) => <Ionicons name="diamond-sharp" size={size} color={color} /> }} />
      <Drawer.Screen name="MerlinChat" component={MerlinScreen} options={{ drawerLabel: 'MERLIN Chat', drawerIcon: ({ focused, color, size }) => <Ionicons name="sparkles-sharp" size={size} color={color} /> }} />
    </Drawer.Navigator>
  );
};

// Drawer Content
const DrawerContent = (props: any) => {
  const { system, auth } = useStore();
  const colors = theme.colors;
  
  return (
    <theme.View className="flex-1 bg-ownex-black-100" style={css(theme.shadows.lg)}>
      {/* Header */}
      <theme.View className="p-6 border-b border-ownex-graphite-200">
        <theme.View className="flex-row items-center gap-3 mb-4">
          <theme.View className="w-12 h-12 rounded-xl bg-gradient-to-br from-ownex-cyan to-ownex-electric items-center justify-center">
            <theme.Text className="text-heading-md font-display text-ownex-black">Ω</theme.Text>
          </theme.View>
          <theme.View className="flex-1 min-w-0">
            <theme.Text className="text-heading-sm font-display text-ownex-white truncate">OWNEX Omega</theme.Text>
            <theme.Text className="text-caption text-ownex-white-200">v1.0.0</theme.Text>
          </theme.View>
        </theme.View>
        
        {/* System Status Indicator */}
        <theme.View className="flex-row items-center gap-3 p-3 bg-ownex-graphite-50 rounded-lg">
          <theme.View className={`w-2.5 h-2.5 rounded-full ${system.status === 'online' ? 'bg-ownex-success animate-pulse-soft' : 'bg-ownex-critical'}`} />
          <theme.View className="flex-1 min-w-0">
            <theme.Text className="text-body-sm font-medium text-ownex-white capitalize">
              {system.status === 'online' ? 'System Online' : system.status === 'connecting' ? 'Connecting...' : 'System Offline'}
            </theme.Text>
            <theme.Text className="text-caption-sm text-ownex-white-200">
              {system.agentsActive} agents • {system.workflowsRunning} workflows
            </theme.Text>
          </theme.View>
          <theme.View className="text-right">
            <theme.Text className="text-caption text-ownex-cyan font-mono">{system.aiRuntime}</theme.Text>
          </theme.View>
        </theme.View>
      </theme.View>

      {/* Navigation */}
      <theme.ScrollView className="flex-1" showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 20 }}>
        <theme.View {...props} />
      </theme.ScrollView>

      {/* Footer */}
      <theme.View className="p-4 border-t border-ownex-graphite-200">
        <theme.View className="flex-row items-center gap-3 p-3 bg-ownex-graphite-50 rounded-lg">
          <theme.View className="w-8 h-8 rounded-full bg-ownex-graphite-100 items-center justify-center">
            <Ionicons name="person-circle-sharp" size={24} color={colors.white200} />
          </theme.View>
          <theme.View className="flex-1 min-w-0">
            <theme.Text className="text-body-sm font-medium text-ownex-white truncate">{auth.user?.username || 'User'}</theme.Text>
            <theme.Text className="text-caption-sm text-ownex-white-200">{auth.user?.role || 'operator'}</theme.Text>
          </theme.View>
        </theme.View>
      </theme.View>
    </theme.View>
  );
};

// Types for navigation
import type { RootStackParamList, MainTabParamList } from '@types';