import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

const TYPE_ORDER = ['tax', 'utility', 'vehicle', 'property', 'offshore', 'sanctions']

export default function AssetTimeline({ profile }) {
  const ref = useRef(null)

  useEffect(() => {
    const container = ref.current
    if (!container) return
    container.innerHTML = ''

    const rows = profile?.source_rows || []
    if (!rows.length) {
      container.innerHTML = '<p class="empty-state">No asset or lifestyle events.</p>'
      return
    }

    const events = rows.map((row, i) => {
      const raw = row.raw || {}
      const dateRaw = raw.year || raw.date || raw.registration_year || raw.transaction_date
      const date = dateRaw ? new Date(dateRaw) : null
      return {
        index: i,
        type: row.record_type || 'unknown',
        label: row.dataset || row.record_type,
        date,
        risk: row.risk_contribution || 0,
      }
    })

    const width = container.clientWidth || 400
    const height = 180
    const margin = { top: 16, right: 16, bottom: 36, left: 100 }
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const svg = d3.select(container).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    const hasDates = events.some((e) => e.date && !isNaN(e.date))
    const x = hasDates
      ? d3.scaleTime().domain(d3.extent(events, (d) => d.date)).range([0, innerW]).nice()
      : d3.scaleLinear().domain([0, events.length - 1]).range([0, innerW])

    const y = d3.scaleBand()
      .domain(TYPE_ORDER.filter((t) => events.some((e) => e.type === t)))
      .range([0, innerH])
      .padding(0.4)

    const color = d3.scaleSequential(d3.interpolateOrRd).domain([0, 50])

    g.selectAll('circle.event')
      .data(events)
      .join('circle')
      .attr('class', 'event')
      .attr('cx', (d) => x(hasDates ? d.date : d.index))
      .attr('cy', (d) => (y(d.type) ?? innerH / 2) + y.bandwidth() / 2)
      .attr('r', 6)
      .attr('fill', (d) => color(d.risk))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .append('title')
      .text((d) => `${d.label}${d.date ? ` · ${d.date.toISOString().slice(0, 10)}` : ''}`)

    g.append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(hasDates ? d3.axisBottom(x).ticks(5) : d3.axisBottom(x).ticks(events.length))
      .selectAll('text').style('fill', 'var(--ink-secondary)')

    g.append('g').call(d3.axisLeft(y).tickSizeOuter(0))
      .selectAll('text').style('fill', 'var(--ink-secondary)')

    g.selectAll('.domain, .tick line').style('stroke', 'var(--rule-line)')
  }, [profile])

  return (
    <div className="chart-panel">
      <h4 className="chart-title">When did assets and spending appear?</h4>
      <p className="chart-caption">Events by record type; color shows risk contribution.</p>
      <div className="chart-canvas asset-timeline" ref={ref} />
    </div>
  )
}
