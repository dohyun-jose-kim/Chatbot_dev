# ver2.4.0 — 사용자 인증 + 멀티유저 (user config, id/pw) 구현 계획

> 직전 버전: [`../ver2.6.0_+LangGraph-Agent/PLAN.md`] (에이전트화 완료).
> 개발 순서상 **2.6.0 다음**(코어 안정화 후 사용자 계층), **2.5.0 배포 직전**.
> 인증은 2-tier 원칙대로 **FastAPI(백엔드)가 소유**하고 Streamlit은 로그인하는 클라이언트가 된다.
> 2.5.0 배포는 본 버전이 도입하는 JWT 시크릿/HTTPS 운영에 의존한다(forward dependency).

## 목표

무인증 단일 사용자 앱을 **id/pw 로그인 기반 멀티유저** 앱으로 전환한다.

- **인증**: FastAPI가 `/register`·`/login` 제공, JWT 토큰 발급/검증. `/chat`은 토큰 필요.
- **격리**: 대화 메모리(SqliteSaver thread)와 로그를 **사용자별로 네임스페이스**. A는 B의 맥락을 못 본다.
- **user config**: 사용자별 기본 모델 등 최소 설정을 `users` 테이블에 저장·복원.
- 비밀번호는 **bcrypt 해시**로만 저장(평문 금지).

**성공 기준 (검증 시나리오)**
```
S1 인증:  register(A,pw) → login → JWT 발급 / 잘못된 pw → 401
S2 보호:  토큰 없이 POST /chat → 401 ; 유효 토큰 → 200
S3 격리:  A로 멀티턴 진행 후 같은 session_id를 B 토큰으로 /chat → A의 대화 맥락 안 보임
S4 UI:    브라우저 로그인→챗, 로그아웃, 새로고침 후 재로그인
S5 config: A가 고른 기본 모델이 재로그인 후에도 유지
```

## 빌려오는 것 (직접 구현 최소화)

> 참고 레포 4개에는 인증이 없다 → 코어는 **FastAPI 공식 Security 레시피**를 차용(표준 패턴).

| 출처 | 가져올 것 | 수정 |
|---|---|---|
| FastAPI 공식 "OAuth2 + JWT + password hashing" 튜토리얼 | `/token` 발급, `OAuth2PasswordBearer`, `get_current_user` 의존성, 해시 패턴 | SQLite `users` 테이블 연동, 모델 enum은 gemma |
| ver2.0.0 `03_memory/db_utils.py` | SQLite 연결·테이블 생성 패턴 | `users` 테이블 추가, `application_logs`에 `username` 컬럼 |
| ver2.6.0 `05_api/main.py` | `/chat` 흐름(에이전트 캐시, thread_id, steps) | `Depends(get_current_user)` 보호 + thread_id 유저 네임스페이스 |
| ver2.6.0 `06_ui` | `session_state`, `api_utils` HTTP 클라이언트 | 로그인 게이트 + `Authorization: Bearer` 헤더 |

## 핵심 설계 결정

### 1. 인증은 API 소유, JWT(stateless)
Streamlit은 로그인 폼 → `/login` 호출 → JWT 수신 → `st.session_state`에 보관 → `/chat` 호출 시
`Authorization: Bearer <token>` 전송. FastAPI가 토큰 검증(서버 측 세션 스토어 불필요).
`pyjwt`로 발급/검증, 시크릿은 **env(`JWT_SECRET`)**, 만료(`exp`) 부여.

### 2. 비밀번호 해시
`bcrypt`로 해시 후 `users.hashed_password`에 저장. 로그인 시 `bcrypt.checkpw`로 검증. 평문 미저장.

### 3. 사용자별 격리 = 서버 측 thread 네임스페이스
신원은 **토큰에서만** 취한다(클라이언트 session_id를 신뢰하지 않음).
`thread_id = f"{username}:{client_session_id}"` 로 SqliteSaver 상태를 사용자별로 분리.
`application_logs`에 `username` 컬럼 추가 → 로그도 사용자별. (체크포인터 DB는 공유하되 키로 격리.)

### 4. user config 최소
`users.default_model` 1개로 시작(로그인 시 UI 기본 모델 세팅). 확장은 추후.

### 5. Streamlit 게이트
`st.session_state.token` 없으면 로그인/회원가입 폼, 있으면 챗 화면. 토큰은 session_state에만
보관 → **새로고침 시 재로그인**(쿠키 영속은 범위 외). 로그아웃 = 토큰·메시지 초기화.

### 6. 시크릿/CORS는 env, 배포는 2.5.0
`JWT_SECRET`은 env에서 로드(개발 기본값 + 경고). 현재 Streamlit 서버사이드 호출이라 CORS 불필요.
2.5.0 배포에서 실제 시크릿·HTTPS(토큰 평문 전송 방지)·CORS를 다룬다.

## 파일 구성

```
RAG-LLM_ver2.0.0/
├── config.py                    # + JWT_SECRET(env)·JWT_ALG·ACCESS_TOKEN_EXPIRE_MIN
├── requirements.txt             # + pyjwt, bcrypt, python-multipart
├── 03_memory/
│   ├── auth_db.py               # (신규) users 테이블: create_user/get_user/verify/set_default_model
│   └── db_utils.py              # application_logs에 username 컬럼 + insert 시그니처 갱신
├── 05_api/
│   ├── auth.py                  # (신규) pw 해시, JWT 생성/검증, OAuth2 scheme, get_current_user
│   ├── models.py                # + UserCreate, Token, UserOut (QueryInput은 그대로)
│   └── main.py                  # /register, /login, /me + /chat 보호·유저 스코프
└── 06_ui/
    ├── auth_ui.py               # (신규) 로그인/회원가입 폼
    ├── api_utils.py             # login/register 호출 + Authorization 헤더
    ├── streamlit_app.py         # 미로그인→auth_ui, 로그인→chat 게이트
    └── sidebar.py               # 사용자명·로그아웃·기본모델(user config)
```

