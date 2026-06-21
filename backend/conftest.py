"""pytest 경로 설정 — backend/ 를 sys.path에 넣어 `import analytics` 등이 되게 한다."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
