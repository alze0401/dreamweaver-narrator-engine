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
  const doneRef = useRef(!animate)
  // 记录是否曾经启动过打字机（区分"从未动画"和"动画已完成"）
  const everAnimatedRef = useRef(animate)

  useEffect(() => {
    // 打字机已完成且之前启动过 → 不再重启（防循环）
    if (doneRef.current && everAnimatedRef.current) return

    if (!animate) {
      // 不需要动画 → 直接显示全文
      if (timerRef.current) clearTimeout(timerRef.current)
      setDisplayedText(fullText)
      setIsComplete(true)
      // 不设 doneRef、不设 everAnimated —— 后续 animate 变 true 时还需启动
      return
    }

    // 开始打字机动画
    everAnimatedRef.current = true
    setDisplayedText('')
    setIsComplete(false)
    doneRef.current = false
    indexRef.current = 0

    if (!fullText) {
      setIsComplete(true)
      doneRef.current = true
      onComplete?.()
      return
    }

    const tick = () => {
      if (indexRef.current < fullText.length) {
        indexRef.current++
        setDisplayedText(fullText.slice(0, indexRef.current))
        timerRef.current = setTimeout(tick, speed)
      } else {
        setIsComplete(true)
        doneRef.current = true
        onComplete?.()
      }
    }

    timerRef.current = setTimeout(tick, speed)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [fullText, animate]) // eslint-disable-line react-hooks/exhaustive-deps

  const skip = useCallback(() => {
    if (doneRef.current) return
    if (timerRef.current) clearTimeout(timerRef.current)
    setDisplayedText(fullText)
    setIsComplete(true)
    doneRef.current = true
    everAnimatedRef.current = true
    onComplete?.()
  }, [fullText, onComplete])

  return { displayedText, isComplete, skip }
}
