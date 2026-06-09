<template>
  <el-tabs type="border-card">
    <!-- 泵站管理 -->
    <el-tab-pane label="泵站管理">
      <el-button v-if="canWrite" type="primary" size="small" @click="showStationForm()" style="margin-bottom:12px">
        <el-icon><Plus /></el-icon> 新增泵站
      </el-button>
      <el-table :data="stations" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="站名" />
        <el-table-column prop="location" label="位置" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <template v-if="canWrite">
              <el-button text type="primary" @click="showStationForm(row)">编辑</el-button>
              <el-button text type="danger" @click="delStation(row.id)">删除</el-button>
            </template>
            <el-button text type="success" @click="showUnits(row)">机组</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-tab-pane>

    <!-- 机组管理 -->
    <el-tab-pane label="机组管理">
      <el-form inline style="margin-bottom:12px">
        <el-form-item label="泵站">
          <el-select v-model="unitStationId" placeholder="选择泵站" @change="loadUnits">
            <el-option v-for="s in stations" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button v-if="canWrite" type="primary" size="small" @click="showUnitForm()" :disabled="!unitStationId">
            <el-icon><Plus /></el-icon> 新增机组
          </el-button>
        </el-form-item>
      </el-form>
      <el-table :data="units" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="unit_name" label="名称" />
        <el-table-column prop="rated_power_kw" label="额定功率(kW)" width="140" />
        <el-table-column prop="rated_flow" label="额定流量(m³/h)" width="150" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <template v-if="canWrite">
              <el-button text type="primary" @click="showUnitForm(row)">编辑</el-button>
              <el-button text type="danger" @click="delUnit(row.id)">删除</el-button>
            </template>
            <span v-else style="color:#999;font-size:12px">只读</span>
          </template>
        </el-table-column>
      </el-table>
    </el-tab-pane>
  </el-tabs>

  <!-- 泵站表单弹窗 -->
  <el-dialog v-model="stationDialogVisible" :title="editingStation ? '编辑泵站' : '新增泵站'" width="460px">
    <el-form :model="stationForm" label-width="80px">
      <el-form-item label="站名"><el-input v-model="stationForm.name" /></el-form-item>
      <el-form-item label="位置"><el-input v-model="stationForm.location" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="stationDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="saveStation">保存</el-button>
    </template>
  </el-dialog>

  <!-- 机组表单弹窗 -->
  <el-dialog v-model="unitDialogVisible" :title="editingUnit ? '编辑机组' : '新增机组'" width="460px">
    <el-form :model="unitForm" label-width="120px">
      <el-form-item label="名称"><el-input v-model="unitForm.unit_name" /></el-form-item>
      <el-form-item label="额定功率(kW)"><el-input-number v-model="unitForm.rated_power_kw" :min="0" /></el-form-item>
      <el-form-item label="额定流量(m³/h)"><el-input-number v-model="unitForm.rated_flow" :min="0" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="unitDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="saveUnit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import {
  getStations, createStation, updateStation, deleteStation,
  getUnits, createUnit, updateUnit, deleteUnit,
} from '../api'

const userStore = useUserStore()
const canWrite = computed(() => ['admin', 'operator'].includes(userStore.role))

const stations = ref<any[]>([])
const units = ref<any[]>([])
const unitStationId = ref<number | null>(null)

const stationDialogVisible = ref(false)
const editingStation = ref<any>(null)
const stationForm = reactive({ name: '', location: '' })

const unitDialogVisible = ref(false)
const editingUnit = ref<any>(null)
const unitForm = reactive({ unit_name: '', rated_power_kw: 0, rated_flow: 0 })

async function loadStations() {
  const { data } = await getStations()
  stations.value = data
  if (data.length > 0 && !unitStationId.value) {
    unitStationId.value = data[0].id
    await loadUnits()
  }
}
async function loadUnits() {
  if (!unitStationId.value) return
  const { data } = await getUnits(unitStationId.value); units.value = data
}

function showStationForm(row?: any) {
  editingStation.value = row || null
  stationForm.name = row?.name || ''
  stationForm.location = row?.location || ''
  stationDialogVisible.value = true
}

async function saveStation() {
  if (editingStation.value) {
    await updateStation(editingStation.value.id, stationForm)
  } else {
    await createStation(stationForm)
  }
  stationDialogVisible.value = false
  ElMessage.success('保存成功')
  await loadStations()
}

async function delStation(id: number) {
  await ElMessageBox.confirm('确定删除该泵站？', '确认')
  await deleteStation(id)
  ElMessage.success('删除成功')
  await loadStations()
}

function showUnits(row: any) {
  unitStationId.value = row.id
  loadUnits()
}

function showUnitForm(row?: any) {
  editingUnit.value = row || null
  unitForm.unit_name = row?.unit_name || ''
  unitForm.rated_power_kw = row?.rated_power_kw || 0
  unitForm.rated_flow = row?.rated_flow || 0
  unitDialogVisible.value = true
}

async function saveUnit() {
  if (!unitStationId.value) return
  if (editingUnit.value) {
    await updateUnit(unitStationId.value, editingUnit.value.id, unitForm)
  } else {
    await createUnit(unitStationId.value, unitForm)
  }
  unitDialogVisible.value = false
  ElMessage.success('保存成功')
  await loadUnits()
}

async function delUnit(id: number) {
  if (!unitStationId.value) return
  await ElMessageBox.confirm('确定删除该机组？', '确认')
  await deleteUnit(unitStationId.value, id)
  ElMessage.success('删除成功')
  await loadUnits()
}

onMounted(loadStations)
</script>
