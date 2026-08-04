#!/usr/bin/env python3
"""The clean placement-isolation experiment (round-2 review, MC2).

The reviewer's control: deliver the EXACT same per-link observation sequence
(y, q, dt) to every controller at identical logical update instants, so the
only remaining difference is WHERE the recursion state lives -- one shared
register (switch) vs one private register per sender. No ns-3, no sampling
asymmetry, no RTT heterogeneity: a deterministic fluid model of one link.

Model: link capacity C; fluid queue q' = max(0, y - C); every controller
updates at the same instants t = k*d with the same observed (y, q) and the
identical RCP rule  R <- R * (1 + (a*(C - y) - b*q/d)/C), clamped [1 Mbps, C].
Flows transmit at their controller's R. Flow 1 starts at t = 0; flow 2
arrives at t = T_arr. Private controllers initialise R = C/2 on arrival
(exactly as the switch register initialises once).

  shared      one register; every flow adopts its current value
              (a late arrival INHERITS the evolved state)
  private-syn both flows present from t = 0, same R0, same observations
              -> identical trajectories (information is sufficient)
  private-arr flow 2 arrives at T_arr with fresh R0 while flow 1 holds
              evolved state; both see IDENTICAL observations afterwards
              -> the ratio R1/R2 at arrival is frozen forever

Run:  python3 examples/hpcc/hpcc-fs/run_consistency.py
"""

C = 25e9
ALPHA, BETA = 0.4, 0.226
D = 20e-6                # control interval (s), same for every controller
DT = 1e-6                # fluid integration step
T_END = 0.030
T_ARR = 0.005
R0 = C / 2
RMIN = 1e6


def clamp(r):
    return max(RMIN, min(C, r))


def rcp_step(R, y, q):
    return clamp(R * (1.0 + (ALPHA * (C - y) - BETA * q / D) / C))


def simulate(mode):
    """Returns (rate1, rate2, ratio) at t = T_END."""
    q = 0.0
    Rs = R0                     # shared register
    R1 = R0                     # private registers
    R2 = None                   # flow 2 not yet arrived
    next_upd = D
    t = 0.0
    while t < T_END:
        f2 = t >= T_ARR
        if mode == "shared":
            r1, r2 = Rs, (Rs if f2 else 0.0)
        else:
            if f2 and R2 is None:
                R2 = R0          # newcomer initialises fresh -- it cannot
                                 # have observed the past
            r1, r2 = R1, (R2 if f2 else 0.0)
        y = r1 + r2
        q = max(0.0, q + (y - C) * DT)
        t += DT
        if t >= next_upd:
            # every controller sees the SAME (y, q) at the SAME instant
            if mode == "shared":
                Rs = rcp_step(Rs, y, q)
            else:
                R1 = rcp_step(R1, y, q)
                if R2 is not None:
                    R2 = rcp_step(R2, y, q)
            next_upd += D
    return r1, r2, (r1 / r2 if r2 else float("inf"))


def main():
    print("One link, identical observations (y,q) at identical update instants,")
    print("identical RCP law and gains. Only the STATE placement differs.")
    print(f"{'variant':<14} {'flow1 Gbps':>11} {'flow2 Gbps':>11} {'ratio':>8}")
    for mode, lab in (("shared", "shared R"), ("private", "private R")):
        # synchronized-arrival control for private
        pass
    # shared register, staggered arrival
    r1, r2, k = simulate("shared")
    print(f"{'shared, stag':<14} {r1/1e9:>11.2f} {r2/1e9:>11.2f} {k:>7.2f}x")
    # private registers, synchronized (both t=0): emulate by T_ARR=0
    global T_ARR
    hold = T_ARR
    T_ARR = 0.0
    r1, r2, k = simulate("private")
    print(f"{'private, sync':<14} {r1/1e9:>11.2f} {r2/1e9:>11.2f} {k:>7.2f}x")
    T_ARR = hold
    # private registers, staggered arrival — the decisive case
    r1, r2, k = simulate("private")
    print(f"{'private, stag':<14} {r1/1e9:>11.2f} {r2/1e9:>11.2f} {k:>7.2f}x")


if __name__ == "__main__":
    main()
