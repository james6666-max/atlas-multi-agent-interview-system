import { useCallback, useState } from "react"
import { formatAskResult } from "../utils/formatAskResult"
import { useI18n } from "../i18n/LanguageProvider"

// OCR detection runs (and uploads) much faster on a bounded image, and the
// model rescales internally anyway — text recognition is unaffected at this
// size. Images already within the cap are passed through untouched.
const OCR_MAX_DIMENSION = 2000

async function dataUrlToFile(dataUrl: string, filename: string) {
  const response = await fetch(dataUrl)
  const blob = await response.blob()
  const type = blob.type || "image/png"
  return new File([blob], filename, { type })
}

async function downscaleForOcr(file: File): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file)
    const longest = Math.max(bitmap.width, bitmap.height)
    if (longest <= OCR_MAX_DIMENSION) {
      bitmap.close()
      return file
    }
    const scale = OCR_MAX_DIMENSION / longest
    const canvas = document.createElement("canvas")
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    const ctx = canvas.getContext("2d")
    if (!ctx) {
      bitmap.close()
      return file
    }
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.92)
    )
    if (!blob) return file
    const name = file.name.replace(/\.[^.]+$/, "") + ".jpg"
    return new File([blob], name, { type: "image/jpeg" })
  } catch {
    // Any decode/canvas failure: fall back to the original image.
    return file
  }
}

async function postImageFileToAtlas(image: Blob, filename = "screenshot.png", language = "Unknown") {
  const formData = new FormData()
  formData.append("image", image, filename)
  formData.append("language", language)
  formData.append("source", "ocr")

  const res = await fetch("http://127.0.0.1:8000/ask_image_file", {
    method: "POST",
    body: formData
  })

  const text = await res.text()
  let json: any = {}
  try {
    json = text ? JSON.parse(text) : {}
  } catch {
    json = {}
  }
  if (!res.ok || json?.detail) {
    throw new Error(json?.detail ?? text ?? `HTTP ${res.status}`)
  }

  return json
}

export function useImageAsk(onCompleted?: () => void) {
  const { apiLanguage, lang } = useI18n()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState("")

  const captureAndUpload = useCallback(async (
    trigger: () => Promise<any>,
    captureLabel: string,
    filename: string
  ) => {
    setResult(captureLabel)
    return await new Promise<any>((resolve, reject) => {
      let finished = false
      const unsubscribe = window.electronAPI.onScreenshotTaken(async (data: { path: string; preview: string }) => {
        if (finished) return
        finished = true
        try {
          setResult("Uploading screenshot to OCR...")
          const rawFile = await dataUrlToFile(data.preview, filename)
          const imageFile = await downscaleForOcr(rawFile)
          const json = await postImageFileToAtlas(imageFile, imageFile.name, apiLanguage)
          if (typeof unsubscribe === "function") unsubscribe()
          resolve(json)
        } catch (error) {
          if (typeof unsubscribe === "function") unsubscribe()
          reject(error)
        }
      })

      trigger()
        .then((screenshotResult: any) => {
          if (screenshotResult?.cancelled) {
            finished = true
            if (typeof unsubscribe === "function") unsubscribe()
            resolve({ cancelled: true })
            return
          }
          if (screenshotResult?.error) {
            finished = true
            if (typeof unsubscribe === "function") unsubscribe()
            reject(new Error(screenshotResult.error))
          }
        })
        .catch((error: any) => {
          finished = true
          if (typeof unsubscribe === "function") unsubscribe()
          reject(error)
        })

      window.setTimeout(() => {
        if (finished) return
        finished = true
        if (typeof unsubscribe === "function") unsubscribe()
        reject(new Error("Screenshot timed out. Please try again."))
      }, 30000)
    })
  }, [apiLanguage])

  const submitImage = useCallback(async () => {
    try {
      setLoading(true)

      if (window.electronAPI?.triggerScreenshot) {
        const response = await captureAndUpload(
          () => window.electronAPI.triggerScreenshot(),
          "Taking screenshot...",
          "screenshot.png"
        )

        if (response?.detail) {
          setResult(`Request failed: ${response.detail}`)
          return
        }

        setResult(formatAskResult(response, lang))
        onCompleted?.()
        return
      }

      setResult("Select an image file...")
      const input = document.createElement("input")
      input.type = "file"
      input.accept = "image/*"

      const file = await new Promise<File | null>((resolve) => {
        input.onchange = () => resolve(input.files?.[0] || null)
        input.click()
      })

      if (!file) {
        setResult("Selection cancelled")
        return
      }

      setResult("Uploading image...")
      const scaledFile = await downscaleForOcr(file)
      const response = await postImageFileToAtlas(scaledFile, scaledFile.name, apiLanguage)
      if (response?.detail) {
        setResult(`Request failed: ${response.detail}`)
        return
      }

      setResult(formatAskResult(response, lang))
      onCompleted?.()
    } catch (error: any) {
      console.error("Local ask image failed:", error)
      setResult([
        "Screenshot question failed",
        "",
        "Please check whether the FastAPI backend is running.",
        `Error: ${error?.message ?? String(error)}`
      ].join("\n"))
    } finally {
      setLoading(false)
    }
  }, [onCompleted, captureAndUpload, apiLanguage, lang])

  const submitRegionImage = useCallback(async () => {
    try {
      setLoading(true)

      if (!window.electronAPI?.triggerRegionScreenshot) {
        setResult("Region screenshot is not available in this environment.")
        return
      }

      const response = await captureAndUpload(
        () => window.electronAPI.triggerRegionScreenshot(),
        "Select a screenshot region...",
        "region-screenshot.png"
      )

      if (response?.cancelled) {
        setResult("Region screenshot cancelled")
        return
      }
      if (response?.detail) {
        setResult(`Request failed: ${response.detail}`)
        return
      }

      setResult(formatAskResult(response, lang))
      onCompleted?.()
    } catch (error: any) {
      console.error("Local ask region image failed:", error)
      setResult([
        "Region screenshot question failed",
        "",
        "Please check whether the FastAPI backend is running.",
        `Error: ${error?.message ?? String(error)}`
      ].join("\n"))
    } finally {
      setLoading(false)
    }
  }, [onCompleted, captureAndUpload, lang])

  const clearImage = useCallback(() => setResult(""), [])

  return {
    loading,
    result,
    submitImage,
    submitRegionImage,
    clearImage
  }
}
