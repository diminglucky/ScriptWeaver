"""
项目管理事件处理器 - 从director_mixin.py重构出来
负责处理项目保存和加载相关的事件
"""
import json
from pathlib import Path
from tkinter import messagebox

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class ProjectHandler:
    """项目管理事件处理器"""
    
    @staticmethod
    def auto_save_script_to_project(mixin_instance, script_text: str) -> None:
        """自动保存剧本到项目"""
        if not hasattr(mixin_instance, 'current_project') or not mixin_instance.current_project:
            return
        
        try:
            project_dir = Path(mixin_instance.current_project.project_dir)
            script_file = project_dir / "director" / "script.txt"
            script_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_text)
            
            logger.debug(f"剧本已自动保存到: {script_file}")
        except Exception as e:
            logger.error(f"保存剧本失败: {e}", exc_info=True)
    
    @staticmethod
    def auto_save_shots_to_project(mixin_instance) -> None:
        """自动保存分镜到项目"""
        if not hasattr(mixin_instance, 'current_project') or not mixin_instance.current_project:
            return
        
        if not hasattr(mixin_instance, 'current_shots') or not mixin_instance.current_shots:
            return
        
        try:
            project_dir = Path(mixin_instance.current_project.project_dir)
            shots_file = project_dir / "director" / "shots.json"
            shots_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(shots_file, 'w', encoding='utf-8') as f:
                json.dump(mixin_instance.current_shots, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"分镜已自动保存到: {shots_file}")
        except Exception as e:
            logger.error(f"保存分镜失败: {e}", exc_info=True)
    
    @staticmethod
    def load_director_data_from_project(mixin_instance) -> None:
        """从项目加载导演数据"""
        if not hasattr(mixin_instance, 'current_project') or not mixin_instance.current_project:
            return
        
        try:
            project_dir = Path(mixin_instance.current_project.project_dir)
            
            # 加载剧本
            script_file = project_dir / "director" / "script.txt"
            if script_file.exists():
                with open(script_file, 'r', encoding='utf-8') as f:
                    script_text = f.read()
                
                if hasattr(mixin_instance, 'script_text'):
                    mixin_instance.script_text.config(state="normal")
                    mixin_instance.script_text.delete("1.0", "end")
                    mixin_instance.script_text.insert("1.0", script_text)
                    mixin_instance.script_text.config(state="disabled")
            
            # 加载分镜
            shots_file = project_dir / "director" / "shots.json"
            if shots_file.exists():
                with open(shots_file, 'r', encoding='utf-8') as f:
                    shots_data = json.load(f)
                
                # 处理不同的JSON格式
                if isinstance(shots_data, dict):
                    # 如果是字典格式 {"shots": [...]} 或 {"version": "1.0", "shots": [...]}
                    shots = shots_data.get('shots', [])
                elif isinstance(shots_data, list):
                    # 如果是列表格式 [...]
                    shots = shots_data
                else:
                    logger.warning(f"shots.json格式不正确，期望字典或列表，实际是: {type(shots_data)}")
                    shots = []
                
                # 验证shots是列表且元素是字典
                if not isinstance(shots, list):
                    logger.error(f"shots不是列表格式: {type(shots)}")
                    shots = []
                else:
                    # 过滤掉非字典元素（可能是字符串或其他类型）
                    shots = [s for s in shots if isinstance(s, dict)]
                    if len(shots) != len(shots_data.get('shots', shots_data if isinstance(shots_data, list) else [])):
                        logger.warning(f"过滤了 {len(shots_data.get('shots', shots_data if isinstance(shots_data, list) else [])) - len(shots)} 个非字典元素")
                
                mixin_instance.current_shots = shots
                
                # 更新分镜显示
                if hasattr(mixin_instance, 'shots_list'):
                    shots_text = json.dumps(shots, ensure_ascii=False, indent=2)
                    mixin_instance.shots_list.config(state="normal")
                    mixin_instance.shots_list.delete("1.0", "end")
                    mixin_instance.shots_list.insert("1.0", shots_text)
                    mixin_instance.shots_list.config(state="disabled")
                
                # 刷新下拉框
                if hasattr(mixin_instance, '_refresh_shot_combo'):
                    mixin_instance._refresh_shot_combo(silent=True)
                
                logger.info(f"已加载 {len(shots)} 个分镜")
        except Exception as e:
            logger.error(f"加载项目数据失败: {e}", exc_info=True)
    
    @staticmethod
    def handle_save_director_project(mixin_instance) -> None:
        """处理保存导演项目的事件"""
        try:
            if not hasattr(mixin_instance, 'current_project') or not mixin_instance.current_project:
                messagebox.showwarning("提示", "请先打开一个项目")
                return
            
            # 保存剧本
            if hasattr(mixin_instance, 'script_text'):
                script_text = mixin_instance.script_text.get("1.0", "end-1c")
                ProjectHandler.auto_save_script_to_project(mixin_instance, script_text)
            
            # 保存分镜
            ProjectHandler.auto_save_shots_to_project(mixin_instance)
            
            messagebox.showinfo(
                "成功",
                "导演项目已保存完成！\n\n已保存内容：\n- 剧本\n- 分镜头列表\n- 一致性设定\n- 生成参数\n- 视频提示词"
            )
        except Exception as e:
            logger.error(f"保存项目失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"项目保存失败: {str(e)}")

