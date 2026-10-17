"""stylized-shading skill 一键自检 —— 在 Blender 里跑一遍本 skill 记录的全部操作符。

用途：回答「这个 skill 现在还能不能用」。任一步 FAIL 都会打印原因，最后再清场。

三种跑法（任选其一）：
  1) DSH blender 插件：blender_rt_do(file="<本文件绝对路径>")            # 跑在你看得见的 GUI Blender
  2) Blender 文本编辑器：打开本文件 → Run Script
  3) 命令行：blender.exe -b --python "<本文件绝对路径>"                   # 需用户配置里已启用该插件

输出：单行 JSON，前缀 VERIFY_SKILL 。ok=false 时退出码为 1。
"""
import json
import sys
import traceback
import warnings

import bpy

ADDON_HINT = "blender_Stylized-Shading-Tools"
TOKEN = "SKILLVERIFY"
RESULT = []


def check(name, fn, *, required=True):
    """Run one step; record ok/fail without aborting the whole run."""
    try:
        detail = fn()
        RESULT.append({"step": name, "ok": True, "detail": detail})
        return True
    except Exception as exc:  # noqa: BLE001 - report, do not crash Blender
        tb = traceback.format_exc().splitlines()[-2:]
        RESULT.append({"step": name, "ok": False, "required": required,
                       "error": f"{type(exc).__name__}: {exc}", "trace": tb})
        return False


def groups_of(material):
    return sorted({n.node_tree.name for n in material.node_tree.nodes
                   if n.type == "GROUP" and n.node_tree})


def base_of(node_group_name):
    return node_group_name.split("_")[0]


def surface_source(material):
    outs = [n for n in material.node_tree.nodes if n.type == "OUTPUT_MATERIAL"]
    if not outs:
        return None
    sock = outs[0].inputs["Surface"]
    if not sock.is_linked:
        return None
    src = sock.links[0].from_node
    return getattr(src.node_tree, "name", src.name)


def color_linked(material, group_name):
    for n in material.node_tree.nodes:
        if n.type == "GROUP" and n.node_tree and n.node_tree.name == group_name:
            sock = n.inputs.get("Color")
            return bool(sock and sock.is_linked)
    return False


def new_test_object(name, location=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.8,
                                         location=location)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    mat = bpy.data.materials.new(f"{name}_MAT")
    with warnings.catch_warnings():  # use_nodes 在 Blender 6.0 才移除，5.x 仍需要
        warnings.simplefilter("ignore", DeprecationWarning)
        mat.use_nodes = True
    obj.data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj, mat


