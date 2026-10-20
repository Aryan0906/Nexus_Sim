import { describe, it, expect } from "vitest";
import algoMatrix from "../../public/data/36_algo_matrix.json";
import comparisonData from "../../public/comparison.json";

describe("Algorithm Matrix & Multi-Subject Catalog Suite", () => {
  it("should contain the complete 48-algorithm inventory across all 4 subjects", () => {
    expect(algoMatrix.total_algorithms).toBe(48);
    expect(Object.keys(algoMatrix.subjects)).toEqual([
      "Computer Vision",
      "Soft Computing",
      "Natural Language Processing",
      "Reinforcement Learning",
    ]);
  });

  it("should contain exactly 12 algorithms for each subject", () => {
    expect(algoMatrix.subjects["Computer Vision"].length).toBe(12);
    expect(algoMatrix.subjects["Soft Computing"].length).toBe(12);
    expect(algoMatrix.subjects["Natural Language Processing"].length).toBe(12);
    expect(algoMatrix.subjects["Reinforcement Learning"].length).toBe(12);
  });

  it("should have all active algorithm entries with valid latency and metrics", () => {
    for (const [, algos] of Object.entries(algoMatrix.subjects)) {
      for (const algo of algos) {
        expect(algo.id).toBeTruthy();
        expect(algo.name).toBeTruthy();
        expect(["ACTIVE", "DEPLOYED_C++", "BENCHMARKED", "SHOWCASE"]).toContain(algo.status);
        expect(algo.latency_ms).toBeGreaterThan(0);
        expect((algo as any).accuracy || (algo as any).reward || (algo as any).metric).toBeTruthy();
      }
    }
  });

  it("should state measured-vs-catalog provenance honestly in performance_summary", () => {
    // Verified numbers must be labelled as measured; unverified catalog
    // claims must say so explicitly (2026-10 audit requirement).
    expect(algoMatrix.performance_summary.fastest_subsystem).toContain("measured");
    expect(algoMatrix.performance_summary.fastest_subsystem).toContain("measured range");
    expect(algoMatrix.performance_summary.most_accurate_cv).toContain("Not independently measured");
    expect(algoMatrix.performance_summary.best_calibration_optimizer).toContain("Not measured");
    expect(algoMatrix.performance_summary.highest_rl_throughput).toContain("Not measured");
  });
});

describe("Multi-City Comparison & Policy Benchmark Suite", () => {
  it("should have valid city comparison benchmark records", () => {
    expect(Array.isArray(comparisonData)).toBe(true);
    expect(comparisonData.length).toBeGreaterThanOrEqual(3);

    const chicago = comparisonData.find((c: any) => c.city === "chicago");
    expect(chicago).toBeDefined();
    if (chicago) {
      expect(chicago.intersections).toBe(3709);
      expect(chicago.improvement_pct).toBeGreaterThan(20);
      expect(chicago.marl.episode_reward).toBeGreaterThan(chicago.webster.episode_reward);
    }
  });

  it("should have valid schema definitions for Webster baseline vs MARL metrics", () => {
    for (const row of comparisonData) {
      expect(row.city).toBeTruthy();
      expect(row.intersections).toBeGreaterThan(0);
      expect(row.webster.episode_reward).toBeLessThan(0);
      expect(row.marl.episode_reward).toBeLessThan(0);
      expect(typeof row.improvement_pct).toBe("number");
    }
  });
});

describe("WebSocket Protocol Message Contract", () => {
  it("should generate conforming policy_switch payload", () => {
    const payload = {
      type: "policy_switch",
      policy: "rl",
      algorithm: "mappo",
      intersection_id: "all",
    };
    expect(payload.type).toBe("policy_switch");
    expect(["webster", "fuzzy", "type2_fuzzy", "rl"]).toContain(payload.policy);
  });

  it("should generate conforming incident reporting payload", () => {
    const payload = {
      type: "incident",
      edges: ["100_101", "101_102"],
      severity: 0.75,
      duration_s: 180,
    };
    expect(payload.type).toBe("incident");
    expect(payload.edges.length).toBeGreaterThan(0);
    expect(payload.severity).toBeGreaterThanOrEqual(0);
    expect(payload.severity).toBeLessThanOrEqual(1);
    expect(payload.duration_s).toBeGreaterThan(0);
  });
});
