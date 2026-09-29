/**
 * Client-side browser projection engine for the Plant Pathway Atlas.
 * Runs 100% in-browser: zero server uploads, privacy-preserving, and instant.
 */

// Okabe-Ito Diverging Colors
function colorForValue(val, maxFc = 3.0) {
  if (val === null || val === undefined || isNaN(val)) return '#f8fafc';
  const clamped = Math.max(-maxFc, Math.min(maxFc, val));
  const ratio = Math.abs(clamped) / maxFc;
  let r, g, b;
  if (clamped > 0) {
    // Vermillion: 255,255,255 -> 213,94,0
    r = Math.round(255 - ratio * (255 - 213));
    g = Math.round(255 - ratio * (255 - 94));
    b = Math.round(255 - ratio * (255 - 0));
  } else if (clamped < 0) {
    // Blue: 255,255,255 -> 0,114,178
    r = Math.round(255 - ratio * (255 - 0));
    g = Math.round(255 - ratio * (255 - 114));
    b = Math.round(255 - ratio * (255 - 178));
  } else {
    return '#f8fafc';
  }
  return `rgb(${r}, ${g}, ${b})`;
}

export function parseTable(text) {
  const lines = text.trim().split(/\r?\n/).filter(ln => ln && !ln.startsWith('#'));
  if (lines.length === 0) throw new Error('Table is empty.');
  const delimiter = lines[0].includes('\t') ? '\t' : ',';
  const header = lines[0].split(delimiter).map(c => c.trim().replace(/^["']|["']$/g, ''));
  const rows = lines.slice(1).map(ln => ln.split(delimiter).map(c => c.trim().replace(/^["']|["']$/g, '')));
  return { header, rows, delimiter };
}

export function detectColumns(header, rows) {
  let locusIdx = 0;
  let valIdx = -1;
  let padjIdx = -1;

  for (let i = 0; i < header.length; i++) {
    const col = header[i].toLowerCase();
    if (['locus', 'gene', 'id', 'agi', 'tair', 'identifier'].some(k => col.includes(k))) locusIdx = i;
    if (['log2fc', 'logfc', 'fc', 'diff', 'value', 'stat'].some(k => col.includes(k))) valIdx = i;
    if (['padj', 'fdr', 'qval', 'adj.p.val', 'pvalue', 'p_adj'].some(k => col.includes(k))) padjIdx = i;
  }

  // Fallbacks if not named
  if (valIdx === -1 && header.length > 1) valIdx = 1;

  return { locusIdx, valIdx, padjIdx };
}

export async function projectDataToSvg(svgElement, parsedData, sidecar, options = {}) {
  const { locusIdx, valIdx, padjIdx } = detectColumns(parsedData.header, parsedData.rows);
  const aggMode = options.aggregator || 'mean';
  const alpha = options.alpha !== undefined ? options.alpha : 0.05;
  const species = options.species || 'arabidopsis_thaliana';
  const orthologs = options.orthologs || null;

  // Build lookup map from input rows: locus -> { val, padj }
  const inputMap = new Map();
  for (const row of parsedData.rows) {
    if (row.length <= Math.max(locusIdx, valIdx)) continue;
    const id = row[locusIdx].toUpperCase();
    const val = parseFloat(row[valIdx]);
    if (isNaN(val)) continue;
    const padj = padjIdx !== -1 && row.length > padjIdx ? parseFloat(row[padjIdx]) : null;
    inputMap.set(id, { val, padj });
  }

  let mappedNodeCount = 0;
  let addressableNodeCount = 0;

  for (const node of sidecar.nodes) {
    const rawLoci = node.loci || [];
    if (rawLoci.length === 0) continue;
    addressableNodeCount++;

    const nodeVals = [];
    const nodePadjs = [];

    for (const locus of rawLoci) {
      const locUp = locus.toUpperCase();
      if (species === 'arabidopsis_thaliana') {
        if (inputMap.has(locUp)) {
          const hit = inputMap.get(locUp);
          nodeVals.push(hit.val);
          if (hit.padj !== null && !isNaN(hit.padj)) nodePadjs.push(hit.padj);
        }
      } else if (orthologs && orthologs.species && orthologs.species[species]) {
        const spData = orthologs.species[species];
        const orthoEntry = spData.orthologs ? spData.orthologs[locUp] : null;
        if (orthoEntry && orthoEntry.targets) {
          for (const targetId of orthoEntry.targets) {
            const tidUp = targetId.toUpperCase();
            if (inputMap.has(tidUp)) {
              const hit = inputMap.get(tidUp);
              nodeVals.push(hit.val);
              if (hit.padj !== null && !isNaN(hit.padj)) nodePadjs.push(hit.padj);
            }
          }
        }
      }
    }

    if (nodeVals.length > 0) {
      mappedNodeCount++;
      let finalVal;
      if (aggMode === 'median') {
        nodeVals.sort((a, b) => a - b);
        finalVal = nodeVals[Math.floor(nodeVals.length / 2)];
      } else if (aggMode === 'extreme') {
        finalVal = nodeVals.reduce((max, cur) => Math.abs(cur) > Math.abs(max) ? cur : max, nodeVals[0]);
      } else {
        // default mean
        finalVal = nodeVals.reduce((a, b) => a + b, 0) / nodeVals.length;
      }

      const isSig = nodePadjs.length > 0 ? nodePadjs.some(p => p <= alpha) : null;
      const fillColor = colorForValue(finalVal);

      // Locate DOM node in SVG
      const gNode = svgElement.querySelector(`#node-${node.id}`);
      if (gNode) {
        const rect = gNode.querySelector('rect');
        if (rect) {
          rect.style.fill = fillColor;
          if (isSig === true) {
            rect.style.stroke = 'var(--ppa-ink)';
            rect.style.strokeWidth = '2.5px';
            rect.style.strokeDasharray = 'none';
          } else if (isSig === false) {
            rect.style.stroke = 'var(--ppa-hairline)';
            rect.style.strokeWidth = '1.0px';
            rect.style.strokeDasharray = '3 2';
          }
        }
        gNode.setAttribute('data-projected-val', finalVal.toFixed(3));
      }
    }
  }

  const fraction = addressableNodeCount > 0 ? (mappedNodeCount / addressableNodeCount) : 0;
  if (mappedNodeCount === 0 && addressableNodeCount > 0) {
    throw new Error(
      `Zero of ${addressableNodeCount} addressable nodes matched any identifiers in your dataset. ` +
      `Ensure you selected the right species and column.`
    );
  }

  return {
    mappedNodes: mappedNodeCount,
    totalAddressable: addressableNodeCount,
    fractionMapped: fraction,
    lowCoverage: fraction < 0.25,
  };
}
