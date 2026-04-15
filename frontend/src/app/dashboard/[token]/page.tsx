import type { Metadata } from "next";
import DashboardClient from "@/components/DashboardClient";

export const metadata: Metadata = {
  title: "Pet Dashboard | PetCircle",
  description: "View your pet's preventive health records and reminders",
};

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <DashboardClient token={token} />;
}
