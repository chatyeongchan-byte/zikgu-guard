# Weidian H5 Web Simulator & VIP Automation Bot

문서 버전: v1.2 (하이브리드 시각적 검증 프로토타입 포함)  
작성일: 2026-07-25

## 📋 개요

본 시스템은 Weidian 모바일 웹 (H5) 환경을 시뮬레이션하여 네트워크 계층의 API 통신을 분석하고, 주문·결제·VIP 회원 등급 관리 흐름을 파악하며, 실제 변경 결과가 결제 창에 시각적으로 반영되는지 검증하는 것을 목적으로 합니다.

## 🔑 핵심 개념

- **모바일 H5 시뮬레이션**: 브라우저 렌더링 없이 네트워크 계층만 남기고, User-Agent 및 Referer 를 조작하여 서버가 모바일 H5 환경으로 인식하도록 위장
- **파라미터 및 캐시 직접 주입 (Injection)**: 세션 관리, 토큰 갱신 등을 직접 통제하여 API 호출 시 필요한 동적 파라미터 (ct, token, actionToken) 를 주입
- **하이브리드 시각적 검증**: API 조작 후 Playwright 헤드리스 브라우저를 통해 실제 모바일 결제 페이지를 렌더링하여 할인 적용 여부 등을 "눈으로 직접 확인"

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
cd weidian_bot
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. 세션 쿠키 준비

Chrome 브라우저에서 Weidian 에 로그인한 상태에서 EditThisCookie 등의 확장 프로그램으로 `weidian.com` 도메인 쿠키를 JSON 형식으로 내보내기 합니다.

해당 파일을 `cookies.json` 으로 저장하여 스크립트와 동일한 디렉토리에 배치합니다.

### 3. 설정 수정

`backend_api_client.py` 또는 GUI 에서 다음 값을 실제 테스트 대상 값으로 변경합니다:

- `shop_id`: 상점 ID
- `item_id`: 상품 ID
- `sku_id`: 상품 옵션 (SKU) ID

### 4. 실행

#### 백엔드 API 테스트 (CLI)

```bash
python backend_api_client.py
```

#### GUI 애플리케이션 실행

```bash
python gui_simulator.py
```

GUI 가 실행되면:
1. **쿠키 파일 로드** 버튼을 눌러 cookies.json 선택
2. Shop ID, Item ID, SKU ID 입력 후 **정보 저장**
3. **VIP 정보 조회**로 현재 등급 확인
4. 등급 선택 후 **⭐ 등급 변경 적용**
5. **💳 결제 창 확인**으로 시각적 검증

## 📁 프로젝트 구조

```
weidian_bot/
├── backend_api_client.py    # 백엔드 API 클라이언트 및 보안 테스트 모듈
├── gui_simulator.py         # CustomTkinter + Playwright 통합 GUI
├── requirements.txt         # Python 의존성
├── cookies.json             # 세션 쿠키 (직접 생성 필요)
└── .weidian-bulk-manifest-v1.json  # 로컬 메타데이터 (자동 생성)
```

## 🔌 API 엔드포인트

### 주문 및 결제 트랜잭션 (State Machine)

| 단계 | 엔드포인트 | 설명 |
|------|-----------|------|
| 조회 | `/detail/getItemInfo/1.0` | 상품 정보 조회 |
| 검증 | `/vbuy/ConfirmOrder/1.0` | 주문 사전 검증 |
| 재검증 | `/vbuy/ReConfirmOrder/1.0` | 주문 재검증 |
| 생성 | `/vbuy/CreateOrder/1.0` | 주문 생성 |
| 결제 (PC) | `/pay-h5/cashier/pc` | PC 결제 진입 |
| 결제 (Mobile) | `/pay-h5/cashier/index` | 모바일 결제 진입 |

### 주요 파라미터

| 파라미터 | 설명 | 특이사항 |
|---------|------|---------|
| `ct` | 결제 거래 컨텍스트 | PC/Mobile 상이, 일회성, 2~3 분 내 만료 |
| `token` | 주문 - 결제 세션 단기 토큰 | 2~3 분 내 만료 |
| `actionToken` | 클라이언트 - 서버 내부 명령 검증 토큰 | 결제 토큰과 별개, 일회성 |
| `orderId` | 주문 고유 식별자 | CreateOrder 성공 후 발급 |
| `shopId` | 상점 구분 핵심 식별값 | 모든 통신에 필수 |

## 🔒 보안 검증 가이드

### 준비 사항

