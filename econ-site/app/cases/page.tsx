import { CasesPage } from "@/app/components/research-modules";
import { ProtectedPage } from "@/app/components/protected-page";
export const dynamic = "force-dynamic";
export default function Page() { return <ProtectedPage path="/cases"><CasesPage /></ProtectedPage>; }
