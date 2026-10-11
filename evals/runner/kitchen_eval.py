"""Frozen four-input native diagnostic for the newly expanded kitchen scope."""
import argparse
from pathlib import Path
import closure_eval as bounded

DATA="data/business/lg-kitchen-v4"
SPECS=[
    ("fridge","K01","B502S33",1,
     "B502S33의 실제 후기를 바탕으로 불편을 찾아 기존 기능과 비교한 개선안을 하나 만들어줘. 새 부품 없이 적용할 방법과 남는 문제를 알려줘. 실제 사용 경험과 일반 선호를 구분하고, 구현 단계·효과 측정 방법·사업적 기대 가치와 한계를 포함해줘."),
    ("microwave","K02","MWJ25E",1,
     "MWJ25E를 선택했어. 실제 후기에서 사용 불편을 찾아 기존 기능과 비교해 한 가지 개선안을 기획해줘. 제안서에 없던 불편도 근거가 있으면 검토해줘. 폭260×깊이210×높이160mm 용기를 넣고 회전해도 안전하다고 확정할 수 있는지도 검토해줘. 새 부품은 추가하지 않을게. 구현 단계·효과 측정 방법·사업적 기대 가치와 한계를 포함해줘."),
    ("product-1","K03","DUBJ2EA",2,
     "DUBJ2EA의 실제 후기에서 불편을 찾아 기존 기능과 비교한 개선안을 두 개 이내로 만들어줘. 기존 부품과 사용 방법은 활용해도 되지만 새 부품은 추가하지 않을게. 근거와 미확인, 구현 단계·효과 측정 방법·사업적 기대 가치 및 이 모델의 판매 상태 한계를 함께 보여줘."),
    ("followup","K04","DUBJ2EA",1,
     "방금 DUBJ2EA 검토를 이어갈게. 이제 식기를 다시 배치하거나 부품을 분리하는 방법은 쓰지 않을 거야. 새 부품 금지는 유지하고 한 가지 안만 남겨줘. 못 하는 일과 효과를 확인해야 할 항목을 밝히고 이전 제안·검토·출처 기록을 보존해줘. 구현 단계와 효과 검증 계획도 이 조건에 맞춰줘."),
]

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation",choices=("prepare","run"))
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--jobs",nargs="+",default=[])
    args=parser.parse_args()
    if args.operation=="prepare":
        bounded.prepare(args.report,specs=SPECS,data_path=DATA)
    else:
        bounded.run(args.report,args.jobs)
