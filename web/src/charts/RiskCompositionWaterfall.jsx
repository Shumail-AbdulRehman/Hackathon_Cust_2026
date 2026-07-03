import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

const SEGMENTS = [
  { key: 'direct_score', label: 'Direct', color: '#a64b2a' },
  { key: 'associate_proxy_score', label: 'Proxy', color: '#c88a2a' },
  { key: 'ml_score', label: 'ML', color: '#3d5a80' },
  { key: 'lli_gap_score', label: 'LLI gap', color: '#3d6b52' },
]

export default function RiskCompositionWaterfall({ profile }) {
  const ref = useRef(null)

  useEffect(() => {
    const container = ref.current
    if (!container) return
    container.innerHTML = ''

    if (!profile) {
      container.innerHTML = '<p class="empty-state">Select a profile.</p>'
      return
    }

    const data = SEGMENTS.map((s) => ({
      ...s,
      value: Number(profile[s.key]) || 0,
    })).filter((s) => s.value > 0)

    if (!data.length) {
      container.innerHTML = '<p class="empty-state">No score components.</p>'
      return
    }

    const width = container.clientWidth || 400
    const height = 120
    const margin = { top: 24, right: 16, bottom: 36, left: 80 }
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const total = data.reduce((sum, d) => sum + d.value, 0)
    const x = d3.scaleLinear().domain([0, Math.max(total, 100)]).range([0, innerW])
    const y = d3.scaleBand().domain(data.map((d) => d.label)).range([0, innerH]).padding(0.35)

    const svg = d3.select(container).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    let current = 0
    data.forEach((d) => {
      g.append('rect')
        .attr('x', x(current))
        .attr('y', y(d.label))
        .attr('width', 0)
        .attr('height', y.bandwidth())
        .attr('fill', d.color)
        .attr('rx', 3)
        .transition()
        .duration(400)
        .attr('width', x(d.value))

      g.append('text')
        .attr('x', -10)
        .attr('y', y(d.label) + y.bandwidth() / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .style('font-size', '0.8125rem')
        .style('fill', 'var(--ink-secondary)')
        .text(d.label)

      g.append('text')
        .attr('x', x(current + d.value / 2))
        .attr('y', y(d.label) + y.bandwidth() / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .style('font-size', '0.75rem')
        .style('fill', '#fff')
        .text(d.value.toFixed(1))

      current += d.value
    })

    g.append('text')
      .attr('x', x(current))
      .attr('y', -6)
      .attr('text-anchor', 'end')
      .style('font-size', '0.8125rem')
      .style('font-weight', 600)
      .style('fill', 'var(--ink)')
      .text(`Total ${current.toFixed(1)}`)
  }, [profile])

  return (
    <div className="chart-panel">
      <h4 className="chart-title">What makes up the risk score?</h4>
      <p className="chart-caption">Direct, proxy, ML, and lifestyle contributions.</p>
      <div className="chart-canvas risk-waterfall" ref={ref} />
    </div>
  )
}
