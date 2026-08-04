import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, ScrollView, TouchableOpacity, KeyboardAvoidingView, Platform } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useStore } from '@stores/useStore';
import { apiService } from '@services/api';
import { socketService } from '@services/socket';
import { theme, css, styled } from '@utils/theme';
import { MerlinState, MerlinMessage } from '@types';

export const MerlinCard: React.FC<{ merlin: MerlinState }> = ({ merlin }) => {
  const colors = theme.colors;
  const [expanded, setExpanded] = useState(false);
  const [inputText, setInputText] = useState('');
  const { addMerlinMessage, setMerlinState, merlin: storeMerlin } = useStore();
  
  const messages = expanded ? storeMerlin.messages : storeMerlin.messages.slice(-3);
  const suggestions = storeMerlin.suggestions;

  const sendMessage = async () => {
    if (!inputText.trim()) return;
    
    const userMessage: MerlinMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputText,
      timestamp: Date.now(),
    };
    
    addMerlinMessage(userMessage);
    setMerlinState({ status: 'thinking' });
    
    const text = inputText;
    setInputText('');
    
    try {
      const response = await apiService.merlinChat(text);
      const assistantMessage: MerlinMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: response.data?.response || 'No response',
        timestamp: Date.now(),
        metadata: response.data?.metadata,
      };
      addMerlinMessage(assistantMessage);
      setMerlinState({ status: 'idle', suggestions: response.data?.suggestions || suggestions });
    } catch (e) {
      const errorMessage: MerlinMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: 'Connection error. Please try again.',
        timestamp: Date.now(),
      };
      addMerlinMessage(errorMessage);
      setMerlinState({ status: 'error' });
    }
  };

  const sendSuggestion = (suggestion: string) => {
    setInputText(suggestion);
    sendMessage();
  };

  const statusConfig = {
    idle: { color: colors.success, icon: 'circle', label: 'Ready' },
    thinking: { color: colors.warning, icon: 'sync', label: 'Thinking...', animate: true },
    responding: { color: colors.cyan, icon: 'pulse', label: 'Responding...', animate: true },
    error: { color: colors.critical, icon: 'alert-circle', label: 'Error' },
  };

  const config = statusConfig[merlin.status];

  if (!expanded) {
    return (
      <TouchableOpacity
        onPress={() => setExpanded(true)}
        className="bg-ownex-black-100 rounded-2xl p-5 border border-ownex-graphite-200"
        activeOpacity={0.9}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View className="w-12 h-12 rounded-xl items-center justify-center" style={{ backgroundColor: `${colors.merlin}20` }}>
              <Ionicons name="sparkles-sharp" size={24} color={colors.merlin} />
            </View>
            <View>
              <Text className="text-heading-sm font-display text-ownex-white">MERLIN</Text>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 }}>
                <Ionicons
                  name={config.icon}
                  size={12}
                  color={config.color}
                  style={config.animate ? { animation: 'spin 1s linear infinite' } : undefined}
                />
                <Text className="text-caption-sm font-medium" style={{ color: config.color }}>
                  {config.label}
                </Text>
              </View>
            </View>
          </View>
          <Ionicons name="chevron-forward-sharp" size={20} color={colors.white200} />
        </View>
        
        {messages.length > 0 && (
          <View className="mt-4 pt-4 border-t border-ownex-graphite-200">
            <Text className="text-caption text-ownex-white-200 mb-2">Last: {messages[messages.length - 1].content.substring(0, 60)}...</Text>
          </View>
        )}
        
        <View className="mt-3 flex-row items-center gap-2">
          <Ionicons name="chatbubble-sharp" size={16} color={colors.cyan} />
          <Text className="text-caption-sm text-ownex-cyan">Tap to chat</Text>
        </View>
      </TouchableOpacity>
    );
  }

  // Expanded chat view
  return (
    <styled.View className="bg-ownex-black-100 rounded-2xl border border-ownex-graphite-200 overflow-hidden">
      {/* Header */}
      <View className="flex-row items-center justify-between p-4 border-b border-ownex-graphite-200">
        <View className="flex-row items-center gap-3">
          <View className="w-10 h-10 rounded-lg items-center justify-center" style={{ backgroundColor: `${colors.merlin}20` }}>
            <Ionicons name="sparkles-sharp" size={22} color={colors.merlin} />
          </View>
          <View>
            <Text className="text-heading-sm font-display text-ownex-white">MERLIN</Text>
            <View className="flex-row items-center gap-2 mt-1">
              <Ionicons name={config.icon} size={12} color={config.color} style={config.animate ? { animation: 'spin 1s linear infinite' } : undefined} />
              <Text className="text-caption-sm" style={{ color: config.color }}>{config.label}</Text>
            </View>
          </View>
        </View>
        <TouchableOpacity onPress={() => setExpanded(false)} className="p-1">
          <Ionicons name="chevron-down-sharp" size={24} color={colors.white200} />
        </TouchableOpacity>
      </View>

      {/* Messages */}
      <ScrollView
        className="max-h-96"
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        inverted
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
      </ScrollView>

      {/* Suggestions */}
      {suggestions.length > 0 && merlin.status === 'idle' && (
        <View className="px-4 py-3 border-t border-ownex-graphite-200">
          <Text className="text-caption-sm text-ownex-white-200 mb-2">Suggestions</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
            {suggestions.map((s, i) => (
              <TouchableOpacity
                key={i}
                onPress={() => sendSuggestion(s)}
                className="px-3 py-1.5 rounded-full bg-ownex-graphite-100 border border-ownex-graphite-200"
              >
                <Text className="text-caption-sm text-ownex-cyan">{s}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* Input */}
      <View className="p-4 border-t border-ownex-graphite-200 bg-ownex-black-100">
        <View className="flex-row items-center gap-3">
          <TextInput
            value={inputText}
            onChangeText={setInputText}
            onSubmitEditing={sendMessage}
            placeholder="Ask MERLIN..."
            className="flex-1 bg-ownex-graphite-100 rounded-xl px-4 py-3 text-ownex-white"
            placeholderTextColor={colors.white200}
            maxLength={500}
            multiline
            maxHeight={100}
          />
          <TouchableOpacity
            onPress={sendMessage}
            disabled={!inputText.trim() || merlin.status === 'thinking'}
            className="w-12 h-12 rounded-xl items-center justify-center"
            style={{ backgroundColor: inputText.trim() && merlin.status !== 'thinking' ? colors.merlin : colors.graphite200 }}
          >
            <Ionicons name="send-sharp" size={22} color={colors.white} />
          </TouchableOpacity>
        </View>
      </View>
    </styled.View>
  );
};

interface MessageBubbleProps {
  message: MerlinMessage;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const colors = theme.colors;
  const isUser = message.role === 'user';
  
  return (
    <View className="flex-row" style={{ justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <View
        className="max-w-[80%] px-4 py-3 rounded-2xl"
        style={{
          backgroundColor: isUser ? colors.merlin : colors.graphite100,
          borderRadius: isUser ? 24 : 24,
          borderBottomRightRadius: isUser ? 4 : 24,
          borderBottomLeftRadius: isUser ? 24 : 4,
        }}
      >
        <Text className="text-body-sm text-ownex-white" style={{ color: isUser ? colors.white : colors.white }}>
          {message.content}
        </Text>
        <Text className="text-caption-sm mt-1 text-right" style={{ color: isUser ? 'rgba(255,255,255,0.6)' : colors.white200 }}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </Text>
      </View>
    </View>
  );
};