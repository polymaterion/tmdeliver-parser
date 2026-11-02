"""python -m app.tools.skeleton "текст" — показать скелет (для написания regex-правил)."""
import sys

from app.filter.normalize import skeleton

if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(skeleton(a))
