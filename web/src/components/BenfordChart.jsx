import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { BENFORD_EXPECTED } from '../constants'

export default function BenfordChart({ rows }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const values = (rows || [])
      .filter((r) => r.record_type === 'tax')
      .flatMap((r) => [r.raw?.declared_income_pkr, r.raw?.tax_paid_pkr])
      .filter(Boolean)

    if (!containerRef.current) return
    const container = d3.select(containerRef.current)
    container.selectAll('*').remove()

    if (values.length < 10) {
      container.html('<p class="empty-state">Not enough numeric records for Benford analysis.</p>')
      return
    }

    const digitCounts = {}
    for (let d = 1; d <= 9; d += 1) digitCounts[d] = 0
    values.forEach((v) => {
      const text = String(v).replace(/[^0-9]/g, '')
      for (const ch of text) {
        if (ch !== '0') {
          digitCounts[ch] = (digitCounts[ch] || 0) + 1
          break
        }
      }
    })
    const total = Object.values(digitCounts).reduce((a, b) => a + b, 0)
    if (total < 5) {
      container.html('<p class="empty-state">Not enough first digits.</p>')
      return
    }

    const data = Array.from({ length: 9 }, (_, i) => ({
      digit: String(i + 1),
      observed: total ? digitCounts[String(i + 1)] / total : 0,
      expected: BENFORD_EXPECTED[i],
    }))

    const width = containerRef.current.clientWidth || 280
    const height = containerRef.current.clientHeight || 160
    const margin = { top: 16, right: 16, bottom: 32, left: 32 }
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const svg = container.append('svg').attr('width', width).attr('height', height)
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    const x0 = d3.scaleBand().domain(data.map((d) => d.digit)).range([0, innerW]).padding(0.2)
    const x1 = d3.scaleBand().domain(['observed', 'expected']).range([0, x0.bandwidth()]).padding(0.1)
    const y = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => Math.max(d.observed, d.expected)) || 1])
      .nice()
      .range([innerH, 0])
    const color = d3.scaleOrdinal().domain(['observed', 'expected']).range(['#1a2b4a', '#d4b876'])

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x0))
    g.append('g').call(d3.axisLeft(y).ticks(5).tickFormat((d) => `${(d * 100).toFixed(0)}%`))

    g.selectAll('.domain, .tick line').style('stroke', '#dcd6cc')
    g.selectAll('.tick text').style('fill', '#5e5c58').style('font-family', 'Source Sans 3, sans-serif')

    const groups = g
      .selectAll('g.digit-group')
      .data(data)
      .join('g')
      .attr('class', 'digit-group')
      .attr('transform', (d) => `translate(${x0(d.digit)},0)`)

    groups
      .selectAll('rect')
      .data((d) => [
        { key: 'observed', value: d.observed },
        { key: 'expected', value: d.expected },
      ])
      .join('rect')
      .attr('x', (d) => x1(d.key))
      .attr('y', (d) => y(d.value))
      .attr('width', x1.bandwidth())
      .attr('height', (d) => innerH - y(d.value))
      .attr('fill', (d) => color(d.key))
      .attr('rx', 2)

    const legend = svg.append('g').attr('transform', `translate(${width - 110}, 16)`)
    ;['observed', 'expected'].forEach((key, i) => {
      const item = legend.append('g').attr('transform', `translate(0, ${i * 18})`)
      item.append('rect').attr('width', 10).attr('height', 10).attr('fill', color(key))
      item.append('text').attr('x', 16).attr('y', 9).style('font-size', '0.75rem').text(key)
    })

    return () => {
      container.selectAll('*').remove()
    }
  }, [rows])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
