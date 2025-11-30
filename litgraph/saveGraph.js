// saveGraph.js

// Function to clean graph and trigger download
function saveGraph(graphData, filename = "graph_updated.json") {
  if (!graphData) return;

  // Clean links to use IDs only
  const cleanLinks = graphData.links.map(l => ({
    source: typeof l.source === "object" ? l.source.id : l.source,
    target: typeof l.target === "object" ? l.target.id : l.target
  }));

  // Clean nodes to remove simulation properties
  const cleanNodes = graphData.nodes.map(n => {
    const { x, y, vx, vy, fx, fy, ...rest } = n;
    return rest;
  });

  const cleanData = { nodes: cleanNodes, links: cleanLinks };

  // Create Blob and trigger download
  const blob = new Blob([JSON.stringify(cleanData, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
