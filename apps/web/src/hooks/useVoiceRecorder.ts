import { useCallback, useRef, useState } from "react";
import { blobToWav16k } from "@/utils/audioWav";

export function useVoiceRecorder() {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const start = useCallback(async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Trình duyệt không hỗ trợ ghi âm");
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      // Timeslice giúp browser ghi chunk ổn định trước khi stop.
      recorder.start(250);
      mediaRecorderRef.current = recorder;
      setRecording(true);
      return true;
    } catch (err) {
      const msg =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Cần quyền micro để dùng giọng nói"
          : "Không mở được micro";
      setError(msg);
      stopTracks();
      return false;
    }
  }, [stopTracks]);

  const stop = useCallback(async (): Promise<Uint8Array | null> => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      setRecording(false);
      stopTracks();
      return null;
    }

    return new Promise((resolve) => {
      recorder.onstop = () => {
        void (async () => {
          try {
            const blob = new Blob(chunksRef.current, {
              type: recorder.mimeType || "audio/webm",
            });
            const wav = await blobToWav16k(blob);
            resolve(wav);
          } catch {
            setError("Không chuyển được audio sang WAV");
            resolve(null);
          } finally {
            mediaRecorderRef.current = null;
            chunksRef.current = [];
            setRecording(false);
            stopTracks();
          }
        })();
      };
      recorder.stop();
    });
  }, [stopTracks]);

  const cancel = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.onstop = null;
      recorder.stop();
    }
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    setRecording(false);
    stopTracks();
  }, [stopTracks]);

  return { recording, error, start, stop, cancel };
}
