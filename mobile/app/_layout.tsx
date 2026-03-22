/**
 * Root layout: sets up React Query provider.
 */
import '../global.css'
import React from 'react'
import { Stack } from 'expo-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

export default function RootLayout() {
  console.log('RootLayout rendering')

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
