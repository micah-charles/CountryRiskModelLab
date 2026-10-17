import { env } from "cloudflare:workers";

/** Local loopback previews may open full bond data and exports; hosted Sites stay chart-only. */
export function isLocalBondDataAccessEnabled() {
  return env.BOND_LOCAL_DATA_ACCESS === "true";
}
