<template>
  <div>
    <el-card shadow="never" style="margin-bottom:16px">
      <template #header><span style="font-weight:600">创建调度任务</span></template>
      <el-form :model="form" inline>
        <el-form-item label="泵站">
          <el-select v-model="form.station_id" placeholder="选择泵站" style="width:180px">
            <el-option v-for="s in stations" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标流量(m³/h)">
          <el-input-number v-model="form.min_flow" :min="0" :step="10" />
        </el-form-item>
        <el-form-item label="调度目标">
          <el-input v-model="form.objective" placeholder="如：最小化能耗" style="width:240px" />
        </el-form-item>
        <el-form-item label="异步队列">
          <el-switch v-model="form.useAsync" :disabled="!celeryEnabled" active-text="Celery" inactive-text="同步" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="createAndOptimize" :loading="optimizing">
            <el-icon><Lightning /></el-icon> 执行优化
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header><span style="font-weight:600">调度任务记录</span></template>
      <el-table :data="tasks" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="objective_text" label="调度目标" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text type="primary" @click="viewPlan(row.id)">查看方案</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="planVisible" title="调度方案详情" width="760px">
      <div v-if="currentPlan">
        <el-alert
          v-if="currentSafety"
          :title="currentSafety.passed ? '安全校验通过' : '安全校验存在告警'"
          :type="currentSafety.passed ? 'success' : 'warning'"
          :closable="false"
          style="margin-bottom:16px"
        />
        <h4 style="margin-bottom:12px">机组启停方案</h4>
        <el-table :data="currentPlan.plan_json?.plan || []" stripe size="small">
          <el-table-column prop="unit_name" label="机组" />
          <el-table-column prop="action" label="操作" width="80">
            <template #default="{ row }">
              <el-tag :type="row.action === '启动' ? 'success' : 'info'" size="small">{{ row.action }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target_power_kw" label="功率(kW)" width="100" />
          <el-table-column prop="target_flow" label="流量(m³/h)" width="110" />
        </el-table>
        <el-divider />
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="总功率">{{ currentPlan.plan_json?.total_energy_kwh ?? currentPlan.energy_kwh }} kW</el-descriptions-item>
          <el-descriptions-item label="总流量">{{ currentPlan.plan_json?.total_flow }} m³/h</el-descriptions-item>
          <el-descriptions-item label="可行性">
            <el-tag :type="currentPlan.plan_json?.feasible ? 'success' : 'danger'" size="small">
              {{ currentPlan.plan_json?.feasible ? '可行' : '不可行' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <el-divider v-if="currentSafety?.checks?.length" />
        <div v-if="currentSafety?.checks?.length">
          <h4>安全校验明细</h4>
          <el-table :data="currentSafety.checks" size="small" stripe>
            <el-table-column prop="item" label="检查项" width="140" />
            <el-table-column prop="detail" label="说明" />
            <el-table-column label="结果" width="80">
              <template #default="{ row }">
                <el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '通过' : '未通过' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-divider v-if="currentSafetySummary" />
        <div v-if="currentSafetySummary">
          <h4>安全摘要</h4>
          <div class="explanation">{{ currentSafetySummary }}</div>
        </div>
        <el-divider />
        <h4>AI 解释</h4>
        <div class="explanation" v-html="renderMd(currentPlan.explanation || '暂无')"></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import { getStations, getTasks, createTask, runOptimize, getTaskPlans, getOptimizeStatus } from '../api'
import axios from 'axios'

const stations = ref<any[]>([])
const tasks = ref<any[]>([])
const optimizing = ref(false)
const planVisible = ref(false)
const currentPlan = ref<any>(null)
const celeryEnabled = ref(false)

const form = reactive({ station_id: null as number | null, min_flow: 200, objective: '最小化能耗', useAsync: false })

const currentSafety = computed(() => currentPlan.value?.plan_json?.safety || null)
const currentSafetySummary = computed(() => currentPlan.value?.plan_json?.safety_summary || '')

const STATUS_LABELS: Record<string, string> = {
  created: '已创建', parsing: '解析中', optimizing: '优化中',
  validating: '校验中', done: '已完成', failed: '失败',
}

function statusType(s: string) {
  const map: Record<string, string> = { done: 'success', failed: 'danger', optimizing: 'warning', parsing: 'warning', validating: 'warning', created: 'info' }
  return map[s] || 'info'
}

function statusLabel(s: string) { return STATUS_LABELS[s] || s }

function renderMd(t: string) { try { return marked.parse(t, { breaks: true }) } catch { return t } }

function showPlanResult(result: any) {
  currentPlan.value = {
    plan_json: result.plan,
    energy_kwh: result.plan?.total_energy_kwh,
    explanation: result.explanation,
  }
  planVisible.value = true
}

async function pollOptimizeResult(taskId: number, jobId: string) {
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 2000))
    const { data: status } = await getOptimizeStatus(taskId, jobId)
    if (status.state === 'done') {
      showPlanResult(status.result)
      return
    }
    if (status.state === 'failed') {
      ElMessage.error('异步优化失败: ' + (status.error || ''))
      return
    }
  }
  ElMessage.warning('优化超时，请稍后查看任务列表')
}

async function createAndOptimize() {
  if (!form.station_id) { ElMessage.warning('请选择泵站'); return }
  optimizing.value = true
  try {
    const { data: task } = await createTask({
      station_id: form.station_id,
      objective_text: form.objective,
      constraints_json: { station_id: form.station_id, min_flow: form.min_flow },
    })
    const { data: result } = await runOptimize(task.id, form.useAsync && celeryEnabled.value)
    if (result.async) {
      ElMessage.info('优化任务已提交队列，正在等待结果...')
      await pollOptimizeResult(task.id, result.job_id)
    } else {
      ElMessage.success(result.safety?.passed !== false ? '优化完成' : '优化完成（存在安全告警）')
      showPlanResult(result)
    }
    await loadTasks()
  } finally { optimizing.value = false }
}

async function viewPlan(taskId: number) {
  const { data } = await getTaskPlans(taskId)
  if (data.length) { currentPlan.value = data[0]; planVisible.value = true }
  else ElMessage.info('暂无方案')
}

async function loadTasks() { const { data } = await getTasks(); tasks.value = data }

onMounted(async () => {
  const { data } = await getStations(); stations.value = data
  if (data.length) form.station_id = data[0].id
  try {
    const res = await axios.get('/api/health')
    const health = res.data?.data ?? res.data
    celeryEnabled.value = !!health?.celery
    form.useAsync = celeryEnabled.value
  } catch {}
  await loadTasks()
})
</script>

<style scoped>
.explanation { padding: 12px; background: #fafafa; border-radius: 8px; line-height: 1.7; font-size: 14px; }
</style>
