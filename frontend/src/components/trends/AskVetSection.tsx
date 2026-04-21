"use client";

import type { AskVetData } from "@/lib/api";

interface AskVetSectionProps {
  data: AskVetData | null;
  vetName: string;
  onOpenDashboardCondition?: (conditionId: string) => void;
}

export default function AskVetSection({
  data,
  vetName,
  onOpenDashboardCondition,
}: AskVetSectionProps) {
  const conditions = data?.conditions || [];

  return (
    <section>
      {conditions.length === 0 ? (
        <div className="card" style={{ fontSize: 13, color: "var(--t2)", lineHeight: 1.5 }}>
          No active conditions are available right now.
        </div>
      ) : (
        <div className="card">
          {/* Conditions summary (compact list) */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--t3)", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 8 }}>
              Active Conditions ({conditions.length})
            </div>
            {conditions.map((condition) => (
              <div
                key={condition.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 10px",
                  borderRadius: 8,
                  background: "var(--warm)",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--t1)" }}>
                    {condition.label}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--t3)", marginTop: 2 }}>
                    {condition.trend}
                  </div>
                </div>
                {onOpenDashboardCondition && (
                  <button
                    type="button"
                    onClick={() => onOpenDashboardCondition(condition.id)}
                    style={{
                      border: "none",
                      background: "transparent",
                      color: "var(--orange)",
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      padding: "4px 8px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    View →
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}