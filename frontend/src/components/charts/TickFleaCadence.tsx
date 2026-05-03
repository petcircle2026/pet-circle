"use client";

import type { FleaTickCadence } from "@/lib/api";
import DotPlotSVG from "./DotPlotSVG";
import {
  buildCriticalGapAnnotations,
  formatAxisDate,
  parseGapWeeks,
} from "@/components/trends/trend-utils";

interface TickFleaCadenceProps {
  data: FleaTickCadence;
}

export default function TickFleaCadence({ data }: TickFleaCadenceProps) {
  const today = new Date();

  return (
    <DotPlotSVG
      doses={data.doses.map((dose, i) => {
        let gapWeeks = parseGapWeeks(dose.gap);

        if (dose.status === "overdue") {
          // Find the last actually-administered dose before this one
          const prevGiven = [...data.doses]
            .slice(0, i)
            .reverse()
            .find((d) => d.status !== "upcoming" && d.status !== "overdue" && d.date);
          if (prevGiven?.date) {
            const msPerWeek = 7 * 24 * 60 * 60 * 1000;
            gapWeeks = Math.floor(
              (today.getTime() - new Date(prevGiven.date).getTime()) / msPerWeek
            );
          }
        }

        return {
          n: dose.num,
          label: formatAxisDate(dose.date),
          gapWeeks,
          gapLabel: dose.status === "overdue" && gapWeeks !== undefined ? `${gapWeeks}w` : (dose.gap ?? undefined),
          isUpcoming: dose.status === "upcoming",
        };
      })}
      criticalGaps={buildCriticalGapAnnotations(data.doses)}
      footer={data.footer.text}
    />
  );
}