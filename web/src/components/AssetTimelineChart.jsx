import { useEffect, useMemo, useRef } from 'react'
import * as d3 from 'd3'

function getChartSize(container) {
  return { width: container.clientWidth || 400, height: container.clientHeight || 240 }
}

function formatNumber(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  if (Math.abs(num) >= 1_000_000) return `₨ ${(num / 1_000_000).toFixed(2)}M`
  if (Math.abs(num) >= 1_000) return `₨ ${(num / 1_000).toFixed(1)}K`
  return `₨ ${num.toLocaleString()}`
}

export default function AssetTimelineChart({ profile }) {
  const containerRef = useRef(null)

  const events = useMemo(() => {
    const rows = profile?.source_rows || []
    const list = []
    rows.forEach((row) => {
      const raw = row.raw || {}
      const type = row.record_type
      if (type === 'property' && raw.transfer_date) {
        const year = parseInt(String(raw.transfer_date).slice(0, 4), 10)
        if (year) {
          list.push({ year, label: 'Property', value: Number(raw.property_value || 0) })
        }
      }
      if (type === 'vehicle' && raw.registration_year) {
        const year = Number(raw.registration_year)
        if (year) {
          list.push({ year, label: 'Vehicle', value: Number(raw.engine_capacity_cc || 0) * 1000 })
        }
      }
    })
    return list
  }, [profile])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    container.innerHTML = ''

    if (!events.length) {
      container.innerHTML = '<p class="empty-state">No dated asset events for this entity.</p>'
      return
    }

    const { width, height } = getChartSize(container)
    const margin = { top: 16, right: 24, bottom: 32, left: 56 }
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const svg = d3.select(container).append('svg').attr('width', width).attr('height', height)
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    const years = events.map((e) => e.year)
    const x = d3.scaleLinear().domain(d3.extent(years)).nice().range([0, innerW])
    const y = d3
      .scaleLinear()
      .domain([0, d3.max(events, (d) => d.value) || 1])
      .nice()
      .range([innerH, 0])
    const color = d3.scaleOrdinal().domain(['Property', 'Vehicle']).range(['#d4b876', '#3d6b52'])

    g.append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(d3.axisBottom(x).tickFormat(d3.format('d')))

    g.append('g').call(d3.axisLeft(y).ticks(5).tickFormat((d) => formatNumber(d)))

    g.selectAll('.domain, .tick line').style('stroke', '#dcd6cc')
    g.selectAll('.tick text')
      .style('fill', '#5e5c58')
      .style('font-family', 'Source Sans 3, sans-serif')

    g.selectAll('circle')
      .data(events)
      .join('circle')
      .attr('cx', (d) => x(d.year))
      .attr('cy', (d) => y(d.value))
      .attr('r', 6)
      .attr('fill', (d) => color(d.label))
      .attr('stroke', '#fdfcf9')
      .attr('stroke-width', 2)

    const line = d3
      .line()
      .x((d) => x(d.year))
      .y((d) => y(d.value))
      .curve(d3.curveMonotoneX)

    g.append('path')
      .datum(events.sort((a, b) => a.year - b.year))
      .attr('fill', 'none')
      .attr('stroke', '#1a2b4a')
      .attr('stroke-width', 2)
      .attr('d', line)

    const legend = svg.append('g').attr('transform', `translate(${margin.left}, 8)`)
    color.domain().forEach((label, index) => {
      const item = legend.append('g').attr('transform', `translate(${index * 90}, 0)`)
      item.append('circle').attr('r', 5).attr('fill', color(label))
      item.append('text').attr('x', 12).attr('y', 0).attr('dy', '0.35em').style('font-size', '0.75rem').text(label)
    })
  }, [events])

  return <div className="chart-container" ref={containerRef} />
}
