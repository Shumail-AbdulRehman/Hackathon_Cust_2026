import { useEffect, useMemo, useRef } from 'react'
import * as d3 from 'd3'

function getChartSize(container) {
  return { width: container.clientWidth || 320, height: container.clientHeight || 160 }
}

export default function SourceMixChart({ profile }) {
  const containerRef = useRef(null)

  const data = useMemo(() => {
    const rows = profile?.source_rows || []
    const counts = {}
    rows.forEach((row) => {
      counts[row.record_type] = (counts[row.record_type] || 0) + 1
    })
    return Object.entries(counts).map(([type, count]) => ({ type, count }))
  }, [profile])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    container.innerHTML = ''

    if (!data.length) {
      container.innerHTML = '<p class="empty-state">No source rows.</p>'
      return
    }

    const { width, height } = getChartSize(container)
    const radius = Math.min(width, height) / 2 - 16

    const svg = d3.select(container).append('svg').attr('width', width).attr('height', height)
    const g = svg.append('g').attr('transform', `translate(${width / 2},${height / 2})`)

    const color = d3
      .scaleOrdinal()
      .domain(data.map((d) => d.type))
      .range(['#1a2b4a', '#3d6b52', '#d4b876', '#c88a2a', '#5e5c58'])

    const pie = d3.pie().value((d) => d.count).sort(null)
    const arc = d3.arc().innerRadius(radius * 0.55).outerRadius(radius)

    g.selectAll('path')
      .data(pie(data))
      .join('path')
      .attr('d', arc)
      .attr('fill', (d) => color(d.data.type))
      .attr('stroke', '#fdfcf9')
      .attr('stroke-width', 2)

    const total = data.reduce((sum, d) => sum + d.count, 0)
    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .style('font-family', 'JetBrains Mono, monospace')
      .style('font-weight', '600')
      .text(total)

    const legend = svg.append('g').attr('transform', `translate(16, ${height - 20})`)
    data.forEach((d, index) => {
      const item = legend.append('g').attr('transform', `translate(${index * 80}, 0)`)
      item.append('rect').attr('width', 10).attr('height', 10).attr('fill', color(d.type))
      item.append('text').attr('x', 16).attr('y', 9).style('font-size', '0.75rem').text(d.type)
    })
  }, [data])

  return <div className="chart-container small" ref={containerRef} />
}
