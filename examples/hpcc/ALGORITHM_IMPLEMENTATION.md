# RDMA Congestion-Control Algorithm Map

This note maps the sender-side and congestion-point-side behavior for the RDMA congestion-control algorithms used by `examples/hpcc/hpcc-validation.cc`.

It is a code-reading summary of this checkout. It focuses on the active implementation path, not only on the names inherited from the original HPCC/Alibaba simulator.

## Algorithm Selection

`cc_mode` selects the algorithm:

| `cc_mode` | Algorithm | Sender feedback field | Switch / congestion-point signal |
|---:|---|---|---|
| `1` | DCQCN / Mellanox-style DCQCN | ACK CNP flag | ECN marking from switch queue thresholds, then receiver reflects mark in ACK |
| `3` | HPCC | Full INT hop records | Switch appends per-hop INT: timestamp, tx bytes, queue length, line rate |
| `7` | TIMELY | Packet timestamp echoed in ACK | No switch queue signal used by TIMELY sender; RTT comes from source timestamp |
| `8` | DCTCP-like rate control | ACK CNP flag | ECN marking from switch queue thresholds, then receiver reflects mark in ACK |
| `10` | HPCC-PINT | Probabilistic encoded utilization | Switch updates compact PINT utilization field |

Config entry points:

- `examples/hpcc/hpcc-config.cc`: reads `cc_mode`, `enable_qcn`, rate parameters, HPCC parameters, PINT parameters, and ECN threshold maps.
- `examples/hpcc/hpcc-validation.cc:768-790`: sets QBB defaults and `IntHeader::mode`.
- `examples/hpcc/hpcc-validation.cc:961-988`: configures switch ECN thresholds, PFC headroom, PFC alpha shift, and buffer size.
- `examples/hpcc/hpcc-validation.cc:998-1021`: sets `RdmaHw` sender attributes from YAML.
- `examples/hpcc/hpcc-validation.cc:1065-1071`: sets switch `CcMode` and `MaxRtt` for INT/PINT behavior.

## Common Data Path

Flows become RDMA queue pairs when the application starts:

- `src/applications/model/rdma-client.cc:135-142`: `RdmaClient::StartApplication()` calls `RdmaDriver::AddQueuePair()`.
- `src/point-to-point/model/rdma-driver.cc:64-66`: forwards the request to `RdmaHw`.
- `src/point-to-point/model/rdma-hw.cc:223-280`: creates `RdmaQueuePair`, chooses the NIC, initializes per-algorithm state, and notifies the NIC.
- `src/point-to-point/model/rdma-queue-pair.h:33-81`: stores all per-QP sender state for DCQCN, HPCC, TIMELY, DCTCP, and HPCC-PINT.

The sender packet scheduler is common:

- `src/point-to-point/model/qbb-net-device.cc:121-225`: `RdmaEgressQueue::GetNextQindex()` selects ACK/control traffic first, then RDMA QPs round-robin. It skips paused priority groups, finished QPs, window-bound QPs, and QPs whose `m_nextAvail` pacing time is still in the future.
- `src/point-to-point/model/qbb-net-device.cc:360-438`: host `QbbNetDevice::DequeueAndTransmit()` dequeues one eligible packet and calls `RdmaHw::PktSent()`.
- `src/point-to-point/model/rdma-hw.cc:659-684`: `PktSent()`, `UpdateNextAvail()`, and `ChangeRate()` implement pacing through `qp->m_rate`.
- `src/point-to-point/model/rdma-queue-pair.cc:118-139`: `GetOnTheFly()`, `GetWin()`, and `IsWinBound()` implement the inflight window.

The receiver feedback path is also common:

- `src/point-to-point/model/rdma-hw.cc:321-386`: `ReceiveUdp()` parses ECN bits, updates receiver-side ECN counters, validates sequence progress, and generates ACK/NACK packets.
- `src/point-to-point/model/rdma-hw.cc:359-366`: ACKs copy the data packet INT/PINT/TIMELY header into the ACK; if the received packet had ECN CE bits, the ACK sets the CNP flag.
- `src/point-to-point/model/rdma-hw.cc:433-489`: `ReceiveAck()` acknowledges bytes, handles NACK recovery, handles DCQCN CNP, then dispatches to HPCC, TIMELY, DCTCP, or HPCC-PINT handlers.

