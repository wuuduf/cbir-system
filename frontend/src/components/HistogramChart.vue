<template>
  <section class="panel chart-panel">
    <div class="chart-head">
      <strong>直方图</strong>
      <el-radio-group v-model="chartType" size="small" @change="$emit('type-change', chartType)">
        <el-radio-button label="hsv">HSV</el-radio-button>
        <el-radio-button label="gray">灰度</el-radio-button>
      </el-radio-group>
    </div>
    <v-chart v-if="option" class="chart" :option="option" autoresize />
    <div v-else class="empty muted">选择结果后显示直方图</div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps({
  data: {
    type: Object,
    default: null
  }
})

defineEmits(['type-change'])

const chartType = ref('hsv')
const option = computed(() => {
  if (!props.data) {
    return null
  }
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 12, top: 18, bottom: 28 },
    xAxis: { type: 'category', data: props.data.bins, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: props.data.values, itemStyle: { color: '#2563eb' } }]
  }
})
</script>

<style scoped>
.chart-panel {
  min-height: 260px;
}

.chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.chart {
  width: 100%;
  height: 210px;
}

.empty {
  height: 210px;
  display: grid;
  place-items: center;
}
</style>