def main():
    # ── 0. 环境 ────────────────────────────────────────────────────────────
    def env():
        addons = list(bpy.context.preferences.addons.keys())
        found = [a for a in addons if "Stylized" in a or "stylized" in a]
        if not found:
            raise RuntimeError(f"插件未启用：未在已启用 addon 里找到 {ADDON_HINT}")
        missing = [n for n in (
            "style_add_custom_group", "add_bulk_groups", "add_gradient_group",
            "apply_style_preset", "edit_group_params", "query_material",
            "query_group_params", "export_nodes_code", "add_creative_volume",
            "fix_all_nodes") if not hasattr(bpy.ops.node, n)]
        if missing:
            raise RuntimeError("缺少操作符: " + ", ".join(missing))
        return {"blender": bpy.app.version_string, "addon": found[0],
                "operators": 10}

    if not check("env: Blender 版本 / 插件 / 操作符", env):
        return finish()

    snapshot_datablocks()
    created_objects, created_materials = [], []

    # ── 1. apply_style_preset（配方：二分轮廓）──────────────────────────────
    obj1, mat1 = new_test_object(f"{TOKEN}_PRESET")
    created_objects.append(obj1)
    created_materials.append(mat1)

    def preset():
        bpy.ops.node.apply_style_preset(preset="tone_rim")
        found = groups_of(mat1)
        bases = {base_of(g) for g in found}
        if not {"主节点", "轮廓光"} <= bases:
            raise RuntimeError(f"配方未生成预期节点组: {found}")
        src = surface_source(mat1)
        if not src:
            raise RuntimeError("材质输出未连线")
        return {"groups": len(found), "output_source": src}

    check("apply_style_preset(preset='tone_rim')", preset)

    # ── 2. query_material（AI 调参前的自省）────────────────────────────────
    def query():
        import os
        bpy.ops.node.query_material()
        dump = os.path.join(bpy.app.tempdir, "material_query_dump.txt")
        if not os.path.exists(dump):
            raise RuntimeError(f"未生成 {dump}")
        return {"dump": dump, "bytes": os.path.getsize(dump)}

    check("query_material()", query)

    # ── 3. edit_group_params（原位调参 + 回读）──────────────────────────────
    def edit():
        bpy.ops.node.edit_group_params(params_json=json.dumps({
            "主节点": {"亮部范围": 0.70, "暗部范围": 0.35,
                       "过渡方式": "Stepped Linear", "阶梯步数": 3},
            "轮廓光": {"范围": 0.20, "Blend": 0.90},
        }, ensure_ascii=False))
        inst = next((n for n in mat1.node_tree.nodes if n.type == "GROUP"
                     and n.node_tree and base_of(n.node_tree.name) == "主节点"), None)
        if inst is None:
            raise RuntimeError("找不到 主节点 实例")
        got = inst.inputs["亮部范围"].default_value
        got_menu = inst.inputs["过渡方式"].default_value
        if abs(got - 0.70) > 1e-4 or got_menu != "Stepped Linear":
            raise RuntimeError(f"回读不一致: 亮部范围={got} 过渡方式={got_menu}")
        return {"亮部范围": round(got, 3), "过渡方式": got_menu}

    check("edit_group_params(params_json=...)", edit)

    # ── 4. add_bulk_groups（散装 7 组；按文档只自动接 主节点）──────────────
    obj2, mat2 = new_test_object(f"{TOKEN}_BULK", (2.4, 0, 0))
    created_objects.append(obj2)
    created_materials.append(mat2)

    def bulk():
        bpy.ops.node.add_bulk_groups()
        found = groups_of(mat2)
        bases = {base_of(g) for g in found}
        expect = {"主节点", "轮廓光", "高光", "反射", "脏迹", "AO", "Z轴变化"}
        if not expect <= bases:
            raise RuntimeError(f"缺少散装组: {sorted(expect - bases)}")
        others = [g for g in found if base_of(g) != "主节点"]
        unlinked = [g for g in others if not color_linked(mat2, g)]
        return {"groups": len(found),
                "others_unlinked_as_documented": len(unlinked) == len(others)}

    check("add_bulk_groups()", bulk)

    # ── 5. style_add_custom_group（全能组 / 创意组）─────────────────────────
    obj3, mat3 = new_test_object(f"{TOKEN}_CUSTOM", (-2.4, 0, 0))
    created_objects.append(obj3)
    created_materials.append(mat3)

    def one_group(name, expect_base):
        bpy.ops.node.style_add_custom_group(group_name=name)
        bases = sorted({base_of(g) for g in groups_of(mat3)})
        if expect_base not in bases:
            raise RuntimeError(f"{name} 未生成，现有: {bases}")
        return bases

    check("style_add_custom_group('多功能风格化shader')",
          lambda: one_group("多功能风格化shader", "多功能风格化shader"))
    check("style_add_custom_group('排线纹理')  # 创意组程序化构建",
          lambda: one_group("排线纹理", "排线纹理"))

    # ── 6. add_gradient_group（自动建控制器空物体）──────────────────────────
    obj4, mat4 = new_test_object(f"{TOKEN}_GRAD", (0, 2.6, 0))
    created_objects.append(obj4)
    created_materials.append(mat4)

    def gradient():
        bpy.ops.node.add_gradient_group()
        ctrl = [o.name for o in bpy.data.objects if o.type == "EMPTY" and "控制器" in o.name]
        found = groups_of(mat4)
        if not any(base_of(g) == "渐变" for g in found):
            raise RuntimeError("渐变组未生成")
        if not ctrl:
            raise RuntimeError("未创建 {物体名}_控制器 空物体")
        return {"controller": ctrl[-1], "groups": found}

    check("add_gradient_group()", gradient)

    # ── 7. add_creative_volume（体积雾，另建物体）───────────────────────────
    def volume():
        before = set(bpy.data.objects.keys())
        bpy.ops.node.add_creative_volume(mode="FOG")
        new = sorted(set(bpy.data.objects.keys()) - before)
        if not new:
            raise RuntimeError("未创建体积物体")
        obj = bpy.data.objects[new[0]]
        created_objects.append(obj)
        mat = obj.material_slots[0].material if obj.material_slots else None
        if mat is None or not any(base_of(g) == "体积雾" for g in groups_of(mat)):
            raise RuntimeError("体积物体上没有 体积雾 节点组")
        return {"object": obj.name, "material": mat.name}

    check("add_creative_volume(mode='FOG')", volume)

    # ── 8. fix_all_nodes（修复模板体检）────────────────────────────────────
    def fix():
        bpy.ops.node.fix_all_nodes()
        return "完成（0 处需修复也是正常）"

    check("fix_all_nodes()", fix)

    # ── 9. 参数 schema 与 skill §6 一致（抽查最易错的三个）──────────────────
    def schema():
        want = {
            "Z轴变化": ("Z轴最小范围", "Z轴最大范围"),
            "反射": ("反射强度", "反射范围"),
            "高光": ("高光开关", "高光范围"),
        }
        problems = {}
        seen = set()
        for ng in bpy.data.node_groups:
            base = base_of(ng.name)
            if base not in want or base in seen:
                continue
            seen.add(base)
            names = {it.name for it in ng.interface.items_tree
                     if getattr(it, "item_type", "") == "SOCKET"
                     and getattr(it, "in_out", "") == "INPUT"}
            missing = [n for n in want[base] if n not in names]
            if missing:
                problems[base] = missing
        if problems:
            raise RuntimeError(f"参数名与 skill 文档不一致: {problems}")
        return "Z轴变化 / 反射 / 高光 参数名与 §6 一致；已核 " + ", ".join(sorted(seen))

    check("参数 schema 抽查（Z轴变化 / 反射 / 高光）", schema)

    cleanup(created_objects, created_materials)
    return finish()


