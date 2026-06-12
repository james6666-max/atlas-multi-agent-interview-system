// ScreenshotHelper.ts

import path from "node:path";
import fs from "node:fs";
import { app, BrowserWindow, ipcMain, nativeImage, screen } from "electron";
import type { Display, Rectangle } from "electron";
import { v4 as uuidv4 } from "uuid";
import { execFile } from "child_process";
import { promisify } from "util";
import screenshot from "screenshot-desktop";

const execFileAsync = promisify(execFile);

export class ScreenshotHelper {
  private screenshotQueue: string[] = [];
  private extraScreenshotQueue: string[] = [];
  private readonly MAX_SCREENSHOTS = 5;

  private readonly screenshotDir: string;
  private readonly extraScreenshotDir: string;
  private readonly tempDir: string;

  private view: "queue" | "solutions" | "debug" = "queue";

  constructor(view: "queue" | "solutions" | "debug" = "queue") {
    this.view = view;

    // Initialize directories
    this.screenshotDir = path.join(app.getPath("userData"), "screenshots");
    this.extraScreenshotDir = path.join(
      app.getPath("userData"),
      "extra_screenshots"
    );
    this.tempDir = path.join(
      app.getPath("temp"),
      "interview-assistant-screenshots"
    );

    // Create directories if they don't exist
    this.ensureDirectoriesExist();

    // Clean existing screenshot directories when starting the app
    this.cleanScreenshotDirectories();
  }

  private ensureDirectoriesExist(): void {
    const directories = [
      this.screenshotDir,
      this.extraScreenshotDir,
      this.tempDir,
    ];

    for (const dir of directories) {
      if (!fs.existsSync(dir)) {
        try {
          fs.mkdirSync(dir, { recursive: true });
          console.log(`Created directory: ${dir}`);
        } catch (err) {
          console.error(`Error creating directory ${dir}:`, err);
        }
      }
    }
  }

  // This method replaces loadExistingScreenshots() to ensure we start with empty queues
  private cleanScreenshotDirectories(): void {
    try {
      // Clean main screenshots directory
      if (fs.existsSync(this.screenshotDir)) {
        const files = fs
          .readdirSync(this.screenshotDir)
          .filter((file) => file.endsWith(".png"))
          .map((file) => path.join(this.screenshotDir, file));

        // Delete each screenshot file
        for (const file of files) {
          try {
            fs.unlinkSync(file);
            console.log(`Deleted existing screenshot: ${file}`);
          } catch (err) {
            console.error(`Error deleting screenshot ${file}:`, err);
          }
        }
      }

      // Clean extra screenshots directory
      if (fs.existsSync(this.extraScreenshotDir)) {
        const files = fs
          .readdirSync(this.extraScreenshotDir)
          .filter((file) => file.endsWith(".png"))
          .map((file) => path.join(this.extraScreenshotDir, file));

        // Delete each screenshot file
        for (const file of files) {
          try {
            fs.unlinkSync(file);
            console.log(`Deleted existing extra screenshot: ${file}`);
          } catch (err) {
            console.error(`Error deleting extra screenshot ${file}:`, err);
          }
        }
      }

      console.log("Screenshot directories cleaned successfully");
    } catch (err) {
      console.error("Error cleaning screenshot directories:", err);
    }
  }

  public getView(): "queue" | "solutions" | "debug" {
    return this.view;
  }

  public setView(view: "queue" | "solutions" | "debug"): void {
    console.log("Setting view in ScreenshotHelper:", view);
    console.log(
      "Current queues - Main:",
      this.screenshotQueue,
      "Extra:",
      this.extraScreenshotQueue
    );
    this.view = view;
  }

  public getScreenshotQueue(): string[] {
    return this.screenshotQueue;
  }

  public getExtraScreenshotQueue(): string[] {
    console.log("Getting extra screenshot queue:", this.extraScreenshotQueue);
    return this.extraScreenshotQueue;
  }

