#!/usr/bin/env python3
"""Quadruped gait simulation using MuJoCo.

Reads gait_params.json, runs parameterized gait simulations,
writes result.json and trajectory.csv.
Supports --quick mode for fast self-check (< 60s).
"""
import argparse
import json
import math
import os
import sys
import time
import csv

import mujoco


def load_params(path="gait_params.json"):
    with open(path, "r") as f:
        return json.load(f)


def gait_signal(t, freq_hz, stance_ratio, amplitude, phase_offset, joint_id):
    omega = 2.0 * math.pi * freq_hz
    phase = omega * t + phase_offset * joint_id * math.pi
    cycle_pos = (phase % (2.0 * math.pi)) / (2.0 * math.pi)
    if cycle_pos < stance_ratio:
        local = cycle_pos / max(stance_ratio, 1e-6)
        angle = -amplitude * math.sin(local * math.pi)
    else:
        local = (cycle_pos - stance_ratio) / max(1.0 - stance_ratio, 1e-6)
        angle = amplitude * math.sin(local * math.pi)
    return angle


def run_single_trial(model_path, params):
    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)
    model.opt.gravity[2] = -9.81
    mujoco.mj_resetData(model, data)
    data.qpos[0] = 0.0
    data.qpos[1] = 0.0
    data.qpos[2] = 0.25
    data.qvel[:] = 0.0

    freq_hz = params["freq_hz"]
    stance_ratio = params["stance_ratio"]
    amplitude = params["amplitude"]
    phase_offset = params.get("phase_offset", 0.5)
    push_force = params.get("push_disturbance", 0.0)

    duration = params.get("_duration_sec", 4.0)
    dt = model.opt.timestep
    disturb_step = params.get("_disturb_step", 1.5)
    n_steps = int(duration / dt)
    disturb_step_idx = int(disturb_step / dt)

    fl_act_id = -1
    fr_act_id = -1
    for i in range(model.nu):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        if name == "fl_motor":
            fl_act_id = i
        elif name == "fr_motor":
            fr_act_id = i

    trajectory = []
    fell = False
    fall_step = -1
    max_tilt = 0.0

    for step in range(n_steps):
        t = step * dt
        if fl_act_id >= 0:
            target_fl = gait_signal(t, freq_hz, stance_ratio, amplitude, phase_offset, 0)
            data.ctrl[fl_act_id] = target_fl * 2.5
        if fr_act_id >= 0:
            target_fr = gait_signal(t, freq_hz, stance_ratio, amplitude, phase_offset, 1)
            data.ctrl[fr_act_id] = target_fr * 2.5

        if step == disturb_step_idx and push_force > 0:
            data.xfrc_applied[1, 1] = push_force

        mujoco.mj_step(model, data)

        torso_pos = data.xpos[1]
        torso_quat = data.xquat[1]
        tilt = 2.0 * math.sqrt(torso_quat[1] ** 2 + torso_quat[2] ** 2)
        if tilt > max_tilt:
            max_tilt = tilt
        height = torso_pos[2]
        if height < 0.08 or tilt > 0.8:
            if not fell:
                fell = True
                fall_step = step

        trajectory.append({
            "time": float(t),
            "x": float(data.qpos[0]),
            "y": float(data.qpos[1]),
            "z": float(data.qpos[2]),
            "vx": float(data.qvel[0]),
            "tilt": float(tilt),
        })

    final_x = float(data.qpos[0])
    final_y = float(data.qpos[1])
    distance = math.sqrt(final_x ** 2 + final_y ** 2)
    recovered = (not fell) and max_tilt < 0.8

    return {
        "distance": float(distance),
        "fell": bool(fell),
        "fall_step": int(fall_step),
        "max_tilt": float(max_tilt),
        "recovered": bool(recovered),
        "trajectory": trajectory,
        "final_x": final_x,
        "final_y": final_y,
    }


def make_trial_configs(params, quick=True):
    scan = params["scan"]
    default = params["default"]
    sim_cfg = params["simulation"]
    duration = sim_cfg.get("duration_sec", 4.0)
    disturb_step = sim_cfg.get("disturb_step", 1.5)
    trial_configs = []
    if quick:
        trial_configs.append(dict(default))
        trial_configs.append({**default, "freq_hz": scan["freq_hz"][0]})
        trial_configs.append({**default, "freq_hz": scan["freq_hz"][-1]})
        trial_configs.append({**default, "stance_ratio": scan["stance_ratio"][0]})
        trial_configs.append({**default, "stance_ratio": scan["stance_ratio"][-1]})
        trial_configs.append({**default, "amplitude": scan["amplitude"][0]})
        trial_configs.append({**default, "amplitude": scan["amplitude"][-1]})
        trial_configs.append({**default, "push_disturbance": 0.0})
    else:
        for freq in scan["freq_hz"]:
            for sr in scan["stance_ratio"]:
                trial_configs.append({**default, "freq_hz": freq, "stance_ratio": sr})
        for push in scan["push_disturbance"]:
            trial_configs.append({**default, "push_disturbance": push})
    for cfg in trial_configs:
        cfg["_duration_sec"] = duration
        cfg["_disturb_step"] = disturb_step
    return trial_configs


