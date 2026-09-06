#!/usr/bin/env python3
"""Quadruped trot-gait simulation with MuJoCo.

Implements a sinusoidal hip+knee drive controller (trot gait) inspired by
arXiv:1907.00456. Parameterised by step_frequency, step_length,
stance_ratio, body_height, swing_height. Measures walking distance, fall
rate and disturbance-recovery success across a sweep of parameter
combinations.

Usage:
    MUJOCO_GL=disable python sim.py [--quick]
"""

import argparse
import csv
import itertools
import json
import math
import os
import sys
import time

import mujoco

# ---------------------------------------------------------------------------
# Joint ordering (must match model.xml actuator order)
# ---------------------------------------------------------------------------
LEG_NAMES = ("FL", "FR", "RL", "RR")
JOINT_NAMES = {"FL": "FL_hip", "FR": "FR_hip", "RL": "RL_hip", "RR": "RR_hip"}
KNEE_NAMES = {"FL": "FL_knee", "FR": "FR_knee", "RL": "RL_knee", "RR": "RR_knee"}

# Trot pairing (arXiv:1907.00456): diagonal pairs share phase, opposite
# pairs differ by pi. We treat "diagonal A" as FL+RR (phase 0) and
# "diagonal B" as FR+RL (phase pi).
TROT_DIAGONAL_A = ("FL", "RR")
TROT_DIAGONAL_B = ("FR", "RL")

# Combined leg length (thigh + shank), matches model.xml (0.12 + 0.12 = 0.24
# when straight down). We use this when mapping step_length -> hip amplitude.
LEG_LENGTH = 0.24
THIGH_LENGTH = 0.12
SHANK_LENGTH = 0.12


def compute_leg_signals(t, params):
    """Return dict leg->(hip_angle, knee_angle) using sinusoidal drive.

    Hip amplitude is set so the foot tip sweeps an arc of length ~step_length
    on the ground. For a leg of length L hanging vertically from the hip,
    a hip angle theta moves the foot horizontally by approximately
    L*sin(theta). We choose amplitude = asin(step_length / (2*L)).

    Knee bends during swing (lift foot off ground) and stays extended during
    stance (push against ground). The duty factor is set by stance_ratio.
    """
    freq = params["step_frequency"]
    step_len = params["step_length"]
    stance = params["stance_ratio"]
    swing_h = params["swing_height"]
    leg_length = LEG_LENGTH

    raw_amp = step_len / (2.0 * leg_length)
    amp = max(0.0, min(raw_amp, 0.45))

    omega = 2.0 * math.pi * freq
    signals = {}
    # Swing fraction = 1 - stance_ratio (clamped to [0.05, 0.95]).
    swing_frac = max(0.05, min(0.95, 1.0 - stance))

    for leg in LEG_NAMES:
        phase = 0.0 if leg in TROT_DIAGONAL_A else math.pi
        s = math.sin(omega * t + phase)

        # Hip drive: positive sine -> swing backward, negative -> stance push.
        hip_angle = amp * s

        # Knee bend: bend during swing (when sin > 0), extend during stance.
        # Knee bend magnitude scales with swing_height (mapped through leg
        # length so swing_height=0.08 m gives a noticeable lift).
        knee_bend = 0.0
        if s > 0.0:
            # Lift proportional to swing_height, capped at ~1 rad so knee
            # range (-0.8..0.8) is respected.
            knee_bend = min(0.8, max(0.0, swing_h / max(THIGH_LENGTH, 1e-3)))

        signals[leg] = (hip_angle, knee_bend)
    return signals


def build_param_combinations(params_cfg):
    """Cartesian product across each parameter's min/max/step."""
    scan = params_cfg["scan_ranges"]
    grids = []
    keys = ("step_frequency", "step_length", "stance_ratio",
            "body_height", "swing_height")
    for k in keys:
        r = scan[k]
        vals = []
        v = r["min"]
        step = r["step"] if r["step"] > 0 else (r["max"] - r["min"])
        while v <= r["max"] + 1e-9:
            vals.append(round(v, 6))
            v += step
        grids.append((k, vals))

    combos = list(itertools.product(*[vals for _, vals in grids]))
    if len(combos) > 8:
        idxs = [round(i * (len(combos) - 1) / 7) for i in range(8)]
        combos = [combos[i] for i in idxs]
    elif len(combos) < 8:
        mean_combo = tuple(
            round(sum(vals) / len(vals), 6) for _, vals in grids
        )
        while len(combos) < 8:
            combos.append(mean_combo)
    out = []
    for combo in combos:
        d = {k: combo[i] for i, k in enumerate(keys)}
        out.append(d)
    return out