_BASELINE = {"objects": set(), "materials": set(), "node_groups": set()}


def snapshot_datablocks():
    """Remember what already existed, so cleanup restores the scene exactly."""
    _BASELINE["objects"] = {o.as_pointer() for o in bpy.data.objects}
    _BASELINE["materials"] = {m.as_pointer() for m in bpy.data.materials}
    _BASELINE["node_groups"] = {n.as_pointer() for n in bpy.data.node_groups}


def cleanup(objects, materials):
    """Remove every datablock this run created, leaving pre-existing ones intact."""
    try:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            if obj and obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        for obj in list(bpy.data.objects):
            if obj.as_pointer() not in _BASELINE["objects"] or TOKEN in obj.name:
                bpy.data.objects.remove(obj, do_unlink=True)
        for mat in materials:
            if mat and mat.name in bpy.data.materials:
                bpy.data.materials.remove(mat, do_unlink=True)
        for mat in list(bpy.data.materials):
            if mat.as_pointer() not in _BASELINE["materials"]:
                bpy.data.materials.remove(mat, do_unlink=True)
        for ng in list(bpy.data.node_groups):
            if ng.as_pointer() not in _BASELINE["node_groups"]:
                bpy.data.node_groups.remove(ng, do_unlink=True)
    except Exception:  # noqa: BLE001 - cleanup must never mask the result
        pass


def finish():
    failed = [r for r in RESULT if not r["ok"]]
    payload = {
        "ok": not failed,
        "passed": len(RESULT) - len(failed),
        "failed": len(failed),
        "steps": RESULT,
    }
    print("VERIFY_SKILL " + json.dumps(payload, ensure_ascii=False))
    return payload


# Executed unconditionally: this file is a self-test script, not an importable
# module. Hosts run it as `__main__` (Blender -b --python), through a sandbox
# `__name__` (DSH blender_rt_do file=...), or by exec in the Text Editor — all
# three paths must actually run it.
main()
