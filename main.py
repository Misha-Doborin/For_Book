"""Tkinter interface for an image-to-video animation workflow.

The application lets a user choose a source image, enter a profession, create a
video render request, and save the resulting video file. The rendering logic is
kept in ``RenderService`` so the demo implementation can be replaced with a
real image-to-video model or API later.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from tkinter import (
    END,
    DISABLED,
    NORMAL,
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
)
from tkinter import ttk

APP_TITLE = "Оживление картинки: мальчик выбирает профессию"
SUPPORTED_IMAGES = (
    ("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
    ("Все файлы", "*.*"),
)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
OUTPUT_VIDEO_EXTENSION = ".mp4"


@dataclass(frozen=True)
class RenderResult:
    """Paths produced by the renderer."""

    video_path: Path
    prompt_path: Path


class RenderService:
    """Creates output videos from uploaded images.

    The current demo renderer turns a still image into a short MP4 clip with
    ffmpeg when it is available on the machine. Replace ``render`` with an
    integration to a real image-to-video backend to produce the requested
    transformation where the boy jumps and lands as the selected profession.
    """

    def __init__(self) -> None:
        self.output_dir = Path(tempfile.mkdtemp(prefix="profession_video_"))

    def render(self, image_path: Path, profession: str, prompt: str) -> RenderResult:
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError("Загрузите именно картинку: PNG, JPG, WEBP, BMP или GIF.")

        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            raise ValueError(
                "Для демо-создания MP4 из картинки нужен установленный ffmpeg. "
                "Либо замените RenderService.render на вызов вашего image-to-video backend."
            )

        safe_profession = self._safe_filename(profession)
        output_path = self.output_dir / f"malchik_pryzhok_{safe_profession}.mp4"
        prompt_path = output_path.with_suffix(output_path.suffix + ".prompt.txt")

        self._create_demo_video(ffmpeg_path, image_path, output_path)
        prompt_path.write_text(prompt, encoding="utf-8")
        return RenderResult(video_path=output_path, prompt_path=prompt_path)

    @staticmethod
    def _create_demo_video(ffmpeg_path: str, image_path: Path, output_path: Path) -> None:
        """Create a short MP4 preview from a still image with ffmpeg."""

        filter_graph = (
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
        )
        command = [
            ffmpeg_path,
            "-y",
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            str(image_path),
            "-vf",
            filter_graph,
            "-t",
            "6",
            "-r",
            "30",
            str(output_path),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)

    @staticmethod
    def _safe_filename(value: str) -> str:
        cleaned = "".join(char if char.isalnum() else "_" for char in value.strip().lower())
        cleaned = "_".join(part for part in cleaned.split("_") if part)
        return cleaned or "profession"


class AnimationApp:
    """Main Tkinter application."""

    def __init__(self, root: Tk) -> None:
        self.root = root
        self.renderer = RenderService()
        self.selected_image: Path | None = None
        self.render_result: RenderResult | None = None

        self.image_var = StringVar(value="Картинка не выбрана")
        self.profession_var = StringVar()
        self.status_var = StringVar(
            value="Выберите картинку, введите профессию и нажмите «Создать видео»."
        )

        self._configure_root()
        self._build_ui()

    def _configure_root(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry("760x560")
        self.root.minsize(680, 500)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=24)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)

        title = ttk.Label(
            main, text="Картинка → видео", font=("Arial", 20, "bold")
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            main,
            text=(
                "Загрузите картинку с маленьким мальчиком. Видео должно показать, "
                "как он высоко подпрыгивает и приземляется уже в выбранной профессии."
            ),
            wraplength=690,
        )
        subtitle.grid(row=1, column=0, sticky="we", pady=(8, 20))

        upload_box = ttk.LabelFrame(main, text="1. Загрузка картинки", padding=16)
        upload_box.grid(row=2, column=0, sticky="we")
        upload_box.columnconfigure(1, weight=1)

        ttk.Button(upload_box, text="Выбрать картинку", command=self.choose_image).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(upload_box, textvariable=self.image_var).grid(
            row=0, column=1, sticky="we", padx=(12, 0)
        )

        profession_box = ttk.LabelFrame(main, text="2. Профессия", padding=16)
        profession_box.grid(row=3, column=0, sticky="we", pady=(16, 0))
        profession_box.columnconfigure(0, weight=1)

        ttk.Label(profession_box, text="Кем мальчик должен стать после приземления?").grid(
            row=0, column=0, sticky="w"
        )
        profession_entry = ttk.Entry(profession_box, textvariable=self.profession_var)
        profession_entry.grid(row=1, column=0, sticky="we", pady=(8, 0))
        profession_entry.bind("<KeyRelease>", lambda _event: self.update_prompt())

        prompt_box = ttk.LabelFrame(main, text="3. Промпт для генерации видео", padding=16)
        prompt_box.grid(row=4, column=0, sticky="nsew", pady=(16, 0))
        prompt_box.columnconfigure(0, weight=1)
        prompt_box.rowconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)

        prompt_frame = ttk.Frame(prompt_box)
        prompt_frame.grid(row=0, column=0, sticky="nsew")
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)

        self.prompt_editor = Text(prompt_frame, height=7, wrap="word", padx=10, pady=10)
        self.prompt_editor.grid(row=0, column=0, sticky="nsew")
        self.update_prompt()

        action_box = ttk.Frame(main)
        action_box.grid(row=5, column=0, sticky="we", pady=(18, 0))
        action_box.columnconfigure(0, weight=1)

        ttk.Button(action_box, text="Создать видео", command=self.create_video).grid(
            row=0, column=0, sticky="w"
        )
        self.download_button = ttk.Button(
            action_box,
            text="Скачать видео",
            command=self.download_video,
            state=DISABLED,
        )
        self.download_button.grid(row=0, column=1, sticky="e")

        ttk.Label(main, textvariable=self.status_var, foreground="#255c2f", wraplength=690).grid(
            row=6, column=0, sticky="we", pady=(14, 0)
        )

    def choose_image(self) -> None:
        filename = filedialog.askopenfilename(
            title="Выберите картинку", filetypes=SUPPORTED_IMAGES
        )
        if not filename:
            return

        selected_image = Path(filename)
        if selected_image.suffix.lower() not in IMAGE_EXTENSIONS:
            messagebox.showwarning(
                "Неверный файл", "Можно загрузить только картинку: PNG, JPG, WEBP, BMP или GIF."
            )
            return

        self.selected_image = selected_image
        self.render_result = None
        self.download_button.configure(state=DISABLED)
        self.image_var.set(str(self.selected_image))
        self.status_var.set("Картинка загружена. Введите профессию и создайте видео.")

    def update_prompt(self) -> None:
        profession = self.profession_var.get().strip() or "[профессия]"
        prompt = self._build_prompt(profession)
        self.prompt_editor.delete("1.0", END)
        self.prompt_editor.insert("1.0", prompt)

    def create_video(self) -> None:
        if self.selected_image is None:
            messagebox.showwarning("Нет картинки", "Сначала загрузите исходную картинку.")
            return

        profession = self.profession_var.get().strip()
        if not profession:
            messagebox.showwarning(
                "Нет профессии",
                "Введите профессию, например: врач, пилот, художник.",
            )
            return

        prompt = self.prompt_editor.get("1.0", END).strip()
        try:
            self.render_result = self.renderer.render(self.selected_image, profession, prompt)
        except ValueError as error:
            messagebox.showinfo("Нужен генератор видео", str(error))
            self.status_var.set(str(error))
            return
        except (OSError, subprocess.CalledProcessError) as error:
            messagebox.showerror("Ошибка", f"Не удалось создать видео: {error}")
            self.status_var.set("Не удалось создать видео.")
            return

        self.download_button.configure(state=NORMAL)
        self.status_var.set(
            "Видео подготовлено из картинки. Нажмите «Скачать видео», чтобы сохранить MP4."
        )

    def download_video(self) -> None:
        if self.render_result is None:
            messagebox.showwarning("Нет результата", "Сначала создайте видео.")
            return

        target = filedialog.asksaveasfilename(
            title="Сохранить видео",
            defaultextension=OUTPUT_VIDEO_EXTENSION,
            initialfile=self.render_result.video_path.name,
            filetypes=(("MP4 видео", "*.mp4"), ("Все файлы", "*.*")),
        )
        if not target:
            return

        try:
            shutil.copy2(self.render_result.video_path, target)
        except OSError as error:
            messagebox.showerror("Ошибка", f"Не удалось сохранить видео: {error}")
            return

        self.status_var.set(f"Видео сохранено: {target}")
        messagebox.showinfo("Готово", "Видео успешно сохранено.")

    @staticmethod
    def _build_prompt(profession: str) -> str:
        return (
            "Создай короткое кинематографичное видео из загруженной картинки. "
            "На первом кадре маленький мальчик с картинки стоит в центре сцены, "
            "улыбается и очень высоко подпрыгивает. В момент прыжка происходит "
            "плавная магическая трансформация одежды и окружения. Когда мальчик "
            f"приземляется, он уже выглядит как {profession}: узнаваемая форма, "
            "аксессуары и фон профессии. Сохрани лицо, возраст и основные черты "
            "ребёнка с исходной картинки. Движение должно быть плавным, добрым, "
            "ярким и семейным, без страшных деталей и насилия."
        )


def main() -> None:
    root = Tk()
    AnimationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