def simulate_once(model, data, params, sim_cfg, quick=False):
    """Run one simulation with given gait params. Return metrics + trajectory."""
    dt = sim_cfg["dt"]
    duration = sim_cfg["quick_duration_seconds"] if quick else sim_cfg["duration_seconds"]
    n_steps = int(round(duration / dt))

    mujoco.mj_resetData(model, data)
    # Place torso at body_height above ground (z = body_height).
    data.qpos[2] = params["body_height"]

    target_body_height = params["body_height"]

    # Actuator addresses (actuator order matches LEG_NAMES).
    hip_act_id = {leg: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR,
                                         leg + "_motor") for leg in LEG_NAMES}
    knee_act_id = {leg: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR,
                                          leg + "_knee_motor") for leg in LEG_NAMES}

    # Logging buffers
    traj_t = []
    traj_pos = []  # (x, y, z)
    traj_quat = []  # (qx, qy, qz, qw)

    fall_frames = 0
    fall_threshold = sim_cfg["fall_z_threshold"]
    fell_ever = False

    if quick:
        dist_time = sim_cfg.get("disturbance_quick_time", 10.0)
    else:
        dist_time = sim_cfg.get("disturbance_time", 30.0)
    dist_step_start = int(round(dist_time / dt))
    dist_step_end = int(round((dist_time + sim_cfg["disturbance_duration"]) / dt))

    recovery_end_step = int(round((dist_time + sim_cfg["disturbance_recovery_seconds"]) / dt))

    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso")

    sample_every = max(1, int(round(0.1 / dt)))

    for step in range(n_steps):
        t = step * dt

        # Compute desired hip+knee angles.
        signals = compute_leg_signals(t, params)
        for leg in LEG_NAMES:
            hip_a, knee_a = signals[leg]
            data.ctrl[hip_act_id[leg]] = hip_a * 10.0
            data.ctrl[knee_act_id[leg]] = knee_a * 10.0

        # Apply lateral disturbance pulse on the torso body.
        if dist_step_start <= step < dist_step_end:
            data.xfrc_applied[body_id, 1] = sim_cfg["disturbance_force"]

        mujoco.mj_step(model, data)

        if step % sample_every == 0:
            traj_t.append(t)
            traj_pos.append((float(data.qpos[0]), float(data.qpos[1]),
                             float(data.qpos[2])))
            traj_quat.append((float(data.qpos[3]), float(data.qpos[4]),
                              float(data.qpos[5]), float(data.qpos[6])))

        torso_z = float(data.qpos[2])
        if torso_z < fall_threshold:
            fall_frames += 1
            fell_ever = True

        if torso_z < -0.2:
            break

    if len(traj_pos) >= 2:
        x0, y0, _ = traj_pos[0]
        xN, yN, _ = traj_pos[-1]
        distance = math.sqrt((xN - x0) ** 2 + (yN - y0) ** 2)
    else:
        distance = 0.0

    fall_rate = fall_frames / max(1, n_steps)

    disturbance_success = False
    x_at_dist = None
    target_idx = int(round(dist_time / (sample_every * dt)))
    target_idx = max(0, min(target_idx, len(traj_t) - 1))
    if target_idx < len(traj_pos):
        x_at_dist = traj_pos[target_idx][0]

    recovery_target_step = recovery_end_step
    recovery_sample_idx = int(round(recovery_target_step / sample_every))
    recovery_sample_idx = max(0, min(recovery_sample_idx, len(traj_t) - 1))
    if recovery_sample_idx < len(traj_pos):
        post_x, post_y, post_z = traj_pos[recovery_sample_idx]
    else:
        post_x, post_y, post_z = traj_pos[-1]

    upright_after = post_z >= fall_threshold
    moved_forward = (x_at_dist is not None) and (post_x > (x_at_dist + 0.005))
    disturbance_success = bool(upright_after and moved_forward and not fell_ever)

    return {
        "distance": float(distance),
        "fall_rate": float(fall_rate),
        "disturbance_success": disturbance_success,
        "trajectory": {
            "time": traj_t,
            "pos": traj_pos,
            "quat": traj_quat,
        },
    }


def write_trajectory_csv(path, traj):
    """Write trajectory to trajectory.csv."""
    t_list = traj["time"]
    pos = traj["pos"]
    quat = traj["quat"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time(s)", "torso_x", "torso_y", "torso_z",
                    "torso_qx", "torso_qy", "torso_qz", "torso_qw"])
        for i in range(len(t_list)):
            x, y, z = pos[i]
            qx, qy, qz, qw = quat[i]
            w.writerow([f"{t_list[i]:.4f}", f"{x:.6f}", f"{y:.6f}",
                        f"{z:.6f}", f"{qx:.6f}", f"{qy:.6f}",
                        f"{qz:.6f}", f"{qw:.6f}"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="Run a shortened (~20s) sweep that finishes in <60s.")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(here, "model.xml")
    params_path = os.path.join(here, "gait_params.json")
    result_path = os.path.join(here, "result.json")
    traj_path = os.path.join(here, "trajectory.csv")

    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)

    with open(params_path) as f:
        params_cfg = json.load(f)
    sim_cfg = params_cfg["simulation"]

    combos = build_param_combinations(params_cfg)
    t_start = time.time()
    experiments = []
    best_traj = None
    best_dist = -1.0

    for i, pset in enumerate(combos):
        result = simulate_once(model, data, pset, sim_cfg, quick=args.quick)
        exp = {
            "param_set": pset,
            "distance": result["distance"],
            "fall_rate": result["fall_rate"],
            "disturbance_success": result["disturbance_success"],
        }
        experiments.append(exp)
        if result["distance"] >= best_dist:
            best_dist = result["distance"]
            best_traj = result["trajectory"]
        print(f"[{i + 1}/{len(combos)}] params={pset} -> "
              f"dist={result['distance']:.3f}m fall={result['fall_rate']:.3f} "
              f"recovery={result['disturbance_success']}",
              flush=True)

    with open(result_path, "w") as f:
        json.dump({"experiments": experiments,
                   "reference": sim_cfg.get("reference", "arXiv:1907.00456")},
                  f, indent=2)
    if best_traj is not None:
        write_trajectory_csv(traj_path, best_traj)

    print(f"Done in {time.time() - t_start:.1f}s; wrote {result_path} and "
          f"{traj_path}.", flush=True)


if __name__ == "__main__":
    main()