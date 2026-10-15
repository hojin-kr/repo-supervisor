# Repo Supervisor

저장소 작업을 현황 확인부터 구현, 검증, 작업 단위 전달까지 관리하는 Codex 스킬입니다.

## 구성

```text
skills/repo-supervisor/
├── SKILL.md
└── agents/openai.yaml
```

스킬은 `.repo-history`를 통한 작업 재개, 독립 작업의 병렬 처리, 런타임 검증, 문서와 구현의 정합성 감사, 검증된 변경의 커밋·푸시·병합 절차를 제공합니다. 사용 가능한 도구와 저장소 규칙에 따라 실행합니다.

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

## GitHub 게시 준비 상태

- 원본: 로컬 Codex용 `repo-supervisor` 버전. 문서 정합성 감사 지침과 UI 메타데이터를 포함하며 내용은 그대로 보존했습니다.
- 원격: `https://github.com/hojin-kr/repo-supervisor.git`
- 로컬 Git 작성자 이메일: `jhj377@gmail.com`
- GitHub CLI의 인증 계정은 `hojin-kr`로 확인했습니다. 공개 프로필의 이메일은 비어 있어 위 이메일과 계정의 연결은 확인하지 못했습니다.
- 2026-10-15에 `hojin-kr/repo-supervisor` 비공개 원격 저장소를 생성했습니다. 푸시는 아직 수행하지 않았습니다. 라이선스는 공개 배포 전에 결정해야 합니다.

다음 명령으로 준비된 내용을 원격 저장소에 올릴 수 있습니다.

```sh
git push -u origin main
```
