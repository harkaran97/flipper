/**
 * Root layout: sets up React Query provider, requests push notification
 * permissions on first launch, and registers the device token with the backend.
 */
import React, { useEffect } from 'react'
import { Stack } from 'expo-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as Notifications from 'expo-notifications'
import { api } from '../lib/api'

const queryClient = new QueryClient()

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
})

const registerForPushNotifications = async () => {
  try {
    const { status } = await Notifications.requestPermissionsAsync()
    if (status !== 'granted') return
    const token = await Notifications.getExpoPushTokenAsync()
    await api.post('/device-tokens', { token: token.data, platform: 'ios' })
  } catch {
    // non-fatal — app works without push
  }
}

export default function RootLayout() {
  useEffect(() => {
    registerForPushNotifications()
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="opportunity/[id]"
          options={{
            title: '',
            headerBackTitle: 'Opportunities',
          }}
        />
      </Stack>
    </QueryClientProvider>
  )
}
