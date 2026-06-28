"""
MaixCAM2 人脸识别智能系统 - 人脸识别模块

功能：
- 人脸检测与识别（使用官方 nn.FaceRecognizer）
- 人脸录入与保存
- 人脸库管理

模型文件：
- 人脸检测：/root/models/yolov8n_face.mud
- 特征提取：/root/models/insghtface_webface_r50.mud
- 人脸库：/root/face_recognition_system/data/faces.bin
"""
import os
from maix import nn, image

class FaceDetector:
    """
    人脸检测器

    功能：
    - 使用 nn.FaceRecognizer 进行人脸检测和识别
    - 支持人脸录入和保存
    - 自动管理人脸库

    官方文档：
    - 人脸检测：https://wiki.sipeed.com/maixpy/doc/zh/vision/face_detection.html
    - 人脸识别：https://wiki.sipeed.com/maixpy/doc/zh/vision/face_recognition.html
    """

    def __init__(self, detect_model, feature_model, faces_db_path="",
                 conf_th=0.5, iou_th=0.45, recognize_th=0.85):
        """
        初始化人脸检测器

        参数：
            detect_model: 人脸检测模型路径（如 yolov8n_face.mud）
            feature_model: 特征提取模型路径（如 insghtface_webface_r50.mud）
            faces_db_path: 人脸数据库文件路径（.bin 格式）
            conf_th: 检测置信度阈值
            iou_th: IoU 阈值
            recognize_th: 人脸识别阈值
        """
        # 人脸数据库路径
        self._faces_db_path = faces_db_path

        # 检测参数
        self._detect_conf_th = conf_th
        self._detect_iou_th = iou_th
        self._recognize_th = recognize_th

        # 初始化人脸识别器
        print("[人脸] 加载人脸检测模型...")
        print(f"[人脸] 检测模型: {detect_model}")
        print(f"[人脸] 特征模型: {feature_model}")

        try:
            # 使用官方 FaceRecognizer
            # dual_buff=True 启用双缓冲，提高处理速度
            self._recognizer = nn.FaceRecognizer(
                detect_model=detect_model,
                feature_model=feature_model,
                dual_buff=True
            )
            print("[人脸] 人脸识别器初始化成功")
            print("[人脸] 输入尺寸: {}x{}".format(
                self._recognizer.input_width(),
                self._recognizer.input_height()
            ))
        except Exception as e:
            print(f"[人脸] 人脸识别器初始化失败: {e}")
            raise e

        # 加载已有人脸数据库
        self._load_faces_db()

        # 状态变量
        self._is_enrolling = False
        self._enroll_label = ""

        print(f"[人脸] 已录入人脸: {len(self._recognizer.labels)} 个")
        print(f"[人脸] 人脸标签: {self._recognizer.labels}")

    def _load_faces_db(self):
        """
        加载人脸数据库

        功能：
        - 从文件加载已录入的人脸数据
        - 如果文件不存在则创建空数据库
        """
        if not self._faces_db_path:
            print("[人脸] 未指定人脸数据库路径")
            return

        try:
            if os.path.exists(self._faces_db_path):
                self._recognizer.load_faces(self._faces_db_path)
                print(f"[人脸] 加载人脸数据库: {self._faces_db_path}")
            else:
                print(f"[人脸] 人脸数据库不存在，将创建新库")
        except Exception as e:
            print(f"[人脸] 加载人脸数据库失败: {e}")

    def _save_faces_db(self):
        """
        保存人脸数据库

        功能：
        - 将当前人脸数据保存到文件
        """
        if not self._faces_db_path:
            print("[人脸] 未指定人脸数据库路径，跳过保存")
            return False

        try:
            self._recognizer.save_faces(self._faces_db_path)
            print(f"[人脸] 保存人脸数据库: {self._faces_db_path}")
            return True
        except Exception as e:
            print(f"[人脸] 保存人脸数据库失败: {e}")
            return False

    def detect_and_recognize(self, img):
        """
        检测并识别人脸

        参数：
            img: MaixPy Image 对象

        返回：
            人脸列表，每个人脸包含：
            - x, y, w, h: 检测框
            - points: 关键点
            - class_id: 类别 ID（0 表示未知）
            - score: 识别分数
        """
        try:
            faces = self._recognizer.recognize(
                img,
                self._detect_conf_th,
                self._detect_iou_th,
                self._recognize_th
            )
            return faces if faces else []
        except Exception as e:
            print(f"[人脸] 检测识别异常: {e}")
            return []

    def detect(self, img):
        """
        仅检测人脸（不识别身份）

        参数：
            img: MaixPy Image 对象

        返回：
            人脸对象列表
        """
        return self.detect_and_recognize(img)

    def detect_faces_only(self, img):
        """
        仅检测人脸位置（不进行身份识别，性能更高）

        参数：
            img: MaixPy Image 对象

        返回：
            人脸对象列表（包含位置信息，class_id 可能为 0 即 unknown）

        说明：
            调用 recognize() 时不传 get_feature 和 get_face 参数，
            只做检测+比对，不做特征提取，性能优于带 get_feature=True 的调用。
        """
        try:
            # 使用较低的置信度阈值进行快速检测
            # 注意：不传 get_feature=True，避免额外特征提取计算
            # 之前错误地传了 True 给 get_feature 参数，反而更慢
            faces = self._recognizer.recognize(
                img,
                self._detect_conf_th * 0.8,  # 降低阈值以提高检测率
                self._detect_iou_th,
                self._recognize_th
                # get_feature 和 get_face 使用默认值 False
            )
            return faces if faces else []
        except Exception as e:
            print(f"[人脸] 快速检测异常: {e}")
            return []

    def start_enrollment(self, label):
        """
        开始人脸录入

        参数：
            label: 人脸标签（人名）

        返回：
            True: 启动成功
            False: 启动失败
        """
        if self._is_enrolling:
            print("[人脸] 已在录入模式中")
            return False

        self._is_enrolling = True
        self._enroll_label = label
        print(f"[人脸] 开始录入: {label}")
        return True

    def enroll_face(self, img):
        """
        录入人脸

        参数：
            img: MaixPy Image 对象（当前帧）

        返回：
            (success, message, count)
            - success: 是否成功
            - message: 提示信息
            - count: 已录入数量
        """
        if not self._is_enrolling:
            return (False, "未在录入模式", 0)

        try:
            # 检测人脸（使用 recognize 并获取特征和裁剪人脸，用于录入）
            # get_feature=True: 获取特征向量，用于 add_face
            # get_face=True: 获取裁剪后的人脸图像
            faces = self._recognizer.recognize(
                img,
                self._detect_conf_th,
                self._detect_iou_th,
                self._recognize_th,
                get_feature=True,
                get_face=True
            )

            if not faces:
                return (False, "未检测到人脸", 0)

            # 取第一个检测到的人脸
            face = faces[0]

            # 添加到人脸库
            self._recognizer.add_face(face, self._enroll_label)

            # 保存数据库
            self._save_faces_db()

            # 更新状态
            self._is_enrolling = False
            label = self._enroll_label
            self._enroll_label = ""

            print(f"[人脸] 录入成功: {label}")
            return (True, f"录入成功: {label}", len(self._recognizer.labels))

        except Exception as e:
            print(f"[人脸] 录入失败: {e}")
            return (False, f"录入失败: {e}", 0)

    def cancel_enrollment(self):
        """
        取消录入
        """
        self._is_enrolling = False
        self._enroll_label = ""
        print("[人脸] 取消录入")

    def draw_face(self, img, face, color=None, label=""):
        """
        在图像上绘制人脸框和标签

        参数：
            img: MaixPy Image 对象
            face: 人脸对象
            color: 框颜色（image.Color 对象或预定义常量）
            label: 标签文字
        """
        if color is None:
            color = image.COLOR_GREEN

        try:
            # 绘制人脸框
            img.draw_rect(
                face.x, face.y,
                face.w, face.h,
                color=color, thickness=2
            )

            # 绘制关键点
            radius = max(face.w // 20, 3)
            img.draw_keypoints(face.points, color, size=radius)

            # 绘制标签
            if label:
                img.draw_string(
                    face.x, face.y - 20,
                    label,
                    color=color, scale=1.0
                )

        except Exception as e:
            print(f"[人脸] 绘制异常: {e}")

    def get_face_label(self, face):
        """
        获取人脸标签

        参数：
            face: 人脸对象

        返回：
            人脸标签字符串
        """
        try:
            if face.class_id < len(self._recognizer.labels):
                return self._recognizer.labels[face.class_id]
            return "unknown"
        except:
            return "unknown"

    def is_known_face(self, face):
        """
        判断是否为已知人脸

        参数：
            face: 人脸对象

        返回：
            True: 已知人脸（class_id > 0）
            False: 未知人脸（class_id == 0）
        """
        return face.class_id > 0

    def get_class_count(self):
        """
        获取已录入的人脸类别数量

        返回：
            类别数量（不含 unknown）
        """
        # labels[0] 默认是 "unknown"
        return max(0, len(self._recognizer.labels) - 1)

    def get_labels(self):
        """
        获取所有人脸标签

        返回：
            标签列表
        """
        return self._recognizer.labels

    def delete_face(self, label):
        """
        删除指定标签的人脸

        参数：
            label: 人脸标签名称

        返回：
            True: 删除成功
            False: 删除失败
        """
        try:
            result = self._recognizer.remove_face(label=label)
            self._save_faces_db()
            print(f"[人脸] 已删除: {label}")
            return True
        except Exception as e:
            print(f"[人脸] 删除失败: {e}")
            return False

    def clear_all_faces(self):
        """
        清空所有人脸（保留 unknown）

        返回：
            True: 清空成功
            False: 清空失败
        """
        try:
            # 反复删除索引 0（删除后索引前移）直到只剩 unknown
            count = len(self._recognizer.labels) - 1
            for _ in range(count):
                self._recognizer.remove_face(0)
            self._save_faces_db()
            print(f"[人脸] 已清空所有人脸（共删除 {count} 个）")
            return True
        except Exception as e:
            print(f"[人脸] 清空失败: {e}")
            return False

    def is_enrolling(self):
        """
        检查是否正在录入

        返回：
            True: 正在录入
            False: 未在录入
        """
        return self._is_enrolling

    def get_input_width(self):
        """
        获取检测器输入宽度

        返回：
            宽度
        """
        return self._recognizer.input_width()

    def get_input_height(self):
        """
        获取检测器输入高度

        返回：
            高度
        """
        return self._recognizer.input_height()

    def get_input_format(self):
        """
        获取检测器输入格式

        返回：
            图像格式
        """
        return self._recognizer.input_format()

    def set_detect_threshold(self, conf_th=0.3, iou_th=0.45, recognize_th=0.35):
        """
        设置检测阈值

        参数：
            conf_th: 检测置信度阈值（越大越严格）
            iou_th: IoU 阈值（过滤重叠框）
            recognize_th: 人脸识别阈值（越大越严格）
        """
        self._detect_conf_th = conf_th
        self._detect_iou_th = iou_th
        self._recognize_th = recognize_th
        print(f"[人脸] 阈值更新: conf={conf_th}, iou={iou_th}, recognize={recognize_th}")