def run_trials(model_path, trial_configs):
    results = []
    all_trajectories = []
    for i, cfg in enumerate(trial_configs):
        result = run_single_trial(model_path, cfg)
        result["trial_id"] = i
        result["params"] = {k: v for k, v in cfg.items() if not k.startswith("_")}
        results.append(result)
        for pt in result["trajectory"]:
            pt["trial"] = i
            all_trajectories.append(pt)
    return results, all_trajectories


def summarize(results):
    distances = [r["distance"] for r in results]
    falls = [1.0 if r["fell"] else 0.0 for r in results]
    recoveries = [1.0 if r["recovered"] else 0.0 for r in results]
    n = len(results)
    fall_rate = sum(falls) / n if n > 0 else 0.0
    recovery_rate = sum(recoveries) / n if n > 0 else 0.0
    avg_distance = sum(distances) / n if n > 0 else 0.0
    max_distance = max(distances) if distances else 0.0
    best = None
    for r in results:
        if not r["fell"]:
            if best is None or r["distance"] > best["distance"]:
                best = r
    first_fall = None
    for r in results:
        if r["fell"]:
            first_fall = r
            break
    return {
        "n_trials": n,
        "avg_distance": float(avg_distance),
        "max_distance": float(max_distance),
        "fall_rate": float(fall_rate),
        "recovery_rate": float(recovery_rate),
        "best_trial_id": best["trial_id"] if best else -1,
        "best_params": best["params"] if best else {},
        "first_fall_trial_id": first_fall["trial_id"] if first_fall else -1,
        "first_fall_params": first_fall["params"] if first_fall else {},
    }


def write_result_json(results, summary, path="result.json"):
    out_results = []
    for r in results:
        out_results.append({
            "trial_id": r["trial_id"],
            "params": r["params"],
            "distance": r["distance"],
            "fell": r["fell"],
            "fall_step": r["fall_step"],
            "max_tilt": r["max_tilt"],
            "recovered": r["recovered"],
            "final_x": r["final_x"],
            "final_y": r["final_y"],
        })
    payload = {
        "results": out_results,
        "summary": summary,
        "metric_description": {
            "distance": "Total horizontal displacement from origin (m)",
            "fell": "Whether robot tipped over (height<0.08 or tilt>0.8)",
            "fall_rate": "Fraction of trials where robot fell",
            "max_tilt": "Maximum body tilt angle during trial (rad)",
            "recovered": "Whether robot stayed upright after disturbance",
            "recovery_rate": "Fraction of trials with successful disturbance recovery",
        },
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_trajectory_csv(all_trajectories, path="trajectory.csv"):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial", "time", "x", "y", "z", "vx", "tilt"])
        writer.writeheader()
        for pt in all_trajectories:
            writer.writerow(pt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Quick mode (< 60s)")
    parser.add_argument("--model", default="model.xml", help="MJCF model path")
    parser.add_argument("--params", default="gait_params.json", help="Gait params path")
    parser.add_argument("--out_result", default="result.json", help="Output result path")
    parser.add_argument("--out_traj", default="trajectory.csv", help="Output trajectory path")
    args = parser.parse_args()

    params = load_params(args.params)
    trial_configs = make_trial_configs(params, quick=args.quick)

    print(f"[sim.py] running {len(trial_configs)} trials (quick={args.quick})", file=sys.stderr)
    t0 = time.time()
    results, all_trajectories = run_trials(args.model, trial_configs)
    summary = summarize(results)
    elapsed = time.time() - t0
    print(f"[sim.py] elapsed={elapsed:.2f}s", file=sys.stderr)

    write_result_json(results, summary, path=args.out_result)
    write_trajectory_csv(all_trajectories, path=args.out_traj)
    print(f"[sim.py] wrote {args.out_result} and {args.out_traj}", file=sys.stderr)
    print(f"[sim.py] summary: n={summary['n_trials']} avg_dist={summary['avg_distance']:.3f}m fall_rate={summary['fall_rate']:.2%}", file=sys.stderr)


if __name__ == "__main__":
    main()