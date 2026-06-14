-- ============================================================
-- 织梦绮谭 - 增量迁移脚本（MinIO 文件存储 + 游戏设置）
-- 适用于已有数据库，无需重新初始化
-- 执行前请先备份数据库
-- ============================================================

USE `narrator_engine`;

-- ---- users 表：新增字段 ----
ALTER TABLE `users`
  ADD COLUMN IF NOT EXISTS `email` VARCHAR(128) DEFAULT NULL COMMENT '用户邮箱' AFTER `display_name`,
  ADD COLUMN IF NOT EXISTS `role` VARCHAR(16) NOT NULL DEFAULT 'user' COMMENT '用户角色：user / admin' AFTER `email`,
  ADD COLUMN IF NOT EXISTS `avatar_url` VARCHAR(512) DEFAULT NULL COMMENT '用户头像 URL' AFTER `role`;

-- ---- templates 表：新增字段 ----
ALTER TABLE `templates`
  ADD COLUMN IF NOT EXISTS `avatar_url` VARCHAR(512) DEFAULT NULL COMMENT '角色头像/立绘 或 世界封面图 URL' AFTER `data`,
  ADD COLUMN IF NOT EXISTS `bg_url` VARCHAR(512) DEFAULT NULL COMMENT '背景图 URL' AFTER `avatar_url`;

-- ---- 新建 user_game_settings 表 ----
CREATE TABLE IF NOT EXISTS `user_game_settings` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `user_id` VARCHAR(32) NOT NULL COMMENT '用户ID（一对一关联 users 表）',
  `bgm_url` VARCHAR(512) DEFAULT NULL COMMENT '自定义 BGM 文件 URL',
  `bgm_volume` FLOAT NOT NULL DEFAULT 0.7 COMMENT 'BGM 音量 (0.0 ~ 1.0)',
  `bgm_enabled` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用 BGM',
  `sfx_volume` FLOAT NOT NULL DEFAULT 0.8 COMMENT '音效音量 (0.0 ~ 1.0)',
  `bg_url` VARCHAR(512) DEFAULT NULL COMMENT '自定义游戏背景图 URL',
  `text_speed` VARCHAR(16) NOT NULL DEFAULT 'normal' COMMENT '文字显示速度: slow / normal / fast / instant',
  `theme` VARCHAR(16) NOT NULL DEFAULT 'dark' COMMENT '界面主题: dark / light / custom',
  `font_size` INT NOT NULL DEFAULT 16 COMMENT '对话文字字号 (px)',
  `auto_advance` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否自动推进对话',
  `show_affection_popup` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否显示好感度变化弹窗',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_id` (`user_id`),
  CONSTRAINT `fk_settings_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户游戏设置表（一对一关联用户）';
