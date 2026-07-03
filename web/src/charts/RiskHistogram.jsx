import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

const BUCKETS = [
  { max: 20, tier: 'green', label: '0–20' },
  { max: 40, tier: 'yellow', label: '20–40' },
  { max: 60, tier: 'orange', label: '40–60' },
  { max: 80, tier: 'red', label: '60–80' },
  { max: 100, tier: 'critical', label: '80–100' },
]

const TIER_COLORS = {
  green: '#3d6b52',
  yellow: '#c88a2a',
  orange: '#c14528',
  red: '#a64b2a',
  critical: '#7a2e1d',
}

export default function RiskHistogram({ profiles, selectedScore }) {
  const ref = useRef(null)

  useEffect(() => {
    const container = ref.current
    if (!container) return
    container.innerHTML = ''

    if (!profiles?.length) {
      container.innerHTML = '<p class="empty-state">No profiles.</p>'
      return
    }

    const data = BUCKETS.map((b) => ({ ...b, count: 0 }))
    profiles.forEach((p) => {
      const score = p.deviation_score || 0
      const bucket = data.find((b) => score <= b.max) || data[data.length - 1]
      bucket.count += 1
    })

    const width = container.clientWidth || 400
    const height = 220
    const margin = { top: 16, right: 16, bottom: 36, left: 36 }
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const svg = d3.select(container).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    const x = d3.scaleBand().domain(data.map((d) => d.label)).range([0, innerW]).padding(0.25)
    const y = d3.scaleLinear().domain([0, d3.max(data, (d) => d.count) || 1]).nice().range([innerH, 0])

    g.selectAll('rect.bar')
      .data(data)
      .join('rect')
      .attr('class', 'bar')
      .attr('x', (d) => x(d.label))
      .attr('y', innerH)
      .attr('width', x.bandwidth())
      .attr('height', 0)
      .attr('fill', (d) => TIER_COLORS[d.tier])
      .attr('rx', 4)
      .transition()
      .duration(400)
      .attr('y', (d) => y(d.count))
      .attr('height', (d) => innerH - y(d.count))

    g.selectAll('text.value')
      .data(data)
      .join('text')
      .attr('x', (d) => x(d.label) + x.bandwidth() / 2)
      .attr('y', (d) => y(d.count) - 6)
      .attr('text-anchor', 'middle')
      .style('font-size', '0.75rem')
      .style('fill', 'var(--ink-secondary)')
      .text((d) => (d.count > 0 ? d.count : ''))

    g.append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(d3.axisBottom(x).tickSizeOuter(0))
      .selectAll('text').style('fill', 'var(--ink-secondary)')

    g.append('g').call(d3.axisLeft(y).ticks(5).tickSizeOuter(0))
      .selectAll('text').style('fill', 'var(--ink-secondary)')

    g.selectAll('.domain, .tick line').style('stroke', 'var(--rule-line)')

    if (selectedScore != null) {
      const xPos = (selectedScore / 100) * innerW
      g.append('line')
        .attr('x1', xPos)
        .attr('x2', xPos)
        .attr('y1', 0)
        .attr('y2', innerH)
        .attr('stroke', 'var(--royal-ink)')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '4 2')
    }
  }, [profiles, selectedScore])

  return (
    <div className="chart-panel">
      <h4 className="chart-title">How risky is the dataset?</h4>
      <p className="chart-caption">Distribution of deviation scores. Dashed line shows the selected entity.</p>
      <div className="chart-canvas risk-histogram" ref={ref} />
    </div>
  )
}
