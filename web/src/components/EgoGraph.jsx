import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { NODE_TYPES, EDGE_TYPES } from '../constants'

function nodeRadius(d) {
  if (d.type === 'Person') return 14
  return 10
}

function nodeShapePath(d) {
  const r = nodeRadius(d)
  const type = NODE_TYPES.find((t) => t.key === d.type)?.shape || 'circle'
  switch (type) {
    case 'square':
      return `M${-r},${-r} h${r * 2} v${r * 2} h${-r * 2} z`
    case 'diamond':
      return `M0,${-r} L${r},0 L0,${r} L${-r},0 z`
    case 'triangle':
      return `M0,${-r} L${r},${r} L${-r},${r} z`
    default:
      return d3.symbol().type(d3.symbolCircle).size(r * r * 4)()
  }
}

export default function EgoGraph({ graph, entityId }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current) return
    const container = d3.select(containerRef.current)
    container.selectAll('*').remove()

    if (!graph?.nodes?.length || !entityId) {
      container.html('<p class="empty-state">No graph data.</p>')
      return
    }

    const nodeIds = new Set([entityId])
    graph.edges.forEach((e) => {
      const s = typeof e.source === 'object' ? e.source.id : e.source
      const t = typeof e.target === 'object' ? e.target.id : e.target
      if (s === entityId || t === entityId) {
        nodeIds.add(s)
        nodeIds.add(t)
      }
    })

    const egoNodes = graph.nodes.filter((n) => nodeIds.has(n.id))
    const egoEdges = graph.edges.filter((e) => {
      const s = typeof e.source === 'object' ? e.source.id : e.source
      const t = typeof e.target === 'object' ? e.target.id : e.target
      return s === entityId || t === entityId
    })

    const width = containerRef.current.clientWidth || 400
    const height = 260

    const svg = container.append('svg').attr('width', width).attr('height', height)
    const g = svg.append('g')

    const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', (event) => {
      g.attr('transform', event.transform)
    })
    svg.call(zoom)

    const simulation = d3
      .forceSimulation(egoNodes)
      .force(
        'link',
        d3
          .forceLink(egoEdges)
          .id((d) => d.id)
          .distance((d) => (d.relation === 'SAME_ADDRESS_AS' || d.relation === 'SHARES_PHONE_WITH' ? 50 : 70)),
      )
      .force('charge', d3.forceManyBody().strength(-150))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius((d) => nodeRadius(d) + 6))

    const link = g
      .append('g')
      .selectAll('line')
      .data(egoEdges)
      .join('line')
      .attr('stroke', (d) => EDGE_TYPES.find((t) => t.key === d.relation)?.color || '#5e5c58')
      .attr('stroke-width', (d) => (d.confidence ? Math.max(1, d.confidence * 2) : 1.5))

    const node = g
      .append('g')
      .selectAll('path')
      .data(egoNodes)
      .join('path')
      .attr('d', (d) => nodeShapePath(d))
      .attr('fill', (d) => NODE_TYPES.find((t) => t.key === d.type)?.color || '#5e5c58')
      .attr('stroke', (d) => (d.id === entityId ? '#1a2b4a' : '#fdfcf9'))
      .attr('stroke-width', (d) => (d.id === entityId ? 3 : 2))

    const label = g
      .append('g')
      .selectAll('text')
      .data(egoNodes)
      .join('text')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => -nodeRadius(d) - 6)
      .style('font-family', 'JetBrains Mono, monospace')
      .style('font-size', '0.75rem')
      .style('fill', '#1e1e24')
      .text((d) => (d.label || d.id).slice(0, 18))

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y)
      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
      label.attr('x', (d) => d.x).attr('y', (d) => d.y)
    })

    return () => {
      simulation.stop()
      container.selectAll('*').remove()
    }
  }, [graph, entityId])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
