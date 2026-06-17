# Repro-verification run log

Code of record: branch `paper-hpcc-fs`, HEAD `e9e167f2d` (engine unchanged since `c4c2c7a54`).
Canonical engine confirmed on both VMs (`hpcc-validation.cc` sha `4ac92a06…`).
Both VMs built **byte-identical** optimized binaries (sha `3f27051846ba`).
Traffic frozen + identical across local/frcc/frcc2 (see `traffic_checksums.txt`).

## 2026-06-16 — BLOCKER: canonical binary segfaults on the full fat-tree

Running any paper-simulations config (`mix/fat.txt`, 376 nodes / 56 switches / 70 292 flows)
with the **canonical** optimized binary **crashes** before the simulation starts:

```
Command terminated by signal 11 (SIGSEGV)   # optimized
SIGABRT via Ptr<RdmaDriver>::operator-> on null   # debug
#9 SetRoutingEntries () at hpcc-validation.cc:715
#10 main () at hpcc-validation.cc:1053
```

`hpcc-validation.cc:715` = `node->GetObject<RdmaDriver>()->m_rdma->AddTableEntry(...)`.

### This is a regression in the canonical code, not a topology problem
- **Control:** the VMs' *original* tree binary (`~/uno-hpcc`, the diverged `afs` work) runs the
  **same** `mix/fat.txt` config fine — simulated to 50 %, 1116+ FCT rows, flows completing.
- Canonical works on the paper's *small* topologies (parking-lot ≤5 switches, k=4/6/8 fat-trees);
  it crashes only on this **376-node / 56-switch** fat-tree → **scales with topology size**.

### It is heap corruption, not an optimization bug
- The **debug** (`-O0`, no `-march=native`) build crashes too → logic/memory bug, not codegen.
- At the crash, gdb shows the offending `node`:
  - `node->GetId() = 0`  (node 0, a server)
  - `node->GetNodeType() = 1936941424`  ← **garbage** (should be 0); `= 0x73716070`, ASCII-ish
    → node 0's object memory was **overwritten** by an out-of-bounds write earlier in setup.
  - `next->GetId() = 320` (first switch), `next->GetNodeType() = 1` (correct).
- Routing source (`SetRoutingEntries`/`CalculateRoute`) and the RDMA-install loop are **identical**
  to the working original, so the overflow is in common setup code whose corruption *happens to
  land on* node 0 under canonical's memory layout (canonical's `SwitchNode` is larger — extra FS
  fields). Likely latent in both; canonical's layout exposes it.

### ROOT CAUSE (resolved): `ns3::Node::m_node_type` is uninitialized
It is **not** an out-of-bounds write — ASan found none, and a hardware watchpoint showed node 0's
`m_node_type` was **already garbage right after construction** (and never written again):
- `Node::Node()` / `Node::Node(uint32_t)` initialize `m_id`, `m_sid` but **not** `m_node_type`;
  `Construct()` doesn't either. A plain `Node` (server) therefore has an **uninitialized**
  `m_node_type`. `SwitchNode`'s ctor sets it to 1, so only servers are affected.
- On small topologies the fresh heap reads 0 (the intended server value) by luck → it "works".
  On the 376-node fat-tree, allocation churn leaves **nonzero garbage** → a server is mistyped as
  non-server → `SetRoutingEntries` takes the `else` branch and derefs a null `RdmaDriver` → crash.
- The bug is latent in the **original** tree too; it only avoided the crash by heap luck. ASan
  can't catch it (uninitialized *read*, not an out-of-bounds *access*).

### Fix
`src/network/model/node.h`: `uint32_t m_node_type = 0;` (default member initializer). Servers
now reliably get 0; `SwitchNode` still overrides to 1. Pure correctness fix — does not touch any
`cc_mode` logic, so stock HPCC (`cc_mode 3`) behavior is restored, not altered.

### Fix verified
After a clean from-scratch rebuild (the incremental builds were unreliable; note the fixed code
lives in `libns3.45-network-optimized.so`, so the 401 KB example *binary*'s sha never changes — the
`.so` is what carries the fix; disasm of `Node::Node()` shows the new `movl $0x0,0x3c(%rbx)`
m_node_type zero-store). A clean `hpcc_ws_30` run: **no SIGSEGV, no "Flow row" error**, simulates
past 50 %, FCT rows accumulating. Both VMs carry the identical fixed `.so` (sha `6dc595bd6631`).

### Campaign launched
30 configs split 15/15, concurrency 8 per VM (`run_repro.sh`):
- **frcc**:  `fb_70`, `ws_70`, `ws_30` (×5 schemes)
- **frcc2**: `fb_50`, `fb_30`, `ws_50` (×5 schemes)
Heavy `fb_*` cells split across the two VMs to balance memory. Collect → analyze → compare.
