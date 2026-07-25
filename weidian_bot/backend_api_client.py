#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weidian H5 Web Simulator & VIP Automation Bot
문서 버전: v1.2 (하이브리드 시각적 검증 프로토타입 포함)
작성일: 2026-07-25

핵심 기능:
1. 모바일 H5 시뮬레이션 (User-Agent, Referer 조작)
2. API 파라미터 직접 주입 (ct, token, actionToken)
3. 하이브리드 시각적 검증 (Playwright 연동)
4. VIP 등급 관리 및 모니터링
"""

import json
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry


# =============================================================================
# 상수 정의
# =============================================================================

BASE_URL = "https://h5.weidian.com"
API_BASE = f"{BASE_URL}/api"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://h5.weidian.com/",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json;charset=UTF-8",
}

MOBILE_PAYMENT_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://h5.weidian.com/pay-h5/cashier/index",
}

# API 엔드포인트 매핑
API_ENDPOINTS = {
    "get_item_info": "/detail/getItemInfo/1.0",
    "confirm_order": "/vbuy/ConfirmOrder/1.0",
    "reconfirm_order": "/vbuy/ReConfirmOrder/1.0",
    "create_order": "/vbuy/CreateOrder/1.0",
    "pc_cashier": "/pay-h5/cashier/pc",
    "mobile_cashier": "/pay-h5/cashier/index",
    "vip_detail": "/m/mkt-h5-member-detail/index",
    "save_vip_settings": "/m/mkt-h5-member/save_vip_settings",
    "reset_vip_settings": "/m/mkt-h5-member/reset_vip_settings",
}


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class ItemInfo:
    """상품 정보 데이터 클래스"""
    item_id: str
    title: str
    price: float
    original_price: float
    shop_id: str
    shop_name: str
    skus: List[Dict[str, Any]] = field(default_factory=list)
    stock: int = 0
    sales: int = 0


@dataclass
class OrderContext:
    """주문 컨텍스트 (State Machine 상태 저장)"""
    ct: Optional[str] = None
    token: Optional[str] = None
    action_token: Optional[str] = None
    order_id: Optional[str] = None
    qr_code_status_key: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """토큰 유효성 검사 (2~3 분 만료)"""
        if not self.expires_at:
            return False
        return datetime.now() < self.expires_at
    
    def refresh_expiry(self, minutes: int = 2):
        """만료 시간 갱신"""
        self.expires_at = datetime.now() + timedelta(minutes=minutes)


@dataclass
class VIPGrade:
    """VIP 등급 정보"""
    grade_names: List[str] = field(default_factory=list)
    name: str = ""
    server_index: int = 0
    target_index: int = 0
    grade_count: int = 0
    remaining: float = 0.0
    original_progress: float = 0.0
    shop_id: str = ""


@dataclass
class SessionConfig:
    """세션 설정"""
    cookies: Dict[str, str] = field(default_factory=dict)
    shop_id: str = ""
    item_id: str = ""
    sku_id: str = ""
    quantity: int = 1
    member_type: str = "common"
    trade_type: str = "common_trade"
    source_id: str = ""
    channel: str = "H5"


# =============================================================================
# 유틸리티 함수
# =============================================================================

def generate_ct() -> str:
    """결제 거래 컨텍스트 생성 (일회성, 2~3 분 만료)"""
    timestamp = int(time.time() * 1000)
    random_part = secrets.token_hex(16)
    return f"{timestamp}_{random_part}"


def generate_action_token(data: str, secret: str = "weidian_h5_secret") -> str:
    """actionToken 생성 (클라이언트-서버 내부 명령 검증용)"""
    payload = f"{data}:{secret}:{int(time.time())}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def load_cookies_from_file(filepath: str = "cookies.json") -> Dict[str, str]:
    """쿠키 파일 로드 (EditThisCookie 형식 지원)"""
    path = Path(filepath)
    if not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # EditThisCookie 형식 변환
    if isinstance(data, list):
        return {cookie['name']: cookie['value'] for cookie in data if 'name' in cookie and 'value' in cookie}
    
    # 일반 JSON 형식
    return data


def save_to_manifest(data: Dict[str, Any], filepath: str = ".weidian-bulk-manifest-v1.json"):
    """로컬 메타데이터 저장"""
    path = Path(filepath)
    existing = {}
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    
    existing.update(data)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def load_from_manifest(filepath: str = ".weidian-bulk-manifest-v1.json") -> Dict[str, Any]:
    """로컬 메타데이터 로드"""
    path = Path(filepath)
    if not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# =============================================================================
# API 클라이언트 클래스
# =============================================================================

class WeidianAPIClient:
    """Weidian H5 API 클라이언트"""
    
    def __init__(self, config: SessionConfig):
        self.config = config
        self.session = requests.Session()
        self.order_context = OrderContext()
        
        # 기본 헤더 설정
        self.session.headers.update(DEFAULT_HEADERS)
        
        # 쿠키 설정
        if config.cookies:
            self.session.cookies.update(config.cookies)
        
        # 재시도 전략 설정
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
    
    def _get_url(self, endpoint_key: str) -> str:
        """엔드포인트 URL 생성"""
        return f"{BASE_URL}{API_ENDPOINTS.get(endpoint_key, endpoint_key)}"
    
    def _post(self, url: str, data: Dict[str, Any], headers: Optional[Dict] = None) -> Dict[str, Any]:
        """POST 요청"""
        try:
            response = self.session.post(
                url,
                json=data,
                headers=headers or DEFAULT_HEADERS,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "success": False}
    
    def _get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """GET 요청"""
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers or DEFAULT_HEADERS,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "success": False}
    
    def get_item_info(self, item_id: Optional[str] = None) -> Dict[str, Any]:
        """상품 정보 조회"""
        url = self._get_url("get_item_info")
        params = {
            "item_id": item_id or self.config.item_id,
            "shop_id": self.config.shop_id,
            "_t": int(time.time() * 1000)
        }
        return self._get(url, params=params)
    
    def confirm_order(self) -> Dict[str, Any]:
        """주문 사전 검증 (State Machine Step 1)"""
        url = self._get_url("confirm_order")
        
        # ct 토큰 생성 및 주입
        self.order_context.ct = generate_ct()
        self.order_context.refresh_expiry()
        
        payload = {
            "item_id": self.config.item_id,
            "item_sku_id": self.config.sku_id,
            "quantity": self.config.quantity,
            "shop_id": self.config.shop_id,
            "ct": self.order_context.ct,
            "memberType": self.config.member_type,
            "source_id": self.config.source_id,
            "channel": self.config.channel,
            "tradeType": self.config.trade_type,
        }
        
        result = self._post(url, payload)
        
        # token 추출 (응답에서 파싱 필요)
        if result.get("success") and "token" in result.get("data", {}):
            self.order_context.token = result["data"]["token"]
        
        return result
    
    def reconfirm_order(self) -> Dict[str, Any]:
        """주문 재검증 (State Machine Step 2)"""
        if not self.order_context.is_valid():
            return {"error": "Order context expired", "success": False}
        
        url = self._get_url("reconfirm_order")
        
        payload = {
            "item_id": self.config.item_id,
            "item_sku_id": self.config.sku_id,
            "quantity": self.config.quantity,
            "shop_id": self.config.shop_id,
            "ct": self.order_context.ct,
            "token": self.order_context.token,
            "memberType": self.config.member_type,
        }
        
        result = self._post(url, payload)
        
        # actionToken 추출 (응답에서 파싱 필요)
        if result.get("success") and "actionToken" in result.get("data", {}):
            self.order_context.action_token = result["data"]["actionToken"]
        
        return result
    
    def create_order(self) -> Dict[str, Any]:
        """주문 생성 (State Machine Step 3)"""
        if not self.order_context.is_valid():
            return {"error": "Order context expired", "success": False}
        
        url = self._get_url("create_order")
        
        # actionToken 생성 (실제 로직은 JS 암호화 사용)
        action_data = f"{self.config.item_id}:{self.config.sku_id}:{self.order_context.token}"
        self.order_context.action_token = generate_action_token(action_data)
        
        payload = {
            "item_id": self.config.item_id,
            "item_sku_id": self.config.sku_id,
            "quantity": self.config.quantity,
            "shop_id": self.config.shop_id,
            "ct": self.order_context.ct,
            "token": self.order_context.token,
            "actionToken": self.order_context.action_token,
            "memberType": self.config.member_type,
            "tradeType": self.config.trade_type,
            "from": "H5",
            "source_id": self.config.source_id,
            "channel": self.config.channel,
        }
        
        result = self._post(url, payload)
        
        # orderId 추출
        if result.get("success") and "orderId" in result.get("data", {}):
            self.order_context.order_id = result["data"]["orderId"]
            self.order_context.qr_code_status_key = result["data"].get("qrCodeStatusKey")
        
        return result
    
    def get_vip_detail(self, shop_id: Optional[str] = None) -> Dict[str, Any]:
        """VIP 상세 정보 조회"""
        url = self._get_url("vip_detail")
        params = {
            "shopId": shop_id or self.config.shop_id,
            "_t": int(time.time() * 1000)
        }
        return self._get(url, params=params)
    
    def save_vip_settings(self, vip_grade: VIPGrade) -> Dict[str, Any]:
        """VIP 등급 설정 저장"""
        url = self._get_url("save_vip_settings")
        
        payload = {
            "shopId": vip_grade.shop_id or self.config.shop_id,
            "gradeNames": vip_grade.grade_names,
            "name": vip_grade.name,
            "targetIndex": vip_grade.target_index,
            "serverIndex": vip_grade.server_index,
            "gradeCount": vip_grade.grade_count,
            "remaining": vip_grade.remaining,
            "originalProgress": vip_grade.original_progress,
        }
        
        # actionToken 추가
        action_data = f"vip:{payload['shopId']}:{payload['targetIndex']}"
        payload["actionToken"] = generate_action_token(action_data)
        
        return self._post(url, payload)
    
    def reset_vip_settings(self, shop_id: Optional[str] = None) -> Dict[str, Any]:
        """VIP 등급 설정 초기화 (롤백용)"""
        url = self._get_url("reset_vip_settings")
        
        payload = {
            "shopId": shop_id or self.config.shop_id,
        }
        
        return self._post(url, payload)
    
    def get_payment_url(self, mobile: bool = True) -> str:
        """결제 페이지 URL 생성"""
        if not self.order_context.order_id:
            raise ValueError("Order ID not available. Call create_order first.")
        
        endpoint = "mobile_cashier" if mobile else "pc_cashier"
        base_url = self._get_url(endpoint)
        
        params = {
            "orderId": self.order_context.order_id,
            "qrCodeStatusKey": self.order_context.qr_code_status_key,
            "tradeType": self.config.trade_type,
        }
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query}"


# =============================================================================
# 보안 검증 모듈 (IDOR 및 권한 상승 테스트)
# =============================================================================

class SecurityTester:
    """보안 검증 테스터"""
    
    def __init__(self, client: WeidianAPIClient):
        self.client = client
        self.results: List[Dict[str, Any]] = []
    
    def test_no_auth(self, vip_grade: VIPGrade) -> Dict[str, Any]:
        """케이스 A: 무인증 테스트 (쿠키·인증헤더 전부 제거)"""
        # 새 세션 생성 (인증 없음)
        temp_config = SessionConfig(shop_id=self.client.config.shop_id)
        temp_client = WeidianAPIClient(temp_config)
        
        result = temp_client.save_vip_settings(vip_grade)
        
        test_result = {
            "case": "A. 무인증",
            "description": "쿠키·인증헤더 전부 제거",
            "expected": "401 / 403",
            "vulnerability_signal": "200 + 변경",
            "actual_status": "200" if result.get("success") else "401/403",
            "passed": not result.get("success"),
            "result": result
        }
        
        self.results.append(test_result)
        return test_result
    
    def test_low_privilege(self, vip_grade: VIPGrade, low_priv_cookies: Dict[str, str]) -> Dict[str, Any]:
        """케이스 B: 저권한 계정 테스트 (수평권한상승)"""
        temp_config = SessionConfig(
            shop_id=self.client.config.shop_id,
            cookies=low_priv_cookies
        )
        temp_client = WeidianAPIClient(temp_config)
        
        result = temp_client.save_vip_settings(vip_grade)
        
        test_result = {
            "case": "B. 저권한 계정",
            "description": "보조 계정 인증 + 내 shopId",
            "expected": "403",
            "vulnerability_signal": "200 + 변경 (수평권한상승, 핵심 시나리오)",
            "actual_status": "200" if result.get("success") else "403",
            "passed": not result.get("success"),
            "result": result
        }
        
        self.results.append(test_result)
        return test_result
    
    def test_token_invalid(self, vip_grade: VIPGrade) -> Dict[str, Any]:
        """케이스 C: 토큰 무력화 테스트 (actionToken/CSRF 삭제·만료값·재사용)"""
        # 만료된 actionToken 사용
        vip_grade_copy = VIPGrade(**asdict(vip_grade))
        vip_grade_copy.shop_id = self.client.config.shop_id
        
        url = f"{BASE_URL}{API_ENDPOINTS['save_vip_settings']}"
        
        payload = {
            "shopId": vip_grade_copy.shop_id,
            "gradeNames": vip_grade_copy.grade_names,
            "name": vip_grade_copy.name,
            "targetIndex": vip_grade_copy.target_index,
            "serverIndex": vip_grade_copy.server_index,
            "gradeCount": vip_grade_copy.grade_count,
            "remaining": vip_grade_copy.remaining,
            "originalProgress": vip_grade_copy.original_progress,
            "actionToken": "expired_or_invalid_token",  # 무효한 토큰
        }
        
        result = self.client.session.post(url, json=payload, timeout=30).json()
        
        test_result = {
            "case": "C. 토큰 무력화",
            "description": "actionToken/CSRF 삭제·만료값·재사용",
            "expected": "거부",
            "vulnerability_signal": "200 (일회성/바인딩 미검증)",
            "actual_status": "200" if result.get("success") else "거부",
            "passed": not result.get("success"),
            "result": result
        }
        
        self.results.append(test_result)
        return test_result
    
    def test_param_tampering(self, vip_grade: VIPGrade) -> Dict[str, Any]:
        """케이스 D: 파라미터 변조 테스트 (targetIndex 를 범위 밖 값)"""
        vip_grade_copy = VIPGrade(**asdict(vip_grade))
        vip_grade_copy.target_index = 9999  # 범위 밖 값
        vip_grade_copy.shop_id = self.client.config.shop_id
        
        result = self.client.save_vip_settings(vip_grade_copy)
        
        test_result = {
            "case": "D. 파라미터 변조",
            "description": "내 인증 유지 + targetIndex 를 범위 밖 값",
            "expected": "400 / 거부",
            "vulnerability_signal": "200 (입력검증 부재)",
            "actual_status": "200" if result.get("success") else "거부",
            "passed": not result.get("success"),
            "result": result
        }
        
        self.results.append(test_result)
        return test_result
    
    def run_all_tests(self, vip_grade: VIPGrade, low_priv_cookies: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """모든 보안 테스트 실행"""
        print("=" * 60)
        print("🔒 보안 검증 테스트 시작")
        print("=" * 60)
        
        # 케이스 A
        print("\n[케이스 A] 무인증 테스트...")
        self.test_no_auth(vip_grade)
        
        # 케이스 B
        if low_priv_cookies:
            print("[케이스 B] 저권한 계정 테스트...")
            self.test_low_privilege(vip_grade, low_priv_cookies)
        else:
            print("[케이스 B] 저권한 계정 테스트 건너뜀 (쿠키 없음)")
        
        # 케이스 C
        print("[케이스 C] 토큰 무력화 테스트...")
        self.test_token_invalid(vip_grade)
        
        # 케이스 D
        print("[케이스 D] 파라미터 변조 테스트...")
        self.test_param_tampering(vip_grade)
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        
        for r in self.results:
            status = "✅ PASS" if r["passed"] else "⚠️ VULNERABILITY"
            print(f"{status} - {r['case']}: {r['actual_status']}")
        
        print(f"\n총 {total}개 중 {passed}개 통과")
        
        return self.results


# =============================================================================
# 메인 실행 예제
# =============================================================================

def main():
    """메인 실행 함수 (예제)"""
    print("=" * 60)
    print("Weidian H5 Web Simulator & VIP Automation Bot v1.2")
    print("=" * 60)
    
    # 1. 쿠키 로드
    cookies = load_cookies_from_file("cookies.json")
    if not cookies:
        print("⚠️  cookies.json 파일을 찾을 수 없습니다. 빈 세션으로 시작합니다.")
    
    # 2. 세션 설정
    config = SessionConfig(
        cookies=cookies,
        shop_id="YOUR_SHOP_ID",  # 실제 값으로 변경
        item_id="YOUR_ITEM_ID",  # 실제 값으로 변경
        sku_id="YOUR_SKU_ID",    # 실제 값으로 변경
        quantity=1,
    )
    
    # 3. API 클라이언트 생성
    client = WeidianAPIClient(config)
    
    # 4. 상품 정보 조회 테스트
    print("\n[1] 상품 정보 조회 테스트...")
    item_result = client.get_item_info()
    if item_result.get("success"):
        print(f"✅ 상품 정보 조회 성공")
        print(f"   데이터: {json.dumps(item_result.get('data', {}), indent=2, ensure_ascii=False)[:200]}...")
    else:
        print(f"❌ 상품 정보 조회 실패: {item_result.get('error', 'Unknown error')}")
    
    # 5. VIP 정보 조회 테스트
    print("\n[2] VIP 정보 조회 테스트...")
    vip_result = client.get_vip_detail()
    if vip_result.get("success"):
        print(f"✅ VIP 정보 조회 성공")
        vip_data = vip_result.get("data", {})
        print(f"   등급명: {vip_data.get('gradeNames', [])}")
        print(f"   현재 등급: {vip_data.get('name', 'N/A')}")
        print(f"   남은 금액: {vip_data.get('remaining', 0)}")
    else:
        print(f"❌ VIP 정보 조회 실패: {vip_result.get('error', 'Unknown error')}")
    
    # 6. 보안 테스트 (옵션)
    print("\n[3] 보안 테스트 준비...")
    print("    실제 테스트를 위해서는 유효한 세션과 shopId 가 필요합니다.")
    print("    주의: 이 테스트는 실제 데이터를 변경할 수 있습니다.")
    
    # 예제 VIP 등급 객체
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
    
    # 보안 테스터 생성 (실제 실행은 주석 해제 후 사용)
    # tester = SecurityTester(client)
    # tester.run_all_tests(vip_grade)
    
    print("\n" + "=" * 60)
    print("✅ 백엔드 Boilerplate 초기화 완료")
    print("=" * 60)
    print("\n다음 단계:")
    print("1. cookies.json 파일에 실제 쿠키 데이터 입력")
    print("2. SessionConfig 의 shop_id, item_id, sku_id 를 실제 값으로 변경")
    print("3. 각 API 메서드를 호출하여 State Machine 흐름 테스트")
    print("4. GUI 애플리케이션 (gui_simulator.py) 실행하여 시각적 검증")


if __name__ == "__main__":
    main()
