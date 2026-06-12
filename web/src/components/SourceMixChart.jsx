import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

const TYPE_COLORS = {
  tax: '#7a9e7e',
  vehicle: '#3d6b52',
  property: '#d4b876',
  utility: '#5e5c58',
  offshore_entity: '#c88a2a',
  generic: '#1a2b4a',
}

export default function SourceMixChart({ rows }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const counts = {}
    ;(rows || []).forEach((r) => {
      counts[r.record_type] = (counts[r.record_type] || 0) + 1
    })
    const data = Object.entries(counts).map(([type, count]) => ({ type, count }))

    if (!containerRef.current) return
    const container = d3.select(containerRef.current)
    container.selectAll('*').remove()

    if (!data.length) {
      container.html('<p class="empty-state">No source rows.</p>')
      return
    }

    const width = containerRef.current.clientWidth || 280
    const height = containerRef.current.clientHeight || 160
    const radius = Math.min(width, height) / 2 - 16

    const svg = container.append('svg').attr('width', width).attr('height', height)
    const g = svg.append('g').attr('transform', `translate(${width / 2},${height / 2})`)

    const color = d3
      .scaleOrdinal()
      .domain(data.map((d) => d.type))
      .range(data.map((d) => TYPE_COLORS[d.type] || '#1a2b4a'))

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
    data.forEach((d, i) => {
      const item = legend.append('g').attr('transform', `translate(${i * 80}, 0)`)
      item.append('rect').attr('width', 10).attr('height', 10).attr('fill', color(d.type))
      item.append('text').attr('x', 16).attr('y', 9).style('font-size', '0.75rem').text(d.type)
    })

    return () => {
      container.selectAll('*').remove()
    }
  }, [rows])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
