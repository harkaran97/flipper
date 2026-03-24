/**
 * Root layout: sets up React Query provider and gesture handler root.
 */
import '../global.css'
import React from 'react'
import { Stack } from 'expo-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { GestureHandlerRootView } from 'react-native-gesture-handler'

const queryClient = new QueryClient()

export default function RootLayout() {
  console.log('RootLayout rendering')

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
    <QueryClientProvider client={queryClient}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="opportunity/[id]"
          options={{
            title: '',
            headerBackTitle: 'Opportunities',
            headerTransparent: true,
            headerStyle: { backgroundColor: 'rgba(255,255,255,0.8)' },
            headerBlurEffect: 'regular',
          }}
        />
      </Stack>
    </QueryClientProvider>
    </GestureHandlerRootView>
  )
}
