declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
    BUCKET?: R2Bucket;
    BOND_EXTENDED_CLOUD_RIGHTS?: string;
    BOND_LOCAL_DATA_ACCESS?: string;
  }
}
