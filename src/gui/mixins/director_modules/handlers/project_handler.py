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
            logger.warning("没有当前项目，无法保存分镜")
            return
        
        if not hasattr(mixin_instance, 'current_shots') or not mixin_instance.current_shots:
            logger.warning("没有分镜数据，无法保存")
            return
        
        try:
            project_dir = Path(mixin_instance.current_project.project_dir)
            shots_file = project_dir / "director" / "shots.json"
            shots_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 将 Shot 对象转换为字典以便 JSON 序列化
            shots_list = []
            for shot in mixin_instance.current_shots:
                # 检查是否是 Shot 对象（有 to_dict 方法）
                if hasattr(shot, 'to_dict'):
                    shots_list.append(shot.to_dict())
                elif isinstance(shot, dict):
                    # 已经是字典，直接使用
                    shots_list.append(shot)
                else:
                    # 其他类型，记录警告并跳过
                    logger.warning(f"无法序列化的分镜对象类型: {type(shot)}")
                    continue
            
            # 确保保存格式一致：{"shots": [...]}
            with open(shots_file, 'w', encoding='utf-8') as f:
                json.dump({"shots": shots_list}, f, ensure_ascii=False, indent=2)
            
            logger.info(f"分镜已自动保存到: {shots_file}，共 {len(mixin_instance.current_shots)} 个")
        except Exception as e:
            logger.error(f"保存分镜失败: {e}", exc_info=True)
    
    @staticmethod
    def load_director_data_from_project(mixin_instance) -> None:
        """从项目加载导演数据"""
        logger.info("========== 开始加载导演数据 ==========")
        
        if not hasattr(mixin_instance, 'current_project') or not mixin_instance.current_project:
            logger.info("没有当前项目，跳过加载")
            return
        
        try:
            project_dir = Path(mixin_instance.current_project.project_dir)
            logger.info(f"项目目录: {project_dir}")
            
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
            logger.info(f"检查分镜文件: {shots_file}")
            
            if shots_file.exists():
                logger.info("分镜文件存在，开始加载")
                with open(shots_file, 'r', encoding='utf-8') as f:
                    shots_data = json.load(f)
                
                logger.info(f"读取到的数据类型: {type(shots_data)}")
                
                # 处理不同的JSON格式
                if isinstance(shots_data, dict):
                    # 如果是字典格式 {"shots": [...]} 或 {"version": "1.0", "shots": [...]}
                    shots = shots_data.get('shots', [])
                    logger.info(f"从字典中提取shots，数量: {len(shots)}")
                elif isinstance(shots_data, list):
                    # 如果是列表格式 [...]
                    shots = shots_data
                    logger.info(f"直接使用列表格式，数量: {len(shots)}")
                else:
                    logger.warning(f"shots.json格式不正确，期望字典或列表，实际是: {type(shots_data)}")
                    shots = []
            else:
                logger.info("分镜文件不存在")
                shots = []
            
            # 验证shots是列表且元素是字典
            if not isinstance(shots, list):
                logger.error(f"shots不是列表格式: {type(shots)}")
                shots = []
            else:
                # 过滤掉非字典元素
                original_count = len(shots)
                shots = [s for s in shots if isinstance(s, dict)]
                if len(shots) != original_count:
                    logger.warning(f"过滤了 {original_count - len(shots)} 个非字典元素")
            
            # 保存到实例变量
            mixin_instance.current_shots = shots
            logger.info(f"已设置 current_shots，数量: {len(shots)}")
            
            # 更新分镜显示（友好格式）
            if hasattr(mixin_instance, 'shots_list') and shots:
                logger.info("开始更新shots_list显示")
                mixin_instance.shots_list.config(state="normal")
                mixin_instance.shots_list.delete("1.0", "end")
                
                # 友好的格式化显示
                for idx, shot in enumerate(shots, 1):
                    mixin_instance.shots_list.insert("end", "="*100 + "\n")
                    mixin_instance.shots_list.insert("end", f"【分镜 {shot.get('shot_number', idx)}】{shot.get('scene_id', '')} - {shot.get('shot_type', '')}\n")
                    mixin_instance.shots_list.insert("end", "="*100 + "\n\n")
                    
                    mixin_instance.shots_list.insert("end", f"📍 位置: {shot.get('location', '')}\n")
                    mixin_instance.shots_list.insert("end", f"👥 人物: {', '.join(shot.get('characters', []))}\n\n")
                    
                    mixin_instance.shots_list.insert("end", f"🎨 画面描述:\n{shot.get('visual_description', '')}\n\n")
                    mixin_instance.shots_list.insert("end", f"🎭 动作:\n{shot.get('action', '')}\n\n")
                    
                    if shot.get('dialogue'):
                        mixin_instance.shots_list.insert("end", f"💬 对白: {shot.get('dialogue', '')}\n\n")
                    
                    camera = shot.get('camera', {})
                    if camera:
                        mixin_instance.shots_list.insert("end", f"📷 镜头: {camera.get('movement', '')} | {camera.get('angle', '')} | {camera.get('lens', '')}\n")
                    
                    mixin_instance.shots_list.insert("end", f"⏱️  时长: {shot.get('duration', '')} | 过渡: {shot.get('transition_to_next', shot.get('transition', ''))}\n\n")
                    
                    if shot.get('jimeng_prompt'):
                        mixin_instance.shots_list.insert("end", f"🖼️  图像提示词:\n{shot.get('jimeng_prompt', '')}\n\n")
                    
                    mixin_instance.shots_list.insert("end", "\n")
                
                mixin_instance.shots_list.config(state="disabled")
                logger.info("shots_list显示更新完成")
            
            # 刷新下拉框（两个位置都要刷新）
            if hasattr(mixin_instance, '_refresh_shot_combo'):
                logger.info("开始刷新【生成图片】下拉框")
                mixin_instance._refresh_shot_combo(silent=True)
                logger.info("【生成图片】下拉框刷新完成")
            
            # 刷新预览页面的下拉框
            if hasattr(mixin_instance, '_refresh_preview_shot_combo'):
                logger.info("开始刷新【预览】下拉框")
                mixin_instance._refresh_preview_shot_combo()
                logger.info("【预览】下拉框刷新完成")
            
            logger.info(f"========== 导演数据加载完成，共 {len(shots)} 个分镜 ==========")
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