  public clearQueues(): void {
    // Clear screenshotQueue
    this.screenshotQueue.forEach((screenshotPath) => {
      fs.unlink(screenshotPath, (err) => {
        if (err)
          console.error(`Error deleting screenshot at ${screenshotPath}:`, err);
      });
    });
    this.screenshotQueue = [];

    // Clear extraScreenshotQueue
    this.extraScreenshotQueue.forEach((screenshotPath) => {
      fs.unlink(screenshotPath, (err) => {
        if (err)
          console.error(
            `Error deleting extra screenshot at ${screenshotPath}:`,
            err
          );
      });
    });
    this.extraScreenshotQueue = [];
  }

  private async captureScreenshot(): Promise<Buffer> {
    try {
      console.log("Starting screenshot capture...");

      // For Windows, try multiple methods
      if (process.platform === "win32") {
        return await this.captureWindowsScreenshot();
      }

      // For macOS and Linux, use buffer directly
      console.log("Taking screenshot on non-Windows platform");
      const buffer = await screenshot({ format: "png" });
      console.log(
        `Screenshot captured successfully, size: ${buffer.length} bytes`
      );
      return buffer;
    } catch (error) {
      console.error("Error capturing screenshot:", error);
      throw new Error(`Failed to capture screenshot: ${(error as Error).message}`);
    }
  }

  private async chooseScreenshotRegion(display: Display): Promise<Rectangle | null> {
    const channelId = uuidv4();
    const selectedChannel = `region-screenshot-selected-${channelId}`;
    const cancelChannel = `region-screenshot-cancel-${channelId}`;
    const overlay = new BrowserWindow({
      x: display.bounds.x,
      y: display.bounds.y,
      width: display.bounds.width,
      height: display.bounds.height,
      frame: false,
      fullscreen: false,
      transparent: true,
      resizable: false,
      movable: false,
      alwaysOnTop: true,
      skipTaskbar: true,
      hasShadow: false,
      focusable: true,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
      },
    });

    overlay.setAlwaysOnTop(true, "screen-saver", 2);

    const html = `
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      html, body {
        height: 100%;
        margin: 0;
        overflow: hidden;
        cursor: crosshair;
        user-select: none;
        background: rgba(0, 0, 0, 0.38);
        font-family: "Segoe UI", system-ui, sans-serif;
      }
      .hint {
        position: fixed;
        left: 50%;
        top: 28px;
        transform: translateX(-50%);
        padding: 8px 12px;
        border-radius: 6px;
        background: rgba(10, 12, 18, 0.88);
        color: rgba(255, 255, 255, 0.92);
        font-size: 13px;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.32);
        pointer-events: none;
      }
      .selection {
        position: fixed;
        display: none;
        border: 2px solid #60a5fa;
        background: rgba(96, 165, 250, 0.18);
        box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.24);
        pointer-events: none;
      }
    </style>
  </head>
  <body>
    <div class="hint">拖拽选择截图区域，Esc 或右键取消</div>
    <div id="selection" class="selection"></div>
    <script>
      const { ipcRenderer } = require("electron");
      const box = document.getElementById("selection");
      let start = null;
      let active = false;

      function draw(current) {
        const x = Math.min(start.x, current.x);
        const y = Math.min(start.y, current.y);
        const width = Math.abs(current.x - start.x);
        const height = Math.abs(current.y - start.y);
        box.style.display = "block";
        box.style.left = x + "px";
        box.style.top = y + "px";
        box.style.width = width + "px";
        box.style.height = height + "px";
      }

      window.addEventListener("mousedown", (event) => {
        if (event.button !== 0) {
          ipcRenderer.send("${cancelChannel}");
          return;
        }
        active = true;
        start = { x: event.clientX, y: event.clientY };
        draw(start);
      });

      window.addEventListener("mousemove", (event) => {
        if (!active || !start) return;
        draw({ x: event.clientX, y: event.clientY });
      });

      window.addEventListener("mouseup", (event) => {
        if (!active || !start || event.button !== 0) return;
        active = false;
        const x = Math.min(start.x, event.clientX);
        const y = Math.min(start.y, event.clientY);
        const width = Math.abs(event.clientX - start.x);
        const height = Math.abs(event.clientY - start.y);
        if (width < 8 || height < 8) {
          ipcRenderer.send("${cancelChannel}");
          return;
        }
        ipcRenderer.send("${selectedChannel}", { x, y, width, height });
      });

      window.addEventListener("keydown", (event) => {
        if (event.key === "Escape") ipcRenderer.send("${cancelChannel}");
      });

      window.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        ipcRenderer.send("${cancelChannel}");
      });
    </script>
  </body>
</html>`;

