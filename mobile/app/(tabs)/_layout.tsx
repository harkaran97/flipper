/**
 * Tab bar configuration. Three tabs: Feed, Saved, Builds.
 * Floating light frosted glass pill — Revolut light mode style. Labels shown.
 * Active tab: black icon + black label + subtle dark highlight bg.
 * Inactive: dimmed grey icons and labels.
 */
import React from 'react'
import { View, Text, Pressable } from 'react-native'
import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

const GLASS_TAB = {
  // Light frosted glass — NOT black
  bg: 'rgba(255, 255, 255, 0.82)',       // frosted white
  border: 'rgba(60, 60, 67, 0.12)',      // iOS separator, very subtle
  shadow: '#000000',
  // Icons and labels
  activeIcon: '#000000',                  // black when active
  inactiveIcon: 'rgba(60, 60, 67, 0.35)', // dim grey when inactive
  activeLabel: '#000000',
  inactiveLabel: 'rgba(60, 60, 67, 0.35)',
  // Active tab highlight
  activeBg: 'rgba(0, 0, 0, 0.06)',       // subtle dark tint on white bg
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
        // Soft shadow underneath — key to the floating glass look
        shadowColor: GLASS_TAB.shadow,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.10,     // lighter than before — glass is subtle
        shadowRadius: 20,
        elevation: 12,
        overflow: 'hidden',
      }}
    >
      {/* Top edge highlight — lighter for white glass */}
      <View
        style={{
          position: 'absolute',
          top: 0,
          left: 16,
          right: 16,
          height: 0.5,
          backgroundColor: 'rgba(255, 255, 255, 0.90)', // bright top edge = glass feel
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
