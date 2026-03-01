from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from src.gui_app import App

if sys.platform == "win32":
	try:
		import io
		if hasattr(sys.stdout, "buffer"):
			sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
		if hasattr(sys.stderr, "buffer"):
			sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
	except Exception:
		pass


def main() -> None:
	project_root = Path(__file__).resolve().parent
	os.chdir(project_root)
	if str(project_root) not in sys.path:
		sys.path.insert(0, str(project_root))
	load_dotenv()
	App().mainloop()

if __name__ == "__main__":
	main()
