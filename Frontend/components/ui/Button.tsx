'use client'

import { ButtonHTMLAttributes, ReactNode } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: ReactNode
}

export function Button({ 
  variant = 'primary', 
  size = 'md', 
  loading, 
  children, 
  className = '',
  disabled,
  ...props 
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0a0a0f]'
  
  const variants = {
    primary: 'bg-[#6c63ff] text-white hover:bg-[#7c73ff] focus:ring-[#6c63ff]',
    secondary: 'bg-[#1a1a24] text-[#e8e8f0] border border-[#2a2a38] hover:border-[#3d3d52] focus:ring-[#2a2a38]',
    danger: 'bg-[#ef4444] text-white hover:bg-red-600 focus:ring-[#ef4444]'
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  }

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span className="mr-2 w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      )}
      {children}
    </button>
  )
}