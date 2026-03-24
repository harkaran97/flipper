/**
 * Tab bar configuration. Three tabs: Feed, Saved, Builds.
 * Floating dark glass pill — Revolut-style. Labels shown.
 * Active tab: white icon + white label + subtle highlight bg.
 * Inactive: dimmed icons and labels.
 */
import React from 'react'
import { View, Text, Pressable } from 'react-native'
import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

const GLASS_TAB = {
  bg: 'rgba(20, 20, 22, 0.92)',
  border: 'rgba(255, 255, 255, 0.10)',
  activeIcon: '#FFFFFF',
  inactiveIcon: 'rgba(255,255,255,0.40)',
  activeLabel: '#FFFFFF',
  inactiveLabel: 'rgba(255,255,255,0.40)',
  activeBg: 'rgba(255,255,255,0.12)',
}

const TABS = [
  {
    key: 'index',
    label: 'Feed',
    icon: (active: boolean) => (
      <Ionicons name="trending-up" size={22} color={active ? GLASS_TAB.activeIcon : GLASS_TAB.inactiveIcon} />
    ),
  },
  {
    key: 'saved',
    label: 'Saved',
    icon: (active: boolean) => (
      <Ionicons name="bookmark" size={22} color={active ? GLASS_TAB.activeIcon : GLASS_TAB.inactiveIcon} />
    ),
  },
  {
    key: 'builds',
    label: 'Builds',
    icon: (active: boolean) => (
      <Ionicons name="construct" size={22} color={active ? GLASS_TAB.activeIcon : GLASS_TAB.inactiveIcon} />
    ),
  },
]

function FloatingTabBar({ state, navigation }: any) {
  const insets = useSafeAreaInsets()

  return (
    <View
      style={{
        position: 'absolute',
        bottom: insets.bottom + 12,
        left: 20,
        right: 20,
        height: 64,
        backgroundColor: GLASS_TAB.bg,
        borderRadius: 32,
        borderWidth: 0.5,
        borderColor: GLASS_TAB.border,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-around',
        paddingHorizontal: 8,
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.35,
        shadowRadius: 24,
        elevation: 20,
        overflow: 'hidden',
      }}
    >
      {/* Glass refraction top edge */}
      <View
        style={{
          position: 'absolute',
          top: 0,
          left: 16,
          right: 16,
          height: 0.5,
          backgroundColor: 'rgba(255,255,255,0.14)',
        }}
      />

      {TABS.map((tab, index) => {
        const isActive = state.index === index
        const route = state.routes[index]

        return (
          <Pressable
            key={tab.key}
            onPress={() => navigation.navigate(route.name)}
            style={{ flex: 1, alignItems: 'center', gap: 3, paddingVertical: 10 }}
          >
            <View
              style={{
                width: 36,
                height: 28,
                borderRadius: 10,
                backgroundColor: isActive ? GLASS_TAB.activeBg : 'transparent',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {tab.icon(isActive)}
            </View>
            <Text
              style={{
                fontSize: 10,
                fontWeight: isActive ? '600' : '400',
                color: isActive ? GLASS_TAB.activeLabel : GLASS_TAB.inactiveLabel,
                letterSpacing: 0.2,
              }}
            >
              {tab.label}
            </Text>
          </Pressable>
        )
      })}
    </View>
  )
}

export default function TabLayout() {
  return (
    <Tabs
      tabBar={(props) => <FloatingTabBar {...props} />}
      screenOptions={{
        headerShown: false,
      }}
    >
      <Tabs.Screen name="index" />
      <Tabs.Screen name="saved" />
      <Tabs.Screen name="builds" />
    </Tabs>
  )
}
