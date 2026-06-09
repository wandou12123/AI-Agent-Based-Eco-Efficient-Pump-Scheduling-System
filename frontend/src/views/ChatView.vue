<template>
  <div class="chat-container">
    <!-- 左侧会话列表 -->
    <div class="conv-panel">
      <el-button type="primary" @click="newConversation" style="width:100%;margin-bottom:12px" :disabled="!canWrite">
        <el-icon><Plus /></el-icon> 新对话
      </el-button>
      <div class="conv-list">
        <div v-for="c in conversations" :key="c.id"
             :class="['conv-item', { active: c.id === activeConvId }]"
             @click="selectConversation(c.id)">
          <el-icon><ChatDotRound /></el-icon>
          <input v-if="editingConvId === c.id"
                 v-model="editingTitle"
                 class="conv-rename-input"
                 @keyup.enter="saveRename(c)"
                 @blur="saveRename(c)"
                 @click.stop
                 ref="renameInputRef"
                 maxlength="100" />
          <span v-else class="conv-title" @dblclick.stop="startRename(c)">{{ c.title }}</span>
          <el-icon class="conv-edit" @click.stop="startRename(c)"><Edit /></el-icon>
          <el-icon class="conv-del" @click.stop="delConversation(c.id)"><Delete /></el-icon>
        </div>
      </div>
    </div>

    <!-- 右侧对话区 -->
    <div class="chat-main">
      <div class="messages" ref="messagesRef">
        <div v-if="messages.length === 0" class="empty-hint">
          <el-icon :size="48" color="#c0c4cc"><ChatRound /></el-icon>
          <p>开始与智水调度助手对话</p>
          <p class="sub">支持文本对话和 .docx 文书上传分析</p>
        </div>
        <div v-for="msg in messages" :key="msg.id" :class="['msg-row', msg.role]">
          <div class="avatar">
            <el-icon v-if="msg.role === 'user'" :size="20"><User /></el-icon>
            <el-icon v-else :size="20"><Cloudy /></el-icon>
          </div>
          <div class="bubble" v-html="renderMd(msg.content || '')"></div>
        </div>
        <div v-if="streaming" class="msg-row assistant">
          <div class="avatar"><el-icon :size="20"><Cloudy /></el-icon></div>
          <div class="bubble" v-html="renderMd(streamContent)"></div>
        </div>
      </div>

      <el-alert v-if="!canWrite" type="info" :closable="false" title="只读账号：可浏览历史对话，不可发送消息或上传文书。" style="margin:8px 16px" />

      <!-- 文件上传提示 -->
      <div v-if="uploadedFile && canWrite" class="file-bar">
        <el-tag closable @close="uploadedFile = null">
          <el-icon><Document /></el-icon> {{ uploadedFile.original_name }}
        </el-tag>
        <el-button size="small" type="primary" plain @click="analyzeDoc('qa')">分析文书内容</el-button>
        <el-button size="small" type="success" plain @click="analyzeDoc('extract', true)">提取并创建任务</el-button>
        <el-button size="small" type="warning" plain @click="analyzeDoc('extract', false)">仅提取参数</el-button>
      </div>

      <!-- 输入区 -->
      <div class="input-bar">
        <el-upload v-if="canWrite" :show-file-list="false" :before-upload="handleUpload" accept=".docx,.doc">
          <el-button circle><el-icon><FolderOpened /></el-icon></el-button>
        </el-upload>
        <el-button v-if="canWrite" circle :type="voiceState === 'recording' ? 'danger' : voiceState === 'transcribing' ? 'warning' : 'default'"
                   :loading="voiceState === 'transcribing'"
                   :class="{ 'voice-recording': voiceState === 'recording' }"
                   @click="toggleVoice"
                   :title="voiceState === 'recording' ? '点击停止录音' : '点击开始语音输入'">
          <el-icon><Microphone /></el-icon>
        </el-button>
        <el-button v-if="canWrite" size="small" type="success" plain @click="sendToolMessage" :loading="streaming">工具 Agent</el-button>
        <span v-if="voiceState === 'recording'" class="voice-hint">正在聆听...</span>
        <el-input v-model="inputText" placeholder="输入消息..." @keyup.enter="sendMessage"
                  :disabled="streaming || !canWrite" style="flex:1" />
        <el-button type="primary" :loading="streaming" @click="sendMessage" :disabled="!canWrite">
          <el-icon><Promotion /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import { marked } from 'marked'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getConversations, createConversation, deleteConversation,
  renameConversation, getMessages, uploadFile, analyzeDocx, transcribeVoice, toolChat,
} from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const canWrite = computed(() => ['admin', 'operator'].includes(userStore.role))

