import { useCallback, useState } from "react"
import { formatAskResult } from "../utils/formatAskResult"

type VoiceLanguage = "Unknown" | "Chinese" | "English"

function getPreferredAudioMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus"
  ]

  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || ""
}

export function useAudioAsk(onCompleted?: () => void) {
  const [recording, setRecording] = useState(false)
  const [recorder, setRecorder] = useState<MediaRecorder | null>(null)
  const [chunks, setChunks] = useState<BlobPart[]>([])
  const [mimeType, setMimeType] = useState("audio/webm")
  const [result, setResult] = useState("")
  const [language, setLanguage] = useState<VoiceLanguage>("Unknown")
  const [sendLoading, setSendLoading] = useState(false)

  const startRecording = useCallback(async () => {
    try {
      setResult("Requesting microphone permission...")
      setChunks([])
      setMimeType("audio/webm")
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      const preferredMimeType = getPreferredAudioMimeType()
      const nextRecorder = preferredMimeType
        ? new MediaRecorder(stream, { mimeType: preferredMimeType })
        : new MediaRecorder(stream)
      setMimeType(nextRecorder.mimeType || preferredMimeType || "audio/webm")
      const nextChunks: BlobPart[] = []

      nextRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) nextChunks.push(event.data)
      }
      nextRecorder.onstart = () => {
        setRecording(true)
        setResult("Recording. Please start speaking...")
      }
      nextRecorder.onerror = (event: any) => {
        setResult(`Recording error: ${event?.error?.message ?? "unknown error"}`)
        setRecording(false)
      }
      nextRecorder.onstop = () => {
        setChunks(nextChunks)
        setRecording(false)
        setRecorder(null)
        stream.getTracks().forEach((track) => track.stop())
        setResult("Recording stopped. You can send it to Whisper.")
      }

      nextRecorder.start(1000)
      setRecorder(nextRecorder)
    } catch (error: any) {
      console.error("Start recording failed:", error)
      setResult([
        "Failed to start recording",
        "",
        "Please check microphone permissions.",
        `Error: ${error?.message ?? String(error)}`
      ].join("\n"))
      setRecording(false)
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (!recorder) {
      setResult("No recording is currently running.")
      return
    }
    if (recorder.state === "recording") {
      try {
        recorder.requestData()
      } catch (error) {
        console.warn("Failed to flush recorder data before stopping:", error)
      }
    }
    recorder.stop()
  }, [recorder])

  const submitAudio = useCallback(async () => {
    setSendLoading(true)
    if (!chunks.length) {
      setResult("No audio data to send. Please record first.")
      setSendLoading(false)
      return
    }
    try {
      setResult("Uploading audio to local Whisper...")
      const audioBlob = new Blob(chunks, { type: mimeType || "audio/webm" })
      if (audioBlob.size === 0) {
        setResult("Audio data is empty. Please record again.")
        return
      }
      const audioExt = mimeType.includes("mp4")
        ? "m4a"
        : mimeType.includes("ogg")
          ? "ogg"
          : "webm"
      const formData = new FormData()
      formData.append("audio", audioBlob, `interview-audio.${audioExt}`)
      formData.append("language", language)
      formData.append("source", "stt")

      const res = await fetch("http://127.0.0.1:8000/ask_audio", { method: "POST", body: formData })
      const json = await res.json()

      if (!res.ok || json?.detail) {
        setResult(`Request failed: ${json?.detail ?? res.statusText}`)
        return
      }

      setResult(formatAskResult(json))
      onCompleted?.()
    } catch (error: any) {
      console.error("Send audio to Whisper failed:", error)
      setResult([
        "Voice interview request failed",
        "",
        "Please check the backend and Whisper service.",
        `Error: ${error?.message ?? String(error)}`
      ].join("\n"))
    } finally {
      setSendLoading(false)
    }
  }, [chunks, language, mimeType, onCompleted])

  const clearAudio = useCallback(() => {
    setChunks([])
    setResult("")
  }, [])

  return {
    language,
    setLanguage,
    recording,
    chunks,
    sendLoading,
    result,
    startRecording,
    stopRecording,
    submitAudio,
    clearAudio
  }
}
