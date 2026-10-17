import { BondDashboard } from "@/app/components/bond-dashboard";
import { LocalBondDashboard } from "@/app/components/local-bond-dashboard";
import { ProtectedPage } from "@/app/components/protected-page";
import { isLocalBondDataAccessEnabled } from "@/lib/site-config";
export const dynamic = "force-dynamic";
export default function BondsPage() { return <ProtectedPage path="/bonds">{isLocalBondDataAccessEnabled() ? <LocalBondDashboard /> : <BondDashboard />}</ProtectedPage>; }