Important implementation note: `src/point-to-point/model/cn-header.*` and protocol `0xFF` describe a standalone CNP packet format, but the active DCQCN/DCTCP feedback path in this tree is the ACK CNP flag. `RdmaHw::ReceiveCnp()` at `src/point-to-point/model/rdma-hw.cc:389-430` only parses/lazy-initializes and does not currently apply rate control, and I did not find active switch-side generation of `0xFF` CNP packets.

## Common Congestion Point And Lossless Ethernet Logic

The switch's common congestion-point behavior is in `SwitchNode` and `SwitchMmu`.

Queue admission, PFC, and ECN:

- `src/point-to-point/model/switch-node.cc:110-138`: `SendToDev()` chooses the output port and priority queue, runs ingress/egress admission, updates MMU accounting, and sends PFC if needed.
- `src/point-to-point/model/switch-mmu.cc:36-62`: ingress admission and shared/headroom accounting.
- `src/point-to-point/model/switch-mmu.cc:76-90`: PFC pause/resume decisions.
- `src/point-to-point/model/switch-mmu.cc:92-98`: dynamic PFC threshold calculation.
- `src/point-to-point/model/switch-mmu.cc:99-115`: ECN marking probability from `kmin`, `kmax`, and `pmax`.
- `src/point-to-point/model/switch-node.cc:199-220`: on switch dequeue, remove MMU accounting, optionally mark ECN CE, and send PFC resume if thresholds allow it.

Switch telemetry:

- `src/point-to-point/model/switch-node.cc:222-309`: on switch dequeue, mutate the in-packet INT/PINT header based on `m_ccMode`.
- `src/network/utils/int-header.cc:16-35`: `IntHeader` size and full HPCC hop push.
- `src/network/utils/int-header.h:10-74`: compact representation of per-hop time, bytes, queue length, and line-rate fields.
- `src/point-to-point/model/pint.cc:12-42`: HPCC-PINT log-base encoding and decoding.

PFC is not owned by one congestion-control algorithm. It is the lossless Ethernet backpressure layer and applies to all modes when QBB/PFC is enabled.

## High-Level Pseudocode

These blocks describe the active algorithm shape in this codebase. They omit packet parsing, routing, and ns-3 event details unless those details are part of the congestion-control behavior.

### DCQCN Pseudocode, `cc_mode = 1`

Sender:

```text
on queue_pair_create:
    rate = line_rate
    target_rate = line_rate
    alpha = 1
    first_cnp = true

on ack_received(ack):
    acknowledge_bytes(ack.seq)

    if ack.has_cnp:
        alpha_cnp_arrived = true
        decrease_cnp_arrived = true

        if first_cnp:
            alpha = 1
            schedule_periodic_alpha_update()
            schedule_periodic_rate_decrease_check()
            target_rate = rate = rate * rate_on_first_cnp
            first_cnp = false

periodic alpha_update:
    if alpha_cnp_arrived:
        alpha = (1 - g) * alpha + g
    else:
        alpha = (1 - g) * alpha
    alpha_cnp_arrived = false
    schedule_next_alpha_update()

periodic rate_decrease_check:
    if decrease_cnp_arrived:
        if clamp_target_rate:
            target_rate = rate
        rate = max(min_rate, rate * (1 - alpha / 2))
        reset_rate_increase_stage()
        decrease_cnp_arrived = false
        schedule_rate_increase_timer()
    schedule_next_rate_decrease_check()

periodic rate_increase_timer:
    if stage < fast_recovery_times:
        rate = 0.5 * rate + 0.5 * target_rate
    else if stage == fast_recovery_times:
        target_rate = min(line_rate, target_rate + rate_ai)
        rate = 0.5 * rate + 0.5 * target_rate
    else:
        target_rate = min(line_rate, target_rate + rate_hai)
        rate = 0.5 * rate + 0.5 * target_rate
    stage += 1
```

Congestion point plus feedback reflection:

```text
on switch_dequeue(packet, output_port, priority_group):
    q = egress_bytes[output_port][priority_group]

    if q > kmax:
        mark_packet_ecn_ce(packet)
    else if q > kmin:
        p = pmax * (q - kmin) / (kmax - kmin)
        if random() < p:
            mark_packet_ecn_ce(packet)

on receiver_data_packet(packet):
    if packet.ecn_ce:
        ack.set_cnp_flag()
    send_ack(ack)
```

