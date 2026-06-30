# Branch Cleanup 이력 - 2026-06-30

정리 시각: 2026-06-30 21:03 KST
저장소: `git@github.com:mangotengcherry/prc_window_demo.git`

## 목적

feature/UI 브랜치 이력이 헷갈리지 않도록 `main`만 활성 브랜치로 남깁니다.
이 문서는 삭제한 브랜치 ref, 삭제 전 tip 커밋, `origin/main` 포함 여부를 기록합니다.

## Main 기준점

- `origin/main`: `b45e1b7` - `Merge pull request #2 from mangotengcherry/codex/rev_0628`
- 로컬 `main`은 브랜치 삭제 전에 `7817fd7`에서 `b45e1b7`로 fast-forward 했습니다.

## 삭제한 원격 브랜치

### `origin/codex/rev_0628`

- Tip: `1772579` - `feat: build Korean YE workbench prototype`
- 삭제 전 상태: `origin/main`에 merge됨
- 보존 위치: `main`의 merge commit `b45e1b7`

### `origin/codex/workbench-risk-briefing`

- Tip: `7bd2176` - `fix: polish risk briefing smoke findings`
- 삭제 전 상태: `origin/main`에 merge되지 않음
- 삭제 전 이 브랜치에만 있던 커밋:
  - `7bd2176` - `fix: polish risk briefing smoke findings`
  - `795d245` - `style: calm first-screen dashboard layout`
  - `d24f432` - `fix: separate compact sidebar feature search`
  - `44487e2` - `fix: add compact sidebar state styles`
  - `51b0789` - `feat: streamline query sidebar`
  - `c559670` - `fix: hide risk briefing outside loaded state`
  - `4e87cec` - `feat: show lag-aware risk briefing`
  - `5e45318` - `fix: align risk briefing band with data shape`
  - `9c2f6a3` - `feat: add risk briefing band component`
  - `19e71f7` - `fix: require forecast shift for risk detail`
  - `cb475d6` - `fix: require exact estimate for risk briefing`
  - `c337bdf` - `fix: keep risk briefing pair selection coherent`
  - `321e06d` - `fix: honor observed count for risk window`
  - `e0f8d33` - `feat: derive risk briefing view model`

### `origin/ui/refined-dashboard`

- Tip: `1840951` - `style(charts): align visualization palette with refined UI`
- 삭제 전 상태: `origin/main`에 merge되지 않음
- 삭제 전 이 브랜치에만 있던 커밋:
  - `1840951` - `style(charts): align visualization palette with refined UI`
  - `945657c` - `style(ui): load refinement layer after component styles`
  - `2e9ba12` - `style(ui): replace decorative theme with restrained design tokens`
  - `93493e4` - `feat(ui): add refined enterprise dashboard styling`

## 삭제한 로컬 브랜치

- `codex/rev_0628` at `1772579`
- `codex/workbench-risk-briefing` at `7bd2176`

## 참고

- 브랜치 삭제는 브랜치 이름(ref)을 제거하는 작업입니다. `main`에서 도달 가능한 커밋은 `main` 이력에 남습니다.
- 미병합 브랜치의 커밋 ID는 감사/추적용으로 이 문서에 남겼습니다. 나중에 미병합 작업이 필요하면 로컬 clone 또는 Git object store에 해당 object가 남아 있는 동안 복구해야 합니다.
