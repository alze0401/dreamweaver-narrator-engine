"""
织梦绮谭 - MinIO 对象存储服务

提供文件上传、URL 生成、Bucket 初始化等功能。
支持：用户头像、角色头像/立绘、场景背景图、BGM 音频。

使用方式:
    from app.storage import storage
    url = await storage.upload_file(bucket_path, file_bytes, content_type)
"""

import uuid
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import ENABLED
from loguru import logger

from app.config import get_settings


class StorageService:
    """MinIO 存储服务封装"""

    # 允许的文件类型
    IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/ogg", "audio/wav", "audio/flac"}
    ALL_ALLOWED = IMAGE_TYPES | AUDIO_TYPES

    # Bucket 内的目录前缀
    PREFIX_USER_AVATAR = "user/avatars"
    PREFIX_CHAR_AVATAR = "preset/characters"
    PREFIX_USER_CHAR = "user/characters"
    PREFIX_BACKGROUND = "preset/backgrounds"
    PREFIX_USER_BG = "user/backgrounds"
    PREFIX_BGM = "preset/bgm"
    PREFIX_USER_BGM = "user/bgm"

    def __init__(self):
        self._settings = get_settings()
        self._client: Optional[Minio] = None
        self._bucket = self._settings.minio_bucket

    @property
    def client(self) -> Minio:
        """惰性初始化 MinIO 客户端"""
        if self._client is None:
            self._client = Minio(
                self._settings.minio_endpoint,
                access_key=self._settings.minio_access_key,
                secret_key=self._settings.minio_secret_key,
                secure=self._settings.minio_secure,
            )
            logger.info(f"MinIO 客户端已初始化: {self._settings.minio_endpoint}")
        return self._client

    def ensure_bucket(self):
        """确保存储桶存在，不存在则创建并设为公开读，同时配置 CORS"""
        try:
            if not self.client.bucket_exists(self._bucket):
                self.client.make_bucket(self._bucket)
                # 设置公开读策略（允许匿名 GET）
                policy = (
                    '{"Version":"2012-10-17",'
                    '"Statement":[{"Effect":"Allow","Principal":{"AWS":["*"]},'
                    '"Action":["s3:GetObject"],'
                    f'"Resource":["arn:aws:s3:::{self._bucket}/preset/*",'
                    f'"arn:aws:s3:::{self._bucket}/user/*"]}}]}}'
                )
                self.client.set_bucket_policy(self._bucket, policy)
                logger.info(f"存储桶 '{self._bucket}' 已创建并设为公开读")
            else:
                logger.debug(f"存储桶 '{self._bucket}' 已存在")

            # 始终确保 CORS 配置正确（允许前端跨域加载图片等资源）
            self._ensure_cors()

        except S3Error as e:
            logger.warning(f"设置 bucket 策略失败（可能不影响使用）: {e}")
        except Exception as e:
            logger.warning(f"确保 bucket 存在时出错: {e}")

    def _ensure_cors(self):
        """配置 MinIO 桶的 CORS 规则，允许前端跨域访问"""
        try:
            from minio.commonconfig import CorsRule, CorsConfiguration
            cors_config = CorsConfiguration([
                CorsRule(
                    allowed_origins=["*"],
                    allowed_methods=["GET", "HEAD"],
                    allowed_headers=["*"],
                    expose_headers=["ETag", "Content-Length", "Content-Type"],
                    max_age_seconds=3600,
                )
            ])
            self.client.set_bucket_cors(self._bucket, cors_config)
            logger.info(f"CORS 规则已配置: {self._bucket}")
        except ImportError:
            logger.warning("minio SDK 未提供 CorsRule/CorsConfiguration，跳过 CORS 配置")
        except S3Error as e:
            logger.warning(f"设置 CORS 失败（可能不影响使用）: {e}")
        except Exception as e:
            logger.warning(f"配置 CORS 时出错: {e}")

    def _generate_object_name(
        self, prefix: str, file_ext: str, user_id: Optional[str] = None
    ) -> str:
        """生成唯一的对象名称"""
        file_id = uuid.uuid4().hex[:12]
        ext = file_ext.lower().lstrip(".")
        if user_id:
            return f"{prefix}/{user_id}/{file_id}.{ext}"
        return f"{prefix}/{file_id}.{ext}"

    def upload_file(
        self,
        data: bytes,
        content_type: str,
        prefix: str,
        file_ext: str = "",
        user_id: Optional[str] = None,
        custom_name: Optional[str] = None,
    ) -> str:
        """
        上传文件到 MinIO。

        Args:
            data: 文件二进制数据
            content_type: MIME 类型
            prefix: 目录前缀（如 "user/avatars"）
            file_ext: 文件扩展名（如 "png"）
            user_id: 用户 ID（用于目录隔离）
            custom_name: 自定义文件名（不含路径）

        Returns:
            可公开访问的 URL
        """
        if content_type not in self.ALL_ALLOWED:
            raise ValueError(f"不支持的文件类型: {content_type}")

        # 检查文件大小
        size = len(data)
        if content_type in self.IMAGE_TYPES:
            max_bytes = self._settings.upload_max_image_mb * 1024 * 1024
            if size > max_bytes:
                raise ValueError(
                    f"图片大小 {size / 1024 / 1024:.1f}MB 超过限制 "
                    f"{self._settings.upload_max_image_mb}MB"
                )
        elif content_type in self.AUDIO_TYPES:
            max_bytes = self._settings.upload_max_audio_mb * 1024 * 1024
            if size > max_bytes:
                raise ValueError(
                    f"音频大小 {size / 1024 / 1024:.1f}MB 超过限制 "
                    f"{self._settings.upload_max_audio_mb}MB"
                )

        # 生成对象名
        if custom_name:
            if user_id:
                object_name = f"{prefix}/{user_id}/{custom_name}"
            else:
                object_name = f"{prefix}/{custom_name}"
        else:
            if not file_ext:
                # 从 content_type 推断扩展名
                ext_map = {
                    "image/png": "png", "image/jpeg": "jpg",
                    "image/webp": "webp", "image/gif": "gif",
                    "audio/mpeg": "mp3", "audio/mp3": "mp3",
                    "audio/ogg": "ogg", "audio/wav": "wav",
                    "audio/flac": "flac",
                }
                file_ext = ext_map.get(content_type, "bin")
            object_name = self._generate_object_name(prefix, file_ext, user_id)

        # 上传
        stream = BytesIO(data)
        self.client.put_object(
            self._bucket,
            object_name,
            stream,
            length=size,
            content_type=content_type,
        )

        # 构建公开访问 URL
        public_url = f"{self._settings.minio_public_url}/{object_name}"
        logger.info(f"文件已上传: {object_name} ({size / 1024:.1f}KB)")
        return public_url

    def upload_user_avatar(self, data: bytes, content_type: str, user_id: str) -> str:
        """上传用户头像（使用 UUID 文件名，避免覆盖导致竞态删除）"""
        # 根据 content_type 确定扩展名
        ext_map = {
            "image/png": "png", "image/jpeg": "jpg",
            "image/webp": "webp", "image/gif": "gif",
        }
        ext = ext_map.get(content_type, "webp")
        file_id = uuid.uuid4().hex[:12]
        return self.upload_file(
            data, content_type, self.PREFIX_USER_AVATAR,
            user_id=user_id, custom_name=f"{file_id}.{ext}",
        )

    def upload_character_avatar(
        self, data: bytes, content_type: str,
        template_id: str, user_id: Optional[str] = None,
    ) -> str:
        """上传角色头像/立绘（使用 UUID 文件名，避免覆盖导致竞态删除）"""
        prefix = self.PREFIX_USER_CHAR if user_id else self.PREFIX_CHAR_AVATAR
        file_id = uuid.uuid4().hex[:12]
        ext_map = {
            "image/png": "png", "image/jpeg": "jpg",
            "image/webp": "webp", "image/gif": "gif",
        }
        ext = ext_map.get(content_type, "webp")
        return self.upload_file(
            data, content_type, prefix,
            user_id=user_id, custom_name=f"{template_id}_{file_id}.{ext}",
        )

    def upload_background(
        self, data: bytes, content_type: str,
        name: str, user_id: Optional[str] = None,
    ) -> str:
        """上传场景背景图"""
        prefix = self.PREFIX_USER_BG if user_id else self.PREFIX_BACKGROUND
        return self.upload_file(
            data, content_type, prefix,
            user_id=user_id, custom_name=f"{name}.jpg",
        )

    def upload_bgm(
        self, data: bytes, content_type: str,
        name: str, user_id: Optional[str] = None,
    ) -> str:
        """上传背景音乐"""
        prefix = self.PREFIX_USER_BGM if user_id else self.PREFIX_BGM
        return self.upload_file(
            data, content_type, prefix,
            user_id=user_id, custom_name=f"{name}.mp3",
        )

    def delete_file(self, url: str) -> bool:
        """通过 URL 删除文件"""
        try:
            # 从 URL 中提取 object_name
            base = self._settings.minio_public_url.rstrip("/") + "/"
            if url.startswith(base):
                object_name = url[len(base):]
                self.client.remove_object(self._bucket, object_name)
                logger.info(f"文件已删除: {object_name}")
                return True
        except Exception as e:
            logger.warning(f"删除文件失败: {e}")
        return False

    def presigned_url(self, object_name: str, expires_hours: int = 24) -> str:
        """生成临时签名 URL（用于私有文件）"""
        from datetime import timedelta
        return self.client.presigned_get_object(
            self._bucket, object_name,
            expires=timedelta(hours=expires_hours),
        )


# 全局单例
storage = StorageService()
