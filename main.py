from __future__ import annotations

import sys
from dotenv import load_dotenv

from src.gui_app import App

if sys.platform == "win32":
	try:
		import io
		sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
		sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
	except Exception:
		pass


def main() -> None:
	load_dotenv()
	App().mainloop()

if __name__ == "__main__":
	main()
