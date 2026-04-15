import threading
import queue
import customtkinter as ctk
from tkinter import messagebox
import vlc
import yt_dlp


class StreamingMusicPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Bellako Stream Player")
        self.geometry("980x680")
        self.minsize(900, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.results = []
        self.current_stream_url = None
        self.current_title = ""
        self.search_queue = queue.Queue()
        self.play_queue = queue.Queue()

        self._build_ui()
        self._build_player()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self._process_search_queue)

    def _build_player(self):
        self.vlc_instance = vlc.Instance("--network-caching=1500")
        self.player = self.vlc_instance.media_player_new()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Search bar
        search_frame = ctk.CTkFrame(self, corner_radius=14)
        search_frame.grid(row=0, column=0, padx=18, pady=(16, 10), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Buscar canciones o artistas en YouTube...",
            height=42,
            corner_radius=10,
        )
        self.search_entry.grid(row=0, column=0, padx=(12, 8), pady=12, sticky="ew")
        self.search_entry.bind("<Return>", lambda event: self.search_tracks())

        self.search_button = ctk.CTkButton(
            search_frame,
            text="Buscar",
            width=120,
            height=40,
            command=self.search_tracks,
        )
        self.search_button.grid(row=0, column=1, padx=(0, 12), pady=12)

        # Status
        self.status_label = ctk.CTkLabel(
            self,
            text="Listo para buscar música 🎵",
            anchor="w",
            text_color=("#B0B8C2", "#B0B8C2"),
        )
        self.status_label.grid(row=1, column=0, padx=22, pady=(0, 8), sticky="ew")

        # Results list
        self.results_frame = ctk.CTkScrollableFrame(self, corner_radius=14)
        self.results_frame.grid(row=2, column=0, padx=18, pady=(0, 10), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)

        self.now_playing_label = ctk.CTkLabel(
            self,
            text="Ahora suena: —",
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.now_playing_label.grid(row=3, column=0, padx=22, pady=(4, 6), sticky="ew")

        # Controls
        controls = ctk.CTkFrame(self, corner_radius=14)
        controls.grid(row=4, column=0, padx=18, pady=(0, 16), sticky="ew")
        controls.grid_columnconfigure(5, weight=1)

        play_btn = ctk.CTkButton(controls, text="▶ Play", width=100, command=self.play)
        pause_btn = ctk.CTkButton(controls, text="⏸ Pause", width=100, command=self.pause)
        stop_btn = ctk.CTkButton(controls, text="⏹ Stop", width=100, command=self.stop)

        play_btn.grid(row=0, column=0, padx=(12, 6), pady=12)
        pause_btn.grid(row=0, column=1, padx=6, pady=12)
        stop_btn.grid(row=0, column=2, padx=6, pady=12)

        vol_text = ctk.CTkLabel(controls, text="Volumen")
        vol_text.grid(row=0, column=3, padx=(16, 8))

        self.volume_slider = ctk.CTkSlider(
            controls,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self.set_volume,
            width=220,
        )
        self.volume_slider.set(75)
        self.volume_slider.grid(row=0, column=4, padx=(0, 12), pady=12)

    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def clear_results(self):
        for child in self.results_frame.winfo_children():
            child.destroy()

    def search_tracks(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showinfo("Búsqueda", "Escribe algo para buscar.")
            return

        self.set_status("Buscando resultados...")
        self.search_button.configure(state="disabled")
        self.clear_results()

        thread = threading.Thread(target=self._search_worker, args=(query,), daemon=True)
        thread.start()

    def _search_worker(self, query: str):
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "noplaylist": True,
            "default_search": "ytsearch15",
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = ydl.extract_info(f"ytsearch15:{query}", download=False)
            entries = data.get("entries", []) if data else []
            parsed = []
            for item in entries:
                if not item:
                    continue
                video_id = item.get("id")
                title = item.get("title", "Sin título")
                uploader = item.get("uploader", "Canal desconocido")
                if video_id:
                    webpage_url = f"https://www.youtube.com/watch?v={video_id}"
                    parsed.append({"title": title, "uploader": uploader, "url": webpage_url})
            self.search_queue.put(("ok", parsed))
        except Exception as e:
            self.search_queue.put(("error", str(e)))

    def _process_search_queue(self):
        try:
            while True:
                status, payload = self.search_queue.get_nowait()
                self.search_button.configure(state="normal")
                if status == "ok":
                    self.results = payload
                    self.render_results()
                    self.set_status(f"Resultados encontrados: {len(self.results)}")
                else:
                    self.results = []
                    self.set_status("Error en la búsqueda")
                    messagebox.showerror("Error", f"No se pudo buscar:\n{payload}")
        except queue.Empty:
            pass
        finally:
            self.after(120, self._process_search_queue)

    def render_results(self):
        self.clear_results()
        if not self.results:
            empty = ctk.CTkLabel(self.results_frame, text="Sin resultados.")
            empty.grid(row=0, column=0, padx=12, pady=10, sticky="w")
            return

        for i, track in enumerate(self.results):
            item = ctk.CTkFrame(self.results_frame, corner_radius=10)
            item.grid(row=i, column=0, padx=10, pady=6, sticky="ew")
            item.grid_columnconfigure(0, weight=1)

            title = ctk.CTkLabel(
                item,
                text=track["title"],
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            title.grid(row=0, column=0, padx=(12, 6), pady=(10, 2), sticky="ew")

            uploader = ctk.CTkLabel(
                item,
                text=f"Canal/Artista: {track['uploader']}",
                anchor="w",
                text_color=("#A8B0BC", "#A8B0BC"),
            )
            uploader.grid(row=1, column=0, padx=(12, 6), pady=(0, 10), sticky="ew")

            play_btn = ctk.CTkButton(
                item,
                text="Reproducir",
                width=110,
                command=lambda idx=i: self.play_selected(idx),
            )
            play_btn.grid(row=0, column=1, rowspan=2, padx=(8, 12), pady=10)

    def _extract_best_audio_url(self, video_url: str):
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "skip_download": True,
            "format": "bestaudio/best",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get("url")
            if not stream_url:
                raise ValueError("No se obtuvo URL de audio temporal.")
            title = info.get("title", "Sin título")
            return stream_url, title

    def play_selected(self, index: int):
        if index < 0 or index >= len(self.results):
            return

        track = self.results[index]
        self.set_status("Preparando stream...")

        def worker():
            try:
                stream_url, title = self._extract_best_audio_url(track["url"])
                self.play_queue.put(("play", {"stream_url": stream_url, "title": title}))
            except Exception as e:
                self.play_queue.put(("play_error", str(e)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._process_play_events)

    def _process_play_events(self):
        processed_any = False
        try:
            while True:
                status, payload = self.play_queue.get_nowait()
                processed_any = True
                if status == "play":
                    self.current_stream_url = payload["stream_url"]
                    self.current_title = payload["title"]
                    self._start_stream(self.current_stream_url)
                    self.now_playing_label.configure(text=f"Ahora suena: {self.current_title}")
                    self.set_status("Reproduciendo stream sin anuncios")
                elif status == "play_error":
                    self.set_status("Error al preparar el stream")
                    messagebox.showerror("Error", f"No se pudo reproducir:\n{payload}")
                else:
                    break
        except queue.Empty:
            pass

        if not processed_any:
            self.after(120, self._process_play_events)

    def _start_stream(self, stream_url: str):
        self.stop()
        media = self.vlc_instance.media_new(stream_url)
        self.player.set_media(media)
        self.player.audio_set_volume(int(self.volume_slider.get()))
        self.player.play()

    def play(self):
        state = self.player.get_state()
        if state in [vlc.State.Paused, vlc.State.Stopped, vlc.State.Ended]:
            self.player.play()
            self.set_status("Reproduciendo")
        elif state == vlc.State.NothingSpecial and self.current_stream_url:
            self._start_stream(self.current_stream_url)
            self.set_status("Reproduciendo")
        elif not self.current_stream_url:
            self.set_status("Selecciona una canción de la lista")

    def pause(self):
        self.player.pause()
        self.set_status("Pausado")

    def stop(self):
        self.player.stop()
        self.set_status("Detenido")

    def set_volume(self, value):
        self.player.audio_set_volume(int(float(value)))

    def on_close(self):
        try:
            self.player.stop()
            self.player.release()
            self.vlc_instance.release()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = StreamingMusicPlayer()
    app.mainloop()
