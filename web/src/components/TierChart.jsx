import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { TIER_LABELS, TIER_ORDER } from '../constants'

export default function TierChart({ profiles }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    container.innerHTML = ''

    if (!profiles?.length) {
      container.innerHTML = '<p class="empty-state">No profiles to display.</p>'
      return
    }

    const counts = {}
    profiles.forEach((profile) => {
      counts[profile.risk_tier] = (counts[profile.risk_tier] || 0) + 1
    })

    const data = TIER_ORDER.map((tier) => ({
      tier,
      count: counts[tier] || 0,
      label: TIER_LABELS[tier],
    })).filter((d) => d.count > 0)

    const total = profiles.length
    const margin = { top: 10, right: 16, bottom: 32, left: 64 }
    const width = container.clientWidth || 400
    const height = 220
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const svg = d3
      .select(container)
      .append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')

    const colorScale = d3
      .scaleOrdinal()
      .domain(TIER_ORDER)
      .range(['#a64b2a', '#c14528', '#c88a2a', '#d4b876', '#3d6b52'])

    const x = d3.scaleLinear().domain([0, total]).nice().range([0, innerW])
    const y = d3
      .scaleBand()
      .domain(data.map((d) => d.label))
      .range([0, innerH])
      .padding(0.25)

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    g.selectAll('rect.bar')
      .data(data)
      .join('rect')
      .attr('class', 'bar')
      .attr('y', (d) => y(d.label))
      .attr('height', y.bandwidth())
      .attr('x', 0)
      .attr('width', 0)
      .attr('fill', (d) => colorScale(d.tier))
      .attr('rx', 4)
      .transition()
      .duration(250)
      .attr('width', (d) => x(d.count))

    g.selectAll('text.value')
      .data(data)
      .join('text')
      .attr('class', 'value')
      .attr('x', (d) => x(d.count) + 6)
      .attr('y', (d) => y(d.label) + y.bandwidth() / 2)
      .attr('dy', '0.35em')
      .style('font-family', 'JetBrains Mono, monospace')
      .style('font-size', '0.8125rem')
      .style('font-weight', '600')
      .style('fill', '#1e1e24')
      .text((d) => `${d.count} (${((d.count / total) * 100).toFixed(0)}%)`)

    g.append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(d3.axisBottom(x).ticks(5).tickSizeOuter(0))

    g.append('g').call(d3.axisLeft(y).tickSizeOuter(0))

    g.selectAll('.domain, .tick line').style('stroke', '#dcd6cc')
    g.selectAll('.tick text')
      .style('fill', '#5e5c58')
      .style('font-family', 'Source Sans 3, sans-serif')
  }, [profiles])

  return <div className="tier-chart" ref={containerRef} />
}