interface Conv { id: number; title: string; created_at: string; updated_at: string }
interface Msg { id: number; role: string; content: string; msg_type: string; file_url?: string; created_at: string }

const conversations = ref<Conv[]>([])
const messages = ref<Msg[]>([])
const activeConvId = ref<number | null>(null)
const inputText = ref('')
const streaming = ref(false)
const streamContent = ref('')
const messagesRef = ref<HTMLElement>()
const uploadedFile = ref<any>(null)

// ========== 对话重命名 ==========
const editingConvId = ref<number | null>(null)
const editingTitle = ref('')
const renameInputRef = ref<HTMLInputElement[]>()

function startRename(c: Conv) {
  editingConvId.value = c.id
  editingTitle.value = c.title
  nextTick(() => {
    const inputs = renameInputRef.value
    if (inputs && inputs.length > 0) {
      inputs[0].focus()
      inputs[0].select()
    }
  })
}

async function saveRename(c: Conv) {
  const newTitle = editingTitle.value.trim()
  editingConvId.value = null
  if (!newTitle || newTitle === c.title) return
  try {
    await renameConversation(c.id, newTitle)
    c.title = newTitle
  } catch (e: any) {
    ElMessage.error('重命名失败: ' + (e.message || ''))
  }
}

// ========== 语音输入 ==========
type VoiceState = 'idle' | 'recording' | 'transcribing'
const voiceState = ref<VoiceState>('idle')

const hasBrowserSTT = typeof window !== 'undefined' && !!(
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
)

let recognition: any = null
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

function toggleVoice() {
  if (streaming.value) return
  if (voiceState.value === 'recording') {
    stopVoice()
  } else if (voiceState.value === 'idle') {
    startVoice()
  }
}

function startVoice() {
  if (hasBrowserSTT) {
    startBrowserSTT()
  } else {
    startMediaRecorder()
  }
}

function stopVoice() {
  if (hasBrowserSTT && recognition) {
    recognition.stop()
  } else if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }
}

function startBrowserSTT() {
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.interimResults = false
  recognition.continuous = false

  recognition.onstart = () => {
    voiceState.value = 'recording'
  }

  recognition.onresult = (event: any) => {
    const text = event.results[0][0].transcript
    if (text) {
      inputText.value = text
      nextTick(() => sendMessage())
    }
  }

  recognition.onerror = (event: any) => {
    console.error('[Voice] Browser STT error:', event.error)
    if (event.error === 'not-allowed') {
      ElMessage.error('麦克风权限被拒绝，请在浏览器设置中允许麦克风访问')
    } else if (event.error === 'no-speech') {
      ElMessage.warning('未检测到语音，请重试')
    } else {
      ElMessage.warning('语音识别出错: ' + event.error)
    }
    voiceState.value = 'idle'
  }

  recognition.onend = () => {
    if (voiceState.value === 'recording') {
      voiceState.value = 'idle'
    }
  }

  try {
    recognition.start()
  } catch (e: any) {
    ElMessage.error('无法启动语音识别: ' + e.message)
    voiceState.value = 'idle'
  }
}

