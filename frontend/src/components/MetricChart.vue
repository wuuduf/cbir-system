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
  },
  comparisonResults: {
    type: Array,
    default: () => []
  }
})

const chartResults = computed(() => {
  if (props.comparisonResults?.length) {
    return props.comparisonResults
  }
  return props.result ? [props.result] : []
})

const elapsedText = computed(() => {
  if (!chartResults.value.length) {
    return ''
  }
  const total = chartResults.value.reduce((sum, item) => sum + Number(item.elapsed_ms || 0), 0)
  return chartResults.value.length > 1
    ? `${chartResults.value.length} 组 · ${Math.round(total)} ms`
    : `${Math.round(chartResults.value[0].elapsed_ms)} ms`
})

const metricOption = computed(() => {
  if (!chartResults.value.length) {
    return null
  }
  if (chartResults.value.length > 1) {
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 42, right: 16, top: 42, bottom: 46 },
      xAxis: {
        type: 'category',
        data: chartResults.value.map((item) => item.label || item.feature)
      },
      yAxis: { type: 'value', min: 0, max: 1 },
      series: [
        {
          name: 'mAP',
          type: 'bar',
          data: chartResults.value.map((item) => Number(item.map.toFixed(4))),
          itemStyle: { color: '#2563eb' },
          barMaxWidth: 34
        },
        {
          name: `P@${chartResults.value[0].k}`,
          type: 'bar',
          data: chartResults.value.map((item) => Number(item.p_at_k.toFixed(4))),
          itemStyle: { color: '#0f766e' },
          barMaxWidth: 34
        }
      ]
    }
  }
  const current = chartResults.value[0]
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 16, top: 34, bottom: 32 },
    xAxis: { type: 'category', data: ['mAP', `P@${current.k}`] },
    yAxis: { type: 'value', min: 0, max: 1 },
    series: [
      {
        type: 'bar',
        data: [
          Number(current.map.toFixed(4)),
          Number(current.p_at_k.toFixed(4))
        ],
        itemStyle: { color: '#2563eb' },
        barWidth: 48
      }
    ]
  }
})

const prOption = computed(() => {
  const validResults = chartResults.value.filter((item) => item.pr_curve?.length)
  if (!validResults.length) {
    return null
  }
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 42, right: 16, top: validResults.length > 1 ? 42 : 34, bottom: 32 },
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
    series: validResults.map((item, index) => {
      const colors = ['#0f766e', '#2563eb', '#f59e0b', '#7c3aed', '#dc2626', '#0891b2', '#65a30d']
      const color = colors[index % colors.length]
      return {
        name: item.label || item.feature,
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: item.pr_curve.map(([recall, precision]) => [
          Number(recall.toFixed(3)),
          Number(precision.toFixed(4))
        ]),
        itemStyle: { color },
        lineStyle: { color, width: 3 },
        areaStyle: validResults.length === 1 ? { color: 'rgba(15, 118, 110, 0.12)' } : undefined
      }
    })
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
