<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="8" v-for="s in stations" :key="s.id">
        <el-card shadow="hover" class="station-card" @click="selectStation(s)">
          <div class="station-icon">
            <el-icon :size="32" color="#1677ff"><OfficeBuilding /></el-icon>
          </div>
          <h3>{{ s.name }}</h3>
          <p class="loc">{{ s.location || '未知位置' }}</p>
          <el-tag size="small" type="success">运行中</el-tag>
        </el-card>
      </el-col>
      <el-col :span="8" v-if="stations.length === 0">
        <el-empty description="暂无泵站，请在配置页面添加" />
      </el-col>
    </el-row>

    <!-- 泵站详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="currentStation?.name || ''" width="800px">
      <h4>机组列表</h4>
      <el-table :data="units" stripe size="small" style="margin:12px 0">
        <el-table-column prop="unit_name" label="名称" />
        <el-table-column prop="rated_power_kw" label="额定功率(kW)" width="130" />
        <el-table-column prop="rated_flow" label="额定流量(m³/h)" width="140" />
      </el-table>

      <h4>近期工况</h4>
      <div v-if="statusData.length" style="height:300px">
        <v-chart :option="chartOption" autoresize style="width:100%;height:100%" />
      </div>
      <el-empty v-else description="暂无工况数据" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { getStations, getUnits, getStationStatus } from '../api'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const stations = ref<any[]>([])
const currentStation = ref<any>(null)
const detailVisible = ref(false)
const units = ref<any[]>([])
const statusData = ref<any[]>([])

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['流量', '功率', '扬程'] },
  xAxis: { type: 'category', data: statusData.value.map((d: any) => d.ts?.slice(11, 16) || '') },
  yAxis: { type: 'value' },
  series: [
    { name: '流量', type: 'line', data: statusData.value.map((d: any) => d.flow), smooth: true },
    { name: '功率', type: 'line', data: statusData.value.map((d: any) => d.power), smooth: true },
    { name: '扬程', type: 'line', data: statusData.value.map((d: any) => d.head), smooth: true },
  ],
}))

async function selectStation(s: any) {
  currentStation.value = s
  detailVisible.value = true
  const [u, st] = await Promise.all([getUnits(s.id), getStationStatus(s.id)])
  units.value = u.data
  statusData.value = st.data.reverse()
}

onMounted(async () => { const { data } = await getStations(); stations.value = data })
</script>

<style scoped>
.station-card { cursor: pointer; text-align: center; margin-bottom: 16px; }
.station-card:hover { border-color: var(--primary); }
.station-icon { margin-bottom: 8px; }
.station-card h3 { font-size: 16px; margin-bottom: 4px; }
.loc { font-size: 13px; color: #999; margin-bottom: 8px; }
</style>
