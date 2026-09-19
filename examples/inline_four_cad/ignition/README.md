# 直列四缸：点火与燃烧示意动画

Blender 4.5.9 LTS，免费开源。官方安装包已核对 SHA-256。
本机启动命令：`/home/linuxjun/.local/bin/blender`。

## 打开与播放

- `inline_four_ignition.mp4`：1440 × 900、24 fps、10 秒完整四冲程周期。
- `inline_four_ignition.blend`：可编辑的 Blender 工程，字体已打包。
- `ignition_detail.png`：火花塞与初始火焰的局部特写。
- `scene_inspection.json`：重新打开工程后的运动与点火检查。

在 Blender 中打开工程，鼠标放在三维视口上按空格播放/暂停。
数字小键盘 0 切换相机视图，Z 菜单可选择渲染显示。
场景集合分别存放原 CAD 零件、示意缸盖/火花塞、特效、冲程标识和灯光。

选择 **ENGINE CONTROLS**，在对象属性的自定义属性中修改：

- **Spark advance**：整数 0–35°，默认为示意值 12° BTDC；标签同步更新。
- **Crank angle**：0–720°，驱动机械运动、火花、火焰和冲程标识。
  此属性已有关键帧，拖动时间轴会覆盖手动输入值；持续修改运动时编辑其关键帧。

时间轴第 1 帧为 0°，第 241 帧为 720°，渲染输出第 1–240 帧，避免循环端点重复。
改变播放速度可调整控制对象的两个角度关键帧及场景结束帧。
黄色 SPARK 时间轴标记记录默认提前角，修改提前角后标记本身不自动更新。

## 实现与范围

原有 CAD 文件保持原样。从 FreeCAD 的剖视装配导出 74 个可见组件；
补充了 21 个示意缸盖/火花塞组件。原始几何、网格和原生运动样本见
`cad_scene.json`，尺寸由毫米换算为米。

Blender 用曲柄连杆表达式驱动各组件，重新打开工程后逐一对照 FreeCAD
导出的 241 个运动位置。表达式使用 Blender 的原生简单表达式求值器，
不需要启用 Python 自动运行或安装插件。

采用 1–3–4–2 点火顺序，每缸每 720° 点火一次。火花可见约 7°，
随后程序化体积发光从电极附近扩展，在膨胀行程中衰减。发光体下界跟随
活塞顶，上界与径向遮罩限制在示意燃烧室内。

这份工程用于解释点火顺序和展示特效。火焰色彩、传播速度、持续角度与
亮度均为视觉设定，不代表燃烧计算结果。缸盖没有配气机构或进排气道；
冲程标签表示指定的四冲程相位，没有模拟真实进排气。

## 复现

在 FreeCADCmd 中运行 `export_cad.py`，然后在本目录执行：

```bash
blender -b --factory-startup --python build_scene.py
blender -b --factory-startup --disable-autoexec --python check_scene.py
blender -b --factory-startup --python render_animation.py
ffmpeg -framerate 24 -i frames/%04d.png -c:v libx264 -crf 18 \
  -pix_fmt yuv420p -movflags +faststart inline_four_ignition.mp4
```

硬件渲染需要访问主机的图形设备。帧渲染脚本跳过已有图片；修改场景后，
请移走旧的 `frames/` 再渲染，以免混入旧版本。

## 捕获的导出问题

初始导出直接把 0–720° 写入 FreeCAD 的 `App::PropertyAngle`，第二圈的
原生机械运动样本停在一圈终点。跨软件逐组件检查捕获了 86 mm 的位置差。
修正为把机械角度按 360° 取模，单独保留 720° 点火周期。
初始失败记录保存在 `scene_inspection_initial.json`。
