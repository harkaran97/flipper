/**
 * AsyncStorage helpers for persisting saved opportunities and build statuses.
 * All data is local-only — no sync to backend.
 */
import AsyncStorage from '@react-native-async-storage/async-storage'

const SAVED_KEY = 'flipper:saved'
const BUILDS_KEY = 'flipper:builds'

export const getSavedIds = async (): Promise<string[]> => {
  const raw = await AsyncStorage.getItem(SAVED_KEY)
  return raw ? JSON.parse(raw) : []
}

export const toggleSaved = async (id: string): Promise<void> => {
  const ids = await getSavedIds()
  const idx = ids.indexOf(id)
  if (idx === -1) {
    ids.push(id)
  } else {
    ids.splice(idx, 1)
  }
  await AsyncStorage.setItem(SAVED_KEY, JSON.stringify(ids))
}

export const getBuildStatuses = async (): Promise<Record<string, string>> => {
  const raw = await AsyncStorage.getItem(BUILDS_KEY)
  return raw ? JSON.parse(raw) : {}
}

export const markAsBuild = async (id: string): Promise<void> => {
  const builds = await getBuildStatuses()
  builds[id] = 'active_build'
  await AsyncStorage.setItem(BUILDS_KEY, JSON.stringify(builds))
}

export const removeFromBuild = async (id: string): Promise<void> => {
  const builds = await getBuildStatuses()
  delete builds[id]
  await AsyncStorage.setItem(BUILDS_KEY, JSON.stringify(builds))
}
