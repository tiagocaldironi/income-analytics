// Preloaded only by the CI runner; VM tests still provide their own fetch doubles.
import net from "node:net";
import dgram from "node:dgram";
import dns from "node:dns";
import { syncBuiltinESMExports } from "node:module";

const blocked = () => { throw new Error("CI_OFFLINE_NETWORK_BLOCKED"); };
net.Socket.prototype.connect = blocked;
dgram.Socket.prototype.send = blocked;
dns.lookup = blocked;
dns.resolve = blocked;
dns.promises.lookup = blocked;
dns.promises.resolve = blocked;
globalThis.fetch = blocked;
syncBuiltinESMExports();
