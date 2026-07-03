import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { NODE_TYPES } from '../constants'

export default function SourceFlowSankey({ profiles }) {
  const ref = useRef(null)

  useEffect(() => {
    const container = ref.current
    if (!container) return
    container.innerHTML = ''

    const counts = {}
    profiles.forEach((profile) => {
      const seen = new Set()
      ;(profile.source_rows || []).forEach((row) => {
        const type = row.record_type || 'unknown'
        if (!seen.has(type)) {
          counts[type] = (counts[type] || 0) + 1
          seen.add(type)
        }
      })
    })

    const types = Object.keys(counts)
    if (!types.length) {
      container.innerHTML = '<p class="empty-state">No source data.</p>'
      return
    }

    const total = Object.values(counts).reduce((a, b) => a + b, 0)
    const width = container.clientWidth || 400
    const height = 220
    const margin = { top: 20, right: 120, bottom: 20, left: 20 }
    const innerW = width - margin.left - margin.right

    const svg = d3.select(container).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    const colorMap = Object.fromEntries(NODE_TYPES.map((t) => [t.key, t.color]))
    const nodeHeight = 24
    const nodeGap = 8
    const nodeY = (i) => i * (nodeHeight + nodeGap)

    const sorted = types
      .map((t) => ({ type: t, count: counts[t], color: colorMap[t] || '#9e9a8e' }))
      .sort((a, b) => b.count - a.count)

    const maxCount = Math.max(...sorted.map((d) => d.count))
    const xScale = d3.scaleLinear().domain([0, maxCount]).range([0, innerW - 100])

    sorted.forEach((d, i) => {
      const y = nodeY(i)
      const w = xScale(d.count)

      g.append('rect')
        .attr('x', 0)
        .attr('y', y)
        .attr('width', 0)
        .attr('height', nodeHeight)
        .attr('fill', d.color)
        .attr('rx', 4)
        .transition()
        .duration(400)
        .attr('width', w)

      g.append('text')
        .attr('x', w + 8)
        .attr('y', y + nodeHeight / 2)
        .attr('dy', '0.35em')
        .style('font-size', '0.8125rem')
        .style('fill', 'var(--ink)')
        .text(`${d.type} · ${d.count} (${((d.count / total) * 100).toFixed(0)}%)`)
    })
  }, [profiles])

  return (
    <div className="chart-panel">
      <h4 className="chart-title">Where is the money coming from?</h4>
      <p className="chart-caption">Record types across all resolved entities.</p>
      <div className="chart-canvas sankey-chart" ref={ref} />
    </div>
  )
}
