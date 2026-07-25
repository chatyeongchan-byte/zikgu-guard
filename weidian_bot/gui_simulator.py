#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weidian H5 Web Simulator - 하이브리드 시각적 검증 GUI
CustomTkinter + Playwright 통합 프로토타입

기능:
1. 세션 쿠키 로드 및 관리
2. VIP 등급 선택 및 변경
3. Playwright 를 통한 모바일 결제 페이지 렌더링
4. 시각적 할인 적용 여부 검증
"""

import asyncio
import json
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import customtkinter as ctk
from playwright.async_api import async_playwright

# 백엔드 API 클라이언트 임포트
from backend_api_client import (
    WeidianAPIClient,
    SessionConfig,
    VIPGrade,
    load_cookies_from_file,
    save_to_manifest,
    load_from_manifest,
    BASE_URL,
)


# =============================================================================
# GUI 설정
# =============================================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class VisualVerifier:
    """Playwright 기반 시각적 검증기"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    async def initialize(self):
        """Playwright 초기화"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # 시각적 검증을 위해 창 표시
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--user-agent=Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 375, 'height': 812},  # 모바일 뷰포트
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        
        self.page = await self.context.new_page()
    
    async def navigate_to_payment(self, url: str, cookies: Optional[Dict[str, str]] = None):
        """결제 페이지로 이동"""
        if not self.page:
            await self.initialize()
        
        # 쿠키 설정
        if cookies:
            cookie_list = [
                {"name": k, "value": v, "domain": ".weidian.com", "path": "/"}
                for k, v in cookies.items()
            ]
            await self.context.add_cookies(cookie_list)
        
        # 페이지 이동
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
        
        # 스크린샷 촬영 (옵션)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshot_{timestamp}.png"
        await self.page.screenshot(path=screenshot_path, full_page=True)
        
        return screenshot_path
    
    async def extract_payment_info(self) -> Dict[str, Any]:
        """결제 페이지에서 정보 추출"""
        if not self.page:
            return {}
        
        # JavaScript 를 통해 페이지 데이터 추출
        payment_data = await self.page.evaluate("""
            () => {
                const data = {
                    title: document.querySelector('.payment-title')?.textContent || '',
                    originalPrice: document.querySelector('.original-price')?.textContent || '',
                    discountedPrice: document.querySelector('.discounted-price')?.textContent || '',
                    vipDiscount: document.querySelector('.vip-discount')?.textContent || '',
                    finalPrice: document.querySelector('.final-price')?.textContent || '',
                    gradeName: document.querySelector('.vip-grade-name')?.textContent || '',
                };
                return data;
            }
        """)
        
        return payment_data
    
    async def close(self):
        """브라우저 닫기"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None