1. 주 계정 (셀러 권한): 브라우저에서 정상 로그인
2. 보조 계정 (저권한, 구매자용): 별도 브라우저/시크릿창에 로그인
3. 요청 캡처: 주 계정 DevTools → Network 켜고 VIP 설정 정상 저장 → `save_vip_settings` 요청을 Copy as cURL 로 확보
4. 핵심 필드 식별: body 에서 `shopId`, `gradeNames/name`, `targetIndex`, 기준금액 등 확인

### 검증 케이스 4 종

| # | 조작 | 정상 응답 (방어 성공) | 취약 신호 |
|---|------|---------------------|----------|
| A | 무인증 (쿠키·인증헤더 전부 제거) | 401 / 403 | 200 + 변경 |
| B | 저권한 계정 (보조 계정 인증 + 내 shopId) | 403 | 200 + 변경 (수평권한상승, 핵심 시나리오) |
| C | 토큰 무력화 (actionToken/CSRF 삭제·만료값·재사용) | 거부 | 200 (일회성/바인딩 미검증) |
| D | 파라미터 변조 (내 인증 유지 + targetIndex 를 범위 밖 값) | 400 / 거부 | 200 (입력검증 부재) |

### 보안 테스트 실행

```python
from backend_api_client import WeidianAPIClient, SessionConfig, VIPGrade, SecurityTester

# 세션 설정
config = SessionConfig(
    shop_id="YOUR_SHOP_ID",
    item_id="YOUR_ITEM_ID",
    sku_id="YOUR_SKU_ID",
)

client = WeidianAPIClient(config)
tester = SecurityTester(client)

# VIP 등급 객체 생성
vip_grade = VIPGrade(
    shop_id=config.shop_id,
    grade_names=["일반", "VIP", "VVIP"],
    name="VIP",
    server_index=1,
    target_index=2,
    grade_count=3,
    remaining=10000.0,
    original_progress=50.0,
)

# 모든 테스트 실행
results = tester.run_all_tests(vip_grade)
```

**주의사항**: 각 케이스는 한 번씩만 실행하고 코드 기록. 반복 폴링·자동 루프 없음. 200 이 하나라도 뜨면 해당 케이스에서 즉시 중단. 웹 UI 에서 실제로 등급이 바뀌었는지 눈으로 1 회 확인 후, `reset_vip_settings` 또는 백업값으로 즉시 원복.

## 🛠 기술 스택

| 영역 | 기술 | 용도 |
|------|------|------|
| Backend (API & Session) | Python + requests / httpx | H5 환경 위장 세션 유지 및 API 호출 |
| Frontend (GUI) | Python + CustomTkinter | 데스크톱 제어 UI 및 로그 콘솔 |
| Visual Verification | Python + Playwright | 모바일 브라우저 렌더링 및 시각적 결과 검증 |
| Local Metadata | JSON (.weidian-bulk-manifest-v1.json) | 상점 카탈로그, 팩토리 버전, 세션 쿠키 등 로컬 관리 |

## 📝 개발 로드맵 (4 단계)

1. **세션 하이재킹**: 실제 브라우저에서 로그인된 세션 쿠키와 Header 값을 하드코딩하여 `getItemInfo` 등 단순 조회를 우선 성공시킴.
2. **핵심 흐름 연결 (State Machine 구축)**: ConfirmOrder → ReConfirmOrder → CreateOrder 호출을 체이닝하고, 반환되는 임시 토큰 (ct, token) 을 다음 Payload 에 매핑.
3. **actionToken 및 동적 파라미터 획득**: 클라이언트 사이드 토큰 생성 로직을 돌파하기 위해 하이브리드 방식 (Playwright 등 헤드리스 브라우저로 JS 암호화 로직 실행 후 값 추출) 채택.
4. **VIP 모니터링 분리 및 조건부 트리거**: `remaining` 값을 Read-Only 로 주기적으로 Polling 하고, 특정 임계치 도달 시 결제 엔진 (CreateOrder) 을 트리거.

## ⚠️ 주의사항

- 본 도구는 교육 및 보안 연구 목적으로만 사용해야 합니다.
- 실제 상점 운영자에 대한 허가 없이 시스템을 테스트하지 마십시오.
- 모든 테스트는 자체 소유 상점 또는 명시적 허가를 받은 상점에서만 수행하십시오.
- 200 응답이 하나라도 나오면 해당 케이스에서 즉시 중단하고 웹 UI 에서 실제로 등급이 바뀌었는지 눈으로 1 회 확인 후, `reset_vip_settings` 또는 백업값으로 즉시 원복하십시오.

## 📄 라이선스

본 프로젝트는 교육 및 연구 목적으로만 제공됩니다.
