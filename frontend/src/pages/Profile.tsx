/**
 * Profile - 用户个人资料页
 * 织梦绮谭 - 头像上传、修改昵称、修改密码
 */

import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Camera, Upload, Loader2, Check, Eye, EyeOff, Lock, User as UserIcon,
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { uploadApi, authApi } from '@/services/api'
import { ImageCropper } from '@/components/ImageCropper'


export const Profile: React.FC = () => {
  const navigate = useNavigate()
  const { user, isAuthenticated, setAuth } = useAuthStore()

  // ---- 头像 ----
  const avatarInputRef = useRef<HTMLInputElement>(null)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [cropImageSrc, setCropImageSrc] = useState<File | null>(null)
  const [avatarImgFailed, setAvatarImgFailed] = useState(false)

  // ---- 昵称 ----
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [savingName, setSavingName] = useState(false)
  const [nameSaved, setNameSaved] = useState(false)

  // ---- 修改密码 ----
  const [showOldPw, setShowOldPw] = useState(false)
  const [showNewPw, setShowNewPw] = useState(false)
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [changingPw, setChangingPw] = useState(false)
  const [pwMsg, setPwMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-dark">
        <div className="glass-panel p-8 text-center max-w-sm">
          <p className="text-text text-lg mb-4">请先登录后使用</p>
          <button
            onClick={() => navigate('/login')}
            className="btn-gradient px-6 py-2 rounded-xl text-sm text-white font-medium"
          >
            前往登录
          </button>
        </div>
      </div>
    )
  }

  // ---- 头像上传 ----
  const handleAvatarClick = () => avatarInputRef.current?.click()
  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setCropImageSrc(file)
    e.target.value = ''
  }

  const handleCropConfirm = async (croppedBlob: Blob) => {
    setCropImageSrc(null)
    const previewUrl = URL.createObjectURL(croppedBlob)
    setAvatarPreview(previewUrl)
    setAvatarImgFailed(false)
    setAvatarUploading(true)
    try {
      const croppedFile = new File([croppedBlob], 'avatar.webp', { type: 'image/webp' })
      const { url } = await uploadApi.avatar(croppedFile)
      if (user) {
        const updatedUser = { ...user, avatar_url: url }
        setAuth(useAuthStore.getState().token!, updatedUser)
      }
      setAvatarPreview(url)
    } catch (err: any) {
      alert(`头像上传失败: ${err.message}`)
      setAvatarPreview(null)
    } finally {
      setAvatarUploading(false)
      URL.revokeObjectURL(previewUrl)
    }
  }

  const handleCropCancel = () => {
    setCropImageSrc(null)
  }

  // ---- 修改昵称 ----
  const handleSaveName = async () => {
    if (!displayName.trim()) return
    setSavingName(true)
    try {
      const updated = await authApi.updateProfile({ display_name: displayName.trim() })
      if (user) {
        setAuth(useAuthStore.getState().token!, {
          ...user,
          display_name: updated.display_name,
        })
      }
      setNameSaved(true)
      setTimeout(() => setNameSaved(false), 1500)
    } catch (err: any) {
      alert(`修改失败: ${err.message}`)
    } finally {
      setSavingName(false)
    }
  }

  // ---- 修改密码 ----
  const handleChangePassword = async () => {
    setPwMsg(null)
    if (!oldPassword || !newPassword) {
      setPwMsg({ type: 'err', text: '请填写完整' })
      return
    }
    if (newPassword.length < 6) {
      setPwMsg({ type: 'err', text: '新密码至少 6 位' })
      return
    }
    if (newPassword !== confirmPassword) {
      setPwMsg({ type: 'err', text: '两次输入的密码不一致' })
      return
    }
    setChangingPw(true)
    try {
      await authApi.changePassword(oldPassword, newPassword)
      setPwMsg({ type: 'ok', text: '密码修改成功' })
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setPwMsg({ type: 'err', text: err.message || '修改失败' })
    } finally {
      setChangingPw(false)
    }
  }

  const displayAvatar = avatarPreview || user?.avatar_url || null
  const inputCls =
    'w-full bg-surface-dark/60 border border-white/[0.06] focus:border-primary/40 rounded-xl px-4 py-3 text-text-bright text-sm outline-none transition-colors placeholder:text-text-dim/30'

  return (
    <div className="min-h-screen bg-gradient-to-b from-surface-dark via-surface to-surface-dark py-8 px-4">
      <div className="max-w-xl mx-auto">

        {/* ---- 顶部导航 ---- */}
        <div className="flex items-center justify-between mb-8 animate-fade-in">
          <button
            onClick={() => navigate('/')}
            className="glass-panel flex items-center gap-2 px-4 py-2
                       text-text-dim hover:text-text-bright text-sm transition-colors duration-200"
          >
            <ArrowLeft size={15} />
            <span>返回首页</span>
          </button>
        </div>

        {/* ---- 页面标题 ---- */}
        <div className="text-center mb-10 animate-fade-in">
          <h1 className="title-shimmer text-3xl font-bold tracking-wider font-display">
            个人资料
          </h1>
          <p className="text-text-dim/40 text-xs tracking-widest mt-2">
            PROFILE & ACCOUNT SETTINGS
          </p>
        </div>

        <div className="space-y-6">

          {/* ==========================================
              头像区域
              ========================================== */}
          <section className="glass-panel p-6 choice-appear">
            <div className="flex items-center gap-2 mb-5">
              <Camera size={16} className="text-primary-light" />
              <h3 className="text-text-bright text-sm font-medium tracking-wide">个人头像</h3>
              <div className="flex-1 divider-gradient ml-2" />
            </div>
            <div className="flex items-center gap-6">
              <button
                onClick={handleAvatarClick}
                className="relative group w-24 h-24 rounded-2xl overflow-hidden shrink-0
                           bg-surface-light border border-white/5
                           hover:border-primary/30 transition-all duration-300"
              >
                {displayAvatar && !avatarImgFailed ? (
                  <img src={displayAvatar} alt="头像" className="w-full h-full object-cover"
                       onError={() => setAvatarImgFailed(true)} />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-4xl font-display text-primary/40">
                      {(user?.display_name || user?.username || '?')[0]}
                    </span>
                  </div>
                )}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100
                                flex items-center justify-center transition-opacity duration-200">
                  {avatarUploading ? (
                    <Loader2 size={24} className="animate-spin text-white" />
                  ) : (
                    <Upload size={20} className="text-white" />
                  )}
                </div>
              </button>
              <div className="flex-1">
                <p className="text-text text-sm mb-1">{user?.display_name || user?.username}</p>
                <p className="text-text-dim/50 text-xs mb-3">
                  点击头像上传，支持 PNG / JPEG / WebP，最大 5MB
                </p>
                <button
                  onClick={handleAvatarClick}
                  className="text-xs text-primary-light hover:text-accent-light transition-colors"
                >
                  {displayAvatar ? '更换头像' : '上传头像'}
                </button>
              </div>
            </div>
            <input
              ref={avatarInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className="hidden"
              onChange={handleAvatarChange}
            />
          </section>

          {/* ==========================================
              基本信息
              ========================================== */}
          <section className="glass-panel p-6 choice-appear">
            <div className="flex items-center gap-2 mb-5">
              <UserIcon size={16} className="text-primary-light" />
              <h3 className="text-text-bright text-sm font-medium tracking-wide">基本信息</h3>
              <div className="flex-1 divider-gradient ml-2" />
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-text-dim/70 text-xs block mb-2 tracking-wide">用户名</label>
                <input
                  type="text"
                  value={user?.username || ''}
                  disabled
                  className={`${inputCls} opacity-50 cursor-not-allowed`}
                />
                <p className="text-text-dim/30 text-[10px] mt-1">用户名不可修改</p>
              </div>
              <div>
                <label className="text-text-dim/70 text-xs block mb-2 tracking-wide">显示昵称</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="输入显示名称"
                    className={inputCls}
                  />
                  <button
                    onClick={handleSaveName}
                    disabled={!displayName.trim() || savingName || displayName === (user?.display_name || '')}
                    className={`shrink-0 flex items-center gap-1.5 px-4 rounded-xl text-xs font-medium transition-all duration-200
                      ${(!displayName.trim() || savingName || displayName === (user?.display_name || ''))
                        ? 'bg-surface-light/20 text-text-dim/40 cursor-not-allowed border border-white/[0.04]'
                        : 'btn-gradient text-white'
                      }`}
                  >
                    {savingName ? <Loader2 size={13} className="animate-spin" /> :
                     nameSaved ? <Check size={13} /> :
                     <Check size={13} />}
                    {nameSaved ? '已保存' : '保存'}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-text-dim/70 text-xs block mb-2 tracking-wide">角色</label>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2.5 py-1 rounded-lg ${
                    user?.role === 'admin'
                      ? 'bg-amber-400/10 text-amber-400 border border-amber-400/20'
                      : 'bg-primary/10 text-primary-light border border-primary/20'
                  }`}>
                    {user?.role === 'admin' ? '管理员' : '普通用户'}
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* ==========================================
              修改密码
              ========================================== */}
          <section className="glass-panel p-6 choice-appear">
            <div className="flex items-center gap-2 mb-5">
              <Lock size={16} className="text-primary-light" />
              <h3 className="text-text-bright text-sm font-medium tracking-wide">修改密码</h3>
              <div className="flex-1 divider-gradient ml-2" />
            </div>
            <div className="space-y-4">
              {/* 旧密码 */}
              <div>
                <label className="text-text-dim/70 text-xs block mb-2 tracking-wide">当前密码</label>
                <div className="relative">
                  <input
                    type={showOldPw ? 'text' : 'password'}
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    placeholder="输入当前密码"
                    className={`${inputCls} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowOldPw(!showOldPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-dim/40 hover:text-text-dim transition-colors"
                  >
                    {showOldPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              {/* 新密码 */}
              <div>
                <label className="text-text-dim/70 text-xs block mb-2 tracking-wide">新密码</label>
                <div className="relative">
                  <input
                    type={showNewPw ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="至少 6 位"
                    className={`${inputCls} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPw(!showNewPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-dim/40 hover:text-text-dim transition-colors"
                  >
                    {showNewPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              {/* 确认新密码 */}
              <div>
                <label className="text-text-dim/70 text-xs block mb-2 tracking-wide">确认新密码</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="再次输入新密码"
                  className={inputCls}
                />
              </div>

              {/* 提示消息 */}
              {pwMsg && (
                <p className={`text-xs ${pwMsg.type === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pwMsg.text}
                </p>
              )}

              <button
                onClick={handleChangePassword}
                disabled={changingPw || !oldPassword || !newPassword}
                className={`flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                  ${(!oldPassword || !newPassword || changingPw)
                    ? 'bg-surface-light/20 text-text-dim/40 cursor-not-allowed border border-white/[0.04]'
                    : 'btn-gradient text-white shadow-[0_4px_16px_rgba(168,130,255,0.25)]'
                  }`}
              >
                {changingPw ? <Loader2 size={13} className="animate-spin" /> : <Lock size={13} />}
                {changingPw ? '修改中...' : '确认修改'}
              </button>
            </div>
          </section>

        </div>

        <div className="h-12" />
      </div>

      {/* 头像裁剪器 */}
      {cropImageSrc && (
        <ImageCropper
          imageSrc={cropImageSrc}
          cropSize={240}
          onConfirm={handleCropConfirm}
          onCancel={handleCropCancel}
        />
      )}
    </div>
  )
}