    return await new Promise<Rectangle | null>((resolve) => {
      let resolved = false;
      const finish = (region: Rectangle | null) => {
        if (resolved) return;
        resolved = true;
        ipcMain.removeAllListeners(selectedChannel);
        ipcMain.removeAllListeners(cancelChannel);
        overlay.close();
        resolve(region);
      };

      ipcMain.once(selectedChannel, (_event, region: Rectangle) => finish(region));
      ipcMain.once(cancelChannel, () => finish(null));
      overlay.once("closed", () => finish(null));

      // Show only after the dimmed page has rendered. While the document is
      // still loading the window is fully transparent, and Windows makes
      // alpha-0 areas of transparent windows click-through — clicks would
      // land on the window below (e.g. a chat app) instead of starting the
      // selection.
      let shown = false;
      const reveal = () => {
        if (shown || overlay.isDestroyed()) return;
        shown = true;
        overlay.show();
        overlay.focus();
      };
      overlay.webContents.once("did-finish-load", reveal);
      // Safety net: never leave an invisible overlay blocking the flow.
      setTimeout(reveal, 800);

      overlay.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
    });
  }

  private cropScreenshotBuffer(screenshotBuffer: Buffer, selection: Rectangle, displayBounds: Rectangle): Buffer {
    const image = nativeImage.createFromBuffer(screenshotBuffer);
    const imageSize = image.getSize();
    const displays = screen.getAllDisplays();
    const left = Math.min(...displays.map((display) => display.bounds.x));
    const top = Math.min(...displays.map((display) => display.bounds.y));
    const right = Math.max(...displays.map((display) => display.bounds.x + display.bounds.width));
    const bottom = Math.max(...displays.map((display) => display.bounds.y + display.bounds.height));
    const virtualWidth = right - left;
    const virtualHeight = bottom - top;
    const scaleX = imageSize.width / virtualWidth;
    const scaleY = imageSize.height / virtualHeight;

    // TODO: Multi-display + mixed-DPI setups may need per-display scaling. This
    // maps primary-display DIP coordinates into the captured virtual desktop.
    const cropRect = {
      x: Math.max(0, Math.round((displayBounds.x + selection.x - left) * scaleX)),
      y: Math.max(0, Math.round((displayBounds.y + selection.y - top) * scaleY)),
      width: Math.max(1, Math.round(selection.width * scaleX)),
      height: Math.max(1, Math.round(selection.height * scaleY)),
    };

    cropRect.width = Math.min(cropRect.width, imageSize.width - cropRect.x);
    cropRect.height = Math.min(cropRect.height, imageSize.height - cropRect.y);

    return image.crop(cropRect).toPNG();
  }

  private async saveScreenshotBuffer(screenshotBuffer: Buffer): Promise<string> {
    let screenshotPath = "";

    if (this.view === "queue") {
      screenshotPath = path.join(this.screenshotDir, `${uuidv4()}.png`);
      const screenshotDir = path.dirname(screenshotPath);
      if (!fs.existsSync(screenshotDir)) {
        fs.mkdirSync(screenshotDir, { recursive: true });
      }
      await fs.promises.writeFile(screenshotPath, screenshotBuffer);
      console.log("Adding screenshot to main queue:", screenshotPath);
      this.screenshotQueue.push(screenshotPath);
      if (this.screenshotQueue.length > this.MAX_SCREENSHOTS) {
        const removedPath = this.screenshotQueue.shift();
        if (removedPath) {
          try {
            await fs.promises.unlink(removedPath);
            console.log("Removed old screenshot from main queue:", removedPath);
          } catch (error) {
            console.error("Error removing old screenshot:", error);
          }
        }
      }
    } else {
      screenshotPath = path.join(this.extraScreenshotDir, `${uuidv4()}.png`);
      const screenshotDir = path.dirname(screenshotPath);
      if (!fs.existsSync(screenshotDir)) {
        fs.mkdirSync(screenshotDir, { recursive: true });
      }
      await fs.promises.writeFile(screenshotPath, screenshotBuffer);
      console.log("Adding screenshot to extra queue:", screenshotPath);
      this.extraScreenshotQueue.push(screenshotPath);
      if (this.extraScreenshotQueue.length > this.MAX_SCREENSHOTS) {
        const removedPath = this.extraScreenshotQueue.shift();
        if (removedPath) {
          try {
            await fs.promises.unlink(removedPath);
            console.log("Removed old screenshot from extra queue:", removedPath);
          } catch (error) {
            console.error("Error removing old screenshot:", error);
          }
        }
      }
    }

    return screenshotPath;
  }

  /**
   * Windows-specific screenshot capture with multiple fallback mechanisms
   */
  private async captureWindowsScreenshot(): Promise<Buffer> {
    console.log("Attempting Windows screenshot with multiple methods");

    // Method 1: Try screenshot-desktop with filename first
    try {
      const tempFile = path.join(this.tempDir, `temp-${uuidv4()}.png`);
      console.log(
        `Taking Windows screenshot to temp file (Method 1): ${tempFile}`
      );

      await screenshot({ filename: tempFile });

      if (fs.existsSync(tempFile)) {
        const buffer = await fs.promises.readFile(tempFile);
        console.log(
          `Method 1 successful, screenshot size: ${buffer.length} bytes`
        );

        // Cleanup temp file
        try {
          await fs.promises.unlink(tempFile);
        } catch (cleanupErr) {
          console.warn("Failed to clean up temp file:", cleanupErr);
        }

        return buffer;
      } else {
        console.log("Method 1 failed: File not created");
        throw new Error("Screenshot file not created");
      }
    } catch (error) {
      console.warn("Windows screenshot Method 1 failed:", error);

      // Method 2: Try using PowerShell
      try {
        console.log("Attempting Windows screenshot with PowerShell (Method 2)");
        const tempFile = path.join(this.tempDir, `ps-temp-${uuidv4()}.png`);

        // PowerShell command to take screenshot using .NET classes
        const psScript = `
        Add-Type -AssemblyName System.Windows.Forms,System.Drawing
        $screens = [System.Windows.Forms.Screen]::AllScreens
        $top = ($screens | ForEach-Object {$_.Bounds.Top} | Measure-Object -Minimum).Minimum
        $left = ($screens | ForEach-Object {$_.Bounds.Left} | Measure-Object -Minimum).Minimum
        $width = ($screens | ForEach-Object {$_.Bounds.Right} | Measure-Object -Maximum).Maximum
        $height = ($screens | ForEach-Object {$_.Bounds.Bottom} | Measure-Object -Maximum).Maximum
        $bounds = [System.Drawing.Rectangle]::FromLTRB($left, $top, $width, $height)
        $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
        $graphics = [System.Drawing.Graphics]::FromImage($bmp)
        $graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bounds.Size)
        $bmp.Save('${tempFile.replace(
          /\\/g,
          "\\\\"
        )}', [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bmp.Dispose()
        `;

        // Execute PowerShell
        await execFileAsync("powershell", [
          "-NoProfile",
          "-ExecutionPolicy",
          "Bypass",
          "-Command",
          psScript,
        ]);

        // Check if file exists and read it
        if (fs.existsSync(tempFile)) {
          const buffer = await fs.promises.readFile(tempFile);
          console.log(
            `Method 2 successful, screenshot size: ${buffer.length} bytes`
          );

          // Cleanup
          try {
            await fs.promises.unlink(tempFile);
          } catch (err) {
            console.warn("Failed to clean up PowerShell temp file:", err);
          }

          return buffer;
        } else {
          throw new Error("PowerShell screenshot file not created");
        }
      } catch (psError) {
        console.warn("Windows PowerShell screenshot failed:", psError);

        // Method 3: Last resort - create a tiny placeholder image
        console.log(
          "All screenshot methods failed, creating placeholder image"
        );

        console.log("Created placeholder image as fallback");

        // Show the error but return a valid buffer so the app doesn't crash
        throw new Error(
          "Could not capture screenshot with any method. Please check your Windows security settings and try again."
        );
      }
    }
  }

  public async takeScreenshot(
    hideMainWindow: () => void,
    showMainWindow: () => void
  ): Promise<string> {
    console.log("Taking screenshot in view:", this.view);
    hideMainWindow();

    // Increased delay for window hiding on Windows
    const hideDelay = process.platform === "win32" ? 500 : 300;
    await new Promise((resolve) => setTimeout(resolve, hideDelay));

    let screenshotPath = "";
    try {
      // Get screenshot buffer using cross-platform method
      const screenshotBuffer = await this.captureScreenshot();

      if (!screenshotBuffer || screenshotBuffer.length === 0) {
        throw new Error("Screenshot capture returned empty buffer");
      }

      screenshotPath = await this.saveScreenshotBuffer(screenshotBuffer);
    } catch (error) {
      console.error("Screenshot error:", error);
      throw error;
    } finally {
      // Increased delay for showing window again
      await new Promise((resolve) => setTimeout(resolve, 200));
      showMainWindow();
    }

    return screenshotPath;
  }

  public async takeRegionScreenshot(
    hideMainWindow: () => void,
    showMainWindow: () => void
  ): Promise<string | null> {
    console.log("Taking region screenshot in view:", this.view);
    // Select on the display the cursor is on, so questions shown on a
    // secondary monitor can be captured too (was: primary display only).
    const display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
    hideMainWindow();

    const hideDelay = process.platform === "win32" ? 300 : 180;
    await new Promise((resolve) => setTimeout(resolve, hideDelay));

    let screenshotPath = "";
    try {
      // Dim overlay for selection, then capture and crop the chosen region.
      const selection = await this.chooseScreenshotRegion(display);
      if (!selection) {
        console.log("Region screenshot cancelled");
        return null;
      }

      await new Promise((resolve) => setTimeout(resolve, 120));
      const screenshotBuffer = await this.captureScreenshot();
      if (!screenshotBuffer || screenshotBuffer.length === 0) {
        throw new Error("Screenshot capture returned empty buffer");
      }

      const croppedBuffer = this.cropScreenshotBuffer(screenshotBuffer, selection, display.bounds);
      screenshotPath = await this.saveScreenshotBuffer(croppedBuffer);
    } catch (error) {
      console.error("Region screenshot error:", error);
      throw error;
    } finally {
      await new Promise((resolve) => setTimeout(resolve, 150));
      showMainWindow();
    }

    return screenshotPath;
  }

  public async getImagePreview(filepath: string): Promise<string> {
    try {
      if (!fs.existsSync(filepath)) {
        console.error(`Image file not found: ${filepath}`);
        return "";
      }

      const data = await fs.promises.readFile(filepath);
      return `data:image/png;base64,${data.toString("base64")}`;
    } catch (error) {
      console.error("Error reading image:", error);
      return "";
    }
  }

  public async deleteScreenshot(
    path: string
  ): Promise<{ success: boolean; error?: string }> {
    try {
      if (fs.existsSync(path)) {
        await fs.promises.unlink(path);
      }

      if (this.view === "queue") {
        this.screenshotQueue = this.screenshotQueue.filter(
          (filePath) => filePath !== path
        );
      } else {
        this.extraScreenshotQueue = this.extraScreenshotQueue.filter(
          (filePath) => filePath !== path
        );
      }
      return { success: true };
    } catch (error) {
      console.error("Error deleting file:", error);
      return { success: false, error: (error as Error).message };
    }
  }

  public clearExtraScreenshotQueue(): void {
    // Clear extraScreenshotQueue
    this.extraScreenshotQueue.forEach((screenshotPath) => {
      if (fs.existsSync(screenshotPath)) {
        fs.unlink(screenshotPath, (err) => {
          if (err)
            console.error(
              `Error deleting extra screenshot at ${screenshotPath}:`,
              err
            );
        });
      }
    });
    this.extraScreenshotQueue = [];
  }
}
