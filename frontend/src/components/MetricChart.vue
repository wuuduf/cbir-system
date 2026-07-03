<template>
  <section class="charts">
    <div class="panel">
      <div class="chart-title">
        <strong>指标对比</strong>
        <span v-if="result" class="muted">查询 {{ result.query_count }} 张</span>
      </div>
      <v-chart v-if="metricOption" class="chart" :option="metricOption" autoresize />
      <div v-else class="empty muted">暂无评估结果</div>
    </div>

    <div class="panel">
      <div class="chart-title">
        <strong>PR 曲线</strong>
        <span v-if="result" class="muted">{{ elapsedText }}</span>
      </div>
      <v-chart v-if="prOption" class="chart" :option="prOption" autoresize />
      <div v-else class="empty muted">暂无曲线</div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent])

const props = defineProps({
  result: {
    type: Object,
    default: null
  }
})

const elapsedText = computed(() => {
  if (!props.result) {
    return ''
  }
  return `${Math.round(props.result.elapsed_ms)} ms`
})

const metricOption = computed(() => {
  if (!props.result) {
    return null
  }
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 16, top: 34, bottom: 32 },
    xAxis: { type: 'category', data: ['mAP', `P@${props.result.k}`] },
    yAxis: { type: 'value', min: 0, max: 1 },
    series: [
      {
        type: 'bar',
        data: [
          Number(props.result.map.toFixed(4)),
          Number(props.result.p_at_k.toFixed(4))
        ],
        itemStyle: { color: '#2563eb' },
        barWidth: 48
      }
    ]
  }
})

const prOption = computed(() => {
  if (!props.result?.pr_curve?.length) {
    return null
  }
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 16, top: 34, bottom: 32 },
    xAxis: {
      type: 'value',
      min: 0,
      max: 1,
      name: 'Recall'
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      name: 'Precision'
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: props.result.pr_curve.map(([recall, precision]) => [
          Number(recall.toFixed(3)),
          Number(precision.toFixed(4))
        ]),
        itemStyle: { color: '#0f766e' },
        lineStyle: { color: '#0f766e', width: 3 },
        areaStyle: { color: 'rgba(15, 118, 110, 0.12)' }
      }
    ]
  }
})
</script>

<style scoped>
.charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.chart-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.chart {
  height: 300px;
}

.empty {
  height: 300px;
  display: grid;
  place-items: center;
}

@media (max-width: 860px) {
  .charts {
    grid-template-columns: 1fr;
  }
}
</style>
