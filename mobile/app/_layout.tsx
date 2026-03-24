/**
 * Root layout: sets up React Query provider and gesture handler root.
 */
import '../global.css'
import React from 'react'
import { Stack } from 'expo-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { colours } from '../constants/colours'

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
            headerStyle: { backgroundColor: colours.bg },
            headerShadowVisible: false,
          }}
        />
      </Stack>
    </QueryClientProvider>
    </GestureHandlerRootView>
  )
}
