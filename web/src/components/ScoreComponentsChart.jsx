import { useEffect, useMemo, useRef } from 'react'
import * as d3 from 'd3'

function getChartSize(container) {
  return { width: container.clientWidth || 400, height: container.clientHeight || 240 }
}

export default function ScoreComponentsChart({ profile }) {
  const containerRef = useRef(null)

  const data = useMemo(() => {
    const components = profile?.score_components || {}
    return Object.entries(components)
      .filter(([, value]) => value > 0)
      .map(([key, value]) => ({ key: key.replace(/_/g, ' '), value }))
      .sort((a, b) => b.value - a.value)
  }, [profile])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    container.innerHTML = ''

    if (!data.length) {
      container.innerHTML = '<p class="empty-state">No score components available.</p>'
      return
    }

    const { width, height } = getChartSize(container)
    const margin = { top: 8, right: 56, bottom: 24, left: 120 }
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const svg = d3.select(container).append('svg').attr('width', width).attr('height', height)
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    const x = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => d.value) || 1])
      .nice()
      .range([0, innerW])
    const y = d3
      .scaleBand()
      .domain(data.map((d) => d.key))
      .range([0, innerH])
      .padding(0.2)

    g.selectAll('rect')
      .data(data)
      .join('rect')
      .attr('y', (d) => y(d.key))
      .attr('height', y.bandwidth())
      .attr('x', 0)
      .attr('width', 0)
      .attr('fill', '#1a2b4a')
      .attr('rx', 4)
      .transition()
      .duration(250)
      .attr('width', (d) => x(d.value))

    g.selectAll('text.value')
      .data(data)
      .join('text')
      .attr('x', (d) => x(d.value) + 6)
      .attr('y', (d) => y(d.key) + y.bandwidth() / 2)
      .attr('dy', '0.35em')
      .style('font-family', 'JetBrains Mono, monospace')
      .style('font-size', '0.75rem')
      .style('fill', '#1e1e24')
      .text((d) => d.value.toFixed(1))

    g.append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(d3.axisBottom(x).ticks(4).tickSizeOuter(0))

    g.append('g').call(d3.axisLeft(y).tickSizeOuter(0))

    g.selectAll('.domain, .tick line').style('stroke', '#dcd6cc')
    g.selectAll('.tick text')
      .style('fill', '#5e5c58')
      .style('font-family', 'Source Sans 3, sans-serif')
  }, [data])

  return <div className="chart-container" ref={containerRef} />
}
