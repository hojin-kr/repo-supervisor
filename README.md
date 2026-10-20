# Repo Supervisor

저장소 작업을 현황 확인부터 구현, 검증, 작업 단위 전달까지 관리하는 Codex 스킬입니다.

## 구성

```text
skills/repo-supervisor/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── verify.py
│   └── coordination_policy.py
├── assets/verification-packet.json
└── references/
    ├── execution-protocol.md
    ├── continuity-and-evidence.md
    ├── verification.md
    └── storage-policy.md
```

스킬은 `.repo-history`를 통한 작업 재개, 독립 작업의 병렬 처리, 런타임 검증, 문서와 구현의 정합성 감사, 검증된 변경의 커밋·푸시·병합 절차를 제공합니다. 사용 가능한 도구와 저장소 규칙에 따라 실행합니다.

## 주요 설계 개념: 구현 요청은 전달까지 상시 승인

사용자가 이 스킬을 **구현 요청으로 호출하는 명시적 의도**는 해당 요청 범위의 구현·검증뿐 아니라 **commit·push, 저장소의 머지 조건을 충족한 경우 merge까지 재확인 없이 진행하는 상시 승인**을 포함합니다. 작업 단위가 검증되면 전달까지 마치는 것이 이 스킬의 주요 설계 개념입니다.

merge는 품질·수용 기준, 필수 검수와 CI, 충돌 해결, 대상 브랜치 확인, branch protection 등 해당 저장소의 필수 조건을 모두 충족해야 합니다. 범위·대상 브랜치·실행 권한이 불명확하면 확인한 뒤 진행합니다. 계획만 요청하거나 읽기 전용 검수를 요청한 경우에는 이 상시 승인이 적용되지 않습니다.

승인의 근거는 사용자의 구현 요청이며, README나 스킬 파일 자체가 실행 권한을 부여하지 않습니다. 사용자의 중단 지시·승인 제한이 우선하고, 필수 플랫폼 승인과 저장소 보호규칙도 그대로 적용됩니다. 구체적인 전달 조건은 [스킬 Workflow와 Guardrails](skills/repo-supervisor/SKILL.md)를 따릅니다.

## 작업 계약과 재개

ChatGPT Codex와 사용 가능한 기본 도구만 사용하며, Codex 모델의 역량 프로필로 작업을 배정합니다. 외부 AI 서비스 호출이나 쿼터에 따른 서비스 전환은 하지 않습니다. Codex가 차단되면 체크포인트를 보존하고 원인을 보고합니다. 필수 역량·권한·컨텍스트 예산을 먼저 확인하고, 한 목표·제한된 쓰기 범위·입출력·수용 기준·의존성·중단 조건을 담은 작업 패킷을 사용합니다. 설계와 불확실성 해소는 조정자가 맡고, 독립 구현과 검수는 계약과 쓰기 경계가 준비된 경우에 나눕니다.

- [실행 프로토콜과 합성 예제](skills/repo-supervisor/references/execution-protocol.md): 프로필 선택, 의존성 그래프 검증, 단일 작성자, 재시도·재분해·통합 검수.
- [체크포인트와 증거 상태](skills/repo-supervisor/references/continuity-and-evidence.md): 중복 방지, 작업 재개, baseline 비교, 일시 장애와 실패 구분, revision별 완료·전달 상태.

이는 스킬이 따르는 수동 실행 계약이며 자동 스케줄러는 아닙니다. 단순 변경은 직접 처리하고, 위임 도구가 없으면 같은 계약으로 순차 실행합니다. 단위 테스트 성공과 실제 사용자 흐름의 수용 기준 충족을 구분합니다.

## 반복 오류를 구조와 검증으로 줄이기

반복 피드백은 먼저 타입·불변량·경계, 기존 린트·테스트·CI로 옮길 수 있는지 판단하고, 자동화할 수 없는 판단만 짧은 지침으로 남깁니다. 목표를 내부적으로 재진술하고, 관찰로 풀 수 있는 질문은 안전한 프로토타입과 실측으로 해결합니다. 구현자의 테스트 기대값도 독립 검수 대상입니다.

