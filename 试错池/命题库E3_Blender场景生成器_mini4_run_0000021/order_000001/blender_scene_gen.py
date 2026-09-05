#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_scene_gen.py
Blender 场景生成脚本（在 Blender 内运行）：
    blender --background --python blender_scene_gen.py -- --风格=北欧 --输出目录=./test_render
接受 --风格 和 --输出目录 参数，读取 style_mapping.json，按风格参数创建
相机/主光/环境光/材质/产品占位几何体，并渲染 3 张图到输出目录，控制台输出'完成'。
"""

import argparse
import json
import math
import os
import sys

# 本文件既可在普通 python 跑（导入自检），也可在 blender --python 下跑
try:
    import bpy  # type: ignore
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    bpy = None


# ----------------------------- 参数范围（摄影理论） -----------------------------
LIGHT_MIN = 75
LIGHT_MAX = 150
KELVIN_MIN = 2700
KELVIN_MAX = 6500
FOV_DEFAULT = 35
CAM_H_DEFAULT = 1.5
MAIN_LIGHT_ENERGY = 700   # 摄影棚主光范围 500-1000W，取中间
MAIN_LIGHT_KELVIN = 5500  # 中性日光 4000-6500K，取中间
ENV_RATIO_DEFAULT = 0.2   # 环境光/补光约主光 20%


def parse_args():
    """解析 blender --python 后的 -- 之后参数。支持 --风格=北欧 与 --风格 北欧 两种写法。"""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parsed = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            if "=" in a:
                k, v = a[2:].split("=", 1)
                parsed[k] = v
                i += 1
            else:
                k = a[2:]
                if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                    parsed[k] = argv[i + 1]
                    i += 2
                else:
                    parsed[k] = True
                    i += 1
        else:
            i += 1

    style = parsed.get("风格", parsed.get("style", "北欧"))
    out_dir = parsed.get("输出目录", parsed.get("out", "./test_render"))
    return style, out_dir


def clamp(v, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return float(lo)
    return max(float(lo), min(float(hi), v))


def load_style_params(style):
    """从 style_mapping.json 读取并修正参数；缺失则用 _fallback 或内置默认。"""
    mapping_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style_mapping.json")
    if not os.path.exists(mapping_path):
        print("[WARN] 找不到 style_mapping.json，使用内置默认参数")
        return default_params(style), True
    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
    except Exception as e:
        print("[WARN] 读取 style_mapping.json 失败: %s，使用默认参数" % e)
        return default_params(style), True

    if style not in mapping:
        print("[WARN] 风格 '%s' 不在映射表中，使用 _fallback" % style)
        params = mapping.get("_fallback", default_params(style))
    else:
        params = mapping[style]

    light = dict(params.get("光照", {}))
    mat = dict(params.get("材质", {}))
    comp = dict(params.get("构图", {}))

    light["主光强度"] = clamp(light.get("主光强度", MAIN_LIGHT_ENERGY), LIGHT_MIN, LIGHT_MAX)
    light["色温"] = clamp(light.get("色温", MAIN_LIGHT_KELVIN), KELVIN_MIN, KELVIN_MAX)
    light["环境光强度"] = clamp(light.get("环境光强度", ENV_RATIO_DEFAULT), 0.0, 1.0)
    mat["反射度"] = clamp(mat.get("反射度", 0.5), 0.0, 1.0)
    mat["粗糙度"] = clamp(mat.get("粗糙度", 0.5), 0.0, 1.0)
    comp.setdefault("相机高度", CAM_H_DEFAULT)
    comp.setdefault("目标高度", 0.8)
    comp.setdefault("视角", FOV_DEFAULT)
    comp["相机高度"] = clamp(comp["相机高度"], 0.3, 3.0)
    comp["目标高度"] = clamp(comp["目标高度"], 0.0, 3.0)
    comp["视角"] = clamp(comp["视角"], 15.0, 90.0)

    return {"光照": light, "材质": mat, "构图": comp}, False


def default_params(style):
    return {
        "光照": {"主光强度": 100, "色温": 5000, "环境光强度": 0.4},
        "材质": {"反射度": 0.5, "粗糙度": 0.5, "主色": "#A0A0A0", "材质类型": "通用"},
        "构图": {"相机高度": 1.2, "目标高度": 0.8, "视角": 35},
    }


def kelvin_to_rgb(k):
    k = max(1000, min(40000, float(k)))
    temp = k / 100.0
    if temp <= 66:
        r = 255
        if temp > 0:
            g = 99.4708025861 * math.log(temp) - 161.1195681661
            g = max(0, g)
        else:
            g = 0
        if temp <= 19:
            b = 0
        else:
            b = 138.5177312231 * math.log(temp - 10) - 305.0447927307
            b = max(0, b)
    else:
        r = 329.698727446 * ((temp - 60) ** -0.1332047592)
        g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
        b = 255
    return (min(1.0, r / 255.0), min(1.0, g / 255.0), min(1.0, b / 255.0))


def hex_to_rgb(hx):
    if isinstance(hx, str) and len(hx) == 7 and hx.startswith("#"):
        return (int(hx[1:3], 16) / 255.0, int(hx[3:5], 16) / 255.0, int(hx[5:7], 16) / 255.0)
    return (0.6, 0.6, 0.6)


def apply_material(obj, params, style_name):
    """为物体设置风格化材质：北欧=哑光浅木色、日式=淡雅原木、奢华=高光泽金属。"""
    mat_type = params.get("材质类型", "通用")
    base = hex_to_rgb(params.get("主色", "#A0A0A0"))
    rough = float(params.get("粗糙度", 0.5))
    reflect = float(params.get("反射度", 0.5))

    if mat_type == "哑光浅木" or style_name == "北欧":
        rough = max(rough, 0.55)
        reflect = min(reflect, 0.25)
        metallic = 0.0
    elif mat_type == "淡雅原木" or style_name == "日式":
        rough = max(rough, 0.5)
        reflect = min(reflect, 0.3)
        metallic = 0.0
    elif mat_type == "高光泽金属" or style_name == "奢华":
        rough = min(rough, 0.2)
        reflect = max(reflect, 0.7)
        metallic = 1.0
    else:
        metallic = reflect

    mat = bpy.data.materials.new(name="Mat_%s" % style_name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
        if "Specular" in bsdf.inputs:
            bsdf.inputs["Specular"].default_value = 0.5 + reflect * 0.4
    obj.data.materials.append(mat)


def clear_scene():
    """清除默认场景所有物体。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_camera(params):
    """创建相机：高度 1.5m（人眼视角 1.2-1.8m 取中），视角 35 度（产品摄影 25-45 取中）。"""
    cam_h = float(params["构图"]["相机高度"])
    target_h = float(params["构图"]["目标高度"])
    fov_deg = float(params["构图"]["视角"])

    bpy.ops.object.camera_add(location=(3.5, -3.5, cam_h))
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    cam.data.lens_unit = "FOV"
    cam.data.angle = fov_deg * math.pi / 180.0

    bpy.ops.object.empty_add(location=(0, 0, target_h))
    tgt = bpy.context.active_object
    tgt.name = "CamTarget"
    con = cam.constraints.new(type="TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    return cam


def setup_lights(params):
    """创建主光源（区域光 700W/5500K）+ 环境光（世界环境，主光 20%）。"""
    main_w = float(params["光照"]["主光强度"])
    kelvin = float(params["光照"]["色温"])
    env_ratio = float(params["光照"]["环境光强度"])
    r, g, b = kelvin_to_rgb(kelvin)

    bpy.ops.object.light_add(type="AREA", location=(0, -3, 2.5))
    main_light = bpy.context.active_object
    main_light.data.energy = main_w
    main_light.data.size = 2.0
    main_light.data.color = (r, g, b)

    bpy.ops.object.light_add(type="POINT", location=(2, 2, 1.5))
    fill = bpy.context.active_object
    fill.data.energy = main_w * env_ratio * 2.0
    fill.data.color = (r, g, b)

    world = bpy.context.scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new(type="ShaderNodeBackground")
    bg.inputs["Color"].default_value = (r, g, b, 1.0)
    bg.inputs["Strength"].default_value = env_ratio


def setup_geometry(params, style_name):
    """创建简单几何体占位（立方体+地面）。"""
    target_h = float(params["构图"]["目标高度"])

    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    apply_material(floor, {"反射度": 0.15, "粗糙度": 0.85, "主色": "#E8E0D4", "材质类型": "哑光"}, style_name + "_floor")

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, target_h))
    prod = bpy.context.active_object
    prod.name = "ProductCube"
    apply_material(prod, params["材质"], style_name)

    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(1.2, 0, target_h - 0.3))
    p2 = bpy.context.active_object
    p2.name = "ProductCube2"
    apply_material(p2, params["材质"], style_name + "_b")

    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(-1.2, 0, target_h - 0.3))
    p3 = bpy.context.active_object
    p3.name = "ProductCube3"
    apply_material(p3, params["材质"], style_name + "_c")