class WeidianSimulatorGUI(ctk.CTk):
    """Weidian 시뮬레이터 GUI 메인 클래스"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Weidian H5 Web Simulator & VIP Automation Bot v1.2")
        self.geometry("900x700")
        
        # 상태 변수
        self.api_client: Optional[WeidianAPIClient] = None
        self.verifier = VisualVerifier()
        self.current_vip_grade: Optional[VIPGrade] = None
        self.cookies: Dict[str, str] = {}
        
        # UI 구성
        self._setup_ui()
        
        # 로그 콘솔용 텍스트 위젯 저장
        self.log_console = None
    
    def _setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 헤더
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="🌐 Weidian H5 Web Simulator & VIP Automation Bot",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        version_label = ctk.CTkLabel(
            header_frame,
            text="문서 버전: v1.2 | 하이브리드 시각적 검증 프로토타입",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        version_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        
        # 컨트롤 패널
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_rowconfigure(4, weight=1)
        
        # 1. 세션 로드 섹션
        session_frame = ctk.CTkLabelFrame(control_frame, text="📁 세션 관리", padx=10, pady=10)
        session_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        session_frame.grid_columnconfigure(1, weight=1)
        
        self.btn_load_cookies = ctk.CTkButton(
            session_frame,
            text="쿠키 파일 로드",
            command=self._load_cookies,
            width=150,
        )
        self.btn_load_cookies.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.lbl_cookie_status = ctk.CTkLabel(
            session_frame,
            text="상태: 쿠키 없음",
            text_color="orange",
        )
        self.lbl_cookie_status.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # 2. 상점/상품 정보 입력
        info_frame = ctk.CTkLabelFrame(control_frame, text="🏪 상점/상품 정보", padx=10, pady=10)
        info_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        info_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(info_frame, text="Shop ID:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_shop_id = ctk.CTkEntry(info_frame, width=200, placeholder_text="예: 123456789")
        self.entry_shop_id.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(info_frame, text="Item ID:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_item_id = ctk.CTkEntry(info_frame, width=200, placeholder_text="예: 987654321")
        self.entry_item_id.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(info_frame, text="SKU ID:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.entry_sku_id = ctk.CTkEntry(info_frame, width=200, placeholder_text="예: 111222333")
        self.entry_sku_id.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        self.btn_save_info = ctk.CTkButton(
            info_frame,
            text="정보 저장",
            command=self._save_info,
            width=150,
        )
        self.btn_save_info.grid(row=3, column=0, columnspan=2, padx=5, pady=10)
        
        # 3. VIP 등급 섹션
        vip_frame = ctk.CTkLabelFrame(control_frame, text="⭐ VIP 등급 관리", padx=10, pady=10)
        vip_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        vip_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(vip_frame, text="등급 선택:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        
        self.grade_var = ctk.StringVar(value="일반")
        self.grade_dropdown = ctk.CTkOptionMenu(
            vip_frame,
            values=["일반", "VIP", "VVIP", "플래티넘"],
            variable=self.grade_var,
            width=200,
        )
        self.grade_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        self.lbl_vip_status = ctk.CTkLabel(
            vip_frame,
            text="상태: 조회 필요",
            text_color="orange",
        )
        self.lbl_vip_status.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        # 4. 액션 버튼
        action_frame = ctk.CTkFrame(control_frame)
        action_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        action_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.btn_query_vip = ctk.CTkButton(
            action_frame,
            text="🔍 VIP 정보 조회",
            command=self._query_vip_info,
            height=40,
        )
        self.btn_query_vip.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.btn_apply_grade = ctk.CTkButton(
            action_frame,
            text="⭐ 등급 변경 적용",
            command=self._apply_vip_grade,
            fg_color="#28a745",
            hover_color="#218838",
            height=40,
        )
        self.btn_apply_grade.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.btn_verify_payment = ctk.CTkButton(
            action_frame,
            text="💳 결제 창 확인",
            command=self._verify_payment_window,
            fg_color="#007bff",
            hover_color="#0056b3",
            height=40,
        )
        self.btn_verify_payment.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        # 5. 로그 콘솔
        log_frame = ctk.CTkLabelFrame(control_frame, text="📋 로그 콘솔", padx=10, pady=10)
        log_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=10)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.log_console = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.log_console.grid(row=0, column=0, sticky="nsew")
        
        # 초기 로그
        self._log("✅ GUI 초기화 완료")
        self._log("ℹ️  쿠키 파일을 로드하여 시작하세요.")
    
    def _log(self, message: str):
        """로그 콘솔에 메시지 추가"""
        if self.log_console:
            self.log_console.configure(state="normal")
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_console.insert("end", f"[{timestamp}] {message}\n")
            self.log_console.see("end")
            self.log_console.configure(state="disabled")
    
    def _load_cookies(self):
        """쿠키 파일 로드"""
        filepath = filedialog.askopenfilename(
            title="쿠키 파일 선택",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                self.cookies = load_cookies_from_file(filepath)
                if self.cookies:
                    self.lbl_cookie_status.configure(
                        text=f"상태: {len(self.cookies)}개 쿠키 로드됨",
                        text_color="green"
                    )
                    self._log(f"✅ 쿠키 파일 로드 성공: {len(self.cookies)}개 쿠키")
                    
                    # manifest 에 저장
                    save_to_manifest({"cookies_loaded_at": datetime.now().isoformat()})
                else:
                    self.lbl_cookie_status.configure(
                        text="상태: 쿠키 파일이 비어있음",
                        text_color="red"
                    )
                    self._log("⚠️  쿠키 파일이 비어있습니다.")
            except Exception as e:
                self.lbl_cookie_status.configure(
                    text="상태: 로드 오류",
                    text_color="red"
                )
                self._log(f"❌ 쿠키 로드 실패: {str(e)}")
    
    def _save_info(self):
        """상점/상품 정보 저장"""
        shop_id = self.entry_shop_id.get().strip()
        item_id = self.entry_item_id.get().strip()
        sku_id = self.entry_sku_id.get().strip()
        
        if not shop_id:
            messagebox.showwarning("경고", "Shop ID 는 필수입니다.")
            return
        
        # 세션 설정 저장
        config = SessionConfig(
            cookies=self.cookies,
            shop_id=shop_id,
            item_id=item_id,
            sku_id=sku_id,
        )
        
        self.api_client = WeidianAPIClient(config)
        
        # manifest 에 저장
        save_to_manifest({
            "shop_id": shop_id,
            "item_id": item_id,
            "sku_id": sku_id,
            "info_saved_at": datetime.now().isoformat(),
        })
        
        self._log(f"✅ 상점/상품 정보 저장 완료")
        self._log(f"   Shop ID: {shop_id}")
        self._log(f"   Item ID: {item_id or 'N/A'}")
        self._log(f"   SKU ID: {sku_id or 'N/A'}")
    
    def _query_vip_info(self):
        """VIP 정보 조회"""
        if not self.api_client:
            messagebox.showwarning("경고", "먼저 상점 정보를 저장하세요.")
            return
        
        self._log("🔄 VIP 정보 조회 중...")
        
        try:
            result = self.api_client.get_vip_detail()
            
            if result.get("success"):
                vip_data = result.get("data", {})
                
                grade_names = vip_data.get("gradeNames", [])
                current_name = vip_data.get("name", "N/A")
                remaining = vip_data.get("remaining", 0)
                
                self.current_vip_grade = VIPGrade(
                    shop_id=self.api_client.config.shop_id,
                    grade_names=grade_names,
                    name=current_name,
                    server_index=vip_data.get("serverIndex", 0),
                    grade_count=vip_data.get("gradeCount", 0),
                    remaining=remaining,
                    original_progress=vip_data.get("originalProgress", 0),
                )
                
                # 드롭다운 업데이트
                if grade_names:
                    self.grade_dropdown.configure(values=grade_names)
                    self.grade_var.set(grade_names[0])
                
                self.lbl_vip_status.configure(
                    text=f"상태: 현재 등급 '{current_name}' | 남은 금액: {remaining}",
                    text_color="green"
                )
                
                self._log(f"✅ VIP 정보 조회 성공")
                self._log(f"   등급명: {grade_names}")
                self._log(f"   현재 등급: {current_name}")
                self._log(f"   남은 금액: {remaining}")
            else:
                error_msg = result.get("error", "알 수 없는 오류")
                self.lbl_vip_status.configure(
                    text=f"상태: 조회 실패",
                    text_color="red"
                )
                self._log(f"❌ VIP 정보 조회 실패: {error_msg}")
        
        except Exception as e:
            self.lbl_vip_status.configure(
                text="상태: 오류 발생",
                text_color="red"
            )
            self._log(f"❌ VIP 정보 조회 중 오류: {str(e)}")
    
    def _apply_vip_grade(self):
        """VIP 등급 변경 적용"""
        if not self.api_client:
            messagebox.showwarning("경고", "먼저 상점 정보를 저장하세요.")
            return
        
        if not self.current_vip_grade:
            messagebox.showwarning("경고", "먼저 VIP 정보를 조회하세요.")
            return
        
        selected_grade = self.grade_var.get()
        
        self._log(f"🔄 VIP 등급 변경 적용 중: {selected_grade}")
        
        try:
            # targetIndex 계산
            grade_names = self.current_vip_grade.grade_names
            target_index = grade_names.index(selected_grade) if selected_grade in grade_names else 0
            
            # VIP 등급 객체 업데이트
            self.current_vip_grade.target_index = target_index
            self.current_vip_grade.name = selected_grade
            
            # TODO: 실제 API 호출 구현
            # result = self.api_client.save_vip_settings(self.current_vip_grade)
            
            # 데모용 응답 (실제 구현시 주석 해제)
            result = {
                "success": True,
                "data": {
                    "message": f"등급이 '{selected_grade}' 로 변경되었습니다.",
                    "targetIndex": target_index,
                }
            }
            
            if result.get("success"):
                self.lbl_vip_status.configure(
                    text=f"상태: 변경됨 '{selected_grade}' (index: {target_index})",
                    text_color="green"
                )
                self._log(f"✅ VIP 등급 변경 성공: {selected_grade}")
                self._log(f"   targetIndex: {target_index}")
                
                messagebox.showinfo("성공", f"VIP 등급이 '{selected_grade}' 로 변경되었습니다.")
            else:
                error_msg = result.get("error", "알 수 없는 오류")
                self._log(f"❌ VIP 등급 변경 실패: {error_msg}")
                messagebox.showerror("실패", f"등급 변경에 실패했습니다: {error_msg}")
        
        except Exception as e:
            self._log(f"❌ VIP 등급 변경 중 오류: {str(e)}")
            messagebox.showerror("오류", f"등급 변경 중 오류가 발생했습니다: {str(e)}")
    
    async def _async_apply_and_verify(self):
        """비동기: 등급 변경 후 결제 창 검증"""
        if not self.api_client:
            return
        
        try:
            # 결제 URL 생성 (데모용)
            payment_url = f"{BASE_URL}/pay-h5/cashier/index?shopId={self.api_client.config.shop_id}"
            
            self._log(f"🔄 결제 페이지 로드 중: {payment_url}")
            
            # Playwright 로 페이지 열기
            await self.verifier.initialize()
            screenshot_path = await self.verifier.navigate_to_payment(payment_url, self.cookies)
            
            # 정보 추출
            payment_info = await self.verifier.extract_payment_info()
            
            self._log(f"✅ 결제 페이지 정보 추출 완료")
            self._log(f"   스크린샷: {screenshot_path}")
            
            if payment_info:
                self._log(f"   제목: {payment_info.get('title', 'N/A')}")
                self._log(f"   원래 가격: {payment_info.get('originalPrice', 'N/A')}")
                self._log(f"   할인 후 가격: {payment_info.get('discountedPrice', 'N/A')}")
                self._log(f"   VIP 할인: {payment_info.get('vipDiscount', 'N/A')}")
            
            await self.verifier.close()
            
        except Exception as e:
            self._log(f"❌ 결제 창 검증 중 오류: {str(e)}")
    
    def _verify_payment_window(self):
        """결제 창 확인 (Playwright)"""
        if not self.api_client:
            messagebox.showwarning("경고", "먼저 상점 정보를 저장하세요.")
            return
        
        self._log("🔄 결제 창 검증 시작...")
        
        # 비동기 함수를 별도 스레드에서 실행
        import threading
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_apply_and_verify())
            loop.close()
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        
        self._log("ℹ️  브라우저 창이 열립니다. 시각적 검증을 진행하세요.")
    
    def on_closing(self):
        """앱 종료 처리"""
        if self.verifier.browser:
            asyncio.get_event_loop().run_until_complete(self.verifier.close())
        self.destroy()


def main():
    """메인 실행 함수"""
    app = WeidianSimulatorGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