async function startMediaRecorder() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data)
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (audioChunks.length === 0) {
        voiceState.value = 'idle'
        return
      }
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      voiceState.value = 'transcribing'
      try {
        const { data } = await transcribeVoice(blob)
        if (data.text) {
          inputText.value = data.text
          nextTick(() => sendMessage())
        } else {
          ElMessage.warning('未识别到语音内容')
        }
      } catch (e: any) {
        const msg = e.response?.data?.detail || e.message || '语音转写失败'
        ElMessage.error(msg)
      } finally {
        voiceState.value = 'idle'
      }
    }

    mediaRecorder.onerror = () => {
      ElMessage.error('录音出错，请重试')
      voiceState.value = 'idle'
    }

    mediaRecorder.start()
    voiceState.value = 'recording'
  } catch (e: any) {
    if (e.name === 'NotAllowedError') {
      ElMessage.error('麦克风权限被拒绝，请在浏览器设置中允许麦克风访问')
    } else {
      ElMessage.error('无法访问麦克风: ' + e.message)
    }
    voiceState.value = 'idle'
  }
}

onUnmounted(() => {
  if (recognition) { try { recognition.abort() } catch {} }
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    try { mediaRecorder.stop() } catch {}
  }
})

function renderMd(text: string) {
  try {
    return marked.parse(text || '', { breaks: true })
  } catch { return text }
}

function scrollBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

async function loadConversations() {
  const { data } = await getConversations()
  conversations.value = data
}

async function selectConversation(id: number) {
  activeConvId.value = id
  const { data } = await getMessages(id)
  messages.value = data
  scrollBottom()
}

async function newConversation() {
  const { data } = await createConversation()
  conversations.value.unshift(data)
  activeConvId.value = data.id
  messages.value = []
}

async function delConversation(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该对话？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteConversation(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (activeConvId.value === id) {
      activeConvId.value = null
      messages.value = []
    }
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e.message || ''))
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || streaming.value || !canWrite.value) return

  messages.value.push({ id: Date.now(), role: 'user', content: text, msg_type: 'text', created_at: '' })
  inputText.value = ''
  streaming.value = true
  streamContent.value = ''
  scrollBottom()

  const token = localStorage.getItem('token')
  try {
    const body = JSON.stringify({
      conversation_id: activeConvId.value || undefined,
      content: text,
      msg_type: uploadedFile.value ? 'docx' : 'text',
      file_url: uploadedFile.value?.url || null,
    })

    console.log('[Chat] 发送消息 ->', { conv: activeConvId.value, text: text.slice(0, 40) })

    const response = await fetch('/api/v1/chat/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body,
    })

    console.log('[Chat] 响应状态:', response.status)

    if (!response.ok) {
      const errText = await response.text()
      let detail = errText
      try { detail = JSON.parse(errText).detail } catch {}
      throw new Error(`HTTP ${response.status}: ${detail}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(line.slice(6))
            if (parsed.content) {
              streamContent.value += parsed.content
              scrollBottom()
            }
            if (parsed.done) {
              messages.value.push({
                id: Date.now() + 1, role: 'assistant',
                content: streamContent.value, msg_type: 'text', created_at: '',
              })
              if (parsed.conversation_id) {
                activeConvId.value = parsed.conversation_id
              }
            }
          } catch {}
        }
      }
    }

    if (!streamContent.value) {
      ElMessage.warning('AI 未返回任何内容，请检查后端日志')
    }
  } catch (e: any) {
    console.error('[Chat] 错误:', e)
    ElMessage.error('请求失败: ' + (e.message || ''))
  } finally {
    streaming.value = false
    streamContent.value = ''
    uploadedFile.value = null
    await loadConversations()
  }
}

async function sendToolMessage() {
  const text = inputText.value.trim()
  if (!text || streaming.value || !canWrite.value) return
  messages.value.push({ id: Date.now(), role: 'user', content: `[工具] ${text}`, msg_type: 'text', created_at: '' })
  inputText.value = ''
  streaming.value = true
  scrollBottom()
  try {
    const { data } = await toolChat({ conversation_id: activeConvId.value || undefined, content: text })
    if (!activeConvId.value && data.conversation_id) activeConvId.value = data.conversation_id
    messages.value.push({
      id: Date.now() + 1, role: 'assistant', content: data.content, msg_type: 'text', created_at: '',
    })
    scrollBottom()
    await loadConversations()
  } catch (e: any) {
    ElMessage.error('工具 Agent 失败: ' + (e.message || ''))
  } finally {
    streaming.value = false
  }
}

async function handleUpload(file: File) {
  try {
    const { data } = await uploadFile(file)
    uploadedFile.value = data
    ElMessage.success('文件上传成功')
  } catch {}
  return false
}

async function analyzeDoc(mode: string, autoCreate = false) {
  if (!activeConvId.value) await newConversation()
  if (!uploadedFile.value) return
  streaming.value = true
  try {
    const { data } = await analyzeDocx({
      conversation_id: activeConvId.value,
      file_url: uploadedFile.value.url,
      mode,
      question: mode === 'qa' ? '请总结文书的主要内容和调度要求' : '',
      auto_create_task: mode === 'extract' && autoCreate,
    })
    messages.value.push({
      id: Date.now(), role: 'assistant', content: data.content, msg_type: 'text', created_at: '',
    })
    if (data.task_created) {
      ElMessage.success(`已创建调度任务 #${data.task_id}，请前往调度优化页面执行`)
    }
    scrollBottom()
  } finally {
    streaming.value = false
    uploadedFile.value = null
  }
}

