'use client'

import { useState, useRef, DragEvent, ChangeEvent } from 'react'

interface UploadZoneProps {
  onUpload: (files: File[]) => void
  uploading?: boolean
}

export function UploadZone({ onUpload, uploading }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDragIn = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(true)
  }

  const handleDragOut = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(false)
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      onUpload(files)
    }
  }

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) {
      onUpload(files)
    }
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  return (
    <div
      className={`upload-zone ${dragging ? 'dragging' : ''}`}
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={() => !uploading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.txt,.md,.json"
        onChange={handleChange}
        className="hidden"
        disabled={uploading}
      />
      <div className="upload-icon">📄</div>
      <div className="upload-text">
        {uploading ? 'Uploading...' : 'Drag & drop files here, or click to browse'}
      </div>
      <div className="upload-hint">
        Supports PDF, TXT, MD, and JSON files
      </div>
    </div>
  )
}