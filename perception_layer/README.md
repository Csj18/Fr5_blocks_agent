# perception_layer — 感知层

仅负责视觉定位**未搭建的原料积木**的位姿；已搭建结构由 memory_layer 的内部世界模型维护。

## 模块

- **视觉检测** (`vision_detector.py`)：通过 YOLO/SAM 识别未搭建积木的位姿（位置、姿态），输出 `BlockPose.msg`
- **场景校准** (`scene_calibrator.py`)：每层搭建后对当前层积木进行局部视觉校准，修正微小滑动误差（≤2mm），更新 scene_graph

## 设计理念

采用"视觉定位原料 + 内部模型维护已搭建结构"的混合感知架构，平衡精度与算力效率。`scene_calibrator` 仅在每层搭建后触发，避免过度算力消耗。

## 注意

视觉识别坐标需通过 TF 广播转换至机械臂基坐标系。
