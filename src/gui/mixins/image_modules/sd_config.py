"""SD配置相关功能"""
import tkinter as tk
from tkinter import messagebox
import requests
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class SDConfigMixin:
	"""SD配置相关功能"""
	
	def _load_sd_vaes(self) -> None:
		"""从SD WebUI加载VAE列表"""
		try:
			base_url = self.img_base_url.get()
			if not base_url:
				messagebox.showwarning("提示", "请先配置SD WebUI的Base URL")
				return
			
			# 从SD API获取VAE列表
			url = f"{base_url}/sdapi/v1/sd-vae"
			response = requests.get(url, timeout=10)
			response.raise_for_status()
			
			vaes = response.json()
			if not vaes:
				messagebox.showinfo("提示", "未找到可用的VAE")
				return
			
			# 更新下拉框
			vae_list = ["Automatic", "None"] + vaes
			self.combo_sd_vae['values'] = vae_list
			
			logger.info(f"✅ 已加载 {len(vaes)} 个VAE模型")
			if hasattr(self, 'status'):
				self.status.set(f"已加载 {len(vaes)} 个VAE模型")
			
		except requests.exceptions.ConnectionError:
			messagebox.showerror("连接失败", 
				"无法连接到SD WebUI\n\n" +
				"请确保：\n" +
				"1. SD WebUI已启动\n" +
				"2. 启动时添加了 --api 参数\n" +
				"3. Base URL 配置正确")
		except Exception as e:
			logger.error(f"加载VAE列表失败: {e}")
			messagebox.showerror("错误", f"加载VAE列表失败：{str(e)}")
	
	def _get_sd_config(self) -> dict:
		"""获取当前SD配置"""
		return {
			"sampler": self.sd_sampler.get() if hasattr(self, 'sd_sampler') else "Euler a",
			"steps": self.sd_steps.get() if hasattr(self, 'sd_steps') else 25,
			"cfg_scale": self.sd_cfg_scale.get() if hasattr(self, 'sd_cfg_scale') else 8.0,
			"seed": self.sd_seed.get() if hasattr(self, 'sd_seed') else -1,
			"batch_size": 1,  # 强制固定为1
			"denoising_strength": self.sd_denoising.get() if hasattr(self, 'sd_denoising') else 0.4,
			"vae": self.sd_vae.get() if hasattr(self, 'sd_vae') else "Automatic",
			"clip_skip": self.sd_clip_skip.get() if hasattr(self, 'sd_clip_skip') else 1
		}

