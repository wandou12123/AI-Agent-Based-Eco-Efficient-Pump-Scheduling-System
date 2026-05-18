import api from './request'

// Auth
export const login = (data: { username: string; password: string }) =>
  api.post('/auth/login', data)
export const register = (data: { username: string; password: string }) =>
  api.post('/auth/register', data)
export const getMe = () => api.get('/auth/me')

// Conversations
export const getConversations = () => api.get('/conversations')
export const createConversation = () => api.post('/conversations')
export const deleteConversation = (id: number) => api.delete(`/conversations/${id}`)
export const renameConversation = (id: number, title: string) =>
  api.patch(`/conversations/${id}`, { title })
export const getMessages = (convId: number) => api.get(`/conversations/${convId}/messages`)

// Chat (SSE handled separately)
export const analyzeDocx = (data: any) => api.post('/chat/docx-analyze', data)

// Stations
export const getStations = () => api.get('/stations')
export const createStation = (data: any) => api.post('/stations', data)
export const updateStation = (id: number, data: any) => api.put(`/stations/${id}`, data)
export const deleteStation = (id: number) => api.delete(`/stations/${id}`)
export const getUnits = (stationId: number) => api.get(`/stations/${stationId}/units`)
export const createUnit = (stationId: number, data: any) => api.post(`/stations/${stationId}/units`, data)
export const updateUnit = (stationId: number, unitId: number, data: any) =>
  api.put(`/stations/${stationId}/units/${unitId}`, data)
export const deleteUnit = (stationId: number, unitId: number) =>
  api.delete(`/stations/${stationId}/units/${unitId}`)
export const getStationStatus = (stationId: number) => api.get(`/stations/${stationId}/status`)

// Tasks
export const getTasks = () => api.get('/tasks')
export const createTask = (data: any) => api.post('/tasks', data)
export const getTask = (id: number) => api.get(`/tasks/${id}`)
export const getTaskPlans = (id: number) => api.get(`/tasks/${id}/plans`)
export const runOptimize = (id: number) => api.post(`/tasks/${id}/optimize`)

// Upload
export const uploadFile = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
}

// Voice
export const transcribeVoice = (file: Blob, filename = 'recording.webm') => {
  const form = new FormData()
  form.append('file', file, filename)
  return api.post('/voice/transcribe', form, { headers: { 'Content-Type': 'multipart/form-data' } })
}
