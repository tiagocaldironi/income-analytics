import assert from "node:assert/strict";
import net from "node:net";
import dns from "node:dns";

assert.throws(() => net.connect(8002, "127.0.0.1"), /CI_OFFLINE_NETWORK_BLOCKED/);
assert.throws(() => fetch("https://example.invalid"), /CI_OFFLINE_NETWORK_BLOCKED/);
assert.throws(() => dns.promises.lookup("example.invalid"), /CI_OFFLINE_NETWORK_BLOCKED/);
console.log("Node offline guard passed.");