### HPCC Pseudocode, `cc_mode = 3`

Sender:

```text
on queue_pair_create:
    rate = line_rate
    hpcc_current_rate = line_rate
    for each hop_state:
        hop_rate = line_rate
        utilization = 1
        increase_stage = 0

on ack_received(ack):
    if first_hpcc_feedback:
        save_int_hop_snapshot(ack.int_header)
        last_update_seq = snd_nxt
        return

    if ack.seq advanced beyond last_update_seq:
        full_update = true
    else if fast_react_enabled:
        full_update = false
    else:
        return

    updated_any = false

    for each hop in ack.int_header:
        old = previous_hop_snapshot[hop]
        dt = hop.time - old.time
        bytes_delta = hop.tx_bytes - old.tx_bytes
        tx_rate = bytes_delta * 8 / dt

        u = tx_rate / hop.line_rate
            + min(hop.queue, old.queue) * max_rate / hop.line_rate / window

        smooth utilization over base_rtt
        update previous_hop_snapshot[hop]
        updated_any = true

    if single_rate_hpcc:
        c = aggregate_utilization / target_util
        if c >= 1 or increase_stage >= mi_thresh:
            new_rate = hpcc_current_rate / c + rate_ai
            new_stage = 0
        else:
            new_rate = hpcc_current_rate + rate_ai
            new_stage = increase_stage + 1
    else:
        for each hop:
            c = hop_utilization / target_util
            if c >= 1 or hop_increase_stage >= mi_thresh:
                hop_new_rate = hop_rate / c + rate_ai
                hop_new_stage = 0
            else:
                hop_new_rate = hop_rate + rate_ai
                hop_new_stage = hop_increase_stage + 1
        new_rate = min(hop_new_rate over path)

    new_rate = clamp(new_rate, min_rate, line_rate)
    change_pacing_rate(new_rate)

    if full_update:
        commit hpcc_current_rate, increase_stage, per-hop states
        last_update_seq = snd_nxt
```

Congestion point:

```text
on switch_dequeue(packet, output_port):
    if packet is RDMA data and IntHeader.mode == NORMAL:
        packet.int_header.push_hop(
            time = now,
            tx_bytes = switch_tx_bytes[output_port],
            queue_bytes = output_queue_total_bytes(output_port),
            line_rate = output_link_rate(output_port)
        )

    switch_tx_bytes[output_port] += packet.size

on receiver_data_packet(packet):
    ack.int_header = packet.int_header
    send_ack(ack)
```

### TIMELY Pseudocode, `cc_mode = 7`

Sender:

```text
on data_packet_create:
    packet.timestamp = now

on ack_received(ack):
    acknowledge_bytes(ack.seq)

    if ack.seq has not advanced beyond last_update_seq:
        return

    rtt = now - ack.timestamp

    if this is first timely update:
        last_rtt = rtt
        last_update_seq = snd_nxt
        return

    new_rtt_diff = rtt - last_rtt
    rtt_diff = (1 - timely_alpha) * previous_rtt_diff
             + timely_alpha * new_rtt_diff
    gradient = rtt_diff / timely_min_rtt

    if rtt < timely_t_low:
        increase = true
    else if rtt > timely_t_high:
        decrease_factor = 1 - timely_beta * (1 - timely_t_high / rtt)
        increase = false
    else if gradient <= 0:
        increase = true
    else:
        decrease_factor = max(0, 1 - timely_beta * gradient)
        increase = false

    if increase:
        if increase_stage < 5:
            rate = current_rate + rate_ai
        else:
            rate = current_rate + rate_hai
        rate = min(rate, line_rate)
        increase_stage += 1
    else:
        rate = max(min_rate, current_rate * decrease_factor)
        increase_stage = 0

    current_rate = rate
    previous_rtt_diff = rtt_diff
    last_rtt = rtt
    last_update_seq = snd_nxt
```

Congestion point:

```text
on switch_dequeue(packet):
    forward packet normally

on receiver_data_packet(packet):
    ack.timestamp = packet.timestamp
    send_ack(ack)
```

