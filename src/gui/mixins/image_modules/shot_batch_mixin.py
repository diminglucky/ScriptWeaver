"""Batch generation workflows for parsed shots."""

from __future__ import annotations

from tkinter import DISABLED, END, NORMAL, messagebox
import logging

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize

logger = logging.getLogger(__name__)


def print(*args, **kwargs):  # type: ignore[override]
    logger.info(" ".join(str(a) for a in args))


def _resolve_deepseek_client_cls():
    """Use aggregator module symbol so tests can monkey-patch one stable path."""
    try:
        from . import shot_manager as shot_manager_module  # local import avoids circular init timing issues

        patched = getattr(shot_manager_module, "DeepSeekClient", None)
        if patched is not None:
            return patched
    except Exception:
        pass
    return DeepSeekClient


class ShotBatchMixin:
    """Batch-generate image prompts and images for all shots."""
    def _on_batch_generate_all_shots(self) -> None:
        """批量生成所有分镜的图片（借鉴自 DirectorAI）
        
        功能：
        1. 自动为每个分镜生成图片描述
        2. 使用角色三视图作为参考保持一致性
        3. 支持中断和恢复
        """
        if not hasattr(self, "parsed_shots") or not self.parsed_shots:
            messagebox.showwarning("提示", "请先生成分镜列表")
            return

        if not self.current_project:
            messagebox.showwarning("提示", "请先创建或打开一个项目")
            return

        shot_count = len(self.parsed_shots)
        if not self._confirm_batch_generation(shot_count):
            return

        reference_images = self._collect_batch_reference_images()
        self._batch_cancelled = False
        self._set_batch_generate_button_running(True)

        import threading

        threading.Thread(
            target=lambda: self._run_batch_generate_all_shots(reference_images, shot_count),
            daemon=True,
        ).start()

    def _confirm_batch_generation(self, shot_count: int) -> bool:
        """弹窗确认是否执行批量生成。"""
        return messagebox.askyesno(
            "批量生成确认",
            f"即将为 {shot_count} 个分镜生成图片\n\n"
            f"⚠️ 注意事项：\n"
            f"• 每张图片需要调用API，会产生费用\n"
            f"• 预计耗时：{shot_count * 15}-{shot_count * 30} 秒\n"
            f"• 生成过程中可以取消\n\n"
            f"是否继续？"
        )

    def _collect_batch_reference_images(self) -> list[str]:
        """收集用于批量生成的参考人物图。"""
        reference_images = []
        for char in self.character_list:
            if isinstance(char, dict):
                if char.get("turnaround_image"):
                    reference_images.append(char["turnaround_image"])
                elif char.get("photo_path"):
                    reference_images.append(char["photo_path"])
            else:
                if hasattr(char, "turnaround_image") and char.turnaround_image:
                    reference_images.append(char.turnaround_image)
                elif hasattr(char, "primary_photo") and char.primary_photo:
                    reference_images.append(char.primary_photo)
        return reference_images

    def _set_batch_generate_button_running(self, running: bool) -> None:
        """切换批量生成按钮状态。"""
        if not hasattr(self, "btn_batch_generate"):
            return
        state = DISABLED if running else NORMAL
        text = "⏳ 生成中..." if running else "🚀 批量生成所有分镜"
        self.after(0, lambda: self.btn_batch_generate.config(state=state, text=text))

    def _run_batch_generate_all_shots(self, reference_images: list[str], shot_count: int) -> None:
        """后台批量生成所有分镜图片。"""
        generated_count = 0
        failed_count = 0
        try:
            import time

            shots_dir = self.current_project.project_dir / "shots"
            shots_dir.mkdir(parents=True, exist_ok=True)

            for index, shot in enumerate(self.parsed_shots):
                if self._batch_cancelled:
                    self.after(
                        0,
                        lambda: self._ui(
                            self.status.set,
                            f"⚠️ 批量生成已取消，已完成 {generated_count}/{shot_count}",
                        ),
                    )
                    break

                self._update_batch_progress(index, shot_count)
                try:
                    self.after(0, lambda idx=index: self._select_shot_for_batch(idx))
                    time.sleep(0.1)
                    self._generate_shot_description_sync(shot, index)
                    time.sleep(0.5)
                    self._generate_shot_image_sync(index, reference_images)
                    generated_count += 1
                    time.sleep(1)
                except Exception as exc:
                    print(f"❌ 分镜 {index + 1} 生成失败: {exc}")
                    failed_count += 1

            self.after(
                0,
                lambda: self._on_batch_generate_complete(
                    generated_count=generated_count,
                    failed_count=failed_count,
                    shots_dir=shots_dir,
                ),
            )
        except Exception as exc:
            import traceback

            traceback.print_exc()
            self.after(0, lambda: messagebox.showerror("错误", f"批量生成失败: {exc}"))
        finally:
            self._set_batch_generate_button_running(False)

    def _update_batch_progress(self, index: int, shot_count: int) -> None:
        """更新批量生成进度。"""
        self.after(
            0,
            lambda idx=index, total=shot_count: self._ui(
                self.status.set,
                f"🎨 [{idx + 1}/{total}] 正在生成第 {idx + 1} 个分镜的图片...",
            ),
        )
        self.after(
            0,
            lambda idx=index, total=shot_count: self._header_status(f"[{idx + 1}/{total}] 批量生成...", "🎨"),
        )

    def _select_shot_for_batch(self, index: int) -> None:
        """在列表中选中当前批量处理的分镜。"""
        self.shots_listbox.selection_clear(0, END)
        self.shots_listbox.selection_set(index)

    def _on_batch_generate_complete(self, *, generated_count: int, failed_count: int, shots_dir) -> None:
        """批量生成结束后的 UI 提示。"""
        self._ui(self.status.set, f"✅ 批量生成完成！成功 {generated_count} 张，失败 {failed_count} 张")
        self._header_status("批量完成", "✅")
        messagebox.showinfo(
            "批量生成完成",
            f"生成结果：\n\n"
            f"✅ 成功：{generated_count} 张\n"
            f"❌ 失败：{failed_count} 张\n\n"
            f"保存位置：{shots_dir}",
        )
    
    def _generate_shot_description_sync(self, shot: str, index: int) -> str:
        """同步生成单个分镜的图片描述"""
        # 分镜转描述：根据模型路由选择 API
        fallback_provider = None
        if hasattr(self, 'quick_story_api'):
            fallback_provider = self.quick_story_api.get()
        if not fallback_provider and hasattr(self, 'api_preset'):
            fallback_provider = self.api_preset.get()
        fallback_model = None
        if hasattr(self, 'story_model_var'):
            fallback_model = self.story_model_var.get()
        elif hasattr(self, 'model'):
            fallback_model = self.model.get()
        
        api_config = self._resolve_task_api("image_shot_to_desc", fallback_provider=fallback_provider, fallback_model=fallback_model)
        api_key = _sanitize(api_config.get("key", ""))
        base_url = _sanitize(api_config.get("base_url", ""))
        model = _sanitize(api_config.get("model", ""))
        
        if not api_key:
            return shot  # 如果没有API Key，直接使用分镜文本
        
        # 简化的描述生成
        img_type = self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
        
        client = _resolve_deepseek_client_cls()( api_key=api_key, base_url=base_url, model=model)
        
        inst = f"将以下分镜转换为简洁的图片描述，用于生成【{img_type}】风格的图片。只输出描述，200字以内。"
        resp = client.chat([
            {"role": "system", "content": inst},
            {"role": "user", "content": shot},
        ], temperature=0.5)
        
        description = resp.strip()
        
        # 更新UI
        self.after(0, lambda: self.img_txt_prompt_cn.delete("1.0", END))
        self.after(0, lambda d=description: self.img_txt_prompt_cn.insert(END, d))
        
        return description
    
    def _generate_shot_image_sync(self, index: int, reference_images: list = None) -> None:
        """同步生成单个分镜的图片"""
        import time
        old_count = 0
        if self.current_project:
            shots_dir = self.current_project.project_dir / "shots"
            if shots_dir.exists():
                old_count = len(list(shots_dir.glob("*.png")))
        self.after(0, self._on_img_generate)
        for _ in range(90):
            time.sleep(1)
            if hasattr(self, '_batch_cancelled') and self._batch_cancelled:
                break
            if self.current_project:
                shots_dir = self.current_project.project_dir / "shots"
                if shots_dir.exists() and len(list(shots_dir.glob("*.png"))) > old_count:
                    time.sleep(0.5)
                    break
            if hasattr(self, '_is_busy') and not self._is_busy:
                break
    
    def _cancel_batch_generation(self) -> None:
        """取消批量生成"""
        self._batch_cancelled = True
        self._ui(self.status.set, "⏳ 正在取消批量生成...")
    
