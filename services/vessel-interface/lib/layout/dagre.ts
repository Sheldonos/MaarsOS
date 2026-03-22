/**
 * Dagre layout algorithm for automatic graph positioning.
 * Converts React Flow nodes and edges into a hierarchical DAG layout.
 */

import dagre from 'dagre';
import { Node, Edge } from 'reactflow';

export interface LayoutOptions {
  direction?: 'TB' | 'LR' | 'BT' | 'RL';
  nodeWidth?: number;
  nodeHeight?: number;
  rankSep?: number;
  nodeSep?: number;
}

const defaultOptions: Required<LayoutOptions> = {
  direction: 'TB', // Top to Bottom
  nodeWidth: 300,
  nodeHeight: 200,
  rankSep: 100, // Vertical spacing between ranks
  nodeSep: 80,  // Horizontal spacing between nodes
};

/**
 * Apply Dagre layout algorithm to React Flow nodes and edges.
 * Returns new nodes with calculated positions.
 */
export function getLayoutedElements<T = any>(
  nodes: Node<T>[],
  edges: Edge[],
  options: LayoutOptions = {}
): { nodes: Node<T>[]; edges: Edge[] } {
  const opts = { ...defaultOptions, ...options };
  
  // Create a new directed graph
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  // Set graph layout options
  dagreGraph.setGraph({
    rankdir: opts.direction,
    ranksep: opts.rankSep,
    nodesep: opts.nodeSep,
  });

  // Add nodes to the graph
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: opts.nodeWidth,
      height: opts.nodeHeight,
    });
  });

  // Add edges to the graph
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Calculate layout
  dagre.layout(dagreGraph);

  // Apply calculated positions to nodes
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    
    return {
      ...node,
      position: {
        // Center the node at the calculated position
        x: nodeWithPosition.x - opts.nodeWidth / 2,
        y: nodeWithPosition.y - opts.nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

/**
 * Re-layout nodes when the graph structure changes.
 * Useful for dynamic graphs that update in real-time.
 */
export function relayoutGraph<T = any>(
  nodes: Node<T>[],
  edges: Edge[],
  options?: LayoutOptions
): { nodes: Node<T>[]; edges: Edge[] } {
  return getLayoutedElements(nodes, edges, options);
}

/**
 * Calculate the bounding box of all nodes.
 * Useful for fitting the graph to the viewport.
 */
export function getGraphBounds(nodes: Node[]): {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
} {
  if (nodes.length === 0) {
    return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  nodes.forEach((node) => {
    const { x, y } = node.position;
    const width = (node.width as number) || defaultOptions.nodeWidth;
    const height = (node.height as number) || defaultOptions.nodeHeight;

    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x + width);
    maxY = Math.max(maxY, y + height);
  });

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

// Made with Bob
