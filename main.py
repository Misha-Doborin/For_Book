"""Tkinter interface for a simple image-to-video workflow.

The application lets a user choose a source image or video, enter a
profession, create a render request, and save the resulting video file. The
current implementation contains a local mock renderer: when a video is uploaded
it copies the source video as the generated result and writes a prompt sidecar.
The renderer is isolated in ``RenderService`` so it can be replaced with a real
animation/video-generation backend later.
"""

from __future__ import annotations

import shutil
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
SUPPORTED_MEDIA = (
    (
        "Изображения и видео",
        "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.mp4 *.mov *.avi *.mkv",
    ),
    ("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
    ("Видео", "*.mp4 *.mov *.avi *.mkv"),
    ("Все файлы", "*.*"),
)
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


@dataclass(frozen=True)
class RenderResult:
    """Paths produced by the renderer."""

    video_path: Path
    prompt_path: Path


class RenderService:
    """Creates output videos for the UI.

    Replace ``render`` with an integration to a real model/API when it becomes
    available. The UI already passes a complete prompt and expects a video path
    in return.
    """

    def __init__(self) -> None:
        self.output_dir = Path(tempfile.mkdtemp(prefix="profession_video_"))

    def render(self, source_path: Path, profession: str, prompt: str) -> RenderResult:
        if source_path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(
                "Сейчас демо-рендер умеет сохранять результат только из загруженного видео. "
                "Для изображения подключите реальный backend генерации видео."
            )

        safe_profession = self._safe_filename(profession)
        output_path = (
            self.output_dir
            / f"malchik_pryzhok_{safe_profession}{source_path.suffix.lower()}"
        )
        prompt_path = output_path.with_suffix(output_path.suffix + ".prompt.txt")

        shutil.copy2(source_path, output_path)
        prompt_path.write_text(prompt, encoding="utf-8")
        return RenderResult(video_path=output_path, prompt_path=prompt_path)

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
        self.selected_media: Path | None = None
        self.render_result: RenderResult | None = None

        self.media_var = StringVar(value="Файл не выбран")
        self.profession_var = StringVar()
        self.status_var = StringVar(
            value="Выберите видео, введите профессию и нажмите «Создать видео»."
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
            main, text="Оживление картинки / видео", font=("Arial", 20, "bold")
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            main,
            text=(
                "Сценарий закреплён: маленький мальчик высоко подпрыгивает, "
                "а приземляется уже в выбранной профессии."
            ),
            wraplength=690,
        )
        subtitle.grid(row=1, column=0, sticky="we", pady=(8, 20))

        upload_box = ttk.LabelFrame(main, text="1. Загрузка исходного файла", padding=16)
        upload_box.grid(row=2, column=0, sticky="we")
        upload_box.columnconfigure(1, weight=1)

        ttk.Button(upload_box, text="Выбрать файл", command=self.choose_media).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(upload_box, textvariable=self.media_var).grid(
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

        prompt_box = ttk.LabelFrame(main, text="3. Промпт для генерации", padding=16)
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

    def choose_media(self) -> None:
        filename = filedialog.askopenfilename(
            title="Выберите картинку или видео", filetypes=SUPPORTED_MEDIA
        )
        if not filename:
            return

        self.selected_media = Path(filename)
        self.render_result = None
        self.download_button.configure(state=DISABLED)
        self.media_var.set(str(self.selected_media))
        self.status_var.set("Файл загружен. Введите профессию и создайте видео.")

    def update_prompt(self) -> None:
        profession = self.profession_var.get().strip() or "[профессия]"
        prompt = self._build_prompt(profession)
        self.prompt_editor.delete("1.0", END)
        self.prompt_editor.insert("1.0", prompt)

    def create_video(self) -> None:
        if self.selected_media is None:
            messagebox.showwarning("Нет файла", "Сначала загрузите исходное изображение или видео.")
            return

        profession = self.profession_var.get().strip()
        if not profession:
            messagebox.showwarning(
                "Нет профессии",
                "Введите професссию, например: врач, пилот, художник.",
            )
            return

        prompt = self.prompt_editor.get("1.0", END).strip()
        try:
            self.render_result = self.renderer.render(self.selected_media, profession, prompt)
        except ValueError as error:
            messagebox.showinfo("Нужен backend генерации", str(error))
            self.status_var.set(str(error))
            return
        except OSError as error:
            messagebox.showerror("Ошибка", f"Не удалось создать видео: {error}")
            self.status_var.set("Не удалось создать видео.")
            return

        self.download_button.configure(state=NORMAL)
        self.status_var.set(
            "Видео подготовлено. Нажмите «Скачать видео», чтобы сохранить файл в нужную папку."
        )

    def download_video(self) -> None:
        if self.render_result is None:
            messagebox.showwarning("Нет результата", "Сначала создайте видео.")
            return

        target = filedialog.asksaveasfilename(
            title="Сохранить видео",
            defaultextension=self.render_result.video_path.suffix,
            initialfile=self.render_result.video_path.name,
            filetypes=(
                ("Видео", f"*{self.render_result.video_path.suffix}"),
                ("Все файлы", "*.*"),
            ),
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
            "Создай короткое кинематографичное видео. На первом кадре маленький мальчик "
            "стоит в центре сцены, улыбается и очень высоко подпрыгивает. В момент прыжка "
            "происходит плавная магическая трансформация одежды и окружения. Когда мальчик "
            f"приземляется, он уже выглядит как {profession}: узнаваемая форма, аксессуары "
            "и фон профессии. Движение должно быть плавным, добрым, ярким и семейным. "
            "Сохрани лицо и возраст ребёнка, без страшных деталей, без насилия."
        )


def main() -> None:
    root = Tk()
    AnimationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