[프로젝트 검증 절차](skills/repo-supervisor/references/verification.md)는 변경 영향에 맞는 최소 검증 선택, Xcode 결과의 출처 보존, 실제 사용자 표면을 구동하는 방법을 설명합니다. 함께 제공하는 JSON 패킷과 Python 표준 라이브러리 도구는 명령·예상 결과·불변량을 커밋/소스 스냅샷·환경에 연결합니다. 실패·`NOT RUN`·오래된 증거는 통과하지 않으며, 템플릿의 수동 항목도 실제 driver가 생기기 전에는 통과하지 않습니다. 도구는 패킷의 명령을 실행하므로 먼저 신뢰성과 부작용을 확인해야 합니다. 전후 스냅샷 사이에서 소스를 변경한 뒤 복원하는 동작은 탐지하지 못하므로, 불변 실행이 필요한 경우 외부에서 쓰기를 차단한 소스나 식별된 불변 산출물로 독립 검증해야 합니다.

저장소 자체 회귀 검증은 추가 설치 없이 실행합니다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

pstack의 원칙을 참고해 독자적으로 작성했으며, [고정 revision의 1차 자료와 MIT 라이선스](skills/repo-supervisor/references/verification.md#sources-and-adaptation-boundaries)를 기록했습니다. pstack 설치·모델 기본값·외부 작업 권한은 채택하지 않습니다.

## 공용 정책과 로컬 실행 정보 분리

공용 저장소에는 범용 정책·합성 예제·테스트만 두고, 실제 볼륨 식별자·호스트 경로·설정·상태·원시 로그·백업은 모든 Git checkout 밖에 보존합니다. [저장 정책](skills/repo-supervisor/references/storage-policy.md)과 작은 정책 모듈은 로컬 비공개 경계, 볼륨 관측·공간 예약·복구 비교를 다룹니다. 기존 작업 패킷과 strict v1 검증 도구를 재사용합니다.

서비스 선택·비용/쿼터 전환 구현과 관련 합성 테스트는 제거했습니다. 현재 테스트는 저장 경계와 검증 도구를 확인합니다. 물리 mount 검사·파일 이동 도구는 제공하지 않으며, 이동 결정은 원본을 보존하고 영구삭제를 승인하지 않습니다.

## 설치

이 저장소를 내려받은 뒤 저장소 루트에서 실행합니다. 기존 설치가 있으면 먼저 차이를 검토하세요.

Codex의 설치 위치는 host와 버전에 따라 다를 수 있습니다. 2026-10-20 확인한 [공식 로컬 스킬 위치 안내](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)는 사용자 스킬 경로로 `$HOME/.agents/skills`를 표기합니다. 이 Mac에서 확인한 기존 설치는 `$CODEX_HOME/skills` 아래였습니다. 아래 명령은 그 Mac 관측 경로를 예로 든 것이므로, 다른 host에서는 해당 버전의 공식 안내와 실제 활성 경로를 확인해 사용하세요. 경로가 다르다고 기존 설치를 이동하거나 삭제하지 마세요.

```sh
skill_root="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_root"
if [ -e "$skill_root/repo-supervisor" ]; then
  echo "repo-supervisor is already installed; review differences before updating."
else
  cp -R skills/repo-supervisor "$skill_root/repo-supervisor"
fi
```

저장소의 `skills/repo-supervisor`가 원본입니다. 사용 중인 Codex의 `CODEX_HOME`을 확인하고 그 아래 `skills/repo-supervisor`에 설치하세요. 이미 설치된 디렉터리는 차이를 검토한 뒤 갱신하고, 다른 작업 저장소의 복사본만 바꾸지 마세요. Codex를 다시 시작해 스킬 목록을 갱신합니다. 스킬 구조는 [공식 OpenAI 문서](https://learn.chatgpt.com/docs/build-skills)를 참고하세요.

## 사용 예시

```text
$repo-supervisor 현재 저장소 상태와 이전 작업 기록을 확인하고 다음 작업을 계획해줘.
```

```text
$repo-supervisor 요청한 기능을 구현하고 필요한 검증을 거쳐 작업 단위로 전달해줘.
```

계획 요청은 읽기 전용으로 조사합니다. 구현 요청은 위 주요 설계 개념의 실행 계약에 따라 범위 내 검증된 작업의 전달까지 진행합니다.

## 라이선스

[MIT License](LICENSE) — Copyright (c) 2026 hojin.