TIMELY's congestion signal is RTT inflation, so the switch does not need to mark ECN or write queue telemetry for the TIMELY sender. ECN/PFC may still run as shared infrastructure if enabled.

### DCTCP Pseudocode, `cc_mode = 8`

Sender:

```text
on queue_pair_create:
    rate = line_rate
    alpha = 1
    ecn_count = 0
    cwr = false

on ack_received(ack):
    acknowledge_bytes(ack.seq)

    if ack.has_cnp:
        ecn_count += 1

    if ack.seq advanced beyond last_update_seq:
        if first_batch:
            batch_size = packets_sent_so_far
        else:
            fraction_marked = min(1, ecn_count / batch_size)
            alpha = (1 - g) * alpha + g * fraction_marked
            ecn_count = 0
            batch_size = packets_sent_since_ack
        last_update_seq = snd_nxt
        new_batch = true

    if cwr and ack.seq > high_seq:
        cwr = false

    if ack.has_cnp and not cwr:
        rate = max(min_rate, rate * (1 - alpha / 2))
        cwr = true
        high_seq = snd_nxt

    if not cwr and new_batch:
        rate = min(line_rate, rate + dctcp_rate_ai)
```

Congestion point plus feedback reflection:

```text
on switch_dequeue(packet, output_port, priority_group):
    q = egress_bytes[output_port][priority_group]

    if q > kmax:
        mark_packet_ecn_ce(packet)
    else if q > kmin:
        p = pmax * (q - kmin) / (kmax - kmin)
        if random() < p:
            mark_packet_ecn_ce(packet)

on receiver_data_packet(packet):
    if packet.ecn_ce:
        ack.set_cnp_flag()
    send_ack(ack)
```

For the paper configs, DCTCP usually uses step marking: `kmin == kmax` and `pmax == 1.0`.

### HPCC-PINT Pseudocode, `cc_mode = 10`

Sender:

```text
on queue_pair_create:
    rate = line_rate
    pint_current_rate = line_rate
    increase_stage = 0

on ack_received(ack):
    if random_sample_rejects_ack(pint_prob):
        return

    if first_pint_feedback:
        last_update_seq = snd_nxt
        return

    if ack.seq advanced beyond last_update_seq:
        full_update = true
    else:
        full_update = false

    U = decode_pint_utilization(ack.pint_power)
    c = U / target_util

    if c >= 1 or increase_stage >= mi_thresh:
        new_rate = pint_current_rate / c + rate_ai
        new_stage = 0
    else:
        new_rate = pint_current_rate + rate_ai
        new_stage = increase_stage + 1

    new_rate = clamp(new_rate, min_rate, line_rate)
    change_pacing_rate(new_rate)

    if full_update:
        pint_current_rate = new_rate
        increase_stage = new_stage
        last_update_seq = snd_nxt
```

Congestion point:

```text
on switch_dequeue(packet, output_port):
    if packet is RDMA data and IntHeader.mode == PINT:
        dt = now - last_packet_time[output_port]
        dt = min(dt, max_rtt)

        B = output_link_rate_bytes_per_second(output_port)
        q = output_queue_total_bytes(output_port)

        queue_term = approximate(dt * q / (B * max_rtt^2))
        byte_term = approximate(last_packet_size / (B * max_rtt))
        old_util_term = approximate((max_rtt - dt) * old_util / max_rtt)

        new_util = queue_term + byte_term + old_util_term
        encoded = pint_encode(new_util)

        packet.pint_power = max(packet.pint_power, encoded)
        old_util[output_port] = new_util

    last_packet_size[output_port] = packet.size
    last_packet_time[output_port] = now

on receiver_data_packet(packet):
    ack.pint_power = packet.pint_power
    send_ack(ack)
```

HPCC-PINT is HPCC-like at the sender, but the congestion point compresses path utilization into one probabilistic encoded field instead of appending full per-hop records.

## DCQCN, `cc_mode = 1`

Sender-side algorithm:

