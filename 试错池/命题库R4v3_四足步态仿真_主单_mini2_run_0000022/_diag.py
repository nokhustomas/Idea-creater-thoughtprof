import mujoco
import numpy as np

m = mujoco.MjModel.from_xml_path('model.xml')
d = mujoco.MjData(m)
mujoco.mj_forward(m, d)

fl_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, 'FL_foot')
torso_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'torso')
print('feet FL z (initial):', d.site_xpos[fl_id][2])
print('torso z (initial):', d.xpos[torso_id][2])

# Now run 3 seconds of constant zero control
for i in range(1500):
    mujoco.mj_step(m, d)
print('after 3s zero ctrl:')
print('  torso z:', d.xpos[torso_id][2])
print('  torso xpos:', d.xpos[torso_id])
print('  feet FL z:', d.site_xpos[fl_id][2])

# Now apply hip=-0.5 (leg back) for 1 second
hip_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, 'FL_hip')
act_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, 'FL_motor')
print('actuator count:', m.nu)
print('hip qposadr:', m.jnt_qposadr[hip_id])
print('initial hip qpos:', d.qpos[m.jnt_qposadr[hip_id]])
print('hip range:', m.jnt_range[hip_id])
print('motor gear:', m.actuator_gear[act_id])
print('motor ctrlrange:', m.actuator_ctrlrange[act_id])