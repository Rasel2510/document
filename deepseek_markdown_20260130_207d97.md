# Flutter Advanced Gesture Detection
## Complete Developer Guide

---

## 1. Overview
Flutter provides a robust gesture system that recognizes gestures at multiple levels:
- **Pointer Events**: Raw touch data
- **Gesture Detectors**: Processed gesture recognition
- **Scrollables & Dismissibles**: Specialized gesture widgets

---

## 2. Core Gesture Widgets

### 2.1 GestureDetector
```dart
GestureDetector(
  // Tap gestures
  onTap: () => print('Single tap'),
  onTapDown: (TapDownDetails details) {
    print('Tap down at: ${details.localPosition}');
  },
  onTapUp: (TapUpDetails details) {
    print('Tap up at: ${details.localPosition}');
  },
  onTapCancel: () => print('Tap cancelled'),
  
  // Double tap
  onDoubleTap: () => print('Double tap'),
  onDoubleTapDown: (TapDownDetails details) {
    print('Double tap down at: ${details.localPosition}');
  },
  
  // Long press
  onLongPress: () => print('Long press'),
  onLongPressStart: (LongPressStartDetails details) {
    print('Long press started at: ${details.localPosition}');
  },
  onLongPressMoveUpdate: (LongPressMoveUpdateDetails details) {
    print('Long press moving: ${details.localPosition}');
  },
  onLongPressEnd: (LongPressEndDetails details) {
    print('Long press ended at: ${details.localPosition}');
  },
  
  // Vertical drag
  onVerticalDragStart: (DragStartDetails details) {
    print('Vertical drag started');
  },
  onVerticalDragUpdate: (DragUpdateDetails details) {
    print('Vertical drag delta: ${details.delta}');
  },
  onVerticalDragEnd: (DragEndDetails details) {
    print('Vertical drag ended');
  },
  
  // Horizontal drag
  onHorizontalDragStart: (DragStartDetails details) {
    print('Horizontal drag started');
  },
  onHorizontalDragUpdate: (DragUpdateDetails details) {
    print('Horizontal drag delta: ${details.delta}');
  },
  onHorizontalDragEnd: (DragEndDetails details) {
    print('Horizontal drag ended');
  },
  
  // Pan (multi-directional)
  onPanStart: (DragStartDetails details) {
    print('Pan started');
  },
  onPanUpdate: (DragUpdateDetails details) {
    print('Pan delta: ${details.delta}');
  },
  onPanEnd: (DragEndDetails details) {
    print('Pan ended');
  },
  
  // Scale/Pinch
  onScaleStart: (ScaleStartDetails details) {
    print('Scale started with ${details.pointerCount} fingers');
  },
  onScaleUpdate: (ScaleUpdateDetails details) {
    print('Scale: ${details.scale}, Rotation: ${details.rotation}');
  },
  onScaleEnd: (ScaleEndDetails details) {
    print('Scale ended');
  },
  
  // Force press (3D Touch)
  onForcePressStart: (ForcePressDetails details) {
    print('Force press started: ${details.pressure}');
  },
  onForcePressPeak: (ForcePressDetails details) {
    print('Force press peak: ${details.pressure}');
  },
  onForcePressUpdate: (ForcePressDetails details) {
    print('Force press update: ${details.pressure}');
  },
  onForcePressEnd: (ForcePressDetails details) {
    print('Force press ended: ${details.pressure}');
  },
  
  // Hit test behavior
  behavior: HitTestBehavior.opaque, // Options: .opaque, .translucent, .deferToChild
  
  // Exclusive gestures
  excludeFromSemantics: false,
  
  child: Container(
    width: 200,
    height: 200,
    color: Colors.blue,
    child: Center(child: Text('Gesture Area')),
  ),
)