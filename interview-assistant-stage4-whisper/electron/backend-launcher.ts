import { app } from "electron"
import { spawn, ChildProcess } from "child_process"
import path from "path"
import http from "http"
import fs from "fs"

/**
 * Backend lifecycle (M4).
 *
 * - Dev: the FastAPI backend is started separately (start-all.bat / uvicorn),
 *   so this is a no-op.
 * - Packaged: spawn the bundled PyInstaller sidecar (resources/backend/atlas-backend[.exe]),
 *   pointing it at a writable data dir under userData via env vars.
 */

const BACKEND_PORT = 8000
const HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/config/status`

let backendProcess: ChildProcess | null = null

function isBackendUp(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(HEALTH_URL, (res) => {
      res.resume()
      resolve((res.statusCode ?? 500) < 500)
    })
    req.on("error", () => resolve(false))
    req.setTimeout(1500, () => {
      req.destroy()
      resolve(false)
    })
  })
}

async function waitForBackend(timeoutMs = 90000): Promise<boolean> {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    if (await isBackendUp()) return true
    await new Promise((r) => setTimeout(r, 800))
  }
  return false
}

export async function startBackend(): Promise<void> {
  // Dev: backend runs separately.
  if (!app.isPackaged) return

  // Reuse an already-running backend if present.
  if (await isBackendUp()) {
    console.log("[backend] already running; reusing")
    return
  }

  const backendDir = path.join(process.resourcesPath, "backend")
  const exeName = process.platform === "win32" ? "atlas-backend.exe" : "atlas-backend"
  const exePath = path.join(backendDir, exeName)
  const dataDir = path.join(app.getPath("userData"), "atlas_data")
  const logPath = path.join(app.getPath("userData"), "atlas-backend.log")

  if (!fs.existsSync(exePath)) {
    console.error("[backend] sidecar exe not found:", exePath)
    return
  }

  // Capture backend stdout/stderr to a log file so packaged-build crashes are diagnosable.
  let logFd: number | undefined
  try {
    logFd = fs.openSync(logPath, "a")
  } catch {
    logFd = undefined
  }

  console.log("[backend] launching sidecar:", exePath)
  try {
    backendProcess = spawn(exePath, [], {
      cwd: backendDir,
      // NOTE: do NOT set ATLAS_RESOURCE_DIR — the frozen backend reads bundled
      // files via sys._MEIPASS (PyInstaller's _internal dir). Only the writable
      // data dir is redirected to userData.
      env: {
        ...process.env,
        ATLAS_DATA_DIR: dataDir,
        USE_OLLAMA: process.env.USE_OLLAMA ?? "true",
      },
      stdio: logFd !== undefined ? ["ignore", logFd, logFd] : "ignore",
      windowsHide: true,
    })
  } catch (error) {
    console.error("[backend] failed to spawn:", error)
    return
  }

  backendProcess.on("exit", (code) => {
    console.log("[backend] sidecar exited with code", code)
    backendProcess = null
  })

  const up = await waitForBackend()
  console.log(up ? "[backend] ready" : "[backend] did not become ready in time")
}

export function stopBackend(): void {
  if (backendProcess && !backendProcess.killed) {
    try {
      backendProcess.kill()
    } catch {
      /* ignore */
    }
    backendProcess = null
  }
}
