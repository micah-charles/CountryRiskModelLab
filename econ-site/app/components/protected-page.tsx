import { requireChatGPTUser } from "@/app/chatgpt-auth";
import { SiteFrame } from "@/app/components/site-frame";

export async function ProtectedPage({ path, children }: { path: string; children: React.ReactNode }) {
  await requireChatGPTUser(path);
  return <SiteFrame>{children}</SiteFrame>;
}
