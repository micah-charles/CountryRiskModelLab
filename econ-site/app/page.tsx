import { requireChatGPTUser } from "@/app/chatgpt-auth";
import { SiteFrame } from "@/app/components/site-frame";
import { HomeDashboard } from "@/app/components/home-dashboard";

export const dynamic = "force-dynamic";

export default async function Home() {
  await requireChatGPTUser("/");
  return <SiteFrame><HomeDashboard /></SiteFrame>;
}