## 구현 단계 (Phase별)

원칙: 각 Phase는 시스템을 동작 상태로 남긴다. Phase 끝마다 dev→main 커밋, 완료 시 `tag v2.4.0`.

### Phase 0 — 준비 (deps + config + users 테이블)
- **0.1** `requirements.txt`: `+ pyjwt`, `+ bcrypt`, `+ python-multipart`
  → verify: import 성공
- **0.2** `config.py`: `JWT_SECRET=os.environ.get(...)`(개발 기본값+경고), `JWT_ALG="HS256"`, `ACCESS_TOKEN_EXPIRE_MIN`
  → verify: import OK
- **0.3** `03_memory/auth_db.py`: `users(id, username UNIQUE, hashed_password, default_model, created_at)` 생성
  → verify: create_user/get_user 단위 테스트(임시 DB)
- **commit**: `ver2.4.0 P0: deps + users 테이블`

### Phase A — API 인증 코어
- **A.1** `05_api/auth.py`: `hash_pw`/`verify_pw`(bcrypt), `create_access_token`/`decode_token`(pyjwt),
  `OAuth2PasswordBearer`, `get_current_user`(토큰→username)
  → verify: 토큰 발급→디코드 라운드트립, 잘못된 토큰 거부
- **A.2** `05_api/models.py`: `UserCreate`, `Token`, `UserOut`
- **A.3** `05_api/main.py`: `POST /register`(중복 username 409), `POST /login`(폼→JWT), `GET /me`(보호)
  → verify(curl): register→login→토큰으로 `/me` 200, 무토큰 `/me` 401, 오류 pw 401
- **commit**: `ver2.4.0 PA: register/login/JWT`

### Phase B — /chat 보호 + 사용자 격리
- **B.1** `03_memory/db_utils.py`: `application_logs`에 `username` 컬럼(기존행 NULL 마이그레이션),
  `insert_application_logs(..., username)`
  → verify: 신규 컬럼 기록
- **B.2** `05_api/main.py`: `/chat`에 `user = Depends(get_current_user)`,
  `thread_id = f"{user}:{session_id}"`, 로그에 username
  → verify(curl): 무토큰 401; A 멀티턴 후 같은 session_id를 B 토큰으로 → A 맥락 미노출(S3)
- **commit**: `ver2.4.0 PB: /chat 보호 + 유저 스코프`

### Phase C — Streamlit 로그인 UI
- **C.1** `06_ui/api_utils.py`: `login()`/`register()` + `get_api_response`에 Authorization 헤더,
  401 시 토큰 만료 처리
- **C.2** `06_ui/auth_ui.py`: 로그인/회원가입 폼(탭), 성공 시 `session_state.token`·`username` 저장
- **C.3** `06_ui/streamlit_app.py`: 토큰 없으면 `auth_ui`, 있으면 `chat` 게이트
- **C.4** `06_ui/sidebar.py`: 사용자명 표시 + 로그아웃 버튼
  → verify(브라우저): S4(로그인→챗→로그아웃→재로그인), 무효 로그인 에러
- **commit**: `ver2.4.0 PC: 로그인 UI`

### Phase D — user config + 정리 + 릴리스
- **D.1** `users.default_model` 읽기/쓰기: 로그인 시 기본 모델 세팅, 사이드바에서 변경 시 저장
  → verify: S5(재로그인 후 기본 모델 유지)
- **D.2** README(인증·멀티유저 반영, 로드맵 `2.4.0 ✅`) + `VERIFY.md`(S1–S5)
- **D.3** dev 커밋 → main 머지 → **tag `v2.4.0`**

## 범위 제외
- 대화 이력 브라우저 / 과거 세션 재개 (별도 기능)
- 비밀번호 재설정·이메일 인증·소셜(OAuth) 로그인
- 역할/권한(RBAC), 레이트 리밋, 토큰 쿠키 영속(새로고침 시 재로그인)
- 서버 배포·HTTPS·시크릿 운영·CORS (2.5.0)

## 리스크
- **bcrypt/passlib 버전 호환**: passlib 1.7.4 + bcrypt 4.x 경고 이슈 → `bcrypt` 직접 사용으로 회피(본 PLAN 채택).
- **JWT 시크릿 관리**: 하드코딩 금지, env 로드. 개발 기본값은 배포 전 반드시 교체(2.5.0). HTTPS 없으면 토큰 평문 노출 → 배포 시 필수.
- **기존 무인증 로그 마이그레이션**: `application_logs` 기존행 username NULL → `ALTER TABLE ADD COLUMN`로 안전 추가.
- **Streamlit 토큰 영속 부재**: 새로고침 시 session_state 소멸 → 재로그인. 의도된 단순화(쿠키는 범위 외).
- **신원 신뢰 경계**: thread_id 격리는 반드시 **토큰의 username**으로 구성(클라이언트 session_id 단독 신뢰 금지).
- **chroma wart**(2.2.0~): 검색 시 `chroma.sqlite3` modified 표시 → 실행 후 `git restore`, 커밋 금지.
