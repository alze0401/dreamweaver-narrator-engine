/**
 * Typewriter - 打字机效果 Hook
 * 让文字逐字显示，模拟 Galgame 的经典效果
 * @param fullText   完整文本
 * @param onComplete 打字完成回调
 * @param animate    是否播放打字动画（false 时直接显示全文）
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useUIStore } from '@/stores/uiStore'

export function useTypewriter(fullText: string, onComplete?: () => void, animate = true) {
  const [displayedText, setDisplayedText] = useState(animate ? '' : fullText)
  const [isComplete, setIsComplete] = useState(!animate)
  const speed = useUIStore((s) => s.typewriterSpeed)
  const indexRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  // 当文本变化或 animate 切换时重新处理
  useEffect(() => {
    if (!animate) {
      // 不需要动画 → 直接显示全文
      if (timerRef.current) clearTimeout(timerRef.current)
      setDisplayedText(fullText)
      setIsComplete(true)
      return
    }

    setDisplayedText('')
    setIsComplete(false)
    indexRef.current = 0

    if (!fullText) {
      setIsComplete(true)
      return
    }

    const tick = () => {
      if (indexRef.current < fullText.length) {
        indexRef.current++
        setDisplayedText(fullText.slice(0, indexRef.current))
        timerRef.current = setTimeout(tick, speed)
      } else {
        setIsComplete(true)
        onComplete?.()
      }
    }

    timerRef.current = setTimeout(tick, speed)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [fullText, speed, animate]) // eslint-disable-line react-hooks/exhaustive-deps

  // 点击跳过：立即显示全部文字
  const skip = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setDisplayedText(fullText)
    setIsComplete(true)
    onComplete?.()
  }, [fullText, onComplete])

  return { displayedText, isComplete, skip }
}