1. A QP starts at NIC line rate and initializes `qp->mlx.m_targetRate` to line rate in `RdmaHw::AddQueuePair()` (`src/point-to-point/model/rdma-hw.cc:260-266`).
2. On an ACK with the CNP flag, `ReceiveAck()` calls `cnp_received_mlx()` (`src/point-to-point/model/rdma-hw.cc:471-475`).
3. `cnp_received_mlx()` marks that CNP arrived. On the first CNP it sets alpha to 1, schedules alpha update, schedules rate-decrease checking, applies `RateOnFirstCnp`, and clears the first-CNP flag (`src/point-to-point/model/rdma-hw.cc:711-725`).
4. `UpdateAlphaMlx()` periodically updates alpha with binary EWMA:
   - if CNP arrived: `alpha = (1 - g) * alpha + g`
   - otherwise: `alpha = (1 - g) * alpha`
   (`src/point-to-point/model/rdma-hw.cc:691-708`)
5. `CheckRateDecreaseMlx()` periodically reduces the sending rate when CNP arrived:
   - optionally clamps target rate to current rate
   - `rate = max(minRate, rate * (1 - alpha / 2))`
   - resets increase-stage state
   (`src/point-to-point/model/rdma-hw.cc:728-753`)
6. `RateIncEventMlx()` increases after recovery using fast recovery, active increase, then hyper increase:
   - fast recovery moves current rate halfway toward target
   - active increase adds `RateAI` to target
   - hyper increase adds `RateHAI` to target
   (`src/point-to-point/model/rdma-hw.cc:756-812`)

Congestion-point algorithm:

1. The switch tracks egress bytes per port and queue in `SwitchMmu`.
2. `ShouldSendCN()` returns true when queue is above `kmax`, or probabilistically between `kmin` and `kmax` (`src/point-to-point/model/switch-mmu.cc:99-109`).
3. `SwitchNotifyDequeue()` marks the IPv4 ECN field as CE when `ShouldSendCN()` is true (`src/point-to-point/model/switch-node.cc:207-217`).
4. The receiver sees CE bits in `ReceiveUdp()` and sets the ACK CNP flag (`src/point-to-point/model/rdma-hw.cc:350-367`).

So, in this codebase, DCQCN's active congestion signal is switch ECN marking reflected by the receiver in ACKs, not a standalone switch-generated CNP packet.

## HPCC, `cc_mode = 3`

Sender-side algorithm:

1. A QP starts at line rate and initializes `qp->hp.m_curRate`; if `MultiRate` is enabled, each hop's `Rc` is initialized to line rate (`src/point-to-point/model/rdma-hw.cc:266-271`).
2. On ACK, `HandleAckHp()` performs a full RTT update if ACK sequence advanced past `m_lastUpdateSeq`; otherwise it may run fast react (`src/point-to-point/model/rdma-hw.cc:817-825`).
3. On the first RTT, HPCC stores the INT hop records as the baseline (`src/point-to-point/model/rdma-hw.cc:827-845`).
4. On later ACKs, `UpdateRateHp()` compares new and old INT records per hop:
   - `txRate = bytes_delta * 8 / time_delta`
   - `u = txRate / lineRate + min(newQlen, oldQlen) * maxRate / lineRate / window`
   - utilization is smoothed over `baseRtt`
   (`src/point-to-point/model/rdma-hw.cc:846-890`)
5. With single-rate HPCC, it computes `max_c = u / targetUtil`:
   - if `max_c >= 1` or additive-increase stage exceeds `MiThresh`: `newRate = curRate * (1 / max_c) + RateAI`
   - otherwise: `newRate = curRate + RateAI`
   - rate is bounded to `[MinRate, maxRate]`
   (`src/point-to-point/model/rdma-hw.cc:897-924`)
6. With `MultiRate`, the same formula is applied per hop and the sender takes the minimum resulting rate (`src/point-to-point/model/rdma-hw.cc:925-958`).
7. `ChangeRate()` applies the new paced rate. During fast react, the instantaneous rate can change without committing `m_curRate` and inc-stage state (`src/point-to-point/model/rdma-hw.cc:963-990`).

Congestion-point algorithm:

1. `hpcc-validation.cc` sets `IntHeader::mode = IntHeader::NORMAL` for `cc_mode == 3` (`examples/hpcc/hpcc-validation.cc:774-784`).
2. On every switch dequeue, `SwitchNotifyDequeue()` pushes a hop record into the packet:
   - current simulation time
   - transmitted bytes counter for the output port
   - total bytes in the output queue
   - output link data rate
   (`src/point-to-point/model/switch-node.cc:222-229`)
