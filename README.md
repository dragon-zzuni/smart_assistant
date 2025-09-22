# Smart Assistant

AI 기반 스마트 어시스턴트로 이메일과 메신저 메시지를 자동으로 분석하고 TODO 리스트를 생성하는 시스템입니다.

## 🚀 주요 기능

- **📧 이메일 수집**: IMAP을 통한 네이버, Gmail 등 이메일 수집
- **📱 메신저 수집**: Slack, Teams 등 메신저 메시지 수집 (시뮬레이터 지원)
- **🤖 AI 분석**: GPT-4o mini를 사용한 메시지 요약 및 우선순위 분류
- **⚡ 액션 추출**: 메시지에서 필요한 액션과 TODO 항목 자동 추출
- **📋 TODO 생성**: 우선순위별로 정리된 TODO 리스트 생성

## 📁 프로젝트 구조

```
smart_assistant/
├── config/                 # 설정 파일
│   └── settings.py
├── ingestors/             # 데이터 수집 모듈
│   ├── email_imap.py      # 이메일 IMAP 수집기
│   └── messenger_adapter.py # 메신저 어댑터
├── nlp/                   # 자연어 처리 모듈
│   ├── summarize.py       # 메시지 요약
│   ├── priority_ranker.py # 우선순위 분류
│   └── action_extractor.py # 액션 추출
├── store/                 # 데이터 저장소 (향후 구현)
├── drafts/                # 초안 생성 (향후 구현)
├── ui/                    # 사용자 인터페이스 (향후 구현)
├── main.py                # 메인 애플리케이션
├── run_assistant.py       # 실행 스크립트
└── requirements.txt       # 의존성 패키지
```

## 🛠️ 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`env_example.txt`를 참고하여 `.env` 파일을 생성하고 필요한 값들을 설정하세요:

```bash
# OpenAI API 키 (LLM 기능용)
OPENAI_API_KEY=your_openai_api_key_here

# 이메일 설정
EMAIL_ADDRESS=your_email@example.com
EMAIL_PASSWORD=your_app_password_here
```

### 3. 이메일 설정

#### 네이버 메일
1. 네이버 메일 설정 → IMAP/POP3 사용 설정
2. 2단계 인증 활성화
3. 앱 비밀번호 생성

#### Gmail
1. Gmail 설정 → 전달 및 POP/IMAP → IMAP 사용
2. 2단계 인증 활성화
3. 앱 비밀번호 생성

## 🚀 사용법

### 기본 실행

```bash
python run_assistant.py
```

### 프로그래밍 방식

```python
import asyncio
from main import SmartAssistant

async def main():
    assistant = SmartAssistant()
    
    email_config = {
        "email": "your_email@example.com",
        "password": "your_app_password",
        "provider": "naver"
    }
    
    messenger_config = {
        "use_simulator": True
    }
    
    result = await assistant.run_full_cycle(email_config, messenger_config)
    
    if result.get("success"):
        todo_list = result["todo_list"]
        print(f"생성된 TODO: {todo_list['total_items']}개")

asyncio.run(main())
```

## 📊 출력 예시

```
🚀 Smart Assistant 실행 중...
==================================================
📊 수집 결과:
   총 메시지: 15개
   TODO 아이템: 8개
   우선순위: High(3), Medium(4), Low(1)

🔥 상위 TODO 아이템:
 1. [HIGH ] 미팅 참석: 내일 오전 10시 팀 미팅
    요청자: 김부장
    데드라인: 2024-01-16T10:00:00
    타입: meeting

 2. [HIGH ] 문서 검토: 프로젝트 문서 검토 부탁드립니다
    요청자: 박대리
    데드라인: 2024-01-19T18:00:00
    타입: review
```

## 🔧 설정 옵션

### 우선순위 규칙 커스터마이징

`config/settings.py`에서 우선순위 규칙을 수정할 수 있습니다:

```python
PRIORITY_RULES = {
    "high_priority_keywords": [
        "긴급", "urgent", "asap", "즉시", "오늘까지", "deadline"
    ],
    "high_priority_senders": [
        "boss@company.com", "manager@company.com"
    ]
}
```

### LLM 모델 변경

```python
LLM_CONFIG = {
    "model": "gpt-4o-mini",  # 또는 "gpt-4", "gpt-3.5-turbo"
    "max_tokens": 1000,
    "temperature": 0.3
}
```

## 🔒 보안

- 이메일 비밀번호는 앱 비밀번호 사용 권장
- API 키는 환경변수로 관리
- 민감한 정보는 OS Keyring에 저장 (향후 구현)

## 🚧 향후 계획

- [ ] SQLite 데이터베이스 연동
- [ ] FAISS 벡터 검색
- [ ] PyQt6 GUI 인터페이스
- [ ] FastAPI 백엔드 서버
- [ ] APScheduler 자동 스케줄링
- [ ] 실제 메신저 API 연동 (Slack, Teams)
- [ ] 이메일 초안 자동 생성
- [ ] 음성 메시지 STT 처리

## 🐛 문제 해결

### 이메일 연결 실패
- IMAP 설정 확인
- 앱 비밀번호 사용
- 방화벽/프록시 설정 확인

### LLM 오류
- OpenAI API 키 확인
- API 사용량 제한 확인
- 네트워크 연결 확인

### 한글 깨짐
- Windows PowerShell에서 UTF-8 설정 확인
- 환경변수 PYTHONIOENCODING=utf-8 설정

## 📝 라이선스

MIT License

## 🤝 기여

이슈 리포트와 풀 리퀘스트를 환영합니다!
