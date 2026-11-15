/**
 * Seamless Audio Queue Player for sentence-boundary streaming speech.
 * Automatically plays arriving audio chunks in sequential order without gaps.
 */

class AudioQueuePlayer {
  private queue: string[] = [];
  private currentAudio: HTMLAudioElement | null = null;
  private isPlaying: boolean = false;

  enqueue(url: string) {
    if (!url) return;
    this.queue.push(url);
    if (!this.isPlaying) {
      this.playNext();
    }
  }

  private playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      this.currentAudio = null;
      return;
    }

    this.isPlaying = true;
    const url = this.queue.shift()!;
    const audio = new Audio(url);
    this.currentAudio = audio;

    audio.onended = () => {
      this.playNext();
    };

    audio.onerror = (e) => {
      console.warn('Audio playback error on chunk:', url, e);
      this.playNext();
    };

    audio.play().catch((err) => {
      console.warn('Audio play interrupted or blocked:', err);
      this.playNext();
    });
  }

  stop() {
    this.queue = [];
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    this.isPlaying = false;
  }
}

export const audioQueue = new AudioQueuePlayer();
