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

  // Combine all questions from all conditions into one unified list
  const allQuestions = conditions
    .flatMap((condition) => condition.questions)
    .filter((q) => q && q.trim());

  return (
    <section>
      <div
        style={{
          fontSize: 13,
          color: "var(--t2)",
          marginBottom: 14,
          lineHeight: 1.55,
          padding: "10px 14px",
          background: "var(--tr)",
          borderRadius: 10,
          border: "1px solid #FFCDD2",
        }}
      >
        🩺 Share this section with <strong style={{ color: "var(--t1)" }}>Dr. {vetName}</strong> at your next visit.
      </div>

      {allQuestions.length === 0 ? (
        <div className="card" style={{ fontSize: 13, color: "var(--t2)", lineHeight: 1.5 }}>
          No vet discussion items are available right now.
        </div>
      ) : (
        <div className="card">
          {/* Conditions summary (compact list) */}
          {conditions.length > 0 && (
            <div style={{ marginBottom: 16, paddingBottom: 12, borderBottom: "1px solid var(--border)" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--t3)", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 8 }}>
                Active Conditions ({conditions.length})
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
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

          {/* All questions unified */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--t3)", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 8 }}>
              Ask Your Vet ({allQuestions.length})
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              {allQuestions.map((question, index) => (
                <div
                  key={`question-${index}`}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 8,
                    padding: "10px 12px",
                    borderRadius: 10,
                    background: "var(--ta)",
                  }}
                >
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 800,
                      color: "var(--orange)",
                      flexShrink: 0,
                      marginTop: 1,
                    }}
                  >
                    {index + 1}.
                  </span>
                  <span style={{ fontSize: 13, color: "var(--t1)", lineHeight: 1.5, fontWeight: 500 }}>
                    {question}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}