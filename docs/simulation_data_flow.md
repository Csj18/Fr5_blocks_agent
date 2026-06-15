# Simulation Data Flow — Pick & Place Attachment

## Architecture Overview

```
                         ┌────────────────────────┐
                         │     Terminal/CLI        │
                         │  ros2 topic pub         │
                         │  /pick_place            │
                         └───────────┬────────────┘
                                     │ std_msgs/String
                                     │ "pick block_red"
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                     pick_place_server.py                           │
│                      (orchestrator)                                │
│                                                                    │
│  State:  attached{}  block_positions{}                             │
│                                                                    │
│  On PICK:                    On PLACE:                             │
│  ────────                    ─────────                             │
│  ① AttachedCollisionObject   ① AttachedCollisionObject REMOVE      │
│     → /attached_collision_object  → /attached_collision_object     │
│  ② CollisionObject REMOVE    ② TF lookup world→hand_base_link     │
│     → /collision_object      ③ CollisionObject ADD                │
│  ③ Gazebo fixed joint            → /collision_object              │
│     → ign service            ④ Gazebo joint remove                │
│  ④ State → /block_attachment     → ign service                    │
│  ⑤ TF → hand_base_link→block ⑤ State → /block_attachment          │
│                                                                    │
│  Every 100ms (timer):                                              │
│  - Re-publish attached objects (MoveIt needs refresh)              │
│  - Broadcast block TFs (attached: hand_base_link→block,            │
│                          detached: world→block)                    │
└────┬──────────┬──────────────────┬────────────────────────────────┘
     │          │                  │
     ▼          ▼                  ▼
┌─────────┐ ┌──────────┐ ┌──────────────────┐
│ MoveIt  │ │  Gazebo  │ │ /block_attachment │
│Planning │ │  Physics │ │  (std_msgs/String)│
│ Scene   │ │  (ign)   │ └──────┬───────────┘
└────┬────┘ └────┬─────┘        │
     │           │               ├──────────────┬──────────────┐
     ▼           ▼               ▼              ▼              ▼
┌─────────┐ ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌────────────────┐
│  RViz   │ │ Gazebo  │ │block_visual │ │block_tf  │ │block_collision │
│Planning │ │  pose   │ │_marker.py   │ │_bridge.py│ │_updater.py     │
│Scene    │ │ bridge  │ │             │ │          │ │                │
│display  │ │         │ │ on attach:  │ │ skip     │ │ skip attached  │
│         │ │         │ │ frame=hand  │ │ attached │ │ blocks         │
│         │ │         │ │ _base_link  │ │ blocks   │ │                │
└─────────┘ └─────────┘ └─────────────┘ └──────────┘ └────────────────┘
```

## TF Tree

### Before Pick (detached blocks)
```
world
├── fairino5_v6_robot
│   └── base_link
│       └── ... → hand_base_link
├── block_red      (from Gazebo pose or pick_place_server)
├── block_green    (from Gazebo pose or pick_place_server)
└── block_blue     (from Gazebo pose or pick_place_server)
```

### After Pick (block_red attached)
```
world
├── fairino5_v6_robot
│   └── base_link
│       └── ... → hand_base_link
│                     └── block_red   ← attached! pick_place_server broadcasts
├── block_green    (detached, from Gazebo)
└── block_blue     (detached, from Gazebo)
```

## Node Responsibilities

| Node | Attached Block | Detached Block |
|------|---------------|----------------|
| `pick_place_server.py` | Publishes AttachedCollisionObject, broadcasts `hand_base_link→block` TF | Publishes CollisionObject, broadcasts `world→block` TF |
| `block_visual_marker.py` | Marker in `hand_base_link` frame at (0,0,-0.08) | Marker in `world` frame from Gazebo pose |
| `block_tf_bridge.py` | **Skips** — no `world→block` TF | Publishes `world→block` TF from Gazebo pose |
| `block_collision_updater.py` | **Skips** — MoveIt handles via attachment | Publishes `CollisionObject` from Gazebo pose |
