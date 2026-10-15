# Repo Supervisor

저장소 작업을 현황 확인부터 구현, 검증, 작업 단위 전달까지 관리하는 Codex 스킬입니다.

## 구성

```text
skills/repo-supervisor/
├── SKILL.md
├── agents/openai.yaml
└── references/
    ├── execution-protocol.md
    └── continuity-and-evidence.md
```

스킬은 `.repo-history`를 통한 작업 재개, 독립 작업의 병렬 처리, 런타임 검증, 문서와 구현의 정합성 감사, 검증된 변경의 커밋·푸시·병합 절차를 제공합니다. 사용 가능한 도구와 저장소 규칙에 따라 실행합니다.

## 작업 계약과 재개

모델명을 고정하지 않고 사용 환경에서 구성한 역량 프로필로 작업을 배정합니다. 필수 역량·권한·컨텍스트 예산을 먼저 확인하고, 한 목표·제한된 쓰기 범위·입출력·수용 기준·의존성·중단 조건을 담은 작업 패킷을 사용합니다. 설계와 불확실성 해소는 조정자가 맡고, 독립 구현과 검수는 계약과 쓰기 경계가 준비된 경우에 나눕니다.

- [실행 프로토콜과 합성 예제](skills/repo-supervisor/references/execution-protocol.md): 프로필 선택, 의존성 그래프 검증, 단일 작성자, 재시도·재분해·통합 검수.
- [체크포인트와 증거 상태](skills/repo-supervisor/references/continuity-and-evidence.md): 중복 방지, 작업 재개, baseline 비교, 일시 장애와 실패 구분, revision별 완료·전달 상태.

이는 스킬이 따르는 수동 실행 계약이며 자동 스케줄러는 아닙니다. 단순 변경은 직접 처리하고, 위임 도구가 없으면 같은 계약으로 순차 실행합니다. 단위 테스트 성공과 실제 사용자 흐름의 수용 기준 충족을 구분합니다.

## 설치

이 저장소를 내려받은 뒤 저장소 루트에서 실행합니다. 기존 설치가 있으면 먼저 차이를 검토하세요.

```sh
mkdir -p "$HOME/.agents/skills"
if [ -e "$HOME/.agents/skills/repo-supervisor" ]; then
  echo "repo-supervisor is already installed; review differences before updating."
else
  cp -R skills/repo-supervisor "$HOME/.agents/skills/repo-supervisor"
fi
```

Codex를 다시 시작해 스킬 목록을 갱신합니다. 스킬 구조는 [공식 OpenAI 문서](https://learn.chatgpt.com/docs/build-skills)를 참고하세요.

## 사용 예시

```text
$repo-supervisor 현재 저장소 상태와 이전 작업 기록을 확인하고 다음 작업을 계획해줘.
```

```text
$repo-supervisor 요청한 기능을 구현하고 필요한 검증을 거쳐 작업 단위로 전달해줘.
```

계획만 요청하면 읽기 전용으로 조사합니다. 구현 작업에 이 스킬을 명시적으로 적용하면 원본 지침에 따라 범위 내 검증된 변경의 커밋·푸시와 조건을 충족한 병합까지 진행할 수 있습니다. 적용 전에 `SKILL.md`의 전달 범위와 Guardrails를 확인하세요. 실행 환경의 권한과 저장소의 필수 승인·검증 절차가 우선합니다.

## 라이선스

[MIT License](LICENSE) — Copyright (c) 2026 hojin.
