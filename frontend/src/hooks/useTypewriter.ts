/**
 * Typewriter - 打字机效果 Hook
 * 让文字逐字显示，模拟 Galgame 的经典效果
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useUIStore } from '@/stores/uiStore'

export function useTypewriter(fullText: string, onComplete?: () => void) {
  const [displayedText, setDisplayedText] = useState('')
  const [isComplete, setIsComplete] = useState(false)
  const speed = useUIStore((s) => s.typewriterSpeed)
  const indexRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  // 当文本变化时重新开始打字
  useEffect(() => {
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
  }, [fullText, speed]) // eslint-disable-line react-hooks/exhaustive-deps

  // 点击跳过：立即显示全部文字
  const skip = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setDisplayedText(fullText)
    setIsComplete(true)
    onComplete?.()
  }, [fullText, onComplete])

  return { displayedText, isComplete, skip }
}
