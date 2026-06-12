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
    case 'hexagon':
      return d3.symbol().type(d3.symbolWye).size(r * r * 4)()
    default:
      return d3.symbol().type(d3.symbolCircle).size(r * r * 4)()
  }
}

export default function GraphCanvas({ graph, selectedNodeId, onSelectNode, visibleNodeTypes, visibleEdgeTypes }) {
  const containerRef = useRef(null)
  const transformRef = useRef(d3.zoomIdentity)
  const simulationRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current) return
    const container = d3.select(containerRef.current)
    container.selectAll('*').remove()

    if (!graph?.nodes?.length) {
      container.html('<p class="empty-state" style="padding:48px;">Run the pipeline to load the network.</p>')
      return
    }

    const width = containerRef.current.clientWidth || 800
    const height = containerRef.current.clientHeight || 600

    const filteredNodes = graph.nodes.filter((n) => visibleNodeTypes.has(n.type))
    const nodeById = new Map(filteredNodes.map((n) => [n.id, n]))
    const filteredEdges = graph.edges.filter((e) => {
      const s = typeof e.source === 'object' ? e.source.id : e.source
      const t = typeof e.target === 'object' ? e.target.id : e.target
      return visibleEdgeTypes.has(e.relation) && nodeById.has(s) && nodeById.has(t)
    })

    if (!filteredNodes.length) {
      container.html('<p class="empty-state" style="padding:48px;">No visible nodes with current filters.</p>')
      return
    }

    const stats = containerRef.current.parentElement?.querySelector('#graphStats')
    if (stats) stats.textContent = `${filteredNodes.length} nodes · ${filteredEdges.length} edges`

    const svg = container.append('svg').attr('width', width).attr('height', height).attr('viewBox', [0, 0, width, height])
    const tooltip = container.append('div').attr('class', 'graph-tooltip')
    const g = svg.append('g')

    const zoom = d3
      .zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
        transformRef.current = event.transform
      })

    svg.call(zoom)
    if (transformRef.current) {
      svg.call(zoom.transform, transformRef.current)
    }

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

    simulationRef.current = simulation

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
      .attr('fill', (d) => NODE_TYPES.find((t) => t.key === d.type)?.color || '#5e5c58')
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

    const highlightEgo = (centerId) => {
      const neighborIds = new Set([centerId])
      link.each(function (d) {
        const s = typeof d.source === 'object' ? d.source.id : d.source
        const t = typeof d.target === 'object' ? d.target.id : d.target
        if (s === centerId || t === centerId) {
          neighborIds.add(s)
          neighborIds.add(t)
        }
      })
      node.classed('dimmed', (d) => !neighborIds.has(d.id))
      link.classed('dimmed', (d) => {
        const s = typeof d.source === 'object' ? d.source.id : d.source
        const t = typeof d.target === 'object' ? d.target.id : d.target
        return s !== centerId && t !== centerId
      })
      label.classed('dimmed', (d) => !neighborIds.has(d.id))
    }

    const clearHighlight = () => {
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
        if (!selectedNodeId) clearHighlight()
        else highlightEgo(selectedNodeId)
      })
      .on('click', (_event, d) => {
        onSelectNode(d.id)
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
      container.selectAll('*').remove()
      if (stats) stats.textContent = ''
    }
  }, [graph, selectedNodeId, onSelectNode, visibleNodeTypes, visibleEdgeTypes])

  return <div ref={containerRef} className="graph-canvas" aria-label="Interactive evidence network" />
}
