/**
 * ImageCropper - 类 QQ 头像裁剪选择器
 * 织梦绮谭 - 支持拖拽平移 + 滚轮缩放 + 实时圆形预览
 */

import React, { useRef, useState, useEffect, useCallback } from 'react'
import { ZoomIn, ZoomOut, RotateCcw, Check } from 'lucide-react'

interface Props {
  /** 原始图片源（File 对象或 URL 字符串） */
  imageSrc: File | string
  /** 裁剪区域大小（px），默认 200 */
  cropSize?: number
  /** 输出图片质量 0-1 */
  outputQuality?: number
  /** 确认裁剪 */
  onConfirm: (croppedBlob: Blob) => void
  /** 取消 */
  onCancel: () => void
}

export const ImageCropper: React.FC<Props> = ({
  imageSrc,
  cropSize = 200,
  outputQuality = 0.92,
  onConfirm,
  onCancel,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const previewCanvasRef = useRef<HTMLCanvasElement>(null)

  const [imgUrl, setImgUrl] = useState<string>('')
  const [imgNatural, setImgNatural] = useState({ w: 0, h: 0 })
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [dragging, setDragging] = useState(false)
  const dragStart = useRef({ x: 0, y: 0, ox: 0, oy: 0 })

  // ---- 加载图片 ----
  useEffect(() => {
    if (typeof imageSrc === 'string') {
      setImgUrl(imageSrc)
    } else {
      const url = URL.createObjectURL(imageSrc)
      setImgUrl(url)
      return () => URL.revokeObjectURL(url)
    }
  }, [imageSrc])

  // ---- 图片加载完成后初始化 ----
  const handleImageLoad = useCallback(() => {
    const img = imgRef.current
    if (!img) return
    const { naturalWidth: w, naturalHeight: h } = img
    setImgNatural({ w, h })

    // 计算初始缩放：让图片短边刚好填满裁剪区
    const container = containerRef.current
    if (!container) return
    const containerSize = cropSize
    const scaleX = containerSize / w
    const scaleY = containerSize / h
    const initialZoom = Math.max(scaleX, scaleY)
    setZoom(initialZoom)

    // 居中
    setOffset({
      x: (containerSize - w * initialZoom) / 2,
      y: (containerSize - h * initialZoom) / 2,
    })
  }, [cropSize])

  // ---- 拖拽平移 ----
  const handlePointerDown = (e: React.PointerEvent) => {
    e.preventDefault()
    setDragging(true)
    dragStart.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y }
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragging) return
    const dx = e.clientX - dragStart.current.x
    const dy = e.clientY - dragStart.current.y
    setOffset({
      x: dragStart.current.ox + dx,
      y: dragStart.current.oy + dy,
    })
  }

  const handlePointerUp = () => {
    setDragging(false)
  }

  // ---- 滚轮缩放 ----
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    setZoom((prev) => Math.max(0.1, Math.min(prev + delta * prev, 10)))
  }

  // ---- 按钮缩放 ----
  const zoomIn = () => setZoom((prev) => Math.min(prev * 1.2, 10))
  const zoomOut = () => setZoom((prev) => Math.max(prev / 1.2, 0.1))
  const resetView = () => {
    if (!imgNatural.w) return
    const containerSize = cropSize
    const scaleX = containerSize / imgNatural.w
    const scaleY = containerSize / imgNatural.h
    const initialZoom = Math.max(scaleX, scaleY)
    setZoom(initialZoom)
    setOffset({
      x: (containerSize - imgNatural.w * initialZoom) / 2,
      y: (containerSize - imgNatural.h * initialZoom) / 2,
    })
  }

  // ---- 实时预览（圆形裁剪区域） ----
  useEffect(() => {
    const previewCanvas = previewCanvasRef.current
    const img = imgRef.current
    if (!previewCanvas || !img || !imgNatural.w) return

    const ctx = previewCanvas.getContext('2d')
    if (!ctx) return

    const size = 100 // preview canvas size
    previewCanvas.width = size
    previewCanvas.height = size

    ctx.clearRect(0, 0, size, size)

    // 圆形裁剪
    ctx.save()
    ctx.beginPath()
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2)
    ctx.clip()

    // 计算源图坐标
    const scale = imgNatural.w / (img.width * zoom) // canvas px → natural px
    const sx = (-offset.x * scale)
    const sy = (-offset.y * scale)
    const sw = (cropSize * scale)
    const sh = (cropSize * scale)

    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, size, size)
    ctx.restore()

    // 圆形边框
    ctx.strokeStyle = 'rgba(168, 130, 255, 0.5)'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.arc(size / 2, size / 2, size / 2 - 1, 0, Math.PI * 2)
    ctx.stroke()
  }, [offset, zoom, imgNatural, cropSize])

  // ---- 确认裁剪 ----
  const handleConfirm = () => {
    const canvas = canvasRef.current
    const img = imgRef.current
    if (!canvas || !img || !imgNatural.w) return

    canvas.width = cropSize
    canvas.height = cropSize
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 圆形裁剪
    ctx.beginPath()
    ctx.arc(cropSize / 2, cropSize / 2, cropSize / 2, 0, Math.PI * 2)
    ctx.clip()

    // 计算源图坐标
    const displayW = imgNatural.w / zoom * (zoom) // = imgNatural.w at zoom=1
    const scale = imgNatural.w / (img.width * zoom)
    const sx = (-offset.x * scale)
    const sy = (-offset.y * scale)
    const sw = (cropSize * scale)
    const sh = (cropSize * scale)

    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, cropSize, cropSize)

    canvas.toBlob(
      (blob) => {
        if (blob) onConfirm(blob)
      },
      'image/webp',
      outputQuality,
    )
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="glass-panel p-6 max-w-md w-full mx-4 animate-fade-in" style={{ borderRadius: '20px' }}>
        <h3 className="text-text-bright text-base font-medium mb-4 text-center">
          裁剪头像
        </h3>

        {/* 裁剪区域 */}
        <div className="flex flex-col items-center gap-4">
          <div
            ref={containerRef}
            className="relative overflow-hidden rounded-full border-2 border-primary/30 cursor-move select-none"
            style={{ width: cropSize, height: cropSize }}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onWheel={handleWheel}
          >
            {imgUrl && (
              <img
                ref={imgRef}
                src={imgUrl}
                alt="头像预览"
                className="absolute top-0 left-0 select-none pointer-events-none"
                style={{
                  transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
                  transformOrigin: '0 0',
                  maxWidth: 'none',
                }}
                onLoad={handleImageLoad}
                crossOrigin="anonymous"
              />
            )}
            {/* 圆形裁剪遮罩（外部半透明） */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                boxShadow: `0 0 0 ${cropSize}px rgba(0,0,0,0.45)`,
                borderRadius: '50%',
              }}
            />
          </div>

          {/* 实时预览 */}
          <div className="flex items-center gap-4">
            <canvas
              ref={previewCanvasRef}
              width={100}
              height={100}
              className="rounded-full"
              style={{ width: 50, height: 50 }}
            />
            <div className="text-text-dim/60 text-xs">
              拖拽调整位置，滚轮缩放大小
            </div>
          </div>

          {/* 缩放控制 */}
          <div className="flex items-center gap-3">
            <button
              onClick={zoomOut}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                         bg-surface-light/30 hover:bg-surface-light/50 transition-colors"
            >
              <ZoomOut size={14} className="text-text-dim" />
            </button>
            <input
              type="range"
              min={0.1}
              max={5}
              step={0.01}
              value={zoom}
              onChange={(e) => setZoom(parseFloat(e.target.value))}
              className="w-32 h-1.5 appearance-none rounded-full bg-surface-light cursor-pointer
                         accent-primary [&::-webkit-slider-thumb]:appearance-none
                         [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5
                         [&::-webkit-slider-thumb]:rounded-full
                         [&::-webkit-slider-thumb]:bg-primary"
            />
            <button
              onClick={zoomIn}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                         bg-surface-light/30 hover:bg-surface-light/50 transition-colors"
            >
              <ZoomIn size={14} className="text-text-dim" />
            </button>
            <button
              onClick={resetView}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                         bg-surface-light/30 hover:bg-surface-light/50 transition-colors"
              title="重置"
            >
              <RotateCcw size={13} className="text-text-dim" />
            </button>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3 mt-5">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors
                       bg-surface-light/20 text-text-dim hover:text-text hover:bg-surface-light/30"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            className="flex-1 py-2.5 rounded-xl text-sm font-medium transition-all
                       btn-gradient text-white flex items-center justify-center gap-1.5"
          >
            <Check size={15} />
            确认裁剪
          </button>
        </div>

        {/* 隐藏的输出 canvas */}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </div>
  )
}
