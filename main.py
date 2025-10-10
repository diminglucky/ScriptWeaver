from __future__ import annotations

from dotenv import load_dotenv

from src.gui_app import App


def main() -> None:
	load_dotenv()
	App().mainloop()


if __name__ == "__main__":
	main()
