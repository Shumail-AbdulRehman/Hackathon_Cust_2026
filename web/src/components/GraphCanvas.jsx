import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { EDGE_TYPES, NODE_TYPES } from '../constants'
import { getChartSize } from './chartUtils'

const TIER_COLORS = {
  green: '#3d6b52',
  yellow: '#c88a2a',
  orange: '#c14528',
  red: '#a64b2a',
  critical: '#7a2e1d',
}

function nodeFill(d) {
  const tier = d.risk_tier || 'green'
  return TIER_COLORS[tier] || '#9e9a8e'
}

function nodeStroke(d) {
  const color = nodeFill(d)
  return d3.color(color).darker(0.6).formatHex()
}

function nodeRadius(d) {
  const base = d.type === 'Person' ? 16 : d.type === 'AddressHub' || d.type === 'PhoneHub' ? 7 : 10
  const score = d.deviation_score || 0
  return base + Math.min(score / 10, 8)
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

function getNodeId(e) {
  return typeof e === 'object' ? e.id : e
}

export default function GraphCanvas({
  graphData,
  selectedNodeId,
  visibleNodeTypes,
  visibleEdgeTypes,
  onSelectNode,
  onStatsChange,
}) {
  const ref = useRef(null)
  const transformRef = useRef(d3.zoomIdentity)

  useEffect(() => {
    const container = ref.current
    if (!container) return

    container.innerHTML = ''
    const graph = graphData || { nodes: [], edges: [] }

    if (!graph.nodes.length) {
      container.innerHTML = '<p class="empty-state" style="padding:48px;">Run an investigation to build the network graph.</p>'
      onStatsChange?.('0 nodes · 0 edges')
      return
    }

    const nodeTypeSet = new Set(visibleNodeTypes || NODE_TYPES.map((t) => t.key))
    const edgeTypeSet = new Set(visibleEdgeTypes || EDGE_TYPES.map((t) => t.key))

    const filteredNodes = graph.nodes.filter((n) => nodeTypeSet.has(n.type))
    const nodeById = new Map(filteredNodes.map((n) => [n.id, n]))
    const filteredEdges = graph.edges.filter((e) => {
      const s = getNodeId(e.source)
      const t = getNodeId(e.target)
      return edgeTypeSet.has(e.relation) && nodeById.has(s) && nodeById.has(t)
    })

    if (!filteredNodes.length) {
      container.innerHTML = '<p class="empty-state" style="padding:48px;">No visible nodes with current filters.</p>'
      onStatsChange?.('0 nodes · 0 edges')
      return
    }

    onStatsChange?.(`${filteredNodes.length} nodes · ${filteredEdges.length} edges`)

    const { width, height } = getChartSize(container)

    const svg = d3.select(container).append('svg').attr('width', width).attr('height', height).attr('viewBox', [0, 0, width, height])

    const legend = d3.select(container).append('div').attr('class', 'graph-legend')
    Object.entries(TIER_COLORS).forEach(([tier, color]) => {
      const item = legend.append('div').attr('class', 'graph-legend-item')
      item.append('span').attr('class', 'graph-legend-swatch').style('background', color)
      item.append('span').text(tier)
    })

    const tooltip = d3.select(container).append('div').attr('class', 'graph-tooltip')

    const g = svg.append('g')
    const zoom = d3
      .zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
        transformRef.current = event.transform
      })

    svg.call(zoom)
    svg.call(zoom.transform, transformRef.current)

    svg
      .append('defs')
      .selectAll('marker')
      .data(EDGE_TYPES)
      .join('marker')
      .attr('id', (d) => `arrow-${d.key}`)
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
      .forceSimulation(filteredNodes)
      .force(
        'link',
        d3
          .forceLink(filteredEdges)
          .id((d) => d.id)
          .distance((d) => (d.relation === 'SAME_ADDRESS_AS' || d.relation === 'SHARES_PHONE_WITH' ? 70 : 100)),
      )
      .force('charge', d3.forceManyBody().strength(-220))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius((d) => nodeRadius(d) + 6))

    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(filteredEdges)
      .join('line')
      .attr('class', 'graph-link')
      .attr('stroke', (d) => EDGE_TYPES.find((t) => t.key === d.relation)?.color || '#5e5c58')
      .attr('stroke-dasharray', (d) => EDGE_TYPES.find((t) => t.key === d.relation)?.dash || '0')
      .attr('marker-end', (d) => `url(#arrow-${d.relation})`)
      .attr('stroke-width', (d) => (d.confidence ? Math.max(1.5, d.confidence * 2) : 1.5))

    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('path')
      .data(filteredNodes)
      .join('path')
      .attr('class', (d) => `graph-node ${d.id === selectedNodeId ? 'selected' : ''}`)
      .attr('d', (d) => nodeShapePath(d))
      .attr('fill', nodeFill)
      .attr('stroke', nodeStroke)
      .attr('transform', (d) => `translate(${d.x || width / 2},${d.y || height / 2})`)
      .call(
        d3
          .drag()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event, d) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          }),
      )

    const label = g
      .append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(filteredNodes)
      .join('text')
      .attr('class', 'graph-label')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => -nodeRadius(d) - 6)
      .text((d) => (d.label || d.id).slice(0, 22))

    function highlightEgo(centerId) {
      const neighborIds = new Set([centerId])
      link.each(function (d) {
        const s = getNodeId(d.source)
        const t = getNodeId(d.target)
        if (s === centerId || t === centerId) {
          neighborIds.add(s)
          neighborIds.add(t)
        }
      })

      node.classed('dimmed', (d) => !neighborIds.has(d.id))
      link.classed('dimmed', (d) => {
        const s = getNodeId(d.source)
        const t = getNodeId(d.target)
        return s !== centerId && t !== centerId
      })
      label.classed('dimmed', (d) => !neighborIds.has(d.id))
    }

    function clearHighlight() {
      node.classed('dimmed', false)
      link.classed('dimmed', false)
      label.classed('dimmed', false)
    }

    node
      .on('mouseenter', (event, d) => {
        tooltip.html(`<strong>${d.label || d.id}</strong><br>${d.type || 'Node'}`).classed('visible', true)
        highlightEgo(d.id)
      })
      .on('mousemove', (event) => {
        tooltip.style('left', `${event.offsetX + 12}px`).style('top', `${event.offsetY + 12}px`)
      })
      .on('mouseleave', () => {
        tooltip.classed('visible', false)
        clearHighlight()
      })
      .on('click', (_event, d) => {
        onSelectNode?.(d.id)
      })

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y)

      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
      label.attr('x', (d) => d.x).attr('y', (d) => d.y)
    })

    if (selectedNodeId) {
      const selected = filteredNodes.find((n) => n.id === selectedNodeId)
      if (selected) highlightEgo(selected.id)
    }

    return () => {
      simulation.stop()
    }
  }, [graphData, selectedNodeId, visibleNodeTypes, visibleEdgeTypes, onSelectNode, onStatsChange])

  return <div ref={ref} className="graph-canvas" />
}
