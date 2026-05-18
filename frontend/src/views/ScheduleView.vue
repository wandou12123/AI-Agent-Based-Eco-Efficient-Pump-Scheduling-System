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
        <el-form-item>
          <el-button type="primary" @click="createAndOptimize" :loading="optimizing">
            <el-icon><Lightning /></el-icon> 执行优化
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card shadow="never">
      <template #header><span style="font-weight:600">调度任务记录</span></template>
      <el-table :data="tasks" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="objective_text" label="调度目标" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
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

    <!-- 方案详情弹窗 -->
    <el-dialog v-model="planVisible" title="调度方案详情" width="700px">
      <div v-if="currentPlan">
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
          <el-descriptions-item label="总能耗">{{ currentPlan.energy_kwh }} kW</el-descriptions-item>
          <el-descriptions-item label="总流量">{{ currentPlan.plan_json?.total_flow }} m³/h</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <h4>AI 解释</h4>
        <div class="explanation" v-html="renderMd(currentPlan.explanation || '暂无')"></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import { getStations, getTasks, createTask, runOptimize, getTaskPlans } from '../api'

const stations = ref<any[]>([])
const tasks = ref<any[]>([])
const optimizing = ref(false)
const planVisible = ref(false)
const currentPlan = ref<any>(null)

const form = reactive({ station_id: null as number | null, min_flow: 200, objective: '最小化能耗' })

function statusType(s: string) {
  const map: Record<string, string> = { done: 'success', failed: 'danger', optimizing: 'warning', created: 'info' }
  return map[s] || 'info'
}

function renderMd(t: string) { try { return marked.parse(t, { breaks: true }) } catch { return t } }

async function createAndOptimize() {
  if (!form.station_id) { ElMessage.warning('请选择泵站'); return }
  optimizing.value = true
  try {
    const { data: task } = await createTask({
      station_id: form.station_id,
      objective_text: form.objective,
      constraints_json: { station_id: form.station_id, min_flow: form.min_flow },
    })
    const { data: result } = await runOptimize(task.id)
    ElMessage.success('优化完成')
    await loadTasks()
    currentPlan.value = { plan_json: result.plan, energy_kwh: result.plan.total_energy_kwh, explanation: result.explanation }
    planVisible.value = true
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
  await loadTasks()
})
</script>

<style scoped>
.explanation { padding: 12px; background: #fafafa; border-radius: 8px; line-height: 1.7; font-size: 14px; }
</style>
