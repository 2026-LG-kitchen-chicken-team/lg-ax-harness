import { Component, createElement, useEffect, type ReactNode } from 'react'

export function SceneUnavailable({ onUnavailable }: { onUnavailable?: () => void } = {}) {
  useEffect(() => { onUnavailable?.() }, [onUnavailable])
  return createElement('div', { className: 'flex h-full items-center justify-center p-4', role: 'status' },
    createElement('p', { className: 'panel max-w-sm px-4 py-3 text-center text-[13px]' },
      '입체 화면을 표시하지 못했습니다. 진행 목록과 실행 기록에서 작업을 확인할 수 있습니다. 결과 링크도 계속 사용할 수 있습니다.'))
}

// Only the optional scene is inside this boundary; observations and their controls stay mounted.
export class SceneBoundary extends Component<{ children: ReactNode; onUnavailable?: () => void }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch() { this.props.onUnavailable?.() }
  render() { return this.state.failed ? createElement(SceneUnavailable) : this.props.children }
}