def setup_render(out_dir, name_prefix):
    """渲染参数：分辨率 1920x1080，采样 128。"""
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.samples = 128
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.render.image_settings.file_format = "PNG"


def render_three_views(out_dir, style_name):
    """绕产品渲染 3 张图（不同机位，模拟三分法）。"""
    os.makedirs(out_dir, exist_ok=True)
    cam = bpy.context.scene.camera

    # 三分法：相机绕目标点三个角度
    views = [
        (3.5, -3.5, "view1"),
        (0.0, -4.5, "view2"),
        (-3.5, -3.5, "view3"),
    ]
    for (x, y, tag) in views:
        cam.location = (x, y, float(cam.location.z))
        path = os.path.join(out_dir, "%s_%s_%s.png" % (style_name, tag, os.path.basename(out_dir.rstrip('/').rstrip('\\')) or "render"))
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("[OK] 渲染: %s" % path)


def main_in_blender():
    """在 Blender 进程内执行的主流程。"""
    if not HAS_BPY:
        print("[ERROR] 该函数仅在 Blender 内运行；请使用 blender --python blender_scene_gen.py -- --风格=...")
        return False

    style, out_dir = parse_args()
    params, used_fallback = load_style_params(style)
    print("[INFO] 风格: %s, 输出目录: %s" % (style, out_dir))
    print("[INFO] 光照=%s 材质=%s 构图=%s" % (params["光照"], params["材质"], params["构图"]))

    os.makedirs(out_dir, exist_ok=True)

    clear_scene()
    setup_camera(params)
    setup_lights(params)
    setup_geometry(params, style)
    setup_render(out_dir, style)
    render_three_views(out_dir, style)

    print("完成")
    return True


if __name__ == "__main__":
    if HAS_BPY:
        main_in_blender()
    else:
        # 在普通 python 环境下：仅自检参数解析与映射加载
        print("[INFO] 未检测到 bpy 模块；运行参数自检模式。")
        style, out_dir = parse_args()
        params, _ = load_style_params(style)
        print("[OK] 解析成功: style=%s out=%s" % (style, out_dir))
        print("[OK] 参数: %s" % json.dumps(params, ensure_ascii=False))
        print("完成")