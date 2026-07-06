<template>
  <div class="markdown-body" v-html="html"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  content: {
    type: String,
    default: ''
  }
})

const html = computed(() => renderMarkdown(props.content))

function renderMarkdown(markdown) {
  const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n')
  const output = []
  let paragraph = []
  let list = []
  let listTag = 'ul'

  function flushParagraph() {
    if (!paragraph.length) return
    output.push(`<p>${renderInline(paragraph.join(' '))}</p>`)
    paragraph = []
  }

  function flushList() {
    if (!list.length) return
    output.push(`<${listTag}>${list.map((item) => `<li>${renderInline(item)}</li>`).join('')}</${listTag}>`)
    list = []
    listTag = 'ul'
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    const trimmed = line.trim()

    if (!trimmed) {
      flushParagraph()
      flushList()
      continue
    }

    if (/^\|(.+\|)+$/.test(trimmed) && /^\|?[\s:-]+\|[\s|:-]+$/.test((lines[index + 1] || '').trim())) {
      flushParagraph()
      flushList()
      const tableLines = [trimmed]
      index += 2
      while (index < lines.length && /^\|(.+\|)+$/.test(lines[index].trim())) {
        tableLines.push(lines[index].trim())
        index += 1
      }
      index -= 1
      output.push(renderTable(tableLines))
      continue
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/)
    if (heading) {
      flushParagraph()
      flushList()
      const level = heading[1].length
      output.push(`<h${level}>${renderInline(heading[2])}</h${level}>`)
      continue
    }

    if (/^(-{3,}|\*{3,})$/.test(trimmed)) {
      flushParagraph()
      flushList()
      output.push('<hr>')
      continue
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/)
    if (bullet) {
      flushParagraph()
      if (list.length && listTag !== 'ul') flushList()
      listTag = 'ul'
      list.push(bullet[1])
      continue
    }

    const ordered = trimmed.match(/^\d+\.\s+(.+)$/)
    if (ordered) {
      flushParagraph()
      if (list.length && listTag !== 'ol') flushList()
      listTag = 'ol'
      list.push(ordered[1])
      continue
    }

    flushList()
    paragraph.push(trimmed)
  }

  flushParagraph()
  flushList()
  return output.join('')
}

function renderTable(rows) {
  if (!rows.length) return ''
  const cells = rows.map(splitTableRow)
  const head = cells[0] || []
  const body = cells.slice(1)
  return [
    '<div class="markdown-table-wrap"><table>',
    `<thead><tr>${head.map((cell) => `<th>${renderInline(cell)}</th>`).join('')}</tr></thead>`,
    `<tbody>${body.map((row) => `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join('')}</tr>`).join('')}</tbody>`,
    '</table></div>'
  ].join('')
}

function splitTableRow(row) {
  return row
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function renderInline(value) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
</script>

<style scoped>
.markdown-body {
  color: var(--text);
  font-size: 15px;
  line-height: 1.75;
  word-break: break-word;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 18px 0 8px;
  color: var(--text);
  font-weight: 800;
  line-height: 1.35;
}

.markdown-body :deep(h1) {
  font-size: 24px;
}

.markdown-body :deep(h2) {
  font-size: 21px;
}

.markdown-body :deep(h3) {
  font-size: 18px;
}

.markdown-body :deep(h4) {
  font-size: 16px;
}

.markdown-body :deep(p) {
  margin: 8px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 8px 0 12px;
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin: 5px 0;
}

.markdown-body :deep(strong) {
  color: var(--text);
  font-weight: 800;
}

.markdown-body :deep(em) {
  color: var(--text-muted);
}

.markdown-body :deep(code) {
  padding: 2px 5px;
  border-radius: 5px;
  background: color-mix(in srgb, var(--control-bg), #2563eb 8%);
  color: #2563eb;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 0.92em;
}

.markdown-body :deep(hr) {
  height: 1px;
  margin: 18px 0;
  border: 0;
  background: var(--border);
}

.markdown-body :deep(.markdown-table-wrap) {
  width: 100%;
  margin: 12px 0 16px;
  overflow-x: auto;
}

.markdown-body :deep(table) {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  font-size: 14px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 9px 10px;
  border: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  background: color-mix(in srgb, var(--control-bg), #2563eb 7%);
  font-weight: 800;
}

.markdown-body :deep(tr:nth-child(even) td) {
  background: color-mix(in srgb, var(--control-bg), transparent 20%);
}
</style>
