import React, { useEffect, useState } from 'react';
import { AlgoExplorer } from './AlgoExplorer';
import type { AlgorithmItem } from './AlgorithmCard';

// Loads the canonical 48-algorithm matrix (12 per subject) that
// ml/eval/benchmark_36.py generates into dashboard/public/data. The static
// file keeps the explorer usable even when the gateway/algo sidecar is down.
export const AlgoExplorerPanel: React.FC = () => {
  const [algorithms, setAlgorithms] = useState<AlgorithmItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch('/data/36_algo_matrix.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        const flat = Object.values(data.subjects || {}).flat() as AlgorithmItem[];
        setAlgorithms(flat);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div style={{ color: '#f87171', fontSize: '12px', padding: '8px' }}>
        Algorithm catalog unavailable ({error})
      </div>
    );
  }
  if (!algorithms) {
    return (
      <div style={{ color: '#9ca3af', fontSize: '12px', padding: '8px' }}>
        Loading algorithm catalog…
      </div>
    );
  }
  return <AlgoExplorer algorithms={algorithms} />;
};

export default AlgoExplorerPanel;
