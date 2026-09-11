# Inline-four 2.0 L — CAD reference v1

直列四缸 2.0 L 发动机短机体：原创参数化 CAD 能力示例，供后续 FEA / CFD
几何准备使用。此版本冻结原始短机体几何，并添加零件表面名称和边界面组。

核验结果：83 个实体零件，1,183 个唯一面名，68 个工程语义面组（覆盖 132 个面）；
保存重开后所有面引用有效，全部零件相对源 CAD 的双向差集体积为零。

## 入口

- **`inline_four_2l_short_block_named_v1.FCStd`**：首选原生模型，83 个零件 Body，
  保留草图、特征树及曲轴角度驱动的运动表达式。
- **`surface_catalog.csv`**：可读的全部面名称、零件、Face 编号、类型、面积和局部质心。
- **`surface_catalog.json`**：完整索引，额外记录局部/装配坐标几何签名、面组和源文件哈希。
- **`verification.json`**：保存重开、面引用、原始实体双向差集和名义面积核验。
- **`name_surfaces.py`**：通过 FreeCADCmd 重建此命名副本。
- STEP 交换模型使用 [`../inline_four_short_block.step`](../inline_four_short_block.step)。
  STEP 内的面编号及命名传递尚未验证；导入后需根据几何重新匹配并检查。

## 命名与使用

名称使用英文 snake_case，方便脚本和求解器工具处理。示例：

| 面组 | 几何含义 |
|---|---|
| `cylinder_block__cylinder_01_bore_wall` | 第 1 缸的缸孔壁 |
| `cylinder_block__cylinder_01_coolant_barrel_wall` | 第 1 缸外侧接触冷却液的圆柱壁 |
| `cylinder_block__deck_gasket_face` | 缸体顶面 |
| `cylinder_block__oil_pan_gasket_face` | 油底壳结合面 |
| `crankshaft__main_01_journal` | 第 1 道主轴颈圆柱面 |
| `crankshaft__cylinder_01_crankpin` | 第 1 缸连杆轴颈圆柱面 |
| `piston1__crown_top_land` | 活塞顶环形平面 |
| `piston1__crown_bowl_floor` / `crown_bowl_wall` | 活塞顶凹坑底面 / 侧壁 |

每个面均有唯一名称，例如 `crankshaft__main_01_journal__f001`。
尚未赋予工程用途的面采用 `零件__plane/cylinder__fNNN`；**唯一命名不等于
已经确定边界条件**。活塞燃气接触面包括顶面、凹坑底面和侧壁，不能只选一个平面。
冷却缸套外壁面组也不代表整个水套的完整湿壁。

FreeCAD 模型树的 **Named surfaces** 下包含命名面组；Data → References
存储真实的 `(Body, Face列表)`。每个 Body 的 **Surface archive → SurfaceNames**
按 Face1、Face2……顺序列出全部名称。可在 Python 控制台选择某个组：

```python
import FreeCADGui as Gui
group = App.ActiveDocument.getObjectsByLabel('crankshaft__main_01_journal')[0]
body, faces = group.References
Gui.Selection.clearSelection()
for face in faces:
    Gui.Selection.addSelection(body, face)
```

坐标单位 mm：X 为曲轴轴向，Z 为缸轴方向，Y 为连杆摆动方向。
第 1–4 缸沿 X 递增，中心 X=-144,-48,48,144 mm。索引的装配坐标对应曲轴角 0°；
局部坐标不随刚体运动变化。修改零件拓扑、尺寸或重新导入后必须重建/核验名称。
Face 编号后缀仅在本存档版本内有效，不承诺跨版本稳定。

## 能力与适用边界

已展示原创实体建模、独立重复零件、运动放置、装配干涉检查、原生文件与 STEP
交换、剖视展示，以及表面索引。四套活塞连杆几何相同，但为独立 Body。
这是分析的 CAD 起点，尚无网格、材料卡、接触定义、载荷或求解结果。
FEA 需按问题补充圆角、载荷路径及连接理想化；CFD 需提取/封闭流体域，定义真实
进出口并验证完整边界分区。现有模型没有完整缸盖、气门、进排气道或油路。

## 历史版本

- [原始运动总成](../README.md)：49 个运动零件。
- [缸体与原始短机体](../BLOCK_README.md)：本命名副本的几何来源。
- [配重质量矩试算](../counterweight/README.md)：单独的实验分支；配重形状与设计方法
  尚未完成工程优化，**不作为本基础示例的推荐设计**。
- [Blender 点火展示](../ignition/README.md)：采用原始曲轴的可视化，非燃烧 CFD。

完整归档保留源代码、原生/交换模型、图片、动画、历史失败证据及验证记录。
`../archive/` 下的 tar.gz 为冻结快照；对应 `.contents.json` 逐文件记录 SHA-256，
`.sha256` 校验压缩包。归档日期使用创建时 UTC 日期。
