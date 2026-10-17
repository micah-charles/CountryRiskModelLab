import { HistoryPage } from "@/app/components/research-modules";
import { ProtectedPage } from "@/app/components/protected-page";
import { isLocalBondDataAccessEnabled } from "@/lib/site-config";
export const dynamic = "force-dynamic";
export default function Page() { return <ProtectedPage path="/history"><HistoryPage localDataAccess={isLocalBondDataAccessEnabled()} /></ProtectedPage>; }
