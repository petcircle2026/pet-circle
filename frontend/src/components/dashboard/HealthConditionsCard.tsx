"use client";

import type { DashboardData, HealthConditionSummary } from "@/lib/api";
import { normalizeConditions } from "./dashboard-utils";

interface HealthConditionsCardProps {
  data: DashboardData;
  onGoToTrends: () => void;
  compact?: boolean;
}

const HEADLINE_STATE_LABEL: Record<string, string> = {
  needs_attention: "needs attention",
  active: "under treatment",
  monitoring: "under monitoring",
  managed: "managed",
  resolved: "all clear",
  clean: "no concerns",
};

function shouldLimitInsights(items: HealthConditionSummary[]): boolean {
  return !items.some((item) => {
    const label = (item.trend_label || "").toLowerCase();
    return label.includes("active") || label.includes("recurrent") || label.includes("recurring");
  });
}

export default function HealthConditionsCard({
  data,
  onGoToTrends,
  compact = false,
}: HealthConditionsCardProps) {
  const rawHealth = data.health_conditions_v2;
  const summaryConditions = (data.health_conditions_summary ?? []).length;

  // Guard: if the AI cache reports 0 conditions but the DB summary has live conditions,
  // the cache is stale (precompute ran before extraction committed). Fall through to the
  // summary fallback so real conditions are never hidden.
  const health = rawHealth && rawHealth.meta.total_conditions === 0 && summaryConditions > 0
    ? null
    : rawHealth;

  // If Health Prompt 5 result is available, use it directly.
  if (health) {
    const allConditions = health.conditions.filter((c) =>
      (["red", "yellow", "green"] as const).includes(c.severity)
    );
    const headlineLabel = HEADLINE_STATE_LABEL[health.headline_state] ?? "no concerns";

    const severityDotColor = (severity: string) => {
      if (severity === "red") return "var(--red)";
      if (severity === "yellow") return "var(--amber)";
      return "var(--green)";
    };

    return (
      <div className={compact ? undefined : "card"}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6, flexWrap: "wrap", gap: 6 }}>
          <div className="sec-lbl" style={{ margin: 0 }}>Health Conditions</div>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            color: "var(--orange)",
            background: "#FFF3EE",
            border: "1px solid var(--orange)",
            borderRadius: 20,
            padding: "2px 8px",
            whiteSpace: "nowrap",
          }}>
            ⚕ Under review by PetCircle Sr. Vet
          </span>
        </div>
        <button
          onClick={onGoToTrends}
          type="button"
          style={{
            fontSize: 13,
            color: "var(--orange)",
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            fontFamily: "inherit",
            fontWeight: 500,
            marginBottom: 10,
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          📋 See detailed analysis →
        </button>
        <div style={{ fontSize: 13, color: "var(--t2)", marginBottom: 10, lineHeight: 1.5 }}>
          {health.meta.total_conditions} condition{health.meta.total_conditions !== 1 ? "s" : ""} identified —{" "}
          {headlineLabel}.
        </div>

        {allConditions.map((c) => (
          <div key={c.id} style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <div
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: severityDotColor(c.severity),
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--t1)", flex: 1 }}>
                {c.name}
              </span>
              <span style={{ fontSize: 11, color: "var(--t3)" }}>{c.trend_label}</span>
            </div>
            {c.insight && (
              <div
                style={{
                  fontSize: 12,
                  color: "var(--t2)",
                  lineHeight: 1.45,
                  paddingLeft: 15,
                  borderLeft: "2px solid #FFCDD2",
                }}
              >
                {c.insight}
              </div>
            )}
          </div>
        ))}

        <button
          type="button"
          disabled
          style={{
            marginTop: 12,
            width: "100%",
            padding: "10px",
            background: "#FF6B35",
            border: "none",
            borderRadius: "var(--rs)",
            fontSize: 13,
            fontWeight: 700,
            color: "#fff",
            cursor: "default",
            fontFamily: "inherit",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
            opacity: 1,
          }}
        >
          🩺 Book a Consult →
        </button>
      </div>
    );
  }

  // Fallback: legacy health_conditions_summary path.
  const allConditions = normalizeConditions(data);
  const visible = shouldLimitInsights(allConditions) ? allConditions.slice(0, 2) : allConditions;

  return (
    <div className={compact ? undefined : "card"}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6, flexWrap: "wrap", gap: 6 }}>
        <div className="sec-lbl" style={{ margin: 0 }}>Health Conditions</div>
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          color: "#c0392b",
          background: "#FFF0ED",
          border: "1px solid #FFCDD2",
          borderRadius: 20,
          padding: "2px 8px",
          whiteSpace: "nowrap",
        }}>
          ⚕ Under review by PetCircle Sr. Vet
        </span>
      </div>
      {allConditions.length > 0 && (
        <button
          onClick={onGoToTrends}
          type="button"
          style={{
            fontSize: 13,
            color: "var(--orange)",
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            fontFamily: "inherit",
            fontWeight: 500,
            marginBottom: 10,
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          📋 See detailed analysis →
        </button>
      )}

      {allConditions.length === 0 ? (
        <div style={{ fontSize: 13, color: "var(--t2)", marginBottom: 8, lineHeight: 1.5 }}>
          No active concerns · Routine care maintained
        </div>
      ) : (
        <>
          <div style={{ fontSize: 13, color: "var(--t2)", marginBottom: 10, lineHeight: 1.5 }}>
            {allConditions.length} active health condition{allConditions.length > 1 ? "s" : ""} identified.
          </div>

          {visible.map((condition) => (
            <div key={condition.id} style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <div
                  style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--red)", flexShrink: 0 }}
                />
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--t1)", flex: 1 }}>{condition.title}</span>
                <span style={{ fontSize: 11, color: "var(--t3)" }}>{condition.trend_label}</span>
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--t2)",
                  lineHeight: 1.45,
                  paddingLeft: 15,
                  borderLeft: "2px solid #FFCDD2",
                }}
              >
                {condition.insight}
              </div>
            </div>
          ))}
        </>
      )}

      <button
        type="button"
        disabled
        style={{
          marginTop: 12,
          width: "100%",
          padding: "10px",
          background: "#FF6B35",
          border: "none",
          borderRadius: "var(--rs)",
          fontSize: 13,
          fontWeight: 700,
          color: "#fff",
          cursor: "default",
          fontFamily: "inherit",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 6,
          opacity: 1,
        }}
      >
        🩺 Book a Consult →
      </button>
    </div>
  );
}
