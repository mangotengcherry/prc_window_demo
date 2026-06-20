"""실데이터 교체 후 스키마/동작 검증 도구.

    python validate_data.py

data_source.py가 계약을 만족하는지 점검하고, 데이터에서 파생된 차원·표본 통계와
분석 엔드투엔드 smoke까지 돌려본다. 문제가 있으면 무엇이 잘못됐는지 출력하고 1로 종료.
대시보드를 띄우기 전에 먼저 이 스크립트로 초록불을 확인하라.
"""
import sys
from types import SimpleNamespace

import data as D
import analytics


def _hr(t):
    print("\n" + t + "\n" + "─" * len(t))


def main() -> int:
    _hr("1) data_source 스키마 검증")
    problems = D.validate_source()
    if problems:
        print("❌ 스키마 문제:")
        for p in problems:
            print("   -", p)
        print("\nDATA_GUIDE.md의 '필수 스키마'를 참고해 data_source.py를 고치세요.")
        return 1
    print("✓ 스키마 OK")

    _hr("2) 데이터에서 파생된 차원/메타")
    fact = D.load_dataframe()
    print(f"fact_table     : {fact.shape[0]:,} rows × {fact.shape[1]} cols")
    print(f"line_ids       : {D.LINE_IDS}")
    print(f"products       : {D.PRODUCTS}")
    print(f"fab_steps      : {D.FAB_STEPS}")
    print(f"categories     : {D.CATEGORIES}")
    print(f"targets        : {D.ALL_TARGETS}")
    print(f"category_feat. : {{ {', '.join(f'{k}: {len(v)}개' for k, v in D.CATEGORY_FEATURES.items())} }}")
    print(f"numeric feature: {len(D.numeric_feature_keys())} | dc_spec: {len(D.dc_spec())} | lag: {D.TARGET_LAG_DAYS}일")
    if "observed" in fact.columns:
        print(f"observed 비율  : {fact['observed'].mean():.1%}  (낮으면 최근 구간이 미확보)")

    # 표본 충분성 경고(과한 thin 방지)
    _hr("3) 표본 점검")
    warned = False
    for fk in D.numeric_feature_keys()[:8]:
        if fk in fact.columns:
            n = int(fact[fk].notna().sum())
            if n < 30:
                print(f"⚠ feature '{fk}' 비결측 {n}개 — 너무 적으면 bin이 비거나 thin")
                warned = True
    if not warned:
        print("✓ feature별 표본 충분")

    _hr("4) 분석 엔드투엔드 smoke")
    fab = D.FAB_STEPS[0]
    cat = D.CATEGORIES[0]
    yt = D.TARGETS_BY_CATEGORY[cat][0]
    feats = analytics.list_x_features(fab, True, None, None)
    if not feats:
        print(f"❌ fab_step '{fab}'에 매칭되는 X feature가 없음 (feature_catalog 확인)")
        return 1
    xf = feats[0]["name"]
    tmin = fact["fab_track_out_time"].min().strftime("%Y-%m-%d")
    tmax = fact["fab_track_out_time"].max().strftime("%Y-%m-%d")
    dr = SimpleNamespace(start_date=tmin, end_date=tmax, time_column="fab_track_out_time")
    base = dict(line_id=D.LINE_IDS[0], product=D.PRODUCTS[0], category=cat, eds_step=D.EDS_STEPS[0],
                date_range=dr, target_date_range=None, fab_step=fab,
                x_features=[xf], y_targets=[yt], y_target_groups=[], category_feature=None, selection=None)
    b = analytics.compute_binned(SimpleNamespace(bins=10, **base))
    t = analytics.compute_timeseries(SimpleNamespace(**base))
    tbl = analytics.compute_table(SimpleNamespace(**base))
    nb = sum(bb["wafer_count"] for c in b["combos"] for bb in c["bins"])
    print(f"binned   : combos={len(b['combos'])}, bin 합계 wafer={nb}")
    print(f"timeseries: targets={len(t['targets'])}, features={len(t['features'])}, estimates={len(t['estimates'])}")
    print(f"table    : rows={len(tbl['rows'])}, 첫 행 n={tbl['rows'][0]['n'] if tbl['rows'] else 0}")
    if nb == 0:
        print("⚠ 선택 조합의 표본이 0 — 기간/observed/feature 컬럼을 확인하세요.")

    _hr("결과")
    print("✓ 전부 통과 — `uvicorn main:app --reload` 로 대시보드 사용 가능")
    return 0


if __name__ == "__main__":
    sys.exit(main())
