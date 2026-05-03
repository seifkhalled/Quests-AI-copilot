'use client'

import { InputHTMLAttributes, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-[13px] text-[#8888a8] font-medium">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`
            bg-[#1a1a24] border border-[#2a2a38] rounded-lg px-4 py-3 
            text-[#e8e8f0] text-sm transition-all duration-150
            placeholder:text-[#5a5a78] focus:outline-none focus:border-[#6c63ff] focus:shadow-[0_0_0_3px_rgba(108,99,255,0.15)]
            disabled:opacity-50 disabled:cursor-not-allowed
            ${error ? 'border-[#ef4444] focus:border-[#ef4444] focus:shadow-[0_0_0_3px_rgba(239,68,68,0.15)]' : ''}
            ${className}
          `}
          {...props}
        />
        {error && (
          <span className="text-xs text-[#ef4444]">{error}</span>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'