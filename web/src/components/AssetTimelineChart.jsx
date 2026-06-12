import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

export default function AssetTimelineChart({ rows, formatNumber }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const events = []
    ;(rows || []).forEach((row) => {
      const raw = row.raw || {}
      if (row.record_type === 'property' && raw.transfer_date) {
        const year = parseInt(String(raw.transfer_date).slice(0, 4), 10)
        if (year) events.push({ year, label: 'Property', value: Number(raw.property_value || 0) })
      }
      if (row.record_type === 'vehicle' && raw.registration_year) {
        const year = Number(raw.registration_year)
        if (year) events.push({ year, label: 'Vehicle', value: Number(raw.engine_capacity_cc || 0) * 1000 })
      }
    })

    if (!containerRef.current) return
    const container = d3.select(containerRef.current)
    container.selectAll('*').remove()

    if (!events.length) {
      container.html('<p class="empty-state">No dated asset events for this entity.</p>')
      return
    }

    const width = containerRef.current.clientWidth || 400
    const height = containerRef.current.clientHeight || 240
    const margin = { top: 16, right: 24, bottom: 32, left: 56 }
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const svg = container.append('svg').attr('width', width).attr('height', height)
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    const years = events.map((e) => e.year)
    const x = d3.scaleLinear().domain(d3.extent(years)).nice().range([0, innerW])
    const y = d3.scaleLinear().domain([0, d3.max(events, (d) => d.value) || 1]).nice().range([innerH, 0])
    const color = d3.scaleOrdinal().domain(['Property', 'Vehicle']).range(['#d4b876', '#3d6b52'])

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).tickFormat(d3.format('d')))
    g.append('g').call(d3.axisLeft(y).ticks(5).tickFormat((d) => formatNumber(d)))

    g.selectAll('.domain, .tick line').style('stroke', '#dcd6cc')
    g.selectAll('.tick text').style('fill', '#5e5c58').style('font-family', 'Source Sans 3, sans-serif')

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
    color.domain().forEach((label, i) => {
      const item = legend.append('g').attr('transform', `translate(${i * 90}, 0)`)
      item.append('circle').attr('r', 5).attr('fill', color(label))
      item.append('text').attr('x', 12).attr('y', 0).attr('dy', '0.35em').style('font-size', '0.75rem').text(label)
    })

    return () => {
      container.selectAll('*').remove()
    }
  }, [rows, formatNumber])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