onMounted(() => { loadConversations() })
</script>

<style scoped>
.chat-container { display: flex; height: 100%; gap: 0; }
.conv-panel {
  width: 260px; min-width: 260px; padding: 16px; background: #fff;
  border-right: 1px solid #f0f0f0; display: flex; flex-direction: column;
}
.conv-list { flex: 1; overflow-y: auto; }
.conv-item {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 8px;
  cursor: pointer; margin-bottom: 4px; font-size: 14px; color: #333;
}
.conv-item:hover, .conv-item.active { background: var(--primary-light); color: var(--primary); }
.conv-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-edit, .conv-del { opacity: 0; transition: .2s; flex-shrink: 0; }
.conv-item:hover .conv-edit { opacity: 1; color: var(--primary); cursor: pointer; }
.conv-item:hover .conv-del { opacity: 1; color: #f56c6c; cursor: pointer; }
.conv-rename-input {
  flex: 1; border: 1px solid var(--primary); border-radius: 4px;
  padding: 2px 6px; font-size: 13px; outline: none; min-width: 0;
  background: #fff; color: #333;
}

.chat-main { flex: 1; display: flex; flex-direction: column; background: #fafafa; }
.messages { flex: 1; overflow-y: auto; padding: 20px; }
.empty-hint { text-align: center; margin-top: 120px; color: #999; }
.empty-hint .sub { font-size: 13px; color: #bbb; margin-top: 4px; }
.msg-row { display: flex; gap: 12px; margin-bottom: 20px; }
.msg-row.user { flex-direction: row-reverse; }
.avatar {
  width: 36px; height: 36px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; flex-shrink: 0;
}
.msg-row.user .avatar { background: var(--primary); color: #fff; }
.msg-row.assistant .avatar { background: #e8e8e8; color: #333; }
.bubble {
  max-width: 70%; padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.7;
  word-break: break-word;
}
.msg-row.user .bubble { background: var(--primary); color: #fff; border-top-right-radius: 4px; }
.msg-row.assistant .bubble { background: #fff; border: 1px solid #e8e8e8; border-top-left-radius: 4px; }

.file-bar { padding: 8px 20px; background: #fff; border-top: 1px solid #f0f0f0; display: flex; gap: 8px; align-items: center; }
.input-bar {
  padding: 12px 20px; background: #fff; border-top: 1px solid #f0f0f0;
  display: flex; gap: 8px; align-items: center;
}

.voice-recording { animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.5); }
  50% { box-shadow: 0 0 0 8px rgba(245, 108, 108, 0); }
}
.voice-hint {
  font-size: 12px; color: #f56c6c; animation: blink 1s ease-in-out infinite; white-space: nowrap;
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
