/**
 * Home - 主菜单页
 * 织梦绮谭 - 精致二次元 Galgame 风格标题画面
 */

import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, FolderOpen, BookOpen, Settings, LogOut, User, Shield, ChevronRight, Globe, Users, BookMarked, Sparkles, HelpCircle, X } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'

/** 生成浮动光粒子数据 */
const useParticles = (count: number) =>
  useMemo(
    () =>
      Array.from({ length: count }, (_, i) => {
        const size = 2 + Math.random() * 5
        const isGlow = Math.random() > 0.5
        return {
          id: i,
          className: isGlow ? 'particle particle--glow' : 'particle particle--drift',
          style: {
            left: `${Math.random() * 100}%`,
            width: `${size}px`,
            height: `${size}px`,
            background: isGlow
              ? `radial-gradient(circle, rgba(168,130,255,${0.4 + Math.random() * 0.4}) 0%, transparent 70%)`
              : `radial-gradient(circle, rgba(244,114,182,${0.3 + Math.random() * 0.3}) 0%, transparent 70%)`,
            ['--duration' as string]: `${10 + Math.random() * 18}s`,
            ['--delay' as string]: `${Math.random() * 12}s`,
          },
        }
      }),
    [count],
  )

export const Home: React.FC = () => {
  const navigate = useNavigate()
  const particles = useParticles(28)
  const { user, isAuthenticated, logout } = useAuthStore()
  const [avatarFailed, setAvatarFailed] = React.useState(false)
  const [guideOpen, setGuideOpen] = React.useState(false)

  const handleLogout = () => {
    logout()
  }

  const menuItems = [
    { icon: Play, label: '开始新游戏', desc: '踏入新的故事世界', action: () => navigate('/template-select') },
    { icon: FolderOpen, label: '继续游戏', desc: '回到上次冒险', action: () => navigate('/load-save') },
    { icon: BookOpen, label: '模板管理', desc: '浏览与自定义模板', action: () => navigate('/templates') },
    { icon: Settings, label: '设置', desc: '调整游戏参数', action: () => navigate('/settings') },
  ]

  return (
    <div className="min-h-screen flex flex-col items-center justify-center
                    bg-gradient-to-b from-surface-dark via-surface to-surface-dark
                    relative overflow-hidden">

      {/* ====== 浮动光粒子背景 ====== */}
      {particles.map((p) => (
        <div key={p.id} className={p.className} style={p.style} />
      ))}

      {/* ====== 渐变光晕 ====== */}
      <div className="glow-orb"
        style={{
          top: '18%', left: '50%', transform: 'translateX(-50%)',
          width: '500px', height: '500px',
          background: 'radial-gradient(circle, rgba(168,130,255,0.15) 0%, transparent 70%)',
          ['--duration' as string]: '7s',
        }} />
      <div className="glow-orb"
        style={{
          bottom: '15%', right: '20%',
          width: '350px', height: '350px',
          background: 'radial-gradient(circle, rgba(244,114,182,0.12) 0%, transparent 70%)',
          ['--duration' as string]: '9s',
        }} />
      <div className="glow-orb"
        style={{
          top: '55%', left: '10%',
          width: '280px', height: '280px',
          background: 'radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)',
          ['--duration' as string]: '11s',
        }} />

      {/* ====== 右上角工具栏 ====== */}
      <div className="absolute top-5 right-6 z-20 flex items-center gap-2.5">
        {/* 玩法引导按钮 + 弹出面板 */}
        <div className="relative">
          <button
            onClick={() => setGuideOpen(!guideOpen)}
            className="glass-panel w-9 h-9 flex items-center justify-center
                       hover:border-primary/20 transition-all duration-200 group"
            title="玩法引导"
          >
            <HelpCircle size={15} className="text-text-dim/50 group-hover:text-primary-light transition-colors" />
          </button>

          {guideOpen && (
            <div className="absolute top-11 right-0 w-72 glass-panel p-4 animate-fade-in z-30">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles size={13} className="text-accent-light" />
                  <span className="text-text-bright text-sm font-medium">玩法引导</span>
                </div>
                <button onClick={() => setGuideOpen(false)} className="text-text-dim/40 hover:text-text-dim transition-colors">
                  <X size={14} />
                </button>
              </div>

              <p className="text-text-dim/60 text-[11px] leading-relaxed mb-3">
                推荐先创建自定义模板，打造独一无二的故事世界，再开始冒险。
              </p>

              <div className="space-y-1.5">
                {[
                  { icon: Globe, step: 1, title: '创建世界观', desc: '设定时代、地理、规则', target: '/templates?tab=world' },
                  { icon: Users, step: 2, title: '设计角色', desc: '性格、说话风格、关系', target: '/templates?tab=character' },
                  { icon: BookMarked, step: 3, title: '编写剧本', desc: '剧情走向、章节钩子', target: '/templates?tab=scenario' },
                  { icon: Play, step: 4, title: '选择模板开始', desc: '在「新游戏」中选用你的创作', target: '/template-select' },
                ].map(({ icon: Icon, step, title, desc, target }) => (
                  <button
                    key={step}
                    onClick={() => { navigate(target); setGuideOpen(false) }}
                    className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg
                               hover:bg-primary/5 transition-colors duration-200 group text-left"
                  >
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary-light text-[9px]
                                     font-bold flex items-center justify-center shrink-0">
                      {step}
                    </span>
                    <Icon size={12} className="text-text-dim/40 group-hover:text-primary-light shrink-0 transition-colors" />
                    <div className="flex-1 min-w-0">
                      <span className="text-text-bright text-[11px] font-medium block leading-tight">{title}</span>
                      <span className="text-text-dim/40 text-[10px] block">{desc}</span>
                    </div>
                  </button>
                ))}
              </div>

              <div className="mt-3 pt-2.5 border-t border-white/5">
                <p className="text-text-dim/30 text-[10px]">
                  想快速体验？直接在「开始新游戏」中选预置模板也可以。
                </p>
              </div>
            </div>
          )}
        </div>

        {isAuthenticated && user ? (
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/profile')}
              className="glass-panel flex items-center gap-2 px-4 py-2
                         hover:border-primary/20 transition-all duration-200"
              title="个人资料"
            >
              {user.avatar_url && !avatarFailed ? (
                <img
                  src={user.avatar_url}
                  alt="头像"
                  className="w-6 h-6 rounded-lg object-cover"
                  onError={() => setAvatarFailed(true)}
                />
              ) : user.role === 'admin' ? (
                <Shield size={14} className="text-amber-400" />
              ) : (
                <User size={14} className="text-primary-light" />
              )}
              <span className="text-text-bright text-sm font-medium">
                {user.display_name || user.username}
              </span>
              {user.role === 'admin' && (
                <span className="text-[10px] text-amber-400/80 bg-amber-400/10 px-1.5 py-0.5 rounded-md">
                  管理员
                </span>
              )}
            </button>
            <button
              onClick={handleLogout}
              className="glass-panel flex items-center gap-1.5 px-3 py-2
                         text-text-dim/60 hover:text-red-300 text-xs transition-colors duration-200"
              title="退出登录"
            >
              <LogOut size={13} />
              <span>退出</span>
            </button>
          </div>
        ) : (
          <button
            onClick={() => navigate('/login')}
            className="glass-panel flex items-center gap-1.5 px-4 py-2
                       text-primary-light hover:text-primary text-sm font-medium
                       transition-colors duration-200"
          >
            <User size={14} />
            <span>登录</span>
          </button>
        )}
      </div>

      {/* ====== 标题区域 ====== */}
      <div className="text-center mb-14 relative z-10 animate-fade-in">
        {/* 英文装饰文字 */}
        <p className="text-text-dim/50 text-[11px] tracking-[0.5em] mb-5 font-light uppercase">
          Weaving Dreams into Tales
        </p>

        {/* 主标题 - 渐变流光 */}
        <h1 className="title-shimmer text-6xl font-bold tracking-[0.15em] mb-3 font-display"
            style={{ lineHeight: 1.3 }}>
          织梦绮谭
        </h1>

        {/* 副标题 */}
        <p className="text-text-dim/40 text-xs tracking-[0.3em] font-light mt-4">
          AI Galgame Narrative System
        </p>

        {/* 装饰分割线 */}
        <div className="mx-auto mt-6 w-48 divider-gradient" />
      </div>

      {/* ====== 菜单按钮 ====== */}
      <div className="space-y-3 w-80 relative z-10">
        {menuItems.map(({ icon: Icon, label, desc, action }, i) => (
          <button
            key={label}
            onClick={action}
            className="choice-appear menu-item-glow glass-panel w-full flex items-center gap-4 px-5 py-4
                       group cursor-pointer"
            style={{ animationDelay: `${0.15 + i * 0.08}s` }}
          >
            {/* 图标容器 */}
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0
                            bg-gradient-to-br from-primary/15 to-accent/10
                            group-hover:from-primary/25 group-hover:to-accent/20
                            transition-all duration-300">
              <Icon size={18} className="text-primary-light group-hover:text-accent-light transition-colors duration-300" />
            </div>

            {/* 文本 */}
            <div className="text-left flex-1 min-w-0">
              <span className="text-text-bright text-[15px] font-medium block leading-tight">{label}</span>
              <span className="text-text-dim/50 text-xs mt-0.5 block">{desc}</span>
            </div>

            {/* 右箭头 */}
            <div className="opacity-0 group-hover:opacity-100 -translate-x-1
                            group-hover:translate-x-0 transition-all duration-300">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-primary-light">
                <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </button>
        ))}
      </div>

      {/* ====== 底部 ====== */}
      <div className="absolute bottom-6 text-center z-10">
        <div className="divider-gradient w-32 mx-auto mb-3" />
        <p className="text-text-dim/25 text-[11px] tracking-wider">
          v0.1.0 — Powered by DeepSeek
        </p>
      </div>
    </div>
  )
}