3. `IntHeader::PushHop()` appends the hop only in `NORMAL` mode (`src/network/utils/int-header.cc:28-35`).
4. The receiver copies the data packet INT header into the ACK (`src/point-to-point/model/rdma-hw.cc:359-365`).

ECN may still be enabled at the switch, but the HPCC sender handler does not use the ACK CNP flag for rate control. HPCC's real congestion-point signal here is INT.

## TIMELY, `cc_mode = 7`

Sender-side algorithm:

1. `hpcc-validation.cc` sets `IntHeader::mode = IntHeader::TS` for TIMELY (`examples/hpcc/hpcc-validation.cc:774-784`).
2. `SeqTsHeader` stamps `ih.ts = Simulator::Now()` when the packet is created in TS mode (`src/point-to-point/model/seq-ts-header.cc:33-38`).
3. The receiver copies that timestamp into the ACK through `qbbHeader::SetIntHeader()` (`src/point-to-point/model/rdma-hw.cc:359-365`).
4. `HandleAckTimely()` runs a full update once per RTT-equivalent sequence advance (`src/point-to-point/model/rdma-hw.cc:996-1004`).
5. `UpdateRateTimely()` computes:
   - `rtt = now - ack_timestamp`
   - EWMA RTT difference
   - gradient = RTT difference / `TimelyMinRtt`
   (`src/point-to-point/model/rdma-hw.cc:1005-1018`)
6. Rate rule:
   - if `rtt < TLow` or gradient is non-positive: increase by `RateAI`, then by `RateHAI` after enough increase stages
   - if `rtt > THigh`: decrease by `1 - beta * (1 - THigh / rtt)`
   - otherwise, for positive gradient: decrease by `1 - beta * gradient`
   - rate is bounded by `MinRate` and max NIC rate
   (`src/point-to-point/model/rdma-hw.cc:1019-1064`)

Congestion-point algorithm:

TIMELY does not need switch ECN or INT queue telemetry in this implementation. The switch forwards the timestamped packet unchanged for TIMELY. The measured RTT is the congestion signal. `FastReactTimely()` is currently empty (`src/point-to-point/model/rdma-hw.cc:1065-1066`).

If `enable_qcn` is true, switches can still mark ECN, and the receiver can still set ACK CNP flags, but `HandleAckTimely()` ignores that flag.

## DCTCP, `cc_mode = 8`

Sender-side algorithm:

1. DCTCP sender state lives in `qp->dctcp`: `m_alpha`, ECN count, congestion-avoidance state, high sequence, and batch size (`src/point-to-point/model/rdma-queue-pair.h:69-76`).
2. On each ACK, `HandleAckDctcp()` checks the ACK CNP flag and increments the ECN count if marked (`src/point-to-point/model/rdma-hw.cc:1071-1078`).
3. When ACK sequence advances past `m_lastUpdateSeq`, it updates alpha once per batch:
   - `frac = ecnCnt / batchSize`
   - `alpha = (1 - g) * alpha + g * frac`
   - reset ECN count and define the next batch
   (`src/point-to-point/model/rdma-hw.cc:1078-1099`)
4. If marked and not already in congestion-window-reduction state, reduce:
   - `rate = max(minRate, rate * (1 - alpha / 2))`
   - enter CWR until ACK passes `m_highSeq`
   (`src/point-to-point/model/rdma-hw.cc:1101-1118`)
5. If not in CWR and a new batch completed, add `DctcpRateAI` (`src/point-to-point/model/rdma-hw.cc:1120-1122`).

Congestion-point algorithm:

DCTCP uses the same switch ECN and receiver-reflected ACK CNP path as DCQCN:

- ECN marking threshold and probability are in `SwitchMmu::ShouldSendCN()` (`src/point-to-point/model/switch-mmu.cc:99-109`).
- ECN CE is written at switch dequeue (`src/point-to-point/model/switch-node.cc:207-217`).
- Receiver sets ACK CNP flag if ECN CE bits were seen (`src/point-to-point/model/rdma-hw.cc:350-367`).

The DCTCP configs typically use different `kmin`, `kmax`, and `pmax` maps than HPCC/DCQCN/TIMELY. In `examples/hpcc/paper-simulations/gen_configs.py`, DCTCP uses step-style marking with `kmin == kmax` and `pmax == 1.0`.

