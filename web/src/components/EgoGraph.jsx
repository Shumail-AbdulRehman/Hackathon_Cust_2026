import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { EDGE_TYPES, NODE_TYPES } from '../constants'
import { getChartSize } from './chartUtils'

function nodeRadius(d) {
  if (d.type === 'Person') return 14
  if (d.type === 'AddressHub' || d.type === 'PhoneHub') return 8
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
    case 'hexagon':
      return d3.symbol().type(d3.symbolWye).size(r * r * 4)()
    default:
      return d3.symbol().type(d3.symbolCircle).size(r * r * 4)()
  }
}

export default function EgoGraph({ profile, graphData }) {
  const ref = useRef(null)

  useEffect(() => {
    const container = ref.current
    if (!container) return

    container.innerHTML = ''
    const graph = graphData || { nodes: [], edges: [] }

    if (!graph.nodes.length) {
      container.innerHTML = '<p class="empty-state">No graph data.</p>'
      return
    }

    const entityId = profile?.entity_id
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

    if (!egoNodes.length) {
      container.innerHTML = '<p class="empty-state">No ego network for this entity.</p>'
      return
    }

    const { width } = getChartSize(container)
    const heightPx = 260

    const svg = d3
      .select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', heightPx)
      .attr('viewBox', [0, 0, width, heightPx])

    const g = svg.append('g')

    svg
      .append('defs')
      .selectAll('marker')
      .data(EDGE_TYPES)
      .join('marker')
      .attr('id', (d) => `arrow-ego-${d.key}`)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', (d) => d.color)

    const simulation = d3
      .forceSimulation(egoNodes)
      .force(
        'link',
        d3
          .forceLink(egoEdges)
          .id((d) => d.id)
          .distance((d) => (d.relation === 'SAME_ADDRESS_AS' || d.relation === 'SHARES_PHONE_WITH' ? 70 : 100)),
      )
      .force('charge', d3.forceManyBody().strength(-220))
      .force('center', d3.forceCenter(width / 2, heightPx / 2))
      .force('collide', d3.forceCollide().radius((d) => nodeRadius(d) + 6))

    const link = g
      .append('g')
      .selectAll('line')
      .data(egoEdges)
      .join('line')
      .attr('class', 'graph-link')
      .attr('stroke', (d) => EDGE_TYPES.find((t) => t.key === d.relation)?.color || '#5e5c58')
      .attr('stroke-dasharray', (d) => EDGE_TYPES.find((t) => t.key === d.relation)?.dash || '0')
      .attr('marker-end', (d) => `url(#arrow-ego-${d.relation})`)
      .attr('stroke-width', (d) => (d.confidence ? Math.max(1.5, d.confidence * 2) : 1.5))

    const node = g
      .append('g')
      .selectAll('path')
      .data(egoNodes)
      .join('path')
      .attr('class', 'graph-node')
      .attr('d', (d) => nodeShapePath(d))
      .attr('fill', (d) => NODE_TYPES.find((t) => t.key === d.type)?.color || '#5e5c58')
      .attr('transform', (d) => `translate(${d.x || width / 2},${d.y || heightPx / 2})`)

    const label = g
      .append('g')
      .selectAll('text')
      .data(egoNodes)
      .join('text')
      .attr('class', 'graph-label')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => -nodeRadius(d) - 6)
      .text((d) => (d.label || d.id).slice(0, 22))

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
    }
  }, [profile, graphData])

  return <div ref={ref} className="chart-container" />
}
