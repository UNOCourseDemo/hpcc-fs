# HPCC Smoke Debug Notes

This note records the smoke-test flow-completion failure debugged during the ns-3.45 refactor.

## Symptom

The mini smoke run exited with status 0, but the validation runner reported `0/6` completed flows:

```bash
bash examples/hpcc/algorithm-validation/run.sh configs/hpcc_smoke.yml
```

The status output showed QPs were created and still active at `simulator_stop_time`, but no bytes were in flight:

```text
flows active=6 qps=6 started=6/6 completed=0 pending=0 bytes_left=900000 in_flight=0
```

That means the simulation startup and flow scheduling worked, but the host scheduler stopped finding eligible QPs to transmit.

## Root Cause 1: QP Window Underflow

Debug logging around `RdmaEgressQueue::GetNextQindex()` showed QPs with:

```text
snd_nxt=0 snd_una=1000 win_bound=true
```

`RdmaQueuePair::GetOnTheFly()` computed `snd_nxt - snd_una` using unsigned integers. Once ACK or recovery handling advanced `snd_una` beyond `snd_nxt`, the subtraction underflowed to a huge value. `IsWinBound()` then treated the QP as permanently window-bound, so the scheduler skipped it forever.

Fix:

- Keep the sender invariant `snd_nxt >= snd_una` after an ACK advances `snd_una`.
- Saturate `GetOnTheFly()` to 0 if the invariant is ever violated again.

Changed file:

- `src/point-to-point/model/rdma-queue-pair.cc`

## Root Cause 2: PFC RNG Crash After Traffic Progressed

After the QP fix, packets flowed far enough to trigger PFC, then the simulator crashed in `QbbNetDevice::SendPfc()`.

Crash path:

```text
SwitchNode::CheckAndSendPfc()
QbbNetDevice::SendPfc()
UniformRandomVariable::GetInteger()
RngStream::RandU01()
```

The refactor had created a temporary `UniformRandomVariable` directly:

```cpp
UniformRandomVariable().GetInteger(0, 65536)
```

In ns-3.45 this leaves the stream without a valid initialized RNG. The fix uses the global RNG stream and bounds the IPv4 identification field to the 16-bit max:

```cpp
UniformRandomVariable::GetGlobalRng()->GetInteger(0, 65535)
```

Changed file:

- `src/point-to-point/model/qbb-net-device.cc`

## Validation

Build command used:

```bash
/opt/homebrew/bin/cmake --build <repo>/cmake-build-debug --target hpcc-validation -j 14
```

Smoke validation:

```bash
bash examples/hpcc/algorithm-validation/run.sh configs/hpcc_smoke.yml
```

Result:

```text
OK hpcc_smoke 6/6 flows 42 pfc
```

Nearby HPCC incast validation:

```bash
bash examples/hpcc/algorithm-validation/run.sh configs/hpcc_incast.yml
```

Result:

```text
OK hpcc_incast 12/12 flows 990 pfc
```

## Does This Exist In The Alibaba HPCC Repo?

Checked against `alibaba-edu/High-Precision-Congestion-Control` `master` on GitHub.

The QP underflow issue appears to exist in the original source as a latent bug. Upstream `RdmaQueuePair::Acknowledge()` only advances `snd_una`, and upstream `GetOnTheFly()` returns `snd_nxt - snd_una` without guarding against `snd_una > snd_nxt`:

- https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/simulation/src/point-to-point/model/rdma-queue-pair.cc#L886-L900

The exact PFC RNG crash does not appear to be the same upstream bug. The original simulator used the older ns-3 random API:

- https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/simulation/src/point-to-point/model/qbb-net-device.cc#L2018-L2038

In this refactor, that old `UniformVariable` call became a temporary `UniformRandomVariable`, which is not a safe one-for-one migration in ns-3.45. So this one is best classified as a refactor/API-porting bug, not a confirmed original HPCC bug.

