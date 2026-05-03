'use client'

import useSWR from 'swr'
import { useState } from 'react'
import { getDocuments, uploadFiles } from '@/lib/api'
import type { Document } from '@/lib/types'

export function useDocuments() {
  const { data, error, mutate } = useSWR(
    '/api/docs',
    () => getDocuments().then(r => r.data),
    { refreshInterval: 5000 }
  )
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')

  async function upload(files: File[]) {
    setUploading(true)
    setUploadError('')
    try {
      await uploadFiles(files)
      await mutate()
    } catch (e: any) {
      setUploadError(e?.response?.data?.detail || 'Upload failed')
    } finally { setUploading(false) }
  }

  return {
    documents: (data || []) as Document[],
    loading: !data && !error,
    uploading, uploadError,
    upload, refresh: mutate,
  }
}