## HPCC-PINT, `cc_mode = 10`

Sender-side algorithm:

1. `hpcc-validation.cc` sets `IntHeader::mode = IntHeader::PINT`, configures log base, and computes compact PINT header bytes (`examples/hpcc/hpcc-validation.cc:774-790`).
2. `RdmaHw::SetPintSmplThresh()` converts `pint_prob` into a sampling threshold (`src/point-to-point/model/rdma-hw.cc:1128-1130`).
3. `HandleAckHpPint()` randomly samples ACKs; unsampled ACKs do not update rate (`src/point-to-point/model/rdma-hw.cc:1131-1140`).
4. `UpdateRateHpPint()` decodes utilization from the compact field:
   - `U = Pint::decode_u(ih.GetPower())`
   - `max_c = U / targetUtil`
   (`src/point-to-point/model/rdma-hw.cc:1143-1155`)
5. Rate rule is the HPCC aggregate formula:
   - if `max_c >= 1` or inc-stage exceeds `MiThresh`: `newRate = curRate * (1 / max_c) + RateAI`
   - otherwise: `newRate = curRate + RateAI`
   - rate is bounded to `[MinRate, maxRate]`
   (`src/point-to-point/model/rdma-hw.cc:1156-1176`)

Congestion-point algorithm:

1. `SwitchNotifyDequeue()` handles `cc_mode == 10` separately (`src/point-to-point/model/switch-node.cc:229-303`).
2. Per output port, the switch estimates utilization using:
   - time since previous packet on that port
   - output link rate
   - current output queue length
   - previous packet size
   - previous utilization estimate
3. The implementation uses a log-approximation path for compact hardware-like arithmetic (`src/point-to-point/model/switch-node.cc:238-277`).
4. The switch encodes the utilization as PINT power and keeps the maximum value already seen in the packet (`src/point-to-point/model/switch-node.cc:295-302`).
5. `Pint::encode_u()` and `Pint::decode_u()` define the stochastic log-base representation (`src/point-to-point/model/pint.cc:12-42`).

Unlike full HPCC, HPCC-PINT does not carry all per-hop records. It carries one compact encoded utilization field.

## Quick Code Navigation

| Concern | Main implementation |
|---|---|
| Config parsing | `examples/hpcc/hpcc-config.cc`, `examples/hpcc/hpcc-config.h` |
| Simulation wiring | `examples/hpcc/hpcc-validation.cc` |
| Sender state and rate algorithms | `src/point-to-point/model/rdma-hw.cc`, `src/point-to-point/model/rdma-queue-pair.h` |
| RDMA QP scheduling and pacing gate | `src/point-to-point/model/qbb-net-device.cc`, `src/point-to-point/model/rdma-queue-pair.cc` |
| Receiver ACK/NACK/CNP-flag generation | `src/point-to-point/model/rdma-hw.cc:321-386` |
| Switch routing/admission/ECN/INT/PINT | `src/point-to-point/model/switch-node.cc` |
| PFC and ECN thresholds | `src/point-to-point/model/switch-mmu.cc`, `src/point-to-point/model/switch-mmu.h` |
| INT serialization | `src/network/utils/int-header.cc`, `src/network/utils/int-header.h` |
| PINT encoding | `src/point-to-point/model/pint.cc`, `src/point-to-point/model/pint.h` |
| Legacy standalone CNP packet format | `src/point-to-point/model/cn-header.cc`, `src/point-to-point/model/cn-header.h` |

## Sanity Checks When Modifying Algorithms

- If changing DCQCN or DCTCP, verify ECN-to-ACK-CNP propagation by checking that switch queues cross `kmin/kmax` and that ACKs reach `ReceiveAck()` with `FLAG_CNP`.
- If changing HPCC, verify `IntHeader::mode == NORMAL`, switch `CcMode == 3`, and ACKs carry updated hop records.
- If changing TIMELY, verify the timestamp is nonzero in TS mode and ACK RTT is calculated from `ch.ack.ih.ts`.
- If changing HPCC-PINT, verify PINT bytes/log base, sampled ACK probability, and encoded power updates at switches.
- For all modes, verify PFC pause/resume balance separately from rate-control correctness.
