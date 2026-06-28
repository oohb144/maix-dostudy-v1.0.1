# -*- coding: utf-8 -*-
"""
性能测试脚本

功能：
- 测试摄像头帧率
- 测试人脸识别速度
- 验证优化效果
"""

from maix import camera, display, image, app, time, nn

def test_camera_fps():
    """测试摄像头帧率"""
    print("=" * 50)
    print("摄像头帧率测试")
    print("=" * 50)

    # 测试不同分辨率
    resolutions = [
        (640, 480),
        (320, 240),
        (160, 120)
    ]

    for width, height in resolutions:
        print(f"\n测试分辨率: {width}x{height}")

        cam = camera.Camera(width, height, image.Format.FMT_RGB888)
        cam.skip_frames(5)

        # 测试 3 秒内的帧率
        start_time = time.ticks_ms()
        frame_count = 0
        test_duration = 3000  # 3 秒

        while time.ticks_ms() - start_time < test_duration:
            img = cam.read()
            frame_count += 1

        elapsed = time.ticks_ms() - start_time
        fps = frame_count * 1000 // elapsed

        print(f"  帧数: {frame_count}")
        print(f"  时间: {elapsed}ms")
        print(f"  帧率: {fps} FPS")

        del cam

def test_face_detection_speed():
    """测试人脸检测速度"""
    print("\n" + "=" * 50)
    print("人脸检测速度测试")
    print("=" * 50)

    # 加载模型
    detect_model = "/root/models/yolov8n_face.mud"
    feature_model = "/root/models/insghtface_webface_r50.mud"

    try:
        recognizer = nn.FaceRecognizer(
            detect_model=detect_model,
            feature_model=feature_model,
            dual_buff=True
        )
        print("模型加载成功")
    except Exception as e:
        print(f"模型加载失败: {e}")
        return

    # 测试检测速度
    cam = camera.Camera(320, 240, image.Format.FMT_RGB888)
    cam.skip_frames(5)

    test_frames = 30
    start_time = time.ticks_ms()

    for i in range(test_frames):
        img = cam.read()
        faces = recognizer.recognize(img, 0.3, 0.4, 0.6)

    elapsed = time.ticks_ms() - start_time
    avg_time = elapsed // test_frames

    print(f"测试帧数: {test_frames}")
    print(f"总时间: {elapsed}ms")
    print(f"平均每帧: {avg_time}ms")
    print(f"检测帧率: {1000 // avg_time} FPS")

    del cam

def main():
    """主测试函数"""
    print("MaixCAM2 性能测试")
    print("=" * 50)

    try:
        # 测试摄像头帧率
        test_camera_fps()

        # 测试人脸检测速度
        test_face_detection_speed()

        print("\n" + "=" * 50)
        print("测试完成！")
        print("=" * 50)

    except Exception as e:
        print(f"测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
