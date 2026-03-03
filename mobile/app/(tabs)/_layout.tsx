/**
 * Tab bar configuration. Three tabs: Opportunities, Saved, My Builds.
 * Icon-only (no labels). Active tab in black, inactive in grey.
 */
import React from 'react'
import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { colours } from '../../constants/colours'

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colours.tabActive,
        tabBarInactiveTintColor: colours.tabInactive,
        tabBarShowLabel: false,
        tabBarStyle: {
          backgroundColor: colours.bg,
          borderTopWidth: 1,
          borderTopColor: colours.border,
        },
        headerShown: false,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="trending-up" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="saved"
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="bookmark" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="builds"
        options={{
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="construct" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  )
}
