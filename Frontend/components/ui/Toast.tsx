'use client'

import { useEffect, useState, createContext, useContext, ReactNode, useCallback } from 'react'

interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'warning'
}

interface ToastContextType {
  showToast: (message: string, type: Toast['type']) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback((message: string, type: Toast['type']) => {
    const id = Math.random().toString(36).slice(2)
    setToasts(prev => [...prev, { id, message, type }])
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-50">
        {toasts.map(toast => (
          <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000)
    return () => clearTimeout(timer)
  }, [onClose])

  const styles = {
    success: 'bg-[#22c55e] text-black',
    error: 'bg-[#ef4444] text-white',
    warning: 'bg-[#f59e0b] text-black'
  }

  return (
    <div 
      style={{
        animation: 'slideIn 200ms ease'
      }}
      className={`
        px-4 py-3 rounded-lg text-sm flex items-center gap-2
        ${styles[toast.type]}
      `}
    >
      <span>{toast.message}</span>
      <button onClick={onClose} className="ml-2 opacity-70 hover:opacity-100">×</button>
    </div>
  )
}