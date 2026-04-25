"use client";

import { useEffect, useState } from "react";
import type { DashboardData } from "@/lib/api";
import { getLastVetVisit } from "@/lib/api";
import { formatVetVisitDate } from "@/utils/profile-utils";
import { LAYOUT } from "@/lib/css-classes";
import { ARIA_LABELS } from "@/lib/aria-labels";
import {
  ageMonthsFromDob,
  formatAgeLabel,
  getPetAvatar,
  normalizeSex,
  normalizeWeight,
} from "./dashboard-utils";

interface ProfileBannerProps {
  data: DashboardData;
  token: string;
  onGoToReminders: () => void;
}

export default function ProfileBanner({ data, token, onGoToReminders }: ProfileBannerProps) {
  const ageMonths = data.life_stage?.age_months ?? ageMonthsFromDob(data.pet.dob);
  const avatar = getPetAvatar(data.pet.species);
  const fallbackVetName = data.vet_summary?.name || "Not added yet";
  const fallbackVetLastVisit = formatVetVisitDate(data.vet_summary?.last_visit) || "--";
  const [latestVet, setLatestVet] = useState<{ name: string; lastVisit: string }>({
    name: fallbackVetName,
    lastVisit: fallbackVetLastVisit,
  });

  useEffect(() => {
    setLatestVet({ name: fallbackVetName, lastVisit: fallbackVetLastVisit });
  }, [fallbackVetLastVisit, fallbackVetName]);

  useEffect(() => {
    let isActive = true;

    const loadLatestVet = async () => {
      try {
        const lastVet = await getLastVetVisit(token);
        if (!isActive) return;

        const latestName = lastVet.vet_name?.trim() || "Not added yet";
        const latestVisit = formatVetVisitDate(lastVet.last_visit_date);
        const hasLatestRecord = Boolean(lastVet.vet_name?.trim() || lastVet.last_visit_date);
        if (hasLatestRecord) {
          setLatestVet({ name: latestName, lastVisit: latestVisit });
          return;
        }

        setLatestVet({ name: "Not added yet", lastVisit: "--" });
      } catch {
        if (!isActive) return;
        setLatestVet({ name: fallbackVetName, lastVisit: fallbackVetLastVisit });
      }
    };

    void loadLatestVet();

    return () => {
      isActive = false;
    };
  }, [fallbackVetLastVisit, fallbackVetName, token]);

  const vetName = latestVet.name || "Not added yet";
  const vetLastVisit = latestVet.lastVisit || "--";

  const subParts: string[] = [];
  if (data.pet.breed) subParts.push(data.pet.breed);
  if (data.pet.gender) subParts.push(normalizeSex(data.pet.gender));
  if (ageMonths != null && ageMonths > 0 && data.pet.dob) subParts.push(formatAgeLabel(ageMonths));
  if (typeof data.pet.weight === "number" && data.pet.weight > 0) subParts.push(`⚖️ ${normalizeWeight(data.pet.weight)}`);
  const subLine = subParts.join(" · ");

  return (
    <div className={LAYOUT.banner}>
      <div className="bn-top">
        <span className="brand">PetCircle</span>
        <button
          className={LAYOUT.bell}
          onClick={onGoToReminders}
          type="button"
          title={ARIA_LABELS.openReminders}
          aria-label={ARIA_LABELS.openReminders}
        >
          🔔
        </button>
      </div>

      <div className={LAYOUT.profile}>
        <div className={LAYOUT.avatar}>{avatar}</div>
        <div style={{ minWidth: 0 }}>
          <div className="dog-name">{data.pet.name}</div>
          {subLine && (
            <div className="dog-sub truncate">
              {subLine}
            </div>
          )}
        </div>
      </div>

      <div className="vet-row">
        <span>🩺</span>
        <span className="vet-l">Vet</span>
        <span className="vet-v">{vetName}</span>
        <span className="vet-sep">·</span>
        <span className="vet-l">Last visit</span>
        <span className="vet-v">{vetLastVisit}</span>
      </div>
    </div>
  );
}